from jaf.pipeline.base import Pipeline
from jaf.pipeline.type import PipelineTypeEnum
from jaf.pipeline.code.fdep.base import FDepBase
from jaf.types import Query
import jaf.pipeline.code.fdep.utils as utils
import json
import traceback
import re
import os
import subprocess
import shutil
from threading import Timer
from textwrap import wrap

class FDepRustMigrationPipeline(FDepBase, Pipeline):
    def __init__(self, files: dict, ignore_infix_regex = None, module_name = None, skip_module_patterns = []) -> None:
        self.prompt_limit = 16000
        self.pre_hooks = []
        self.post_hooks = []
        self.types = {}
        self.extra_deps = {}
        self.comments_data = {}
        self.package = {}
        self.lines_map = {}
        self.types = {}
        self.types_data = {}
        self.dependencies_data = {}
        self.rust_errors = {}
        self.extra_errors = []
        self.files = files
        self.skip_module_patterns = skip_module_patterns
        self.__load_data_from_files()
        self.__load_types_graph()

        FDepBase.__init__(self, files["data_json"], ignore_infix_regex, module_name)
        Pipeline.__init__(self, PipelineTypeEnum.RUST_MIGRATION_PIPELINE)

    def __load_data_from_files(self):
        with open(self.files["code_comment"], 'r') as file:
            try:
                self.comments_data = json.load(file)
            except json.JSONDecodeError:
                self.comments_data = {}
            file.close()

        with open(self.files["types"], 'r') as file:
            self.types_data = json.load(file)

        with open(self.files["dependencies"], 'r') as file:
            self.dependencies_data = json.load(file)

    def __is_storage_module(self, module: str) -> bool:
        return bool(re.match(r'^\w+\.Types\.Storage\.\w+$', module))
    
    def __load_types_graph(self):
        for mod, types_map in self.types_data.items():
            for name, data in types_map.items():
                if self.__is_storage_module(mod):
                    if bool(re.match(r'type \w+ = \w+T Identity', data["stringified_code"])):
                        continue
                    elif bool(re.match(r'data \w+T f = .*', data["stringified_code"])):
                        name = name[:-1]
                        data["name"] = name
                        data["stringified_code"] = re.sub("T f = ", " = ", data["stringified_code"])
                        data["stringified_code"] = re.sub(" :: B.C f ", " :: ", data["stringified_code"])
                node = f'{mod}->-{name}'
                self.types[node] = {
                    "data": data,
                    "edges": []
                }
        for node, data in self.types.items():
            split = node.split("->-")
            mod = split[0]
            name = split[1]
            if mod not in self.dependencies_data or name not in self.dependencies_data[mod]:
                continue
            dependencies = self.dependencies_data[mod][name]
            name_t = name + "T"
            if self.__is_storage_module(mod) and name_t in self.dependencies_data[mod]:
                dependencies = self.dependencies_data[mod][name_t]
            for dep in dependencies:
                if self.__is_storage_module(dep["module"]) and bool(re.match(r'^\w+T$', dep["name"])):
                    dep["name"] = dep["name"][:-1]
                edge = f'{dep["module"]}->-{dep["name"]}'
                data["edges"].append(self.types[edge])
        for mod, types_map in self.dependencies_data.items():
            for name, data in types_map.items():
                node = f'{mod}->-{name}'
                if not self.__check_valid_node(node):
                    continue
                for dep in data:
                    if self.__is_storage_module(dep["module"]) and bool(re.match(r'^\w+T$', dep["name"])):
                        dep["name"] = dep["name"][:-1]
                self.extra_deps[node] = list(map(lambda e: self.types[f'{e["module"]}->-{e["name"]}'], data))

    def validate_pipe(self):
        return True

    def what_to_do(self, text:str) -> None:
        self.system_prompt = text

    def when_to_do(self, text:str) -> None:
        self.system_prompt_instructions = text
    
    def __run_pipeline(self, query:Query, **kwargs) -> Query:   
        query.system_prompt = self.system_prompt
        return Pipeline.__call__(self, query, **kwargs)

    def __call__(self, query:Query, **kwargs) -> Query:
        return self.__run_pipeline(query, **kwargs)
    
    def __check_valid_node(self, node):
        names = node.split("->-")
        if node.startswith("_") or node.startswith("$"):
            return 0
        elif "None" in names:
            return 0
        elif node not in self.comments_data:
            return 0
        else:
            return 1
    
    def __snake_case(self, name: str) -> str:
        res = ""
        for i in range(0, len(name)):
            if name[i].isupper() and i > 0 and (name[i-1].islower() or (i + 1 < len(name) and name[i + 1].islower())):
                res += '_'
            res += name[i].lower()
        if res == "type":
            res = "r#type"
        return res

    def __mk_node(self, node: dict) -> str:
        return f'{node["data"]["module"]}->-{node["data"]["name"]}'

    def __mk_crate(self, module: str) -> str:
        return "crate::" + "::".join(map(lambda x: self.__snake_case(x), module.split(".")))

    def __refresh_helper_types(self, node):
        comments = self.comments_data[node]
        comments["helper_types"] = []
        if node in self.extra_deps:
            for edge in self.extra_deps[node]:
                crate = self.__mk_crate(edge["data"]["module"])
                name = edge["data"]["name"]
                helper_type = {
                    "crate": f'{crate}::{name}'
                }
                try:
                    helper_type["code"] = next(filter(lambda c: c["type"] == "type" and c["name"] == name, self.package[crate]["content"]))["code"]
                except:
                    pass
                comments["helper_types"].append(helper_type)

    def __format(self, node) -> dict:
        comments = self.comments_data[node]
        if "name" in comments:
            self.__refresh_helper_types(node)
            return comments
        split = node.split("->-")
        hs_name = split[-1]
        hs_module = split[0]
        rs_name = self.__snake_case(hs_name)
        rs_module = self.__mk_crate(hs_module)
        comments["name"] = rs_name
        comments["module"] = rs_module
        self.__refresh_helper_types(node)
        if rs_module in self.package:
            try:
                fn_data = next(filter(lambda c: c["name"] == rs_name, self.package[rs_module]["content"]))
                comments["rust_signature"] = fn_data["code"].split("{")[0]
            except:
                pass
        return comments

    def __limit_prompt_length(self, system_prompt, proper_prompt):
        system_prompt_len = len(system_prompt)
        total_prompt_len = system_prompt_len + len(proper_prompt)
        if total_prompt_len > self.prompt_limit:
            clip_len = self.prompt_limit - system_prompt_len
            proper_prompt = proper_prompt[:clip_len]
        return (system_prompt, proper_prompt)

    def __generate_prompt_for_fn(self, node, descendants):
        system_prompt = utils.RUST_MIGRATION_SYSTEM_PROMPT
        description = self.__format(node)
        proper_prompt = utils.RUST_MIGRATION_MAIN_FN_PROMPT.format(FUNCTION_DESCRIPTION = json.dumps(description))
        if len(descendants) != 0:
            helper_func_string = ""
            for desc_node in descendants:
                if not self.__check_valid_node(desc_node):
                    continue
                hf_formatted = f"\n{utils.RUST_MIGRATION_HELPER_FN_PROMPT.format(HELPER_FUNCTION_DESCRIPTION = json.dumps(self.__format(desc_node)))}"
                helper_func_string += hf_formatted
            proper_prompt += helper_func_string
        return self.__limit_prompt_length(system_prompt, proper_prompt)
    
    def __generate_prompt_for_type(self, node):
        system_prompt = utils.RUST_MIGRATION_TYPE_SYSTEM_PROMPT
        description = {
            "stringified_code": node["data"]["stringified_code"],
            "module": self.__mk_crate(node["data"]["module"]),
            "helper_types": list(map(lambda e: f'{self.__mk_crate(e["data"]["module"])}::{e["data"]["name"]}', node["edges"]))
        }
        proper_prompt = utils.RUST_MIGRATION_MAIN_TYPE_PROMPT.format(TYPE_DESCRIPTION = json.dumps(description))
        return self.__limit_prompt_length(system_prompt, proper_prompt)

    def __generate_error_fix_prompt(self, node, descendants, errors):
        system_prompt = utils.RUST_CODE_FN_ERROR_SYSTEM_PROMPT
        data = self.__format(node)
        key = data["module"] + "->-" + data["name"]
        fn_data = next(filter(lambda c: c["name"] == data["name"], self.package[data["module"]]["content"]))
        error = {
            "code": fn_data["code"],
            "error": errors[key]["error"],
            "explanation": errors[key]["explanation"],
            "helper_functions": [],
            "helper_types": data["helper_types"]
        }
        for desc_node in descendants:
            if not self.__check_valid_node(desc_node):
                continue
            helper = {
                "module": self.__format(desc_node)["module"],
                "signature": self.__format(desc_node)["rust_signature"]
            }
            error["helper_functions"].append(helper)
        proper_prompt = json.dumps(error)
        return self.__limit_prompt_length(system_prompt, proper_prompt)

    def __generate_error_fix_prompt_for_type(self, node, errors):
        system_prompt = utils.RUST_CODE_TYPE_ERROR_SYSTEM_PROMPT
        data = node["data"]
        key = self.__mk_crate(data["module"]) + "->-" + data["name"]
        fn_data = next(filter(lambda c: c["name"] == data["name"], self.package[self.__mk_crate(data["module"])]["content"]))
        error = {
            "code": fn_data["code"],
            "error": errors[key]["error"],
            "explanation": errors[key]["explanation"],
            "helper_types": list(map(lambda e: f'{self.__mk_crate(e["data"]["module"])}::{e["data"]["name"]}', node["edges"]))
        }
        proper_prompt = json.dumps(error)
        return self.__limit_prompt_length(system_prompt, proper_prompt)

    def __generate_other_error_fix_prompt(self, error_obj):
        system_prompt = utils.RUST_CODE_OTHER_ERROR_SYSTEM_PROMPT
        error = {
            "snippet": error_obj["snippet"],
            "crate": error_obj["crate"],
            "error": error_obj["error"],
            "explanation": error_obj["explanation"]
        }
        proper_prompt = json.dumps(error)
        return self.__limit_prompt_length(system_prompt, proper_prompt)
    
    def __clean(self, code: str, imports: list) -> str:
        regex = "use [^;]+;"
        imports_code = re.findall(regex, code)
        imports.extend(imports_code)
        return re.sub(f'{regex}(\n*)', "", code)

    def __check_for_skip(self, node: str, code: str) -> str:
        module = node.split("->-")[0]
        if all(map(lambda r: not bool(re.match(r, module)), self.skip_module_patterns)) or len(code.split("{")) < 2:
            return code
        signature = code.split("{")[0]
        comments = self.comments_data[node]["overview"]
        comments = "/// " + "\n/// ".join(wrap(comments, 100))
        unimpl_code = comments + "\n" + signature + "{\n    unimplemented!()\n}"
        return unimpl_code

    def __insert_code(self, response, node_name) -> bool:
        try:
            json_object = json.loads(response)
            module_name = self.comments_data[node_name]["module"]
            if module_name not in self.package:
                self.package[module_name] = {}
                self.package[module_name]["imports"] = []
                self.package[module_name]["content"] = []
            module = self.package[module_name]
            if "import_statements" not in json_object or type(json_object["import_statements"]) is not list:
                json_object["import_statements"] = []
            code = self.__clean(json_object["stringified_code"], json_object["import_statements"])
            code = self.__check_for_skip(node_name, code)
            for import_st in json_object["import_statements"]:
                if not import_st.startswith("use"):
                    import_st = "use " + import_st
                if not import_st.endswith(";"):
                    import_st += ";"
                module["imports"].append(import_st)
            content = {
                "type": "function",
                "code": code,
                "line": int(self.get_position(node_name).split(":")[1]),
                "name": self.comments_data[node_name]["name"]
            }
            found = False
            for index in range(0, len(module["content"])):
                if module["content"][index]["name"] == content["name"]:
                    found = True
                    module["content"][index] = content
            if not found:
                module["content"].append(content)
            self.comments_data[node_name]["rust_signature"] = code.split("{")[0]
            return True
        except Exception:
            traceback.print_exc()
            print("Cannot write: ", node_name,"\nComment: ", response)
            return False

    def __insert_type_code(self, response, node) -> bool:
        try:
            json_object = json.loads(response)
            module_name = self.__mk_crate(node["data"]["module"])
            if module_name not in self.package:
                self.package[module_name] = {
                    "imports": [],
                    "content": []
                }
            module = self.package[module_name]
            if "import_statements" not in json_object or type(json_object["import_statements"]) is not list:
                json_object["import_statements"] = []
            code = self.__clean(json_object["stringified_code"], json_object["import_statements"])
            for import_st in json_object["import_statements"]:
                if not import_st or type(import_st) is not str:
                    continue
                if not import_st.startswith("use"):
                    import_st = "use " + import_st
                if not import_st.endswith(";"):
                    import_st += ";"
                module["imports"].append(import_st)
            content = {
                "type": "type",
                "code": code,
                "line": int(node["data"]["src_loc"].split(":")[1]),
                "name": node["data"]["name"]
            }
            found = False
            for index in range(0, len(module["content"])):
                if module["content"][index]["name"] == content["name"]:
                    found = True
                    module["content"][index] = content
            if not found:
                module["content"].append(content)
            return True
        except Exception:
            traceback.print_exc()
            print("Cannot write: ", node["data"]["name"],"\nComment: ", response)
            return False

    def __insert_import_statement(self, response, error) -> bool:
        try:
            json_object = json.loads(response)
            code = json_object["stringified_code"]
            module_name = error["crate"]
            import_st = error["snippet"]
            if module_name not in self.package:
                return
            module = self.package[module_name]
            for index in range(0, len(module["imports"])):
                if module["imports"][index] == import_st:
                    module["imports"][index] = code
                    break
        except Exception:
            traceback.print_exc()
            print("Cannot write: ", error["crate"], error["snippet"], "\nComment: ", response)
            return False

    def __call_llm_and_insert(self, llm, system_prompt, proper_prompt, node_name) -> bool:
        print("Calling LLM for node: ", node_name)
        try:
            node_success = False
            for _ in range(10):
                ans = llm.call_llm(system_message=system_prompt, user_message=proper_prompt, response_format="json_object")
                print("Prompt Called: ", proper_prompt)
                response = ans.choices[0].message.content
                print("CODE GENERATED: ", response)
                if self.__insert_code(response, node_name):
                    node_success = True
                    break
            if not node_success:
                print("Unable to Write: ", node_name)
            else:
                print("Insert Successful: ", node_name)
            return node_success
        except Exception:
            traceback.print_exc()
            print("LLM Call Failed")
            return False

    def __call_llm_and_insert_for_type(self, llm, system_prompt, proper_prompt, node) -> bool:
        print("Calling LLM for node: ", self.__mk_node(node))
        try:
            node_success = False
            for _ in range(10):
                ans = llm.call_llm(system_message=system_prompt, user_message=proper_prompt, response_format="json_object")
                print("Prompt Called: ", proper_prompt)
                response = ans.choices[0].message.content
                print("CODE GENERATED: ", response)
                if self.__insert_type_code(response, node):
                    node_success = True
                    break
            if not node_success:
                print("Unable to Write: ", self.__mk_node(node))
            else:
                print("Insert Successful: ", self.__mk_node(node))
            return node_success
        except Exception:
            traceback.print_exc()
            print("LLM Call Failed")
            return False

    def __call_llm_and_insert_extra_errors(self, llm, system_prompt, proper_prompt, error):
        try:
            for _ in range(10):
                ans = llm.call_llm(system_message=system_prompt, user_message=proper_prompt, response_format="json_object")
                print("Prompt Called: ", proper_prompt)
                response = ans.choices[0].message.content
                print("CODE GENERATED: ", response)
                if error["type"] == "import":
                    self.__insert_import_statement(response, error)
                    break
            return True
        except Exception:
            traceback.print_exc()
            print("LLM Call Failed for: ", error)
            return False
        
    def dump_to_file(self):
        rust = {}
        package_json = {}
        for k, v in self.package.items():
            package_json[k] = {"imports": list(set(v["imports"])), "content": v["content"]}
        rust = package_json

        with open(self.files["rust_data"], 'w') as file:
            json.dump(rust, file, indent=4)
            file.close()

    def __load_data(self, path):
        data = {}
        with open(path, 'r') as file:
            data = json.load(file)
        return data

    def __rmtree(self, path):
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
            later = Timer(2, self.__rmtree, (path,))
            later.start()

    def __cargo_new(self, base, name):
        if not os.path.exists(base):
            os.makedirs(base)
        os.chdir(base)
        self.__rmtree(name)
        while os.path.exists(name):
            pass
        subprocess.run(["cargo", "new", name])
        os.chdir(name)

    def __cargo_add(self, libraries):
        for library in libraries:
            try:
                subprocess.run(["cargo", "add", library])
            except:
                print("Invalid library: ", library)    

    def __record_lines(self, snippet_type, snippet, identifier, total_lines, lines_list) -> int:
        code_lines = snippet.count("\n")
        entry = {
            "type": snippet_type,
            "identifier": identifier,
            "start": total_lines + 1,
            "end": total_lines + code_lines
        }
        lines_list.append(entry)
        total_lines += code_lines
        return total_lines

    def __collect_external_crates(self):
        crates = set()
        for _, pieces in self.package.items():
            for import_st in pieces["imports"]:
                if not bool(re.search(r'use .*;', import_st)):
                    continue
                crate = import_st[4:-1].split("::")[0]
                if crate not in ["std", "crate", "super", "derive_more"]:
                    crates.add(crate)
        return list(crates)

    def __add_node(self, node: str, includes: bool, tree: dict) -> dict:
        node = node.strip()
        if node:
            if node not in tree:
                tree[node] = {
                    "includes": includes,
                    "child": {}
                }
            return tree[node]["child"]
        else:
            return tree

    def __insert_import_to_tree(self, import_st: str, tree: dict):
        if not bool(re.search(r'use .*;', import_st)):
            return
        stmt = import_st[4:-1]
        stack = []
        stack.append(tree)
        node = ""
        index = 0
        top = tree
        while index < len(stmt):
            if stmt[index] == ':' and index + 1 < len(stmt) and stmt[index + 1] == ':':
                top = self.__add_node(node, False, top)
                node = ""
                index += 2
            elif stmt[index] == '{':
                top = self.__add_node(node, False, top)
                node = ""
                stack.append(top)
                index += 1
            elif stmt[index] == '}':
                self.__add_node(node, True, top)
                node = ""
                top = stack.pop()
                index += 1
            elif stmt[index] == ',':
                self.__add_node(node, True, top)
                node = ""
                top = stack[-1]
                index += 1
                while index < len(stmt) and stmt[index] == ' ':
                    index += 1
            else:
                node += stmt[index]
                index += 1
        self.__add_node(node, True, top)

    def __traverse_tree(self, path: str, tree: dict, result: list):
        for mod, info in tree.items():
            path_to = path + mod
            if info["includes"]:
                result.append(f'use {path_to};')
            path_to += "::"
            self.__traverse_tree(path_to, info["child"], result)

    def __dedup_import_statements(self, imports: list) -> dict:
        tree = {}
        for import_st in imports:
            self.__insert_import_to_tree(import_st, tree)
        result = []
        self.__traverse_tree("", tree, result)
        return result

    def __process_modules(self, package) -> tuple[dict, str]:
        mods = {}
        main_file = ""
        for module, pieces in self.package.items():
            path_arr =    ["src"] + module.split("::")[1:]
            mod_path = ""
            for edge in path_arr:
                if not mod_path:
                    mod_path = edge
                    continue
                if mod_path != "src" or edge != "main":
                    if mod_path not in mods:
                        mods[mod_path] = set()
                    mods[mod_path].add(edge)
                mod_path = mod_path + f"/{edge}"
            mod_path = mod_path + ".rs"
            mod_path = re.sub("r#type", "type", mod_path)
            self.lines_map[mod_path] = []
            total_lines = 0
            folder = "/".join(path_arr[:-1])
            if folder and not os.path.exists(folder):
                os.makedirs(folder)
            code = ""
            pieces["imports"] = self.__dedup_import_statements(pieces["imports"])
            for import_st in pieces["imports"]:
                if not import_st.startswith(f"use {module}"):
                    snippet = f"{import_st}\n"
                    code += snippet
                    total_lines = self.__record_lines("import", snippet, module + "->-" + import_st, total_lines, self.lines_map[mod_path])
            pieces["content"].sort(key=lambda ct: ct["line"])
            for item in pieces["content"]:
                snippet = f'\n{item["code"]}\n'
                code += snippet
                total_lines = self.__record_lines(item["type"], snippet, module + "->-" + item["name"], total_lines, self.lines_map[mod_path])
            if mod_path == "src/main.rs":
                main_file = code
            else:
                with open(mod_path, 'w') as file:
                    file.write(code)
        return (mods, main_file)

    def __shift_lines_position(self, file_loc, total_lines) -> int:
        if not file_loc in self.lines_map:
            return
        for item in self.lines_map[file_loc]:
            item["start"] += total_lines
            item["end"] += total_lines

    def __create_module_files(self, mods, main_file):
        for file, mod_list in mods.items():
            file_loc = file
            if file == "src":
                file_loc = file_loc + "/main.rs"
            else:
                file_loc = file_loc + "/mod.rs"
            total_lines = 0
            content = ""
            mod_list = list(set(mod_list))
            mod_list.sort()
            for item in mod_list:
                snippet = ""
                if content:
                    snippet = "\n"
                if item == "type":
                    item = "r#type"
                snippet = snippet + f"pub mod {item};"
                content = content + snippet
                total_lines += snippet.count("\n")
            with open(file_loc, 'w') as file:
                file.write(content)
                if file_loc == "src/main.rs" and main_file:
                    file.write("\n")
                    file.write(main_file)
                    total_lines += 1
                    self.__shift_lines_position(file_loc, total_lines)

    def __setup_config(self):
        with open("rustfmt.toml", "w") as file:
            file.write("edition = \"2021\"\ntab_spaces = 4")

    def __write_line_map_to_file(self):
        with open(self.files["lines_map"], 'w') as file:
            json.dump(self.lines_map, file, indent=4)

    def process_package(self):
        code_json = self.__load_data(self.files["rust_data"])
        self.__cargo_new(self.files["rs_base"], self.files["package_name"])
        self.__setup_config()
        crates = self.__collect_external_crates()
        self.__cargo_add(crates)
        mods, main_file = self.__process_modules(code_json)
        self.__create_module_files(mods, main_file)
        self.__write_line_map_to_file()
        print("Package Created")
    
    def __decr_line_num(self, message, path, start):
        regex = f"{path}:\\d*:\\d*"
        matches = re.findall(regex, message)
        for match_r in matches:
            split = match_r.split(":")
            split[1] = str(int(split[1]) - start)
            message.replace(match_r, ":".join(split))
        return message
    
    def __dfs_fix(self, llm, node, visited) -> bool:
        is_valid = self.__check_valid_node(node)
        if not is_valid:
            return
        if node in visited:
            return visited[node]
        visited[node] = False
        dirty = False
        descendants = self.get_all_decendants(node)
        if node in self.extra_deps:
            for child in self.extra_deps[node]:
                dirty = self.__dfs_fix_types(llm, child, visited) or dirty
        for child in descendants:
            dirty = self.__dfs_fix(llm, child, visited) or dirty
        data = self.__format(node)
        errors_key = data["module"] + "->-" + data["name"]
        if dirty or errors_key not in self.rust_errors:
            visited[node] = dirty
            return dirty
        system_prompt, proper_prompt = self.__generate_error_fix_prompt(node, descendants, self.rust_errors)
        if not self.__call_llm_and_insert(llm, system_prompt, proper_prompt, node):
            # TODO: Add to some failed_nodes list
            print("Fix failed for: ", node)
        visited[node] = True 
        return True

    def __dfs_fix_types(self, llm, node, visited) -> bool:
        if self.__mk_node(node) in visited:
            return visited[self.__mk_node(node)]
        visited[self.__mk_node(node)] = False
        dirty = False
        descendants = node["edges"]
        for child in descendants:
            dirty = self.__dfs_fix_types(llm, child, visited) or dirty
        data = node["data"]
        errors_key = self.__mk_crate(data["module"]) + "->-" + data["name"]
        if dirty or errors_key not in self.rust_errors:
            visited[self.__mk_node(node)] = dirty
            return dirty
        system_prompt, proper_prompt = self.__generate_error_fix_prompt_for_type(node, self.rust_errors)
        if not self.__call_llm_and_insert_for_type(llm, system_prompt, proper_prompt, node):
            # TODO: Add to some failed_nodes list
            print("Fix failed for: ", errors_key)
        visited[self.__mk_node(node)] = True
        return True

    def __fetch_component(self, path, line) -> dict:
        if path not in self.lines_map:
            return None
        lines_list = self.lines_map[path]
        for entry in lines_list:
            if entry["start"] <= line and line <= entry["end"]:
                return entry
            elif entry["start"] > line:
                return None
        return None

    def __process_extra_errors(self, llm):
        for error in self.extra_errors:
            system_prompt, proper_prompt = self.__generate_other_error_fix_prompt(error)
            self.__call_llm_and_insert_extra_errors(llm, system_prompt, proper_prompt, error)

    def __process_function_errors(self, llm, visited: dict):
        for node in self.functional_graph.nodes:
            if node not in visited:
                self.__dfs_fix(llm, node, visited)

    def __process_types_errors(self, llm, visited: dict):
        for name, node in self.types.items():
            if name not in visited:
                self.__dfs_fix_types(llm, node, visited)
        
    def __fix_errors(self, llm):
        logs = []
        with open(self.files["logs"]) as file:
            logs = list(filter(lambda x: x.startswith("{"), file.read().split("\n")))
        for log_str in logs:
            log = json.loads(log_str)
            if "message" not in log or log["message"]["level"] != "error" or not log["message"]["spans"]:
                continue
            line = log["message"]["spans"][0]["line_start"]
            path = log["message"]["spans"][0]["file_name"]
            component = self.__fetch_component(path, line)
            if not component:
                continue
            if component["type"] in ["function", "type"]:
                key = component["identifier"]
                if key in self.rust_errors:
                    continue
                self.rust_errors[key] = {
                    "error": self.__decr_line_num(log["message"]["rendered"], path, component["start"]),
                    "explanation": None
                }
                if "code" in log["message"] and log["message"]["code"]:
                    self.rust_errors[key]["explanation"] = log["message"]["code"]["explanation"]
            else:
                split = component["identifier"].split("->-")
                error = {
                    "snippet": split[1],
                    "crate": split[0],
                    "error": self.__decr_line_num(log["message"]["rendered"], path, component["start"]),
                    "type": component["type"],
                    "explanation": None
                }
                if "code" in log["message"] and log["message"]["code"]:
                    error["explanation"] = log["message"]["code"]["explanation"]
                self.extra_errors.append(error)
        visited = {}
        self.__process_extra_errors(llm)
        self.__process_types_errors(llm, visited)
        self.__process_function_errors(llm, visited)

    def __check_build(self) -> bool:
        os.chdir(self.files["rs_path"])
        with open(self.files["logs"], "w") as file:
            subprocess.run(["cargo", "build", "--message-format=json"], stdout = file)
        success_log = subprocess.check_output(["tail", "-1", self.files["logs"]])
        return json.loads(success_log)["success"]

    def refresh_cache(self):
        with open(self.files["lines_map"]) as file:
            self.lines_map = json.loads(file.read())
        with open(self.files["rust_data"]) as file:
            data = json.loads(file.read())
            self.package = data

    def fix_build(self, llm):
        self.refresh_cache()
        fixed = False
        for _ in range(300):
            self.rust_errors = {}
            self.extra_errors = []
            if self.__check_build():
                fixed = True
                break
            self.__fix_errors(llm)
            self.dump_to_file()
            self.process_package()
            self.dump_to_file()
        if fixed:
            subprocess.run(["cargo", "fmt"])
            print("Build Fixed")
        else:
            print("Build fix failed")
    
    def dfs(self, llm, node: str, visited: set, failed_nodes: list):
        is_valid = self.__check_valid_node(node)
        if not is_valid:
            return

        visited.add(node)
        descendants = self.get_all_decendants(node)

        if node in self.extra_deps:
            for child in self.extra_deps[node]:
                if self.__mk_node(child) not in visited:
                    self.dfs_types(llm, child, visited)

        for child in descendants:
            if child not in visited:
                self.dfs(llm, child, visited, failed_nodes)

        system_prompt, proper_prompt = self.__generate_prompt_for_fn(node, descendants)
        #calling llm to generate comment and insert in data.json file
        if not self.__call_llm_and_insert(llm, system_prompt, proper_prompt, node):
            failed_nodes.append(node)

    def dfs_types(self, llm, node: dict, visited: set):
        visited.add(node["data"]["name"])
        visited.add(self.__mk_node(node))

        for child in node["edges"]:
            if self.__mk_node(child) not in visited:
                self.dfs_types(llm, child, visited)

        system_prompt, proper_prompt = self.__generate_prompt_for_type(node)
        if not self.__call_llm_and_insert_for_type(llm, system_prompt, proper_prompt, node):
            print("Failed Type Migration : ", node)
