import re
import os
import tiktoken
import subprocess
from typing import List, Optional
from openai.types.chat import ChatCompletion

from jaf.types import Query
from jaf.types.common import GenerationConfig
from jaf.pipeline.base import Pipeline
from jaf.pipeline.type import PipelineTypeEnum


# TODO: refactor pipline to seperate blocks -> git, reviewer, summerizer
class GitDiffReviewer(Pipeline):
    def __init__(self, repo_path:str, max_token_per_request:int=7000) -> None:

        if not os.path.exists(repo_path):
            raise ValueError(f"Given path - `{repo_path}` does not exisits.")

        self.temp = 0.7
        self.repo_path = repo_path
        self.system_prompt = "You are an AI assistant that helps people find information."
        self.user_prompt_query = """Based on the git diff, can you confirm that only refactoring is done and no logical changes are done. Only return list of logical changes done. 
        Only return list of logical changes. If there are no logical changes in diff just say 'No Logical Changes'."""
        
        self.max_token_per_request = max_token_per_request
        self.tokenizer = tiktoken.get_encoding("o200k_base")

        super().__init__(pipeline_enum=PipelineTypeEnum.CODE_GIT_DIFF_REVIEW_PIPELINE)
    
    def what_to_do(self, text:str) -> None:
        self.system_prompt = text
    
    def validate_pipe(self):
        return True

    def get_changed_files(self, commit_before, commit_after):
        os.chdir(self.repo_path)
        subprocess.run([f'git pull'], check=True, stdout=subprocess.PIPE,shell=True)
        subprocess.run([f'git checkout {commit_after}'], check=True, stdout=subprocess.PIPE,shell=True)
        result = subprocess.run([f'git diff {commit_before} {commit_after} -- \'*.hs\''], check=True, stdout=subprocess.PIPE,shell=True)
        return result.stdout.decode()
    
    def covert_diff_to_chunks(self, diff:str) -> List[str]:
        # chunks git diff to files based diff and format raw diff to remove redundant information
        formated_diffs = parse_git_diff(diff)
        chunks = []
        chunk = ""
        running_tok_count = 0

        for dif in formated_diffs:
            toks = self.tokenizer.encode(dif)
            
            if running_tok_count + len(toks) < self.max_token_per_request:
                chunk += "\n" + dif
                running_tok_count += len(toks)
                continue

            chunks.append(chunk.strip())
            running_tok_count = 0
            chunk = ""

        chunks.append(chunk.strip())
        return chunks

    def __one_dff_review(self, diff:str,dev_description:Optional[str]= None) -> Query:
        q = Query()
        if dev_description is not None:
            q.prompt = self.user_prompt_query + "\nHere is the description provided by developer:\n" + dev_description + "\nHere is the diff:\n" + diff
        else:
            q.prompt = self.user_prompt_query + diff
        q.system_prompt = self.system_prompt
        q.llm_generation_config = GenerationConfig(temperature=self.temp)
        return Pipeline.__call__(self, q)
    
    def summarise(self, diff_res:List[str]) -> Query:
        usr_prompt = f"""Given below is summary of all the diff, can you give answer of original user query - {self.user_prompt_query}
Here's the summary of all diffs:\n""" + "\n------\n".join(diff_res)
        
        q = Query()
        q.prompt = usr_prompt
        q.system_prompt = self.system_prompt
        q.llm_generation_config = GenerationConfig(temperature=self.temp)
        return Pipeline.__call__(self, q)

    def __multi_diff_revivew(self, diffs:List[str],dev_description:Optional[str]= None) -> Query:
        diff_res : List[str] = []
        total_chunks = len(diffs)

        for idx,  diff in enumerate(diffs):
            print(f"Processing diff chunk - {idx+1}/{total_chunks}")
            res = self.__one_dff_review(diff,dev_description)
            res = res.response

            if isinstance(res, ChatCompletion):
                res = res.choices[0].message.content
            
            if res:
                diff_res.append(res)

        return self.summarise(diff_res)
    def __call__(self, diff:Optional[str] = None,dev_description:Optional[str]= None, before_commit:Optional[str] = None, after_commit:Optional[str] = None, **kwargs) -> Query:
        
        if diff is None and before_commit is None and after_commit is None:
            raise ValueError("Please provide either diff text or before and after commit")
        
        if before_commit and after_commit:
            diff = self.get_changed_files(before_commit, after_commit, self.repo_path)

        if diff is None:
            raise Exception("`diff` is None, something is wrong")

        diff_chunks = self.covert_diff_to_chunks(diff)

        if len(diff_chunks) > 1:
            return self.__multi_diff_revivew(diff_chunks,dev_description)
        else:
            return self.__one_dff_review(diff_chunks[0],dev_description)
    

def parse_git_diff(diff: str) -> str:
    """
    Takes a git diff string and returns a better-formatted representation.
    """
    lines = diff.split('\n')
    result = []
    files = []
    current_file = None

    for line in lines:
        if line.startswith('diff --git'):
            # New file diff section
            files.append("\n".join(result).strip())
            result = []
            current_file = re.findall(r'a/(\S+)', line)[0]
            result.append(f"File: {current_file}")
        elif line.startswith('index') or line.startswith('---') or line.startswith('+++'):
            # Ignore index and old/new file names
            continue
        elif line.startswith('@@'):
            # Hunk header
            hunk_info = line.split('@@')[1].strip()
            result.append(f"\nHunk: {hunk_info}")
        elif len(line.strip()) > 0:
            result.append(line)
    
    files.append("\n".join(result).strip())

    return files

class ReleaseNoteGenerator(GitDiffReviewer):
    def __init__(self, repo_path:str, max_token_per_request:int=7000) -> None:
        super().__init__(repo_path, max_token_per_request)
        self.system_prompt = "You are an AI assistant that helps people find information."
        self.user_prompt_query = """Based on the git diff, Can you generate release notes comprising informations like Features Added, Enhancements, Fixes and Breaking changes.
        Breaking changes should also include api contrace changes, if there is any field removed from type or instance then it has be considered, addition of fields can be feature but removal of it is breaking an api contract"""

class ReleaseNoteSummary(GitDiffReviewer):
    def __init__(self, repo_path:str, max_token_per_request:int=7000) -> None:
        super().__init__(repo_path, max_token_per_request)
        self.system_prompt = "You are an AI assistant that helps people find information."
        self.user_prompt_query = """Based on the list of release notes generated, the elements in the list are in the order of the PR's that got merged, summarise the release notes in such a way that you create a summary of release by consolidating all elements"""
    
    def __call__(self, summary_list:List[str] = None, **kwargs) -> Query:
            return self.summarise(summary_list)