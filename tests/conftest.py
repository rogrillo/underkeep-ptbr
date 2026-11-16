"""Fixtures sintéticas: NENHUM byte do jogo real é usado nestes construtores."""
from __future__ import annotations

from pathlib import Path

import pytest

from ukloc.formats.defdb import DefDB, DefList, DefTable, F32, I16, U8, serialize_def
from ukloc.formats.dft import DfTFile, Table, serialize_dft
from ukloc.textdb import TextTable, build_text_table_bytes, text_file_name

SECRET = "COPYRIGHTED-PLACEHOLDER"
REAL_GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Underkeep")


def font_record(name: str, ids: list[int]) -> DefTable:
    glyphs = DefList([DefTable([("id", I16(i) if i > 255 else U8(i)), ("xadvance", U8(3))]) for i in ids])
    meta = DefTable([("line_height", U8(13)), ("scale", F32(b"\x00\x00\x80\x3f")),
                     ("glyphs", glyphs), ("kernings", DefList())])
    return DefTable([("name", name), ("def", "font/x.assets"), ("def_line", U8(1)),
                     ("metadata", meta), ("timestamp", U8(1))])


def rfile_record(name: str) -> DefTable:
    return DefTable([("name", name), ("def", "main.rfiles.txt"), ("def_line", U8(1)),
                     ("metadata", DefTable([("file", name.replace("/", "_") + ".rfile")])),
                     ("timestamp", U8(1))])


BASIC_GLYPHS = list(range(32, 127)) + [ord(c) for c in "áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇü"]


def make_fake_game(root: Path) -> Path:
    base = root / "base"
    base.mkdir(parents=True)
    en_common = [("menu_ok", f"{SECRET} {{color_text}}%1\\nfim"),
                 ("credits_no_localize", f"{SECRET} credits"),
                 ("tooltip_x", "{a:left}Abc{color_white}def")]
    es_common = [("menu_ok", f"{SECRET} ES {{color_text}}%1\\nfim"),
                 ("tooltip_x", "{a:left}Abc ES{color_white}def"),
                 ("credits", f"{SECRET} es credits")]
    en_game = [("npc_talk_01", f"{SECRET} um"), ("npc_talk_02", f"{SECRET} dois")]
    es_game = en_game + [("npc_talk_03", f"{SECRET} tres"), ("npc_cut_01", f"{SECRET} cortado")]
    tables = {("common", "en"): en_common, ("common", "es"): es_common,
              ("game", "en"): en_game, ("game", "es"): es_game}
    names = []
    for (cat, lang), entries in tables.items():
        data = build_text_table_bytes(TextTable(cat, lang, 1, entries))
        (base / text_file_name(cat, lang)).write_bytes(data)
        names.append(f"text/text_{cat}_{lang}.txt")
    script = "on_continue:\n  [state begin]\n  say npc_talk_01\n  // say [[npc_talk_03 comentário]]\n  say npc_talk_02\n"
    defs = Table([("encounter_npc", Table([("script", script), ("hp", Table())])),
                  ("obj", Table([("interact_text", "tooltip_x"), ("enter_text", "rotulo dev"),
                                 ("text", "menu_ok"), ("text2", "menu_ok")]))])
    (base / "def_def.txt.rfile").write_bytes(serialize_dft(DfTFile(1, defs)))
    for i in range(4):  # campo "text" com >= 5 valores para a heurística de campos
        level = Table([("ents", Table([(0, Table([("text", "menu_ok")]))]))])
        (base / f"level_L{i}.level.rfile").write_bytes(serialize_dft(DfTFile(1, level)))
    names.append("def/def.txt")
    (base / "_font.db").write_bytes(serialize_def(DefDB(1, DefList([font_record("f1", BASIC_GLYPHS)]))))
    (base / "_rfile.db").write_bytes(serialize_def(DefDB(1, DefList([rfile_record(n) for n in names]))))
    (root / "underkeep.exe").write_bytes(b"MZ\x00credits_no_localize\x00text_common_%1\x00")
    return root


@pytest.fixture
def fake_game(tmp_path: Path) -> Path:
    return make_fake_game(tmp_path / "game")
