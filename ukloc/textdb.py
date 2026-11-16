"""Tabelas de localização ``text_text_<categoria>_<idioma>.txt.rfile``.

Forma observada (28/28 arquivos): raiz DfT com uma única chave ``text_<cat>_<lang>``
apontando para uma tabela plana ``id (string) -> texto (string)``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from .formats import FormatError
from .formats.dft import DfTFile, Table, parse_dft, serialize_dft

TEXT_FILE_RE = re.compile(r"^text_text_(?P<cat>[a-z]+)_(?P<lang>[a-z]{2})\.txt\.rfile$")


def text_file_name(category: str, language: str) -> str:
    return f"text_text_{category}_{language}.txt.rfile"


def root_key(category: str, language: str) -> str:
    return f"text_{category}_{language}"


@dataclass
class TextTable:
    category: str
    language: str
    version: int = 1
    entries: list[tuple[str, str]] = field(default_factory=list)

    @property
    def root_key(self) -> str:
        return root_key(self.category, self.language)

    def ids(self) -> list[str]:
        return [key for key, _ in self.entries]

    def as_dict(self) -> dict[str, str]:
        return dict(self.entries)


def find_text_tables(base_dir: Path) -> dict[tuple[str, str], Path]:
    found: dict[tuple[str, str], Path] = {}
    for path in sorted(base_dir.glob("text_text_*.txt.rfile")):
        match = TEXT_FILE_RE.match(path.name)
        if match:
            found[(match["cat"], match["lang"])] = path
    return found


def text_table_from_dft(doc: DfTFile, category: str, language: str) -> TextTable:
    expected = root_key(category, language)
    if len(doc.root) != 1 or doc.root.entries[0][0] != expected:
        raise FormatError(f"raiz inesperada: esperado única chave {expected!r}")
    body = doc.root.entries[0][1]
    if not isinstance(body, Table):
        raise FormatError("corpo da tabela de texto não é tabela")
    entries: list[tuple[str, str]] = []
    for key, value in body.entries:
        if not isinstance(key, str) or not isinstance(value, str):
            raise FormatError(f"entrada não textual em {expected}: {key!r}")
        entries.append((key, value))
    return TextTable(category, language, doc.version, entries)


def load_text_table(data: bytes, category: str, language: str) -> TextTable:
    return text_table_from_dft(parse_dft(data), category, language)


def text_table_to_dft(table: TextTable) -> DfTFile:
    body = Table(list(table.entries))
    return DfTFile(table.version, Table([(table.root_key, body)]))


def build_text_table_bytes(table: TextTable) -> bytes:
    return serialize_dft(text_table_to_dft(table))
