"""Embedders for the local vector index (slices/embed.py): Titan Text Embeddings V2 on Bedrock, the
model the lab's Knowledge Base uses too, so local search and the lab's search by the same vectors."""

from __future__ import annotations

import json
import os

DEFAULT_MODEL = "amazon.titan-embed-text-v2:0"
MAX_CHARS = 40_000   # under the model's 8k-token input


class TitanEmbedder:
    def __init__(self, model_id: str = DEFAULT_MODEL, *, dimensions: int = 1024, client=None):
        self.model, self.dimensions, self._client = model_id, dimensions, client

    @property
    def client(self):
        if self._client is None:
            import boto3
            from botocore.config import Config
            # Titan throttles a burst of single-text calls; adaptive retries pace them instead of failing the run
            self._client = boto3.client("bedrock-runtime", config=Config(retries={"max_attempts": 10, "mode": "adaptive"}))
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            body = json.dumps({"inputText": text[:MAX_CHARS], "dimensions": self.dimensions, "normalize": True})
            r = self.client.invoke_model(modelId=self.model, body=body)
            out.append(json.loads(r["body"].read())["embedding"])
        return out


def embedder_from_env() -> TitanEmbedder:
    return TitanEmbedder(os.environ.get("EMBEDDING_MODEL_ID", DEFAULT_MODEL))
