from jaf.core.reranker.fusion import reciprocal_rank_fusion

# from rerankers import Reranker
# from copy import deepcopy
# class ReRanker:
#     def __init__(self, model_name_or_path, model_type=None, lang=None, api_key=None, api_provider=None,top_k=5):
#         self.model_name_or_path = model_name_or_path
#         self.model_type = model_type
#         self.lang = lang
#         self.api_key = api_key
#         self.api_provider = api_provider
#         self.top_k=top_k

#         self.ranker = self._initialize_ranker()

#     def _initialize_ranker(self):
#         if self.api_key:
#             return Reranker(self.model_name_or_path, model_type=self.model_type,api_key=self.api_key)
#         return Reranker(self.model_name_or_path,self.model_type)

#     def __call__(self, query):
#         user_query=query.get_query()
#         prompt_context=query.get_property('prompt_context')
#         chunk_metadata_mapping={item['chunk']: item['metadata'] for item in prompt_context}
#         documents = [(doc['chunk']) for doc in prompt_context]
#         results = self.ranker.rank(query=user_query, docs=documents)
#         results = results.top_k(self.top_k)
#         ranked_documents_with_metadata = [{"chunk":doc.text,"metadata":chunk_metadata_mapping.get(doc.text)} for doc in results]
#         query.add_property("prompt_context", ranked_documents_with_metadata)
#         return deepcopy(query)