"""Cleanup/formatting via a local Ollama text model. Cleans only — never answers.

Uses /api/chat with few-shot example turns: small models follow "reformat, don't reply"
far more reliably when shown examples (including a question that stays a question) than
when only told. A preamble stripper is the backup for the occasional "Here's the ...:".
"""
import re

import httpx

# Strip a leading "Here's the cleaned text:" / "Sure, here is the corrected version:" line.
# Narrow on purpose (must mention clean/text/transcript/etc.) so real dictation like
# "Here's the deal:" is left alone. ponytail: regex guard, not a parser — good enough.
_PREAMBLE = re.compile(
    r"^(?:sure[,.!]?\s*)?here(?:'|’)?s?\b[^\n:]*"
    r"\b(?:clean|text|transcript|format|version|corrected)[^\n:]*:\s*",
    re.IGNORECASE,
)

# Few-shot: teach "clean it, don't answer it". The question examples are the important ones —
# a chat model's instinct is to REPLY to a question, so we show several questions staying questions.
_EXAMPLES = [
    ("um so how are we doing today", "How are we doing today?"),
    ("what do you uh think about the new design", "What do you think about the new design?"),
    ("can you like send me the file when you get a chance", "Can you send me the file when you get a chance?"),
    ("yeah i think we should like ship it tomorrow you know", "I think we should ship it tomorrow."),
]


class Cleaner:
    def __init__(self, url, model, system_prompt, keep_alive="60s", timeout=120):
        self.url = url.rstrip("/")
        self.model = model
        self.system_prompt = system_prompt
        self.keep_alive = keep_alive
        self.timeout = timeout

    def clean(self, text):
        messages = [{"role": "system", "content": self.system_prompt}]
        for raw, cleaned in _EXAMPLES:
            messages.append({"role": "user", "content": raw})
            messages.append({"role": "assistant", "content": cleaned})
        messages.append({"role": "user", "content": text})

        r = httpx.post(
            f"{self.url}/api/chat",
            timeout=self.timeout,
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "keep_alive": self.keep_alive,
                "options": {"temperature": 0},  # deterministic cleanup, no creativity
            },
        )
        r.raise_for_status()
        out = r.json().get("message", {}).get("content", "").strip()
        return _PREAMBLE.sub("", out, count=1).strip()


if __name__ == "__main__":
    # self-check: the preamble stripper removes wrappers but keeps real "Here's ...:" dictation
    assert _PREAMBLE.sub("", "Here's the cleaned text: How are we doing now?").strip() == "How are we doing now?"
    assert _PREAMBLE.sub("", "Sure, here is the corrected version: Ship it.").strip() == "Ship it."
    assert _PREAMBLE.sub("", "Here's the deal: we ship tomorrow.").strip() == "Here's the deal: we ship tomorrow."
    print("cleanup ok")
