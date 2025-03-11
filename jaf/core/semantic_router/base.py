# import logging
# import torch
# import numpy as np
# from sentence_transformers import util as sm_util
# from typing import Any

# from jaf.types import Query


# class SemanticRouterBase:
#     def __init__(self, encoder, score_threshold=0.8) -> None:
#         self.routes = {}
#         self.default_route = None
#         self.score_threshold = score_threshold

#         if encoder is None:
#             raise "No encoder is porvided"
        
#         self.encoder = encoder

#     def add_route(self, route_name, examples=[], set_default=False):
#         if len(examples) == 0 and len(examples) > 10:
#             raise f"You can only give 1-10 examples, but give {len(examples)}"
        
#         if self.routes.get(route_name):
#             raise f"route {route_name} already exists!"
        
#         embs = []
#         for e in examples:
#             q:Query = self.encoder.encode(Query(e))
#             embs.append(q.get_vector())
                        
#         self.routes[route_name] = {
#             "examples" : examples,
#             "embeddings": np.array(embs)
#         }

#         if set_default:
#             if self.default_route is not None:
#                 logging.warning(f"replacing default route {self.default_route} with new default_route {route_name}")
#             self.default_route = route_name

#         return self.routes

#     def remove_route(self, route_name):
#         self.routes = {r_n:ex for r_n, ex in self.routes.items() if r_n != route_name}
#         return True
    
#     def _get_route_score(self, query:Query, weights=[]):
#         # TODO: add more route calculation methods, add weights to the route
#         query_vec = query.get_vector()
#         if query_vec is None:
#             query = self.encoder.encode(query, return_dict=False)
#             query_vec = query.get_vector()
        
#         route_score = []
        
#         for route_name, route in self.routes.items():
#             sim_score = torch.mean(sm_util.cos_sim(np.array(query_vec), route["embeddings"])).item()
#             if sim_score >= self.score_threshold:
#                 route_score.append((sim_score, route_name))
        
#         if len(route_score) > 0:
#             return sorted(route_score, key=lambda x: x[0], reverse=True)
#         else:
#             return [(1, self.default_route)]

#     def select_route(self, query, route_score, **kwargs):
#         raise NotImplementedError

#     def __call__(self, query,  **kwargs) -> Any:
#         scores = self._get_route_score(query, **kwargs)
#         return self.select_route(query, scores, **kwargs)