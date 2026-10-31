"""Thin chat wrapper over mlx-lm, plus a fake for tests and dry runs."""
import re
from typing import Callable

_THINK = re.compile(r"<think>.*?</think>\s*", re.S)
_PREAMBLE = re.compile(r"^\s*(here(?:'s| is)[^\n:]{0,80}:\s*)", re.I)


def clean_output(text: str) -> str:
    text = _THINK.sub("", text)
    text = _PREAMBLE.sub("", text, count=1).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'“”":
        text = text[1:-1].strip()
    return text


class LM:
    def __init__(self, base: str, adapter: str | None = None):
        from mlx_lm import load  # lazy: tests without the model never import mlx

        self.model, self.tokenizer = load(base, adapter_path=adapter)

    def chat(self, system: str, user: str, max_tokens: int = 512, temp: float = 0.3) -> str:
        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler

        prompt = self.tokenizer.apply_chat_template(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            add_generation_prompt=True, tokenize=False,
        )
        out = generate(self.model, self.tokenizer, prompt=prompt, max_tokens=max_tokens,
                       sampler=make_sampler(temp=temp), verbose=False)
        return clean_output(out)


class FakeLM:
    def __init__(self, fn: Callable[[str, str], str]):
        self.fn = fn
        self.calls: list[tuple[str, str]] = []

    def chat(self, system: str, user: str, max_tokens: int = 512, temp: float = 0.3) -> str:
        self.calls.append((system, user))
        return clean_output(self.fn(system, user))
