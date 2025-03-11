from jaf.types import Query
from jaf.core.augment_prompt.base import AugmentPromptBase



SYSTEM_PROMPT_WITH_CONTEXT = """You are 'jaf', friendly and helpful AI assistant by Juspay that provides help with documents. You give concise answers with code examples if possible.
Use the following pieces of context to help answer the users question. If its not relevant to the question, just say you don't know or ask for more clarification.
When using code in response, always use ``` code ``` format. 
"""
SYSTEM_PROMPT_WITH_CONTEXT_FUNCTION_CALLING = """You are 'jaf', friendly and helpful AI assistant by Juspay that provides help with documents. You give concise answers with code examples if possible.
Use the following pieces of context to help answer the users question. Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous.  If its not relevant to the question, just say you don't know or ask for more clarification.
When using code in response, always use ``` code ``` format. 


"""

PROMPT_WITH_CONTEXT = """
Please cite the contexts with the reference numbers, in the format [citation:x]. If a sentence comes from multiple contexts, please list all applicable citations, like [citation:3][citation:5]. Other than code and specific names and citations, your answer must be written in the same language as the question.
Here are the set of contexts:

{CONTEXT}

Don't cite sources from context if you are not using context to answer the question.

And here is the user question: 
{QUESTION}
"""


CHAT_PROMPT_WITH_CONTEXT = """
Please cite the contexts with the reference numbers, in the format [citation:x]. If a sentence comes from multiple contexts, please list all applicable citations, like [citation:3][citation:5]. Other than code and specific names and citations, your answer must be written in the same language as the question.
Here are the set of contexts:

{CONTEXT}

You can also refer to previous converstion history between you and user to know what both are talking about if question is ambiguous.
Here are few previous conversation history

{CHAT_HISTORY}

Don't cite sources from context if you are not using context to answer the question.

And here is the user question:
{QUESTION}
"""


class AugmentPromptWithContext(AugmentPromptBase):
    def __init__(self, chunk_property_name="chunk") -> None:
        super().__init__(chunk_property_name)

    def generate_prompt(self, query:Query, **kwargs):
        context_string = ""
        context = query.retrived_context
        col_name = query.properties[0].retrieve_config.column_name # need fix
        original_query = query.properties[0].value or ""
        for idx, ctx in enumerate(context):
            context_string += f"[[citation:{idx+1}]] " + ctx.data[col_name] + "\n"
        
        #TODO: Handle context length based on LLM selected
        prmpt = PROMPT_WITH_CONTEXT.format(CONTEXT=context_string, QUESTION=original_query)
        
        query.system_prompt = SYSTEM_PROMPT_WITH_CONTEXT 
        query.prompt = prmpt
        
        return query



class ChatAugmentPromptWithContext(AugmentPromptBase):
    def __init__(self, max_chat_turns=5, chunk_property_name="chunk",default_prompt=None) -> None:
        self.max_chat_turns = max_chat_turns
        self.default_prompt=default_prompt
        super().__init__(chunk_property_name)

    def generate_prompt(self, query:Query, **kwargs):
        context_string = ""
        context= query.retrived_context
        # col_name = query.properties[0].retrieve_config.column_name # need fix

        chat_history = query.chat_history
        original_query = ""
        for property in query.properties:
            if property.use_in_llm:
                original_query += property.value + "\n"
        
        for idx, ctx in enumerate(context):
            context_string += f"[[citation:{idx+1}]] " + str(ctx.data) + "\n"
        chat_history_text = ""
        turns = 0

        while len(chat_history) or turns >= self.max_chat_turns :
            chat = chat_history.pop()
            role = chat.get("role")
            content = chat.get("message")

            if role is not None or content is not None:
                chat_history_text += f"{role}: {content}\n"
            turns += 1
        if self.default_prompt:
            if len(chat_history)>0:
                prmpt=self.default_prompt.format(CONTEXT=context_string, QUESTION=original_query,CHAT_HISTORY=chat_history_text)
            else:
                prmpt=self.default_prompt.format(CONTEXT=context_string, QUESTION=original_query,CHAT_HISTORY="")
        else:
            if len(chat_history_text) > 0:                
                prmpt = CHAT_PROMPT_WITH_CONTEXT.format(CONTEXT=context_string, QUESTION=original_query, CHAT_HISTORY=chat_history_text)
            else:
                prmpt = PROMPT_WITH_CONTEXT.format(CONTEXT=context_string, QUESTION=original_query)

        query.system_prompt = SYSTEM_PROMPT_WITH_CONTEXT 
        query.prompt = prmpt
        return query
