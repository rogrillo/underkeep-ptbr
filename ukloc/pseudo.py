"""Pseudo-localização para testes de pipeline (nunca é tradução).

Envolve cada valor em ``[!!`` … ``!!]`` e troca vogais/consoantes por equivalentes
acentuados do PT-BR **somente fora** dos tokens protegidos (``{...}``, ``%N``,
``\\n``, CRLF). Usa apenas caracteres com cobertura confirmada nas fontes do jogo;
nunca usa ``…``.
"""
from __future__ import annotations

from . import markup

ACCENT_MAP = str.maketrans({
    "a": "ã", "e": "ê", "i": "í", "o": "õ", "u": "ú", "c": "ç",
    "A": "Ã", "E": "Ê", "I": "Í", "O": "Õ", "U": "Ú", "C": "Ç",
})
PREFIX = "[!!"
SUFFIX = "!!]"


def pseudolocalize(text: str) -> str:
    if text == "":
        return text
    parts = list(markup.split_tokens(text))
    # Mantém tags iniciais (ex.: alinhamento/cor) antes do marcador de abertura.
    lead = 0
    while lead < len(parts) and parts[lead][0] and parts[lead][1].startswith("{"):
        lead += 1
    head = "".join(piece for _, piece in parts[:lead])
    body = "".join(piece if is_token else piece.translate(ACCENT_MAP)
                   for is_token, piece in parts[lead:])
    return head + PREFIX + body + SUFFIX
