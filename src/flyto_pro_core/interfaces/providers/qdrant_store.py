"""
Qdrant Provider — IVectorStoreRepository implementation.

Requires: pip install flyto-pro[qdrant]
"""

import logging
import os
from typing import Any, Dict, List, Optional

from ..storage import IVectorStoreRepository, VectorSearchResult

logger = logging.getLogger(__name__)

_DEFAULT_URL = "http://localhost:6333"


class QdrantVectorStore(IVectorStoreRepository):
    """
    Qdrant implementation of IVectorStoreRepository.

    Usage:
        from flyto_pro_core.interfaces.providers.qdrant_store import QdrantVectorStore

        store = QdrantVectorStore(url="http://localhost:6333")
        await store.upsert("my_collection", "id1", [0.1, 0.2, ...], {"key": "val"})
        results = await store.search("my_collection", [0.1, 0.2, ...], limit=5)
    """

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        **client_kwargs: Any,
    ):
        self._url = url or os.getenv("QDRANT_URL", _DEFAULT_URL)
        self._api_key = api_key or os.getenv("QDRANT_API_KEY")
        self._client_kwargs = client_kwargs
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
            except ImportError:
                raise ImportError(
                    "qdrant-client is required for QdrantVectorStore. "
                    "Install it with: pip install flyto-pro[qdrant]"
                )
            kwargs = {"url": self._url, **self._client_kwargs}
            if self._api_key:
                kwargs["api_key"] = self._api_key
            self._client = QdrantClient(**kwargs)
        return self._client

    async def upsert(
        self,
        collection: str,
        id: str,
        vector: List[float],
        payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        from qdrant_client.models import PointStruct

        client = self._get_client()
        client.upsert(
            collection_name=collection,
            points=[
                PointStruct(
                    id=id,
                    vector=vector,
                    payload=payload or {},
                )
            ],
        )
        return True

    async def upsert_batch(
        self,
        collection: str,
        points: List[Dict[str, Any]],
    ) -> int:
        from qdrant_client.models import PointStruct

        client = self._get_client()
        qdrant_points = [
            PointStruct(
                id=p["id"],
                vector=p["vector"],
                payload=p.get("payload", {}),
            )
            for p in points
        ]
        client.upsert(collection_name=collection, points=qdrant_points)
        return len(qdrant_points)

    async def search(
        self,
        collection: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        client = self._get_client()

        kwargs: Dict[str, Any] = {
            "collection_name": collection,
            "query_vector": query_vector,
            "limit": limit,
        }
        if score_threshold is not None:
            kwargs["score_threshold"] = score_threshold
        if filter_conditions:
            kwargs["query_filter"] = self._build_filter(filter_conditions)

        hits = client.search(**kwargs)
        return [
            VectorSearchResult(
                id=str(hit.id),
                score=hit.score,
                payload=hit.payload or {},
                vector=None,  # search doesn't return vectors by default
            )
            for hit in hits
        ]

    async def delete(
        self,
        collection: str,
        ids: List[str],
    ) -> int:
        from qdrant_client.models import PointIdsList

        client = self._get_client()
        client.delete(
            collection_name=collection,
            points_selector=PointIdsList(points=ids),
        )
        return len(ids)

    async def get(
        self,
        collection: str,
        id: str,
    ) -> Optional[VectorSearchResult]:
        client = self._get_client()
        results = client.retrieve(
            collection_name=collection,
            ids=[id],
            with_payload=True,
        )
        if not results:
            return None
        point = results[0]
        return VectorSearchResult(
            id=str(point.id),
            score=1.0,
            payload=point.payload or {},
        )

    async def create_collection(
        self,
        name: str,
        dimension: int,
        distance_metric: str = "cosine",
    ) -> bool:
        from qdrant_client.models import Distance, VectorParams

        client = self._get_client()
        distance_map = {
            "cosine": Distance.COSINE,
            "euclidean": Distance.EUCLID,
            "dot": Distance.DOT,
        }
        distance = distance_map.get(distance_metric, Distance.COSINE)

        if client.collection_exists(name):
            return True

        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dimension, distance=distance),
        )
        return True

    async def delete_collection(self, name: str) -> bool:
        client = self._get_client()
        client.delete_collection(name)
        return True

    async def collection_exists(self, name: str) -> bool:
        client = self._get_client()
        return client.collection_exists(name)

    @staticmethod
    def _build_filter(conditions: Dict[str, Any]):
        """
        Convert generic filter dict to Qdrant filter.

        Supports simple key-value equality:
            {"field": "value"}        -> FieldCondition(key="field", match=MatchValue(value="value"))
            {"field": [1, 2, 3]}      -> FieldCondition(key="field", match=MatchAny(any=[1, 2, 3]))
        """
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            MatchAny,
            MatchValue,
        )

        must = []
        for key, value in conditions.items():
            if isinstance(value, list):
                must.append(FieldCondition(key=key, match=MatchAny(any=value)))
            else:
                must.append(FieldCondition(key=key, match=MatchValue(value=value)))
        return Filter(must=must)
