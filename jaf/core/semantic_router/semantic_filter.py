# from jaf.core.semantic_router import SemanticRouterBase


# class SemanticFilter(SemanticRouterBase):
#     def __init__(self, encoder, score_threshold=0.8, return_multiple=True) -> None:
#         """ if multiple is true, returns multiple or condition based on multiple route selection
#         """
#         self.filters = {}
#         self.return_multiple = return_multiple
#         super().__init__(encoder, score_threshold)
    
#     def add_filter(self, filter_name, val, examples=[], set_default=False):
#         routes = super().add_route(filter_name, examples, set_default)
#         #TODO: verify this logic
#         self.filters[filter_name] = val
#         return routes, self.filters

#     def remove_filter(self, filter_name):
#         routes = super().remove_route(filter_name)
#         self.filters = {r_n:ex for r_n, ex in self.filters.items() if r_n != filter_name}
#         return routes, self.filters

#     def select_route(self, query, route_score, **kwargs):
#         if not self.return_multiple:
#             fname = route_score[0][1]
#             val = self.filters[fname]
#             return query.add_property("filters",[(fname,val)])
#         else:
#             filters = []
#             for route in route_score:
#                 fname = route[1]
#                 val = self.filters[fname]
#                 filters.append((fname, val))
#             return query.add_property("filters", filters)
            
            
