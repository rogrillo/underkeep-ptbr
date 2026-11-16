"""Cobertura de glifos derivada de ``_font.db`` (métricas BMFont-like)."""
from __future__ import annotations

from pathlib import Path

from .formats.defdb import DefDB, DefList, DefTable, parse_def, to_python

# Fontes de console/editor (preload) não renderizam texto de jogo.
NON_GAME_FONTS = frozenset({"editor", "console"})


def font_glyphs(db: DefDB) -> dict[str, frozenset[int]]:
    if not isinstance(db.root, DefList):
        raise ValueError("raiz de _font.db não é lista")
    result: dict[str, frozenset[int]] = {}
    for record in db.root.items:
        if not isinstance(record, DefTable):
            raise ValueError("registro de fonte inválido")
        font = to_python(record)
        glyphs = font["metadata"]["glyphs"]
        result[font["name"]] = frozenset(int(glyph["id"]) for glyph in glyphs)
    return result


def game_supported_codepoints(game_root: Path) -> frozenset[int]:
    """Interseção dos glifos de todas as fontes de jogo (texto pode cair em qualquer uma)."""
    sets: list[frozenset[int]] = []
    for db_path in sorted(game_root.glob("*/_font.db")):
        for name, glyphs in font_glyphs(parse_def(db_path.read_bytes())).items():
            if name not in NON_GAME_FONTS:
                sets.append(glyphs)
    if not sets:
        raise ValueError("nenhuma fonte de jogo encontrada")
    common = sets[0]
    for glyphs in sets[1:]:
        common &= glyphs
    return common
