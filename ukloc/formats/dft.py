"""Container ``\\xFFDfT`` (arquivos ``*.rfile``, ``player_profile`` e saves).

Layout observado (107/107 ``.rfile`` da build 26592006)::

    0   magic   FF 44 66 54
    4   u32 LE  versão (=1)
    8   u32 LE  N strings
    12  N x [varint comprimento][UTF-8]          tabela de strings
    ..  tabela raiz: u32 LE n entradas, cada uma:
          u8 tipo_chave   0 = string (varint índice) | 1 = inteiro (varint)
          u8 tipo_valor   1 = int32 LE | 2 = float32 LE | 3 = string (varint índice)
                          4 = tabela (recursivo)
    fim: nenhum byte sobra

Forma canônica (observada em 100% dos arquivos): strings sem duplicatas, na ordem da
primeira ocorrência num percurso pré-ordem (chave antes do valor); varints na largura
observada (ver :mod:`ukloc.formats.varint`). O serializador sempre escreve a forma
canônica, então ``serialize_dft(parse_dft(x)) == x`` para todo arquivo canônico.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import struct
from typing import Iterator, Union

from . import FormatError, NonCanonicalError, UnknownTypeError
from .varint import encode_varint, observed_width, read_varint

MAGIC = b"\xffDfT"
KEY_STRING = 0
KEY_INT = 1
VALUE_INT32 = 1
VALUE_FLOAT32 = 2
VALUE_STRING = 3
VALUE_TABLE = 4
MAX_DEPTH = 64


@dataclass(frozen=True)
class Int32:
    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not -(2**31) <= self.value < 2**31:
            raise ValueError(f"Int32 fora do intervalo: {self.value!r}")


@dataclass(frozen=True)
class Float32:
    """Preserva os 4 bytes originais (inclusive NaN/-0.0) para round-trip exato."""

    raw: bytes

    def __post_init__(self) -> None:
        if len(self.raw) != 4:
            raise ValueError("Float32 exige 4 bytes")

    @classmethod
    def from_float(cls, value: float) -> "Float32":
        return cls(struct.pack("<f", value))

    @property
    def value(self) -> float:
        return struct.unpack("<f", self.raw)[0]


Key = Union[str, int]
Value = Union[str, Int32, Float32, "Table"]


@dataclass
class Table:
    """Tabela ordenada; chaves repetidas são preservadas (o validador as aponta)."""

    entries: list[tuple[Key, Value]] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self) -> Iterator[tuple[Key, Value]]:
        return iter(self.entries)

    def keys(self) -> list[Key]:
        return [key for key, _ in self.entries]

    def get(self, key: Key, default: Value | None = None) -> Value | None:
        for entry_key, value in self.entries:
            if entry_key == key and type(entry_key) is type(key):
                return value
        return default


@dataclass
class DfTFile:
    version: int
    root: Table


# --------------------------------------------------------------------------- leitura
def parse_dft(data: bytes, *, strict: bool = True) -> DfTFile:
    """Lê um DfT. Com ``strict``, exige a forma canônica (garantia de round-trip)."""
    if data[:4] != MAGIC:
        raise FormatError("assinatura DfT ausente")
    if len(data) < 12:
        raise FormatError("cabeçalho DfT truncado")
    version, count = struct.unpack_from("<II", data, 4)
    pos = 12
    noncanonical: list[str] = []
    strings: list[str] = []
    for index in range(count):
        length, pos, width = read_varint(data, pos)
        if width != observed_width(length):
            noncanonical.append(f"largura de varint fora da regra (string {index})")
        if pos + length > len(data):
            raise FormatError(f"string {index} truncada")
        try:
            strings.append(data[pos:pos + length].decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise FormatError(f"string {index} não é UTF-8 válido") from exc
        pos += length

    def varint(where: str) -> int:
        nonlocal pos
        value, pos, width = read_varint(data, pos)
        if width != observed_width(value):
            noncanonical.append(f"largura de varint fora da regra ({where})")
        return value

    def string_at(index: int) -> str:
        if index >= len(strings):
            raise FormatError(f"índice de string {index} fora da tabela ({len(strings)})")
        return strings[index]

    def table(depth: int) -> Table:
        nonlocal pos
        if depth > MAX_DEPTH:
            raise FormatError("aninhamento excessivo")
        if pos + 4 > len(data):
            raise FormatError("contagem de tabela truncada")
        (entries,) = struct.unpack_from("<I", data, pos)
        pos += 4
        result = Table()
        for _ in range(entries):
            if pos >= len(data):
                raise FormatError("entrada truncada")
            key_type = data[pos]
            pos += 1
            key: Key
            if key_type == KEY_STRING:
                key = string_at(varint("chave"))
            elif key_type == KEY_INT:
                key = varint("chave inteira")
            else:
                raise UnknownTypeError("DfT/chave", key_type, pos - 1)
            if pos >= len(data):
                raise FormatError("tipo de valor ausente")
            value_type = data[pos]
            pos += 1
            value: Value
            if value_type == VALUE_TABLE:
                value = table(depth + 1)
            elif value_type == VALUE_STRING:
                value = string_at(varint("valor"))
            elif value_type in (VALUE_INT32, VALUE_FLOAT32):
                if pos + 4 > len(data):
                    raise FormatError("escalar truncado")
                raw = data[pos:pos + 4]
                pos += 4
                value = Int32(struct.unpack("<i", raw)[0]) if value_type == VALUE_INT32 else Float32(raw)
            else:
                raise UnknownTypeError("DfT/valor", value_type, pos - 1)
            result.entries.append((key, value))
        return result

    root = table(0)
    if pos != len(data):
        raise FormatError(f"{len(data) - pos} bytes não consumidos")
    if canonical_strings(root) != strings:
        noncanonical.append("tabela de strings fora da ordem canônica")
    if strict and noncanonical:
        raise NonCanonicalError("; ".join(sorted(set(noncanonical))))
    return DfTFile(version, root)


# --------------------------------------------------------------------------- escrita
def canonical_strings(root: Table) -> list[str]:
    order: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        if text not in seen:
            seen.add(text)
            order.append(text)

    def walk(node: Table) -> None:
        for key, value in node.entries:
            if isinstance(key, str):
                add(key)
            if isinstance(value, str):
                add(value)
            elif isinstance(value, Table):
                walk(value)

    walk(root)
    return order


def serialize_dft(doc: DfTFile) -> bytes:
    strings = canonical_strings(doc.root)
    index = {text: i for i, text in enumerate(strings)}
    out = bytearray(MAGIC)
    out += struct.pack("<II", doc.version, len(strings))
    for text in strings:
        raw = text.encode("utf-8")
        out += encode_varint(len(raw)) + raw

    def write(node: Table, depth: int) -> None:
        if depth > MAX_DEPTH:
            raise FormatError("aninhamento excessivo")
        out.extend(struct.pack("<I", len(node.entries)))
        for key, value in node.entries:
            if isinstance(key, bool):
                raise TypeError("chave booleana não suportada")
            if isinstance(key, str):
                out.append(KEY_STRING)
                out.extend(encode_varint(index[key]))
            elif isinstance(key, int):
                out.append(KEY_INT)
                out.extend(encode_varint(key))
            else:
                raise TypeError(f"tipo de chave não suportado: {type(key).__name__}")
            if isinstance(value, Table):
                out.append(VALUE_TABLE)
                write(value, depth + 1)
            elif isinstance(value, str):
                out.append(VALUE_STRING)
                out.extend(encode_varint(index[value]))
            elif isinstance(value, Int32):
                out.append(VALUE_INT32)
                out.extend(struct.pack("<i", value.value))
            elif isinstance(value, Float32):
                out.append(VALUE_FLOAT32)
                out.extend(value.raw)
            else:
                raise TypeError(f"tipo de valor não suportado: {type(value).__name__}")

    write(doc.root, 0)
    return bytes(out)


def to_python(node: Table) -> dict:
    """Visão dict simplificada (perde duplicatas e tipos exatos; só para inspeção)."""
    result: dict = {}
    for key, value in node.entries:
        if isinstance(value, Table):
            result[key] = to_python(value)
        elif isinstance(value, (Int32, Float32)):
            result[key] = value.value
        else:
            result[key] = value
    return result


def iter_strings(node: Table, path: tuple = ()) -> Iterator[tuple[tuple, str, str]]:
    """Percorre ``(caminho, 'key'|'value', texto)`` para toda string da árvore."""
    for key, value in node.entries:
        here = path + (key,)
        if isinstance(key, str):
            yield here, "key", key
        if isinstance(value, str):
            yield here, "value", value
        elif isinstance(value, Table):
            yield from iter_strings(value, here)
