"""Formatos DfT/Def e varint (dados sintéticos; teste real opcional se o jogo existir)."""
from __future__ import annotations

from pathlib import Path
import struct

import pytest

from conftest import REAL_GAME, font_record
from ukloc.formats import FormatError, NonCanonicalError, UnknownTypeError
from ukloc.formats.defdb import (
    DefDB, DefList, DefTable, F32, I16, U8, canonical_strings as def_strings, parse_def, serialize_def,
)
from ukloc.formats.dft import (
    DfTFile, Float32, Int32, Table, canonical_strings, parse_dft, serialize_dft, to_python,
)
from ukloc.formats.varint import encode_varint, observed_width, read_varint


# ----------------------------------------------------------------- varint
@pytest.mark.parametrize("value,expected", [
    (0, b"\x00"), (127, b"\x7f"), (128, b"\x80\x01"), (1023, b"\xff\x07"),
    (1024, b"\x80\x88\x00"), (2225, b"\xb1\x91\x00"), ((1 << 21) - 1, b"\xff\xff\x7f"),
])
def test_varint_observed_rule(value, expected):
    assert encode_varint(value) == expected
    assert read_varint(expected, 0) == (value, len(expected), len(expected))


def test_varint_limits():
    with pytest.raises(ValueError):
        encode_varint(1 << 21)
    with pytest.raises(ValueError):
        observed_width(-1)
    with pytest.raises(FormatError):
        read_varint(b"\x80\x80", 0)


# ----------------------------------------------------------------- DfT
def sample_tree(n: int = 1200) -> Table:
    body = Table([(f"key_{i}", f"valor {i} {{color_text}}%1") for i in range(n)])
    body.entries.append(("same_value", "valor 0 {color_text}%1"))  # deduplicação
    body.entries.append(("nested", Table([(0, Int32(-5)), (1, Float32.from_float(0.5)),
                                          ("nan", Float32(b"\x01\x00\xc0\x7f"))])))
    return Table([("root", body)])


def test_dft_roundtrip_and_canonical_order():
    doc = DfTFile(1, sample_tree())
    data = serialize_dft(doc)
    back = parse_dft(data)
    assert serialize_dft(back) == data
    strings = canonical_strings(back.root)
    assert strings[:3] == ["root", "key_0", "valor 0 {color_text}%1"]
    assert len(strings) == len(set(strings)) > 1024  # força varints de 3 bytes
    nested = back.root.get("root").get("nested")
    assert nested.get(0) == Int32(-5) and nested.get("nan").raw == b"\x01\x00\xc0\x7f"
    assert to_python(back.root)["root"]["nested"][1] == 0.5


def test_dft_serialize_is_deterministic():
    a = serialize_dft(DfTFile(1, sample_tree(50)))
    b = serialize_dft(DfTFile(1, sample_tree(50)))
    assert a == b


def test_dft_rejects_corruption():
    data = serialize_dft(DfTFile(1, Table([("a", Table([("b", "c")]))])))
    with pytest.raises(FormatError):
        parse_dft(b"XXXX" + data[4:])
    with pytest.raises(FormatError):
        parse_dft(data[:-1])
    with pytest.raises(FormatError):
        parse_dft(data + b"\x00")
    bad = bytearray(data)
    bad[-2] = 9
    with pytest.raises(UnknownTypeError) as exc:
        parse_dft(bytes(bad))
    assert exc.value.type_byte == 9
    bad = bytearray(data)
    bad[-1] = 50  # índice de string fora da tabela
    with pytest.raises(FormatError):
        parse_dft(bytes(bad))


def test_dft_noncanonical_detected():
    # Tabela de strings com ordem trocada: válido, porém não canônico.
    strings = [b"c", b"a", b"b"]
    body = struct.pack("<I", 1) + bytes([0, 1, 4]) + struct.pack("<I", 1) + bytes([0, 2, 3, 0])
    data = b"\xffDfT" + struct.pack("<II", 1, 3) + b"".join(bytes([len(s)]) + s for s in strings) + body
    with pytest.raises(NonCanonicalError):
        parse_dft(data)
    relaxed = parse_dft(data, strict=False)
    assert serialize_dft(relaxed) != data  # o serializador sempre emite a forma canônica


def test_dft_rejects_unsupported_python_types():
    with pytest.raises(TypeError):
        serialize_dft(DfTFile(1, Table([("a", 3.5)])))  # type: ignore[list-item]
    with pytest.raises(ValueError):
        Int32(2**31)


# ----------------------------------------------------------------- Def
def test_def_roundtrip_with_wide_string_indices():
    records = DefList([font_record(f"font_{i}", [32, 0xE3, 1000 + i]) for i in range(300)])
    db = DefDB(1, records)
    data = serialize_def(db)
    assert b"\x06" in data  # índices >= 256 usam o tipo 0x06 (varint)
    back = parse_def(data)
    assert serialize_def(back) == data
    assert def_strings(back.root)[0] == "name"


def test_def_rejects_unknown_type_and_bad_trailer():
    data = bytearray(serialize_def(DefDB(1, DefList([font_record("f", [32])]))))
    data[16] = 3  # tipo 0x03 nunca observado
    with pytest.raises(UnknownTypeError):
        parse_def(bytes(data))
    good = serialize_def(DefDB(1, DefList([])))
    with pytest.raises(FormatError):
        parse_def(good + b"\x00")


def test_def_noncanonical_wide_index():
    db = DefDB(1, DefList(["a"]))
    data = bytearray(serialize_def(db))
    # troca "05 00" (índice u8) por "06 00" (varint com índice < 256): não canônico
    pos = data.index(b"\x05\x00", 16)
    data[pos] = 6
    with pytest.raises(NonCanonicalError):
        parse_def(bytes(data))


def test_def_value_ranges():
    with pytest.raises(ValueError):
        U8(256)
    with pytest.raises(ValueError):
        I16(40000)
    with pytest.raises(ValueError):
        F32(b"\x00")


# ----------------------------------------------------------------- jogo real (opcional)
@pytest.mark.skipif(not REAL_GAME.is_dir(), reason="instalação do jogo ausente (ex.: CI)")
def test_real_game_roundtrip_all_files():
    rfiles = sorted((REAL_GAME / "base").glob("*.rfile"))
    dbs = sorted(REAL_GAME.glob("*/_*.db"))
    assert len(rfiles) == 107 and len(dbs) == 22
    for path in rfiles:
        data = path.read_bytes()
        assert serialize_dft(parse_dft(data)) == data, path.name
    for path in dbs:
        data = path.read_bytes()
        assert serialize_def(parse_def(data)) == data, path.name
