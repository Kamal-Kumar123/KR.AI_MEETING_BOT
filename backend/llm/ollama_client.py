import requests

from config import OLLAMA_BASE_URL, OLLAMA_MODEL


def chat(system: str, user: str, temperature: float = 0.3, max_tokens: int = 500) -> str:
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.json()["message"]["content"].strip()


def is_ollama_available() -> bool:
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code != 200:
            return False
        models = [item.get("name", "") for item in response.json().get("models", [])]
        return any(OLLAMA_MODEL in name for name in models)
    except Exception:
        return False


def list_models() -> list[str]:
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        response.raise_for_status()
        return [item.get("name", "") for item in response.json().get("models", [])]
    except Exception:
        return []
