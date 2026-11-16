"""Container ``\\xFFDef`` (bancos de recursos ``_*.db`` de cada pack).

Layout observado (22/22 ``.db`` da build 26592006, round-trip byte a byte)::

    0   magic        FF 44 65 66
    4   u8           versão (=1)
    5   u32 LE       offset da tabela de strings
    9   7 bytes      reservados (zeros em todos os arquivos)
    16  valor raiz   (tipado, recursivo)
    S   u32 LE       N strings, depois N x [varint comprimento][UTF-8]
    fim 4 bytes      trailer (zeros em todos os arquivos)

Tipos de valor observados:

    0x01 u8 · 0x02 i16 LE · 0x04 float32 LE
    0x05 string, índice u8 (índices < 256)
    0x06 string, índice varint (índices >= 256; mesma regra de largura do DfT)
    0x07 lista: u32 n + n valores
    0x08 tabela: u32 n + n pares (chave, valor) — chaves observadas: sempre string

Tipo 0x03 e outros nunca foram observados e levantam :class:`UnknownTypeError`.
Strings seguem a ordem canônica (primeira ocorrência, pré-ordem, chave antes do valor).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import struct
from typing import Iterator, Union

from . import FormatError, NonCanonicalError, UnknownTypeError
from .varint import encode_varint, observed_width, read_varint

MAGIC = b"\xffDef"
HEADER_SIZE = 16
T_U8, T_I16, T_F32, T_STR8, T_STRV, T_LIST, T_TABLE = 1, 2, 4, 5, 6, 7, 8
MAX_DEPTH = 64


@dataclass(frozen=True)
class U8:
    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not 0 <= self.value <= 255:
            raise ValueError(f"U8 fora do intervalo: {self.value!r}")


@dataclass(frozen=True)
class I16:
    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not -32768 <= self.value <= 32767:
            raise ValueError(f"I16 fora do intervalo: {self.value!r}")


@dataclass(frozen=True)
class F32:
    raw: bytes

    def __post_init__(self) -> None:
        if len(self.raw) != 4:
            raise ValueError("F32 exige 4 bytes")

    @property
    def value(self) -> float:
        return struct.unpack("<f", self.raw)[0]


DefValue = Union[U8, I16, F32, str, "DefList", "DefTable"]


@dataclass
class DefList:
    items: list[DefValue] = field(default_factory=list)


@dataclass
class DefTable:
    entries: list[tuple[DefValue, DefValue]] = field(default_factory=list)

    def get(self, key: str, default: DefValue | None = None) -> DefValue | None:
        for entry_key, value in self.entries:
            if entry_key == key:
                return value
        return default


@dataclass
class DefDB:
    version: int
    root: DefValue
    reserved: bytes = b"\x00" * 7
    trailer: bytes = b"\x00" * 4


def parse_def(data: bytes, *, strict: bool = True) -> DefDB:
    if data[:4] != MAGIC or len(data) < HEADER_SIZE + 8:
        raise FormatError("assinatura Def ausente ou arquivo curto")
    version = data[4]
    (strtab,) = struct.unpack_from("<I", data, 5)
    reserved = data[9:16]
    if not HEADER_SIZE <= strtab <= len(data) - 8:
        raise FormatError("offset da tabela de strings inválido")
    noncanonical: list[str] = []
    (count,) = struct.unpack_from("<I", data, strtab)
    pos = strtab + 4
    strings: list[str] = []
    for index in range(count):
        length, pos, width = read_varint(data, pos)
        if width != observed_width(length):
            noncanonical.append("largura de varint fora da regra (tabela de strings)")
        if pos + length > len(data):
            raise FormatError(f"string {index} truncada")
        try:
            strings.append(data[pos:pos + length].decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise FormatError(f"string {index} não é UTF-8 válido") from exc
        pos += length
    if len(data) - pos != 4:
        raise FormatError(f"trailer inesperado: {len(data) - pos} bytes após as strings")
    trailer = data[pos:]

    body_pos = HEADER_SIZE

    def need(size: int) -> None:
        if body_pos + size > strtab:
            raise FormatError("valor ultrapassa o corpo")

    def string_at(index: int) -> str:
        if index >= len(strings):
            raise FormatError(f"índice de string {index} fora da tabela ({len(strings)})")
        return strings[index]

    def value(depth: int) -> DefValue:
        nonlocal body_pos
        if depth > MAX_DEPTH:
            raise FormatError("aninhamento excessivo")
        need(1)
        kind = data[body_pos]
        body_pos += 1
        if kind == T_U8:
            need(1)
            body_pos += 1
            return U8(data[body_pos - 1])
        if kind == T_I16:
            need(2)
            body_pos += 2
            return I16(struct.unpack_from("<h", data, body_pos - 2)[0])
        if kind == T_F32:
            need(4)
            body_pos += 4
            return F32(data[body_pos - 4:body_pos])
        if kind == T_STR8:
            need(1)
            body_pos += 1
            return string_at(data[body_pos - 1])
        if kind == T_STRV:
            index, body_pos, width = read_varint(data, body_pos)
            if index < 256 or width != observed_width(index):
                noncanonical.append("índice de string 0x06 fora da regra")
            return string_at(index)
        if kind in (T_LIST, T_TABLE):
            need(4)
            (items,) = struct.unpack_from("<I", data, body_pos)
            body_pos += 4
            if kind == T_LIST:
                return DefList([value(depth + 1) for _ in range(items)])
            table = DefTable()
            for _ in range(items):
                key = value(depth + 1)
                table.entries.append((key, value(depth + 1)))
            return table
        raise UnknownTypeError("Def", kind, body_pos - 1)

    root = value(0)
    if body_pos != strtab:
        raise FormatError("corpo não termina no offset da tabela de strings")
    if canonical_strings(root) != strings:
        noncanonical.append("tabela de strings fora da ordem canônica")
    if strict and noncanonical:
        raise NonCanonicalError("; ".join(sorted(set(noncanonical))))
    return DefDB(version, root, reserved, trailer)


def canonical_strings(root: DefValue) -> list[str]:
    order: list[str] = []
    seen: set[str] = set()

    def walk(node: DefValue) -> None:
        if isinstance(node, str):
            if node not in seen:
                seen.add(node)
                order.append(node)
        elif isinstance(node, DefList):
            for item in node.items:
                walk(item)
        elif isinstance(node, DefTable):
            for key, item in node.entries:
                walk(key)
                walk(item)

    walk(root)
    return order


def serialize_def(db: DefDB) -> bytes:
    strings = canonical_strings(db.root)
    index = {text: i for i, text in enumerate(strings)}
    body = bytearray()

    def write(node: DefValue, depth: int) -> None:
        if depth > MAX_DEPTH:
            raise FormatError("aninhamento excessivo")
        if isinstance(node, U8):
            body.extend((T_U8, node.value))
        elif isinstance(node, I16):
            body.append(T_I16)
            body.extend(struct.pack("<h", node.value))
        elif isinstance(node, F32):
            body.append(T_F32)
            body.extend(node.raw)
        elif isinstance(node, str):
            i = index[node]
            if i < 256:
                body.extend((T_STR8, i))
            else:
                body.append(T_STRV)
                body.extend(encode_varint(i))
        elif isinstance(node, DefList):
            body.append(T_LIST)
            body.extend(struct.pack("<I", len(node.items)))
            for item in node.items:
                write(item, depth + 1)
        elif isinstance(node, DefTable):
            body.append(T_TABLE)
            body.extend(struct.pack("<I", len(node.entries)))
            for key, item in node.entries:
                write(key, depth + 1)
                write(item, depth + 1)
        else:
            raise TypeError(f"tipo Def não suportado: {type(node).__name__}")

    write(db.root, 0)
    if len(db.reserved) != 7 or len(db.trailer) != 4:
        raise ValueError("reserved deve ter 7 bytes e trailer 4 bytes")
    out = bytearray(MAGIC)
    out.append(db.version)
    out += struct.pack("<I", HEADER_SIZE + len(body))
    out += db.reserved
    out += body
    out += struct.pack("<I", len(strings))
    for text in strings:
        raw = text.encode("utf-8")
        out += encode_varint(len(raw)) + raw
    out += db.trailer
    return bytes(out)


def to_python(node: DefValue):
    if isinstance(node, (U8, I16, F32)):
        return node.value
    if isinstance(node, DefList):
        return [to_python(item) for item in node.items]
    if isinstance(node, DefTable):
        return {to_python(k): to_python(v) for k, v in node.entries}
    return node


def iter_records(db: DefDB) -> Iterator[DefTable]:
    """Bancos de pack: raiz = lista de registros-tabela."""
    if not isinstance(db.root, DefList):
        raise FormatError("raiz do banco não é lista")
    for item in db.root.items:
        if not isinstance(item, DefTable):
            raise FormatError("registro do banco não é tabela")
        yield item
