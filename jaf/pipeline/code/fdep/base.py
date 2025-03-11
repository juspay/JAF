import re
import os
import json 
import networkx as nx
from typing import Optional, Dict, List, Literal
from collections import deque
from jaf.parser.haskell_treesitter.utils import write_code_snippet_to_file
import traceback

class FDepBase:
    def __init__(self, data_json_path : str, ignore_infix_regex=None, module_name=None) -> None:
        self.functional_graph = nx.DiGraph()
        self.module_fn_binder = "->-"
        self.json_path = data_json_path
        self.module_name = module_name
        self.data = {}
        self.load_functional_graph(data_json_path, ignore_infix_regex)

    def load_functional_graph(self, path:str, ignore_infix_regex=None) -> None:
        self.data = self.__load_fdep_data(path)
        self.__traverse_json(ignore_infix_regex)
        print("functional graph loaded.")

    def __ignore_node_infix(self, regex_pattern:Optional[str], node_name:str) -> bool:
        if regex_pattern is None:
            return False

        matches = re.findall(pattern=regex_pattern, string=node_name)

        if len(matches) > 0: return True
        return False
    
    def __split_position(self, node: str) -> tuple[str, str]:
        split = node.split("**")
        if len(split) > 1:
            name = split[0]
            position = split[1]
            return (name, position)
        else:
            return (node, "") 

    def __traverse_function(self, owner_prefix, function_name_with_pos, function_body, ignore_infix_regex = None):
        if self.__ignore_node_infix(ignore_infix_regex, function_name_with_pos):
            return
        function_name, function_position = self.__split_position(function_name_with_pos)
        function_name_with_module = f"{owner_prefix}{self.module_fn_binder}{function_name}"
        self.functional_graph.add_node(function_name_with_module, position = function_position)
        functions_called = function_body.get("functions_called", [])
        where_functions = function_body.get("where_functions", dict())
        for descendant in functions_called:
            if type(descendant) == str or self.__ignore_node_infix(ignore_infix_regex, descendant.get("module_name")):
                continue
            des_name = descendant.get("name")
            des_module = descendant.get("module_name")
            called_function_full_name = f'{des_module}{self.module_fn_binder}{des_name}'
            self.functional_graph.add_node(called_function_full_name)
            self.functional_graph.add_edge(function_name_with_module, called_function_full_name)
        
        where_function_prefix = f"{function_name_with_module}{self.module_fn_binder}where_functions"
        for (where_function_name, where_function_body) in where_functions.items():
            if type(where_function_body) == str or  self.__ignore_node_infix(ignore_infix_regex, where_function_body.get("function_name")):
                continue
            called_function_full_name = f'{where_function_prefix}{self.module_fn_binder}{where_function_body.get("function_name")}'
            self.functional_graph.add_node(called_function_full_name)
            self.functional_graph.add_edge(function_name_with_module, called_function_full_name)
            self.__traverse_function(where_function_prefix, where_function_name, where_function_body, ignore_infix_regex)

    def __traverse_json(self, ignore_infix_regex = None):
        data = self.data
        for (m,f) in data.items():
            if self.module_name != None and m != self.module_name:
                continue
            if self.__ignore_node_infix(ignore_infix_regex, m):
                continue
            for (function_name, functionBody) in f.items():
                if self.__ignore_node_infix(ignore_infix_regex, function_name):
                    continue
                self.__traverse_function(m, function_name, functionBody, ignore_infix_regex)

    def __bfs(self, node_name, n=5, include_where_fns=True, traverse_up=False, ignore_infix_regex=None) -> Dict[str, List[str]]:
        """ 
            Returns adjacency dict
            {
                "node_name" : ["node1", "node2", "node3"]
            }
        """
        if n == 0: return 
        
        adjacent_nodes = []
        if traverse_up:
            adjacent_nodes = self.functional_graph.predecessors(node_name)
        else:
            adjacent_nodes = self.functional_graph.successors(node_name)
        
        next_nodes = []
        bfs_res = {}
        for node in adjacent_nodes:
            attrs : dict = self.functional_graph.nodes[node_name]
            
            # ignore if infix
            if self.__ignore_node_infix(ignore_infix_regex, node):
                continue

            # where funcs
            if attrs.get("is_where_fn", False) and not include_where_fns:
                continue
            
            next_nodes.append(node)
            res = self.__bfs(node, n-1, include_where_fns, traverse_up)
            if res == None:
                continue
            bfs_res.update(res)

        bfs_res[node_name] = next_nodes
        return bfs_res
    
    def get_all_sinks(self, ignore_infix_regex=None) -> List[str]:
        """ Returns list of all the nodes which only have incoming directed edge with zero outgoing directed edge
        """
        sinks = []

        for n in self.functional_graph.nodes:
            if len(self.functional_graph[n]) == 0 and not self.__ignore_node_infix(ignore_infix_regex, n):
                sinks.append(n)

        return sinks
    
    def findall_function_call_node(self, function_name : str, ignore_modules : List[str] = None) -> List[str]:
        function_calls = []

        for n in self.functional_graph.nodes:
            module_name, fname = n.split(self.module_fn_binder)

            if ignore_modules and module_name in ignore_modules:
                continue

            if fname == function_name:
                function_calls.append(n)

        return function_calls

    def get_n_ancestors(self, node_name, n=5, include_where_fns=False, ignore_infix_regex=None) -> Dict[str, List[str]]:
        return self.__bfs(node_name, n, include_where_fns, traverse_up=True, ignore_infix_regex=ignore_infix_regex)

    def get_n_decendants(self, node_name, n=5, include_where_fns=False, ignore_infix_regex=None) -> Dict[str, List[str]]:
        return self.__bfs(node_name, n, include_where_fns, traverse_up=False, ignore_infix_regex=ignore_infix_regex)
    
    def get_all_ancestors(self, node_name) -> Dict:
        return nx.ancestors(self.functional_graph, node_name)
    
    def get_all_decendants(self, node_name) -> Dict:
        return nx.descendants(self.functional_graph, node_name)
    
    def get_file_data(self) -> Dict:
        with open(self.json_path,"r") as f:
            file_data = json.loads(f.read())
            f.close()
            return (file_data)
        
    def write_to_file(self, file_data):
        with open (self.json_path,"w") as fw:
            json.dump(file_data,fw)
            fw.close()

    def get_position(self, node):
        try:
            return self.functional_graph.nodes[node]["position"]
        except:
            return None 

    def get_code_data(self, node_name, key = Literal["stringified_code","code_commment"]):
        position = self.functional_graph.nodes[node_name].get("position")
        json_data = self.data
        route = node_name.split(self.module_fn_binder)
        path = ""
        code_data = json_data
        try:
            for edge in route:
                path += self.module_fn_binder if path != "" else ""
                path += edge
                position = self.get_position(path)
                if position is not None:
                    code_data = code_data.get(f"{edge}**{position}")
                else:
                    code_data = code_data.get(edge)
            return code_data[key]
        except:
            return None
        
    def get_fn_name_from_node_name(self, node_name):
        return node_name.split(self.module_fn_binder)[-1]

    def __load_fdep_data(self, path:str) -> dict:
        if not os.path.exists(path):
            raise ValueError(f"Path {path} does not exisits")
        
        data = None
        with open(path, "r") as f:
            data = json.loads(f.read())
            f.close()

        if data is None:
            raise Exception(f"Unable to read file at {path}")
        return data
    
    def get_descendants_with_levels(self, node_name):
        levels = {node_name: 0}
        
        queue = deque([(node_name, 0)])
        
        descendants_with_levels = [(node_name,0)]

        while queue:
            current_node, current_level = queue.popleft()
            
            for neighbor in self.functional_graph.successors(current_node):
                if neighbor not in levels:
                    levels[neighbor] = current_level + 1
                    queue.append((neighbor, current_level + 1))
                    descendants_with_levels.append((neighbor, current_level + 1))
        
        descendants_with_levels.sort()
        return descendants_with_levels

    def get_subtree_immediate(self, immediate, subtree_immediate):
        if subtree_immediate is None:
            return []
        else:
            immediate_check = [node[0] for node in subtree_immediate]
            new_immediate = list(set(immediate) & set(immediate_check))
            return new_immediate

    def traverse_json_and_insert(self, comment_json_path=None, repo_path = None, ignore_infix_regex=None, module_name = None, retries=[], skip_module_patterns=[], overwrite=False):
        data = self.__load_fdep_data(comment_json_path)
        module_comment_json = {}
        for (m,f) in data.items():
            splitted = m.split("->-")
            module = splitted[0]
            function = splitted[1]
            if any(map(lambda r: bool(re.match(r, module)), skip_module_patterns)):
                continue
            if module in module_comment_json:
                module_comment_json[module][function]= f
            else:
                module_comment_json[module] = {function: f}

        for m, f in module_comment_json.items():
            if module_name == None or m.startswith(module_name):
                pass 
            else:
                continue

            if m.startswith("app."):
                file_name = repo_path+"/"+m.split("->-")[0].replace(".","/")+".hs"
            else:
                file_name = repo_path+"/src/"+m.split("->-")[0].replace(".","/")+".hs"

            file_data = open(file_name,"r").read()
            encoded_file_data = file_data.encode()
            tree1 = self.tree.parse(encoded_file_data)
            for node in tree1:
                if node.name == None:
                    continue
                if ignore_infix_regex == None:
                    pass
                elif self.__ignore_node_infix(ignore_infix_regex, node.name):
                    continue
                method_source_code = node.method_source_code
                try:
                    # val = next(v for k, v in f.items() if k.startswith(node.name+"**"))
                    comment_generated = f.get(node.name).get("overview")
                    method_source_code = node.method_source_code
                    write_code_snippet_to_file(
                        file_name, node.name, method_source_code, comment_generated, overwrite
                    )
                except Exception as e:
                    retries.append({node.name, e})
                    print("Error Node: ", node.name)
                    pass
