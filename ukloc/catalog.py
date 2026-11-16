"""Catálogo de localização: JSON determinístico, IDs estáveis e hashes por entrada.

Os catálogos extraídos contêm texto original do jogo e só podem ser gravados em
diretórios ignorados pelo Git (``work/``, ``audit/local/``). Ver
:func:`ensure_untracked_output`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .textdb import TextTable

SCHEMA = "ukloc.catalog/1"
ALLOWED_OUTPUT_ROOTS = ("work", "audit/local")


def text_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def bytes_hash(data: bytes) -> str:
    return sha256(data).hexdigest()


@dataclass
class CatalogEntry:
    id: str
    index: int
    text: str
    source_sha256: str  # hash do texto original de onde a entrada veio


@dataclass
class Catalog:
    category: str
    language: str
    dft_version: int = 1
    game_build: str | None = None
    source_file: str | None = None
    source_sha256: str | None = None
    entries: list[CatalogEntry] = field(default_factory=list)


def catalog_from_table(table: TextTable, *, source_file: str | None = None,
                       source_bytes: bytes | None = None,
                       game_build: str | None = None) -> Catalog:
    return Catalog(
        category=table.category,
        language=table.language,
        dft_version=table.version,
        game_build=game_build,
        source_file=source_file,
        source_sha256=bytes_hash(source_bytes) if source_bytes is not None else None,
        entries=[CatalogEntry(key, i, text, text_hash(text))
                 for i, (key, text) in enumerate(table.entries)],
    )


def table_from_catalog(catalog: Catalog, *, language: str | None = None) -> TextTable:
    """Reconstrói a tabela na ordem de ``index``; ``language`` renomeia a raiz."""
    ordered = sorted(catalog.entries, key=lambda entry: entry.index)
    if [entry.index for entry in ordered] != list(range(len(ordered))):
        raise ValueError("índices do catálogo não são 0..n-1 contíguos")
    return TextTable(catalog.category, language or catalog.language, catalog.dft_version,
                     [(entry.id, entry.text) for entry in ordered])


def catalog_to_dict(catalog: Catalog) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "category": catalog.category,
        "language": catalog.language,
        "dft_version": catalog.dft_version,
        "game_build": catalog.game_build,
        "source_file": catalog.source_file,
        "source_sha256": catalog.source_sha256,
        "entries": [{"id": e.id, "index": e.index, "text": e.text,
                     "source_sha256": e.source_sha256} for e in catalog.entries],
    }


def catalog_to_json(catalog: Catalog) -> str:
    return json.dumps(catalog_to_dict(catalog), ensure_ascii=False, indent=1,
                      sort_keys=True) + "\n"


def catalog_from_json(text: str) -> Catalog:
    data = json.loads(text)
    if data.get("schema") != SCHEMA:
        raise ValueError(f"schema inesperado: {data.get('schema')!r}")
    entries = []
    for raw in data["entries"]:
        if not isinstance(raw.get("id"), str) or not isinstance(raw.get("text"), str):
            raise ValueError("entrada de catálogo sem id/text textual")
        entries.append(CatalogEntry(raw["id"], int(raw["index"]), raw["text"],
                                    raw.get("source_sha256") or text_hash(raw["text"])))
    return Catalog(data["category"], data["language"], int(data.get("dft_version", 1)),
                   data.get("game_build"), data.get("source_file"),
                   data.get("source_sha256"), entries)


def ensure_untracked_output(path: Path, project_root: Path, game_root: Path | None = None) -> Path:
    """Garante que a saída fique em ``work/`` ou ``audit/local/`` e fora do jogo."""
    resolved = path.resolve()
    if game_root is not None:
        game = game_root.resolve()
        if resolved == game or game in resolved.parents:
            raise ValueError("a saída não pode ficar dentro da instalação do jogo")
    allowed = [(project_root / root).resolve() for root in ALLOWED_OUTPUT_ROOTS]
    if not any(resolved == root or root in resolved.parents for root in allowed):
        raise ValueError(f"saída deve ficar em {', '.join(ALLOWED_OUTPUT_ROOTS)}: {path}")
    return resolved


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8", newline="\n")
    tmp.replace(path)


def write_bytes_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(content)
    tmp.replace(path)
