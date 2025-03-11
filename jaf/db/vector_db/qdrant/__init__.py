from typing import List

import gc
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import SearchRequest
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import  PointStruct, Filter, FieldCondition, Range, MatchValue, NamedVector, MatchAny

from jaf.types import Query,Chunk
from jaf.types.common import EmbeddingVec, Property, VectorType, LLMContext
from jaf.logger import init_logger
from jaf.utils import run_gc

logger=init_logger(__name__)


def cosine_similarity(vec1, vec2):
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    similarity = dot_product / (norm_vec1 * norm_vec2)
    return similarity



class QdrantDB:
    def __init__(self, host: str = "http://localhost", port:str=6333, verbose=True, garbage_collect=True,timeout=5):
        self.url = f"{host}:{port}"
        self.timeout = timeout
        self.client = self._create_client()
        self.garbage_collect = garbage_collect
        self.verbose = verbose

    def _create_client(self) -> 'QdrantClient':
        try:
            return QdrantClient(url=self.url,timeout=self.timeout)
        except Exception as e:
            print(f"Failed to create QdrantClient: {e}")
            return None


    def create_collection(self,collection_name:str,**kwargs):
        if not self.collection_exists(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                **kwargs
            )

    def get_collections(self):
        return self.client.get_collections()

    def get_points(self,collection_name,limit=1,offset=None):
        return self.client.scroll(
            collection_name=f"{collection_name}",
            with_payload=True,
            with_vectors=False,
            limit=limit,
            offset = offset
        )

    def get_point_by_ids(self,collection_name,ids):
        return self.client.retrieve(
            collection_name=f"{collection_name}",
            ids=ids,
            with_vectors=True,
            with_payload=False
        )

    def upsert_point(self,collection_name,point_id,payload,vector):
        return self.client.upsert(
            collection_name=f"{collection_name}",
            points=[
                models.PointStruct(
                    id=point_id,
                    payload=payload,
                    vector=vector
                ),
            ],
        )

    def collection_exists(self,collection_name):
        return self.client.collection_exists(collection_name)

    def svec_to_qdrant_svec(self, vector:EmbeddingVec):
        if vector.type != VectorType.SPARSE:
            raise ValueError("Sparse vector is not found in chunk, for sparse/hybrid indexing")
        return models.SparseVector(indices=vector.value[0], values=vector.value[1])

    def pre_process_chunk(self, chunk:Chunk):
        named_vectors = {}
        point_id = f"{chunk.doc_id}::{chunk.chunk_id}" if chunk.doc_id else chunk.chunk_id

        for property in chunk.properties:
            # vec_name = index_conifg.column_name if index_conifg.column_name else property.name
            for vec in property.vectors:
                if vec.type == VectorType.SPARSE:
                    named_vectors[vec.vec_name] = self.svec_to_qdrant_svec(vec)
                else:
                    named_vectors[vec.vec_name] = vec.value

        return PointStruct(
            id = point_id,
            vector=named_vectors,
            payload=chunk.db_dump_dict()
        )

    def process_chunks(self, chunks:List[Chunk]) -> list[PointStruct]:
        points = []
        for chunk in chunks:
            point = self.pre_process_chunk(chunk)
            if point:
                points.append(point)
        return points

    def upload_points(self, collection_name, vectors, batch_size=64):
        try:
            operation_info = self.client.upload_points(
                collection_name=collection_name,
                points=vectors,
                batch_size=batch_size,
                wait=True
            )

            if self.verbose:
                logger.info(f"inserted {len(vectors)} points to collection {collection_name}")
                pass

            if self.garbage_collect:
                del vectors
                run_gc(self.__class__.__name__)

            return operation_info
        except Exception as ex:
            logger.exception(f"Exception while inserting point in {collection_name}")
            raise

    def as_indexer(self, collection_name=None):

        def partial_insert(chunks:Chunk | List[Chunk]):
            if collection_name is None or not self.client.collection_exists(collection_name):
                raise Exception(f"Collection {collection_name} does not exist")
            try:
                if not isinstance(chunks, list):
                    chunks = [chunks]
                chunks=self.process_chunks(chunks)
                self.upload_points(collection_name, chunks)
            except Exception as ex:
                raise ex

        return partial_insert

    def run_query(self, collection_name:str, query:Query, top_k:int, **kwargs) -> List[LLMContext]:
        search_vecs = []
        search_vec_names = []
        search_filters = []
        filters = query.filters
        if filters is None:
            filters = []
        for filter in filters:
            if filter['type'] == 'range':
                search_filters.append(FieldCondition(
                    key=filter['key'],
                    range = Range( gte=filter['gte'], lte=filter['lte'])
                ))
            else:
                search_filters.append(FieldCondition(
                    key = filter['key'],
                    match={'value':filter['value']}
                ))
        filters = Filter(must=search_filters)
        for property in query.properties:
            for idx,vec in  enumerate(property.vectors):
                if vec.type == VectorType.SPARSE:
                    req = models.SearchRequest(
                            vector=models.NamedSparseVector(
                                name=vec.vec_name,
                                vector=models.SparseVector(
                                    indices=vec.value[0],
                                    values=vec.value[1],
                                ),
                            ),
                            limit=top_k,
                            score_threshold = property.retrieve_config[idx].score_threshold,
                            with_payload=True,
                            filter=filters
                        )
                else:
                    req = models.SearchRequest(
                            vector=models.NamedVector(
                                name=vec.vec_name,
                                vector=vec.value,
                            ),
                            limit=top_k,
                            score_threshold = property.retrieve_config[idx].score_threshold,
                            with_payload=True,
                            filter=filters
                        )

                search_vecs.append(req)
                search_vec_names.append(vec.vec_name)


        #TODO: Add rank fusion to limit results
        res = self.client.search_batch(
                    collection_name=collection_name,
                    requests=search_vecs)

        context = []
        for vec_name, res_per_query in zip(search_vec_names, res):
            for r in res_per_query:
                context.append(LLMContext(data=r.payload, score=r.score, vec_name=vec_name, point_id=r.id))

        return context

    def as_retriever(self, collection_name:str, top_k:int=5,**kwargs):
        if collection_name is None or not self.client.collection_exists(collection_name):
            raise Exception(f"Collection {collection_name} does not exist")

        def partial_retrive(query:Query, collection_name = collection_name, return_raw=False,top_k=top_k,**kwargs):
            res = self.run_query(collection_name, query, top_k=top_k,**kwargs)
            if return_raw:
                return res

            if self.garbage_collect:
                new_query = Query()
                new_query.tools = query.tools
                new_query.filters = query.filters
                new_query.few_shot_examples = query.few_shot_examples
                for property in query.properties:
                    property.vectors = []
                new_query.properties = query.properties
                del query
                run_gc(self.__class__.__name__)
                query = new_query

            query.retrived_context = res
            return query

        return partial_retrive
