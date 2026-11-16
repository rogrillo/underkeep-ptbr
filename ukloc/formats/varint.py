"""Inteiro de tamanho variável usado pelos containers DfT e Def.

Decodificação: 7 bits por byte, little-endian, bit 7 = continua (estilo LEB128).
Codificação OBSERVADA (não documentada) nos arquivos do jogo:

* ``v < 128``   -> 1 byte
* ``v < 1024``  -> 2 bytes
* ``v < 2**21`` -> 3 bytes (mesmo quando 2 bastariam: forma não mínima)

Valores ``>= 2**21`` nunca foram observados e são rejeitados na escrita.
"""
from __future__ import annotations

from . import FormatError

MAX_OBSERVED_EXCLUSIVE = 1 << 21


def read_varint(data: bytes, pos: int) -> tuple[int, int, int]:
    """Retorna ``(valor, nova_posição, largura_em_bytes)``."""
    start = pos
    value = shift = 0
    while True:
        if pos >= len(data):
            raise FormatError(f"varint truncado no offset {start}")
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            return value, pos, pos - start
        if shift >= 35:
            raise FormatError(f"varint longo demais no offset {start}")


def observed_width(value: int) -> int:
    if value < 0:
        raise ValueError("varint negativo")
    if value < 0x80:
        return 1
    if value < 0x400:
        return 2
    if value < MAX_OBSERVED_EXCLUSIVE:
        return 3
    raise ValueError(f"valor {value} acima do intervalo observado (< 2**21)")


def encode_varint(value: int) -> bytes:
    width = observed_width(value)
    out = bytearray()
    for index in range(width):
        byte = (value >> (7 * index)) & 0x7F
        if index < width - 1:
            byte |= 0x80
        out.append(byte)
    return bytes(out)
