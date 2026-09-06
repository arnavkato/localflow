"""Cleanup/formatting via a local Ollama text model. Cleans only — never answers."""
import httpx


class Cleaner:
    def __init__(self, url, model, system_prompt, keep_alive="60s", timeout=120):
        self.url = url.rstrip("/")
        self.model = model
        self.system_prompt = system_prompt
        self.keep_alive = keep_alive
        self.timeout = timeout

    def clean(self, text):
        r = httpx.post(
            f"{self.url}/api/generate",
            timeout=self.timeout,
            json={
                "model": self.model,
                "system": self.system_prompt,
                "prompt": text,
                "stream": False,
                "keep_alive": self.keep_alive,
                "options": {"temperature": 0},  # deterministic cleanup, no creativity
            },
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()
