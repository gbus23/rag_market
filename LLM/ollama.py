import requests
import json
from typing import Iterator

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "phi3:mini"  

def stream_ollama_chat(prompt: str) -> Iterator[str]:
    payload = {
        "model": MODEL_NAME,
        "stream": True,
        "messages": [
            {"role": "system", "content": "You are a financial news assistant."},
            {"role": "user", "content": prompt},
        ],
    }

    with requests.post(OLLAMA_URL, json=payload, stream=True) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            data = json.loads(line.decode("utf-8"))
            if data.get("done"):
                break
            delta = data.get("message", {}).get("content", "")
            if delta:
                yield delta
