from typing import Dict
from jaf.types import Query
from jaf.types.common import NormalizedLLMContext

def reciprocal_rank_fusion(query:Query,limit:int=5,**kwargs):
    llm_context = query.retrived_context

    def compute_score(pos: int) -> float:
        ranking_constant = (
            2  # the constant mitigates the impact of high rankings by outlier systems
        )
        return 1 / (ranking_constant + pos)

    scores: Dict[str, float] = {}
    point_pile = {}
    for i,ctx in enumerate(llm_context):
        normalized_info = {
            "orig_score":ctx.score,
            "vec_name":ctx.vec_name
            }
        if ctx.point_id in scores:
            scores[ctx.point_id] += compute_score(i)
            point_pile[ctx.point_id]['normalized_info'].append(normalized_info)
        else:
            normalized_ctx = ctx.model_dump()
            normalized_ctx['normalized_info'] = [normalized_info]
            point_pile[ctx.point_id] = normalized_ctx
            scores[ctx.point_id] = compute_score(i)

    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    sorted_points = []
    for point_id, score in sorted_scores[:limit]:
        context = point_pile[point_id]
        context = NormalizedLLMContext(**context)
        context.score = score
        sorted_points.append(context)
    query.retrived_context = sorted_points
    return query