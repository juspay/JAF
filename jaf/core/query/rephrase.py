from typing import Any


SYSTEM_PROMPT = """You are helpful AI assistant by Juspay, that can rephrase vague user question to descriptive question by using recent conversation context or few examples given. Return concise rephrased question as comma seperated value e.g. question1, question2 question3.
Don't add any extra words which are not there in examples or chat history. Return original question if you feel provided conversation context and examples are not enough to rephrase the user question. 
"""

PROMPT = """
Rephrase following question using few examples provided below, if you can not rephrase question or need more examples just return original question as it is.
Please return rephrased questions as comma seperated values. 

Here are examples: 
{EXAMPLES}

And here is original user question:
{ORIGINAL_QUESTION}
"""


CHAT_PROMPT = """
Rephrase following question using previous conversation history provided below, if you can not rephrase question or need more examples just return original question as it is.
Please return rephrased questions as comma seperated values. 

Here is previous conversation history: 
{CONVERSATION_HISTORY}

And here is original user question:
{ORIGINAL_QUESTION}
"""



class FewShotExample:
    def __init__(self, queries, response) -> None:
        self.queries = queries
        self.response = response

    def __repr__(self) -> str:
        query = "user: \n"
        for q in self.queries:
            query += f"{q}\n"
        return query + f"you: {self.response}"


"""
    prompt LLM to genrate response based on convesation history.
    Add propery of original query and replaces current query
"""
class QueryRephraser:
    def __init__(self, llm, few_shot_examples=[], return_multiple=False) -> None:
        self.llm = llm
        self.return_multiple = return_multiple
        self.few_shot_examples = few_shot_examples
        self.few_shot_examples_txt = "\n".join(str(f) for f in few_shot_examples)
    

    def __call__(self, query, **kwargs) -> Any:
        query_text = query.get_property("query")
        user_prompt = PROMPT.format(EXAMPLES=self.few_shot_examples_txt, ORIGINAL_QUESTION=query_text)

        resp = self.llm.chat_raw(SYSTEM_PROMPT, user_prompt)
        
        if self.return_multiple:
            query.add_property("rephrased_query", resp.split(","))
        else:
            query.add_property("rephrased_query", resp.split(",")[:1])
        
        return query
        


class ChatQueryRephraser:
    def __init__(self, llm, limit_history=5, return_multiple=False) -> None:
        self.llm = llm
        self.return_multiple = return_multiple
        self.limit_history=limit_history
    
    def __create_conv_prompt(self, chat_context):
        conv_history_prompt = ""

        for turn in chat_context[-self.limit_history:]:
            role = turn["role"]
            message = turn["response"]
            conv_history_prompt += f"{role}: {message}\n"
        
        return conv_history_prompt

    def __call__(self, query) -> Any:
        chat_context = query.get_property("chat_context")
        query_text = query.get_property("query")

        # don't rephrase is there's no chat query
        if chat_context is None:
            return query

        user_prompt = CHAT_PROMPT.format(CONVERSATION_HISTORY=self.__create_conv_prompt(chat_context), ORIGINAL_QUESTION=query_text)
        resp = self.llm.chat_raw(SYSTEM_PROMPT, user_prompt)
        
        if self.return_multiple:
            query.add_property("rephrased_query", resp.split(","))
        else:
            query.add_property("rephrased_query", resp.split(",")[:1])

        return query

