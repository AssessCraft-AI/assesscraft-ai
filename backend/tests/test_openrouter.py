import json

import httpx
from pydantic import BaseModel

from app.tools.similarity import _OpenRouterModels


class _Out(BaseModel):
    key: str


def test_openrouter_adapter_maps_genai_calls():
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append((request.url.path, body))
        if request.url.path.endswith("/embeddings"):
            return httpx.Response(200, json={"data": [{"index": 1, "embedding": [2.0]}, {"index": 0, "embedding": [1.0]}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"key": "A"}'}}]})

    models = _OpenRouterModels("k")
    models._http = httpx.Client(base_url=models.URL, transport=httpx.MockTransport(handler))

    resp = models.generate_content(
        model="google/gemini-3.1-flash-lite", contents="hi",
        config={"response_mime_type": "application/json", "response_schema": _Out, "thinking_config": {"thinking_budget": 0}, "temperature": 0.7},
    )
    assert json.loads(resp.text) == {"key": "A"}
    _, body = sent[0]
    assert body["reasoning"] == {"enabled": False} and body["temperature"] == 0.7
    assert body["response_format"]["json_schema"]["schema"]["properties"]["key"]["type"] == "string"

    emb = models.embed_content(model="ignored", contents=["a", "b"], config={"output_dimensionality": 768})
    assert [e.values for e in emb.embeddings] == [[1.0], [2.0]]
    assert sent[1][1]["dimensions"] == 768 and sent[1][1]["model"] == "google/gemini-embedding-001"
