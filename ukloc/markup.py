"""Tokenização da marcação observada nos textos do jogo.

Tokens protegidos (nunca alterados por tradução automática/pseudo-localização):

* ``{...}``  tags de cor/estilo/alinhamento/ícone/variável (ex.: ``{color_text}``,
  ``{a:left}``, ``{sprite:x}``, ``{hero_name}``, ``{color:#feffb8}``)
* ``%1``, ``%2``…  placeholders posicionais
* ``\\n``  quebra escapada literal (barra invertida + n)
* ``\\r\\n``  quebra real (CRLF)
"""
from __future__ import annotations

from collections import Counter
import re
from typing import Iterator

TOKEN_RE = re.compile(r"\{[^{}\r\n]*\}|%\d+|\\n|\r\n")
TAG_RE = re.compile(r"\{[^{}\r\n]*\}")
WELL_FORMED_TAG_RE = re.compile(r"\{(?:[a-z][a-z0-9_]*(?::[^{}\r\n]*)?|font:)?\}")
PLACEHOLDER_RE = re.compile(r"%\d+")


def split_tokens(text: str) -> Iterator[tuple[bool, str]]:
    """Gera ``(é_token, trecho)`` cobrindo o texto inteiro, na ordem."""
    pos = 0
    for match in TOKEN_RE.finditer(text):
        if match.start() > pos:
            yield False, text[pos:match.start()]
        yield True, match.group()
        pos = match.end()
    if pos < len(text):
        yield False, text[pos:]


def tokens(text: str) -> list[str]:
    return [piece for is_token, piece in split_tokens(text) if is_token]


def tag_tokens(text: str) -> list[str]:
    return TAG_RE.findall(text)


def placeholders(text: str) -> Counter[str]:
    return Counter(PLACEHOLDER_RE.findall(text))


def brace_problems(text: str) -> list[str]:
    """Chaves desbalanceadas ou tags malformadas (fora do padrão observado)."""
    problems: list[str] = []
    depth = 0
    for index, char in enumerate(text):
        if char == "{":
            depth += 1
            if depth > 1:
                problems.append(f"'{{' aninhado na posição {index}")
        elif char == "}":
            if depth == 0:
                problems.append(f"'}}' sem abertura na posição {index}")
            else:
                depth -= 1
    if depth:
        problems.append("'{' sem fechamento")
    for tag in TAG_RE.findall(text):
        if not WELL_FORMED_TAG_RE.fullmatch(tag):
            problems.append(f"tag malformada {tag!r}")
    return problems


def line_breaks(text: str) -> dict[str, int]:
    crlf = text.count("\r\n")
    return {
        "escaped": text.count("\\n"),
        "crlf": crlf,
        "bare_lf": text.count("\n") - crlf,
        "bare_cr": text.count("\r") - crlf,
    }
