# from jaf.core.semantic_router import SemanticRouterBase


# class RoutePipe(SemanticRouterBase):
#     def __init__(self, encoder, score_threshold) -> None:
#         self.route_pipe_map = {}
#         super().__init__(encoder, score_threshold)

#     def add_route(self, route_name, examples=[], set_default=False, pipeline=None):
#         routes = super().add_route(route_name, examples, set_default)
#         self.route_pipe_map[route_name] = pipeline
#         return routes, self.route_pipe_map
    
#     def remove_route(self, route_name):
#         routes = super().remove_route(route_name)
#         self.route_pipe_map = {r_n:ex for r_n, ex in self.route_pipe_map.items() if r_n != route_name}
#         return routes, self.route_pipe_map
    
#     def select_route(self, query, route_score, **kwargs):
#         sim_route = route_score[0][1]
#         pipeline = self.route_pipe_map.get(sim_route)
#         if pipeline is None:
#             raise f"no pipeline with name {pipeline} found"
        
#         return pipeline(query)



    
    