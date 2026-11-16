"""Análise de referências a IDs de texto em definições, níveis e no executável.

Heurísticas (documentadas no relatório):

* Referência **exata**: um valor string de def/level igual a um ID de texto.
* Referência **em script**: identificador citado no código de um campo ``script``,
  ignorando comentários ``// ...`` (que contêm anotações em inglês das falas).
* Referência **no executável**: ID presente como string ASCII no ``underkeep.exe``.
* Campo "de texto": nome de campo cujos valores são majoritariamente IDs de texto;
  valores desse campo que não existem em nenhuma tabela são **referências órfãs**.

Saídas contêm apenas IDs, nomes de arquivos e contagens — nunca texto do jogo.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
import re
from typing import Iterable, Mapping

from .formats.dft import parse_dft, iter_strings
from .textdb import TextTable

COMMENT_RE = re.compile(r"//[^\r\n]*")
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
EXE_IDENT_RE = re.compile(rb"[A-Za-z0-9_%]{3,}")
GROUP_SUFFIX_RE = re.compile(r"_(\d+)$")
TEXT_FIELD_NAME_RE = re.compile(r"text|tooltip|name|narrator|hint|title|desc")
ID_LIKE_RE = re.compile(r"[a-z][a-z0-9_]*")


@dataclass
class DefReferences:
    exact: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    script: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    field_values: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))


def script_identifiers(script: str) -> set[str]:
    return set(IDENT_RE.findall(COMMENT_RE.sub("", script)))


def collect_def_references(base_dir: Path) -> DefReferences:
    refs = DefReferences()
    for path in sorted(base_dir.glob("*.rfile")):
        if path.name.startswith("text_text_"):
            continue
        doc = parse_dft(path.read_bytes())
        for key_path, kind, text in iter_strings(doc.root):
            if kind != "value":
                continue
            field_name = next((k for k in reversed(key_path) if isinstance(k, str)), "")
            if field_name == "script":
                for ident in script_identifiers(text):
                    refs.script[ident].add(path.name)
            else:
                refs.exact[text].add(path.name)
                refs.field_values[field_name][text] += 1
    return refs


def exe_identifiers(exe: bytes) -> set[str]:
    return {m.group().decode("ascii") for m in EXE_IDENT_RE.finditer(exe)}


def group_of(entry_id: str) -> str:
    return GROUP_SUFFIX_RE.sub("", entry_id)


def analyze(tables: Mapping[tuple[str, str], TextTable], refs: DefReferences,
            exe_ids: Iterable[str], reference: str = "en") -> dict:
    exe_ids = set(exe_ids)
    categories = sorted({cat for cat, _ in tables})
    languages = sorted({lang for _, lang in tables})
    all_ids = {key for table in tables.values() for key in table.ids()}

    def status(entry_id: str) -> str:
        if entry_id in refs.exact:
            return "exact"
        if entry_id in refs.script:
            return "script"
        if entry_id in exe_ids:
            return "exe"
        if group_of(entry_id) in refs.exact or group_of(entry_id) in refs.script:
            return "group_prefix"
        return "none"

    report: dict = {"reference": reference, "categories": {}, "orphan_references": {},
                    "text_fields": {}}
    for cat in categories:
        ref_table = tables.get((cat, reference))
        if ref_table is None:
            continue
        ref_ids = ref_table.ids()
        others = {lang: set(tables[(cat, lang)].ids()) for lang in languages
                  if lang != reference and (cat, lang) in tables}
        common_other = set.intersection(*others.values()) if others else set()
        union_other = set.union(*others.values()) if others else set()
        only_ref = [i for i in ref_ids if i not in union_other]
        only_other = sorted(common_other - set(ref_ids))
        ref_status = Counter(status(i) for i in ref_ids)
        report["categories"][cat] = {
            "reference_ids": len(ref_ids),
            "other_language_key_sets_identical": len({frozenset(s) for s in others.values()}) <= 1,
            "only_in_reference": [{"id": i, "ref": status(i)} for i in only_ref],
            "only_in_other_languages": [{"id": i, "ref": status(i)} for i in only_other],
            "only_in_other_languages_by_ref": dict(Counter(status(i) for i in only_other)),
            "reference_ids_by_ref": dict(ref_status),
        }
    # Campos que guardam IDs de texto -> referências órfãs. Campos cujo nome não
    # sugere texto (ex.: listas de itens, cujas chaves coincidem com IDs de item)
    # são classificados como "id_field" e não geram órfãs.
    for field_name, values in sorted(refs.field_values.items()):
        total = sum(values.values())
        hits = sum(n for v, n in values.items() if v in all_ids)
        if total >= 5 and hits / total >= 0.8:
            kind = "text_field" if TEXT_FIELD_NAME_RE.search(field_name) else "id_field"
            orphans = sorted(v for v in values if v not in all_ids and v != "")
            report["text_fields"][field_name] = {"values": total, "text_id_ratio": round(hits / total, 3),
                                                 "kind": kind, "non_text_values": len(orphans)}
            if orphans and kind == "text_field":
                report["orphan_references"][field_name] = [
                    {"value_sha256": sha256(v.encode("utf-8")).hexdigest()[:16],
                     "looks_like_id": bool(ID_LIKE_RE.fullmatch(v)),
                     "value_if_id": v if ID_LIKE_RE.fullmatch(v) else None,
                     "files": sorted(refs.exact[v])} for v in orphans]
    return report


def dialogue_context(table: TextTable, refs: DefReferences, extra_ids: Iterable[str] = ()) -> list[dict]:
    """Agrupa falas ``<grupo>_NN`` na ordem da tabela, com lacunas e referências."""
    order = table.ids() + [i for i in extra_ids if i not in set(table.ids())]
    groups: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for position, entry_id in enumerate(order):
        groups[group_of(entry_id)].append((position, entry_id))
    out = []
    for group, members in groups.items():
        numbers = [int(m.group(1)) for _, i in members if (m := GROUP_SUFFIX_RE.search(i))]
        gaps = sorted(set(range(1, max(numbers) + 1)) - set(numbers)) if numbers else []
        referenced_by = sorted({f for _, i in members for f in refs.exact.get(i, set()) | refs.script.get(i, set())}
                               | refs.exact.get(group, set()) | refs.script.get(group, set()))
        out.append({"group": group, "first_index": members[0][0],
                    "ids": [i for _, i in members], "numbering_gaps": gaps,
                    "referenced_by": referenced_by})
    out.sort(key=lambda item: item["first_index"])
    return out
