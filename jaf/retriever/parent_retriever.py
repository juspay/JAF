import logging
from typing import Any

from jaf.types import Query
from jaf.db.vector_db import QdrantDB

class ParentRetrieverByProperty:
    def __init__(self, vector_db:QdrantDB, parent_property="parent_id", use_hybrid=False):
        """ 
            Parent Reriever is two step retriver
            1. retrive all the similar childs first
            2. retrive parent of all retrived child

            supports based on parent id
        """
        if vector_db is None:
            raise Exception("Vector DB instance can not be None")

        self.db = vector_db
        
        if use_hybrid:
            self.child_retriever = vector_db.as_hybrid_retriever()
        else:
            self.child_retriever = vector_db.as_retriever()

        self.parent_property_identifier = parent_property

    def retrieve_parents(self, table_name, parent_ids):
        res = []
        for p_ids in parent_ids:
            res.append(self.db.retrieve_by_id(table_name, p_ids))
        
        return res

    def __call__(self, query : Query, parent_table_name : str) -> Any:
        # retrieve childs
        childs = self.child_retriever(query, return_raw=True)
        parent_identifiers = set()

        for child in childs:
            if self.parent_property_identifier in child:
                parent_identifiers.add(child[self.parent_property_identifier])
            else:
                logging.warning(f"Property {self.parent_property_identifier} not found in retrieved chunk")

        # retrieve all parents 
        res = self.retrieve_parents(parent_table_name, parent_identifiers)
        return query.add_property("prompt_context", res)