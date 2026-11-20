"""Compara a localização de duas builds do Underkeep e o catálogo PT-BR (Fase 2A).

Entradas (todas locais, nunca a pasta da Steam):

* ``--old`` / ``--new``: diretórios gerados por ``ukloc_cli.py extract --out`` (contêm
  ``catalog/<categoria>_<idioma>.json``), um para cada build;
* ``--l10n``: catálogos PT-BR (``l10n/pt-BR``).

Classificação por entrada (referência editorial ``en``; slot físico ``es``):

``unchanged``      mesmo ID e mesmo texto en nas duas builds
``added``          ID novo na referência
``removed``        ID que deixou de existir na referência
``changed``        mesmo ID, texto en diferente
``slot_only``      texto en igual, mas o texto es (slot substituído) mudou
``moved``          mesmo ID passou de uma categoria para outra
``renamed``        ID removido cujo texto en reaparece idêntico em um ID novo

Mudanças estruturais (versão DfT, ordem dos IDs, tokens protegidos, cobertura do slot) e o estado do
catálogo PT-BR (preservadas, a revisar, a traduzir, órfãs) também são relatados.

O relatório JSON contém somente IDs, contagens e hashes: nenhum texto original do jogo. Ele deve ficar
em ``audit/local/`` (ignorado pelo Git).
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ukloc import markup  # noqa: E402

CATEGORIES = ("common", "skills", "items", "game")
REPORT_SCHEMA = "ukloc.build_compare/1"


class CompareError(Exception):
    """Entrada ausente ou malformada."""


def text_sha256(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Extract:
    """Uma tabela extraída: ordem dos IDs, textos e metadados (sem copiar nada para o relatório)."""
    build: str | None
    dft_version: int | None
    order: list[str]
    texts: dict[str, str]
    source_sha256: str | None = None


def load_extract(root: Path, category: str, language: str) -> Extract:
    path = root / "catalog" / f"{category}_{language}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CompareError(f"não foi possível ler {path}: {exc}") from exc
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise CompareError(f"{path}: 'entries' deve ser lista")
    order: list[str] = []
    texts: dict[str, str] = {}
    for item in entries:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not isinstance(item.get("text"), str):
            raise CompareError(f"{path}: entrada malformada")
        if item["id"] in texts:
            raise CompareError(f"{path}: ID duplicado {item['id']!r}")
        order.append(item["id"])
        texts[item["id"]] = item["text"]
    return Extract(data.get("game_build"), data.get("dft_version"), order, texts, data.get("source_sha256"))


def token_signature(text: str) -> dict[str, Any]:
    """Assinatura dos tokens protegidos (tags, placeholders, quebras), comparável entre versões."""
    return {"tags": sorted(Counter(markup.tag_tokens(text)).items()),
            "placeholders": sorted(markup.placeholders(text).items()),
            "breaks": markup.line_breaks(text)}


@dataclass
class CategoryDiff:
    category: str
    old_count: int
    new_count: int
    unchanged: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    slot_only: list[str] = field(default_factory=list)
    token_changes: list[str] = field(default_factory=list)
    structural: list[str] = field(default_factory=list)


def diff_category(category: str, old_en: Extract, new_en: Extract, old_es: Extract, new_es: Extract) -> CategoryDiff:
    diff = CategoryDiff(category, len(old_en.texts), len(new_en.texts))
    for entry_id in new_en.order:
        if entry_id not in old_en.texts:
            diff.added.append(entry_id)
        elif old_en.texts[entry_id] != new_en.texts[entry_id]:
            diff.changed.append(entry_id)
            if token_signature(old_en.texts[entry_id]) != token_signature(new_en.texts[entry_id]):
                diff.token_changes.append(entry_id)
        elif old_es.texts.get(entry_id) != new_es.texts.get(entry_id):
            diff.slot_only.append(entry_id)
        else:
            diff.unchanged.append(entry_id)
    diff.removed = [i for i in old_en.order if i not in new_en.texts]
    if old_en.dft_version != new_en.dft_version or old_es.dft_version != new_es.dft_version:
        diff.structural.append(f"versão DfT mudou (en {old_en.dft_version}->{new_en.dft_version}, "
                               f"es {old_es.dft_version}->{new_es.dft_version})")
    common = [i for i in new_en.order if i in old_en.texts]
    old_common = [i for i in old_en.order if i in new_en.texts]
    if common != old_common:
        diff.structural.append("ordem relativa dos IDs existentes mudou na referência en")
    es_only_removed = sorted(set(old_es.texts) - set(new_es.texts) - set(diff.removed))
    if es_only_removed:
        diff.structural.append(f"{len(es_only_removed)} ID(s) removidos apenas do slot es: {es_only_removed[:10]}")
    missing_slot = sorted(set(new_en.texts) - set(new_es.texts))
    if missing_slot:
        diff.structural.append(f"{len(missing_slot)} ID(s) en sem correspondente no slot es: {missing_slot[:10]}")
    extra_slot = sorted(set(new_es.texts) - set(new_en.texts))
    if extra_slot:
        diff.structural.append(f"{len(extra_slot)} ID(s) só no slot es: {extra_slot[:10]}")
    return diff


def find_moves(diffs: Mapping[str, CategoryDiff]) -> list[dict[str, str]]:
    """Mesmo ID removido de uma categoria e adicionado em outra."""
    moves = []
    for src, a in diffs.items():
        for dst, b in diffs.items():
            if src != dst:
                for entry_id in sorted(set(a.removed) & set(b.added)):
                    moves.append({"id": entry_id, "from": src, "to": dst})
    return moves


def find_renames(diffs: Mapping[str, CategoryDiff], old: Mapping[str, Extract],
                 new: Mapping[str, Extract]) -> list[dict[str, str]]:
    """ID removido cujo texto en reaparece idêntico em um ID adicionado (qualquer categoria)."""
    added_by_hash: dict[str, list[tuple[str, str]]] = {}
    for category, diff in diffs.items():
        for entry_id in diff.added:
            added_by_hash.setdefault(text_sha256(new[category].texts[entry_id]), []).append((category, entry_id))
    renames = []
    for category, diff in diffs.items():
        for entry_id in diff.removed:
            for dst, new_id in added_by_hash.get(text_sha256(old[category].texts[entry_id]), []):
                if new_id != entry_id:
                    renames.append({"from": f"{category}/{entry_id}", "to": f"{dst}/{new_id}"})
    return renames


@dataclass
class CatalogState:
    category: str
    entries: int
    preserved: list[str] = field(default_factory=list)
    needs_review: list[str] = field(default_factory=list)
    orphaned: list[str] = field(default_factory=list)
    to_translate: list[str] = field(default_factory=list)
    baseline_mismatch: list[str] = field(default_factory=list)


def catalog_state(category: str, catalog: Mapping[str, Any], old_en: Extract, new_en: Extract) -> CatalogState:
    entries = catalog.get("entries", {})
    state = CatalogState(category, len(entries))
    for entry_id, entry in sorted(entries.items()):
        source = entry.get("source_sha256")
        if entry_id in old_en.texts and text_sha256(old_en.texts[entry_id]) != source:
            state.baseline_mismatch.append(entry_id)
        if entry_id not in new_en.texts:
            state.orphaned.append(entry_id)
        elif text_sha256(new_en.texts[entry_id]) == source:
            state.preserved.append(entry_id)
        else:
            state.needs_review.append(entry_id)
    state.to_translate = [i for i in new_en.order if i not in entries]
    return state


def compare(old_root: Path, new_root: Path, l10n_root: Path, categories: Iterable[str] = CATEGORIES) -> dict[str, Any]:
    old: dict[str, Extract] = {}
    new: dict[str, Extract] = {}
    diffs: dict[str, CategoryDiff] = {}
    states: dict[str, CatalogState] = {}
    old_es_all: dict[str, Extract] = {}
    for category in categories:
        old[category], new[category] = load_extract(old_root, category, "en"), load_extract(new_root, category, "en")
        old_es_all[category] = load_extract(old_root, category, "es")
        new_es = load_extract(new_root, category, "es")
        diffs[category] = diff_category(category, old[category], new[category], old_es_all[category], new_es)
        path = l10n_root / f"{category}.json"
        try:
            catalog = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CompareError(f"não foi possível ler {path}: {exc}") from exc
        states[category] = catalog_state(category, catalog, old[category], new[category])
    builds = {"old": sorted({e.build for e in old.values()} - {None}),
              "new": sorted({e.build for e in new.values()} - {None})}
    totals = Counter()
    report_categories: dict[str, Any] = {}
    for category in categories:
        d, s = diffs[category], states[category]
        counts = {"old_entries": d.old_count, "new_entries": d.new_count, "unchanged": len(d.unchanged),
                  "added": len(d.added), "removed": len(d.removed), "changed": len(d.changed),
                  "slot_only": len(d.slot_only), "token_changes": len(d.token_changes),
                  "catalog_entries": s.entries, "preserved": len(s.preserved), "needs_review": len(s.needs_review),
                  "orphaned": len(s.orphaned), "to_translate": len(s.to_translate),
                  "baseline_mismatch": len(s.baseline_mismatch)}
        totals.update(counts)
        report_categories[category] = {
            "counts": counts,
            "added": d.added, "removed": d.removed, "changed": d.changed, "slot_only": d.slot_only,
            "token_changes": d.token_changes, "structural": d.structural,
            "catalog": {"needs_review": s.needs_review, "orphaned": s.orphaned, "to_translate": s.to_translate,
                        "baseline_mismatch": s.baseline_mismatch},
            "dft_version": {"old": old[category].dft_version, "new": new[category].dft_version},
            "source_sha256": {"old_en": old[category].source_sha256, "new_en": new[category].source_sha256},
        }
    return {"schema": REPORT_SCHEMA, "builds": builds, "totals": dict(totals),
            "moved": find_moves(diffs), "renamed": find_renames(diffs, old, new),
            "categories": report_categories,
            "note": "Somente IDs, contagens e hashes; nenhum texto original do jogo."}


def summary_lines(report: Mapping[str, Any]) -> list[str]:
    t = report["totals"]
    lines = [f"Builds: {report['builds']['old']} -> {report['builds']['new']}",
             f"Entradas en: {t['old_entries']} -> {t['new_entries']} (novas {t['added']}, removidas {t['removed']}, "
             f"alteradas {t['changed']}, só slot es {t['slot_only']}, tokens alterados {t['token_changes']})",
             f"Catálogo PT-BR: {t['catalog_entries']} entradas; preservadas {t['preserved']}, a revisar "
             f"{t['needs_review']}, órfãs {t['orphaned']}, a traduzir {t['to_translate']}",
             f"Movidas: {len(report['moved'])}; renomeadas: {len(report['renamed'])}"]
    for category, data in report["categories"].items():
        c = data["counts"]
        lines.append(f"  {category}: {c['old_entries']}->{c['new_entries']} +{c['added']} -{c['removed']} "
                     f"~{c['changed']} es~{c['slot_only']} | revisar {c['needs_review']} traduzir {c['to_translate']} "
                     f"órfãs {c['orphaned']}")
        for problem in data["structural"]:
            lines.append(f"    estrutura: {problem}")
        if c["baseline_mismatch"]:
            lines.append(f"    AVISO: {c['baseline_mismatch']} entradas do catálogo não batem com a build antiga")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--old", type=Path, required=True, help="extração da build anterior (extract --out)")
    parser.add_argument("--new", type=Path, required=True, help="extração da build nova (extract --out)")
    parser.add_argument("--l10n", type=Path, default=ROOT / "l10n" / "pt-BR", help="catálogos PT-BR")
    parser.add_argument("--report", type=Path, help="relatório JSON (use audit/local/, ignorado pelo Git)")
    args = parser.parse_args(argv)
    try:
        report = compare(args.old, args.new, args.l10n)
    except CompareError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    for line in summary_lines(report):
        print(line)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"Relatório: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
