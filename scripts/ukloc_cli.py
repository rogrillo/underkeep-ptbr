#!/usr/bin/env python3
"""CLI de localização de Underkeep (Fases 1B/1C). Lê o jogo SOMENTE em modo leitura.

Subcomandos:
  roundtrip       parse+serialize de todos os .rfile (DfT) e _*.db (Def), em memória
  extract         28 tabelas -> catálogos JSON em work/, análise de idiomas em audit/local/
  gate-unchanged  catálogo sem alterações -> bytes idênticos ao original (em memória)
  build           catálogo JSON -> .rfile em work/ (nunca na Steam)
  pseudo          pseudo-localização do en no slot de outro idioma, em work/, com validação
  validate        valida um catálogo contra en (referência) e o idioma substituído
  inspect-db      resumo dos bancos Def (índice _rfile.db, timestamps, tipos)

Pack-sombra (Fase 1C-A):
  shadow-build      patch JSON -> pack-sombra completo em work/shadow/ (lê o jogo, não grava nele)
  shadow-verify     confere o pack-sombra contra o manifesto e contra a instalação atual
  shadow-install    instala em Documentos/Underkeep/mods/<pack> (DRY-RUN; --execute para aplicar)
  shadow-uninstall  remove o pack-sombra instalado (DRY-RUN; --execute para aplicar)
  shadow-status     estado do destino em Documentos

Catálogo PT-BR (Fase 1C-B, l10n/pt-BR/, sem texto original):
  l10n-add          acrescenta entradas pending para IDs (nunca sobrescreve traduções)
  l10n-validate     valida o catálogo contra en (referência) e es (slot); relata desatualizadas
  l10n-sheet        planilha de revisão com texto original -> work/l10n/ (não versionar)
  l10n-build        catálogo -> pack-sombra em work/shadow/<nome> + relatório de diferenças
  l10n-promote      promoção em lote (QA) de um lote para reviewed/approved, com nota rastreável

Todas as saídas ficam em work/ ou audit/local/ (ignorados pelo Git). A única exceção é
shadow-install/shadow-uninstall com --execute, que gravam/removem apenas
Documentos/Underkeep/mods/<pack> (nunca a pasta da Steam) e exigem aprovação explícita.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ukloc.catalog import (  # noqa: E402
    bytes_hash, catalog_from_json, catalog_from_table, catalog_to_json, ensure_untracked_output,
    table_from_catalog, write_bytes_atomic, write_text_atomic,
)
from ukloc.fonts import game_supported_codepoints  # noqa: E402
from ukloc.formats import FormatError  # noqa: E402
from ukloc.formats.defdb import DefTable, iter_records, parse_def, serialize_def, to_python  # noqa: E402
from ukloc.formats.dft import parse_dft, serialize_dft  # noqa: E402
from ukloc import markup  # noqa: E402
from ukloc.pseudo import pseudolocalize  # noqa: E402
from ukloc import l10n, shadow  # noqa: E402
from ukloc.refs import analyze, collect_def_references, dialogue_context, exe_identifiers  # noqa: E402
from ukloc.textdb import (  # noqa: E402
    TextTable, build_text_table_bytes, find_text_tables, load_text_table, text_file_name,
)
from ukloc.validate import load_exceptions, validate_catalog  # noqa: E402

DEFAULT_GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Underkeep")


# --------------------------------------------------------------------------- utilidades
def game_build(game_root: Path) -> str | None:
    manifest = game_root.parent.parent / "appmanifest_2411200.acf"
    try:
        match = re.search(r'"buildid"\s+"(\d+)"', manifest.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    return match.group(1) if match else None


def load_tables(game_root: Path) -> tuple[dict[tuple[str, str], TextTable], dict[tuple[str, str], bytes]]:
    base = game_root / "base"
    tables, raw = {}, {}
    for (cat, lang), path in find_text_tables(base).items():
        data = path.read_bytes()
        raw[(cat, lang)] = data
        tables[(cat, lang)] = load_text_table(data, cat, lang)
    if not tables:
        raise ValueError(f"nenhuma tabela de texto em {base}")
    return tables, raw


def resolve_exceptions(path: Path | None) -> list:
    """Caminho explícito precisa existir; o padrão do projeto é opcional."""
    if path is not None:
        return load_exceptions(path)
    default = PROJECT_ROOT / "data" / "validation_exceptions.json"
    return load_exceptions(default) if default.is_file() else []


def out_path(path: Path, game_root: Path | None) -> Path:
    return ensure_untracked_output(path, PROJECT_ROOT, game_root)


def dump_json(path: Path, data: Any) -> None:
    write_text_atomic(path, json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


# --------------------------------------------------------------------------- comandos
def cmd_roundtrip(args: argparse.Namespace) -> int:
    game = args.game_root
    failures: list[str] = []
    dft_ok = dft_total = 0
    for path in sorted((game / "base").glob("*.rfile")) + sorted((game / "preload").glob("*.rfile")):
        dft_total += 1
        data = path.read_bytes()
        try:
            if serialize_dft(parse_dft(data)) == data:
                dft_ok += 1
            else:
                failures.append(f"{path.name}: bytes diferentes")
        except FormatError as exc:
            failures.append(f"{path.name}: {exc}")
    def_ok = def_total = 0
    for path in sorted(game.glob("*/_*.db")):
        def_total += 1
        data = path.read_bytes()
        try:
            if serialize_def(parse_def(data)) == data:
                def_ok += 1
            else:
                failures.append(f"{path.parent.name}/{path.name}: bytes diferentes")
        except FormatError as exc:
            failures.append(f"{path.parent.name}/{path.name}: {exc}")
    print(f"DfT round-trip: {dft_ok}/{dft_total} idênticos")
    print(f"Def round-trip: {def_ok}/{def_total} idênticos")
    for failure in failures:
        print(f"  FALHA {failure}")
    return 0 if not failures else 2


def cmd_extract(args: argparse.Namespace) -> int:
    game = args.game_root
    out_dir = out_path(args.out, game)
    analysis_path = out_path(args.analysis, game)
    tables, raw = load_tables(game)
    build = game_build(game)
    manifest: dict[str, Any] = {"game_build": build, "catalogs": {}}
    for (cat, lang), table in sorted(tables.items()):
        name = text_file_name(cat, lang)
        catalog = catalog_from_table(table, source_file=f"base/{name}", source_bytes=raw[(cat, lang)],
                                     game_build=build)
        content = catalog_to_json(catalog)
        target = out_dir / "catalog" / f"{cat}_{lang}.json"
        write_text_atomic(target, content)
        manifest["catalogs"][f"{cat}_{lang}"] = {
            "file": target.relative_to(out_dir).as_posix(), "entries": len(catalog.entries),
            "source_sha256": catalog.source_sha256, "catalog_sha256": bytes_hash(content.encode("utf-8")),
        }
    dump_json(out_dir / "manifest.json", manifest)

    refs = collect_def_references(game / "base")
    exe_ids = exe_identifiers((game / "underkeep.exe").read_bytes())
    report = analyze(tables, refs, exe_ids, reference="en")
    report["game_build"] = build
    dump_json(analysis_path, report)
    extra = [i for i in tables[("game", "es")].ids()] if ("game", "es") in tables else []
    context = dialogue_context(tables[("game", "en")], refs, extra_ids=extra)
    dump_json(out_dir / "context_game.json", context)
    print(f"Catálogos: {len(manifest['catalogs'])} em {out_dir / 'catalog'}")
    for cat, info in report["categories"].items():
        print(f"  {cat}: ref={info['reference_ids']} só_en={len(info['only_in_reference'])} "
              f"só_outros={len(info['only_in_other_languages'])} {info['only_in_other_languages_by_ref']}")
    print(f"Referências órfãs: { {k: len(v) for k, v in report['orphan_references'].items()} }")
    print(f"Análise: {analysis_path}")
    return 0


def cmd_gate_unchanged(args: argparse.Namespace) -> int:
    tables, raw = load_tables(args.game_root)
    ok = 0
    for key, table in sorted(tables.items()):
        catalog = catalog_from_json(catalog_to_json(catalog_from_table(table)))
        rebuilt = build_text_table_bytes(table_from_catalog(catalog))
        if rebuilt == raw[key]:
            ok += 1
        else:
            print(f"  FALHA {text_file_name(*key)}")
    print(f"Gate 1 (catálogo sem alterações -> bytes idênticos): {ok}/{len(tables)}")
    return 0 if ok == len(tables) else 2


def cmd_build(args: argparse.Namespace) -> int:
    catalog = catalog_from_json(args.catalog.read_text(encoding="utf-8"))
    table = table_from_catalog(catalog, language=args.language)
    data = build_text_table_bytes(table)
    target = out_path(args.out_dir / text_file_name(table.category, table.language), args.game_root)
    load_text_table(data, table.category, table.language)  # re-parse: invariantes do formato
    write_bytes_atomic(target, data)
    print(f"Gerado {target} ({len(data)} bytes, sha256 {bytes_hash(data)})")
    return 0


def cmd_pseudo(args: argparse.Namespace) -> int:
    game = args.game_root
    out_dir = out_path(args.out_dir, game)
    tables, _ = load_tables(game)
    glyphs = game_supported_codepoints(game)
    slot, ref_lang = args.slot, "en"
    exceptions = resolve_exceptions(args.exceptions)
    summary: dict[str, Any] = {"slot": slot, "reference": ref_lang, "tables": {},
                               "exceptions": len(exceptions)}
    failed = False
    all_ids = {cat: set(tables[(cat, ref_lang)].ids()) for cat, lang in tables if lang == ref_lang}
    for cat in sorted(all_ids):
        ref = tables[(cat, ref_lang)]
        entries = [(i, t if i.endswith("_no_localize") else pseudolocalize(t)) for i, t in ref.entries]
        table = TextTable(cat, slot, ref.version, entries)
        data = build_text_table_bytes(table)
        back = load_text_table(data, cat, slot)  # invariantes após reconstrução
        invariant = back.ids() == ref.ids() and all(
            markup.tokens(a) == markup.tokens(b) for (_, a), (_, b) in zip(back.entries, ref.entries))
        others = set().union(*(v for k, v in all_ids.items() if k != cat))
        result = validate_catalog(back.entries, ref.as_dict(),
                                  replaced=tables.get((cat, slot), TextTable(cat, slot)).as_dict(),
                                  glyphs=glyphs, other_category_ids=others, exceptions=exceptions)
        codes = result.codes()
        summary["tables"][cat] = {"entries": len(entries), "bytes": len(data), "sha256": bytes_hash(data),
                                  "token_invariant": invariant, "errors": len(result.errors),
                                  "suppressed": len(result.suppressed),
                                  "issue_codes": dict(sorted(codes.items()))}
        failed |= not invariant or not result.ok
        write_bytes_atomic(out_dir / text_file_name(cat, slot), data)
    dump_json(out_dir / "pseudo_summary.json", summary)
    for cat, info in summary["tables"].items():
        print(f"  {cat}: invariante={info['token_invariant']} erros={info['errors']} {info['issue_codes']}")
    print(f"Arquivos de teste em {out_dir} (NÃO instalar na Steam)")
    return 2 if failed else 0


def cmd_validate(args: argparse.Namespace) -> int:
    game = args.game_root
    tables, _ = load_tables(game)
    catalog = catalog_from_json(args.catalog.read_text(encoding="utf-8"))
    cat = catalog.category
    exceptions = resolve_exceptions(args.exceptions)
    others = {i for (c, lang), t in tables.items() if lang == "en" and c != cat for i in t.ids()}
    result = validate_catalog(
        [(e.id, e.text) for e in sorted(catalog.entries, key=lambda e: e.index)],
        tables[(cat, "en")].as_dict(),
        replaced=tables[(cat, args.replaced)].as_dict() if (cat, args.replaced) in tables else None,
        glyphs=game_supported_codepoints(game), exceptions=exceptions, other_category_ids=others,
    )
    print(f"Erros: {len(result.errors)}  Avisos: {len(result.warnings)}  Suprimidos: {len(result.suppressed)}")
    for code, n in sorted(result.codes().items()):
        print(f"  {code}: {n}")
    if args.report:
        dump_json(out_path(args.report, game), [issue.__dict__ for issue in result.issues])
    return 0 if result.ok else 2


def cmd_inspect_db(args: argparse.Namespace) -> int:
    game = args.game_root
    report: dict[str, Any] = {"databases": {}}
    for path in sorted(game.glob("*/_*.db")):
        db = parse_def(path.read_bytes())
        records = list(iter_records(db))
        keys = Counter(tuple(str(k) for k, _ in r.entries) for r in records)
        timestamps = Counter(to_python(r.get("timestamp")) for r in records if r.get("timestamp") is not None)
        defs = Counter(to_python(r.get("def")) for r in records)
        meta_keys = Counter()
        for r in records:
            meta = r.get("metadata")
            if isinstance(meta, DefTable):
                meta_keys.update(str(k) for k, _ in meta.entries)
        report["databases"][f"{path.parent.name}/{path.name}"] = {
            "records": len(records), "record_shapes": {"|".join(k): n for k, n in keys.items()},
            "timestamp_values": {str(k): n for k, n in timestamps.items()},
            "def_sources": {str(k): n for k, n in defs.items()},
            "metadata_keys": dict(meta_keys), "version": db.version,
            "reserved_zero": db.reserved == bytes(7), "trailer_zero": db.trailer == bytes(4),
        }
    rfile = parse_def((game / "base" / "_rfile.db").read_bytes())
    mapping = [(to_python(r.get("name")), to_python(r.get("metadata")).get("file")) for r in iter_records(rfile)]
    rule = all(file == name.replace("/", "_") + ".rfile" for name, file in mapping)
    report["rfile_name_rule"] = {"records": len(mapping), "file_equals_name_slash_to_underscore_plus_rfile": rule}
    missing = [file for _, file in mapping if not (game / "base" / file).is_file()]
    extra = sorted({p.name for p in (game / "base").glob("*.rfile")} - {file for _, file in mapping})
    report["rfile_index_vs_disk"] = {"indexed_missing_on_disk": missing, "on_disk_not_indexed": extra}
    target = out_path(args.report, game)
    dump_json(target, report)
    for name, info in report["databases"].items():
        print(f"  {name}: {info['records']} registros, timestamps={info['timestamp_values']}")
    print(f"Regra nome->arquivo em _rfile.db: {rule}; faltando={len(missing)} não indexados={len(extra)}")
    print(f"Relatório: {target}")
    return 0


# --------------------------------------------------------------------------- pack-sombra
DEFAULT_PATCH = PROJECT_ROOT / "data" / "patches" / "fase1c_a_novo_jogo.json"


def cmd_shadow_build(args: argparse.Namespace) -> int:
    game = args.game_root
    patch = shadow.load_patch(args.patch)
    out = out_path(args.out or PROJECT_ROOT / "work" / "shadow" / patch.name, game)
    tables, _ = load_tables(game)
    reference = {cat: t.as_dict() for (cat, lang), t in tables.items() if lang == "en"}
    result = shadow.build_shadow(game, patch, out, build=game_build(game), reference=reference,
                                 glyphs=game_supported_codepoints(game))
    m = result.manifest
    print(f"Pack-sombra '{m['patch']}' gerado em {result.root}")
    print(f"  arquivos: {len(m['shadow_files'])}  alterados: {m['patched_files']}")
    for change in m["changes"]:
        print(f"  {change['category']}/{change['id']} -> {change['new_text']!r}")
    print("  verificação: OK (NÃO instalado)")
    return 0


def _single_manifest(shadow_root: Path) -> dict:
    found = sorted((shadow_root / "mods").glob(f"*/{shadow.MANIFEST_NAME}"))
    if len(found) != 1:
        raise ValueError(f"esperado 1 manifesto em {shadow_root / 'mods'}, achados {len(found)}")
    return shadow.read_manifest(found[0].parent)


def cmd_shadow_verify(args: argparse.Namespace) -> int:
    manifest = _single_manifest(args.shadow)
    problems = shadow.verify_shadow(args.shadow, manifest)
    stale = shadow.stale_against_game(manifest, args.game_root)
    print(f"Integridade: {'OK' if not problems else 'FALHA'}")
    for item in problems:
        print(f"  - {item}")
    print(f"Compatível com a instalação atual: {'SIM' if not stale else 'NÃO'}")
    for item in stale:
        print(f"  - {item}")
    return 0 if not problems and not stale else 2


def _print_plan(plan: shadow.Plan) -> int:
    mode = "EXECUTADO" if plan.executed else "DRY-RUN (nada foi alterado)"
    print(f"{plan.action} -> {plan.target}  [{mode}]")
    for step in plan.steps:
        print(f"  passo: {step}")
    for problem in plan.problems:
        print(f"  BLOQUEIO: {problem}")
    return 0 if plan.ok else 2


def cmd_shadow_install(args: argparse.Namespace) -> int:
    documents = args.documents or shadow.documents_dir()
    return _print_plan(shadow.install(args.shadow, documents, args.game_root, execute=args.execute))


def cmd_shadow_uninstall(args: argparse.Namespace) -> int:
    documents = args.documents or shadow.documents_dir()
    return _print_plan(shadow.uninstall(documents, args.pack, execute=args.execute))


def cmd_shadow_status(args: argparse.Namespace) -> int:
    documents = args.documents or shadow.documents_dir()
    info = shadow.status(documents, args.pack, args.game_root)
    print(json.dumps(info, ensure_ascii=False, indent=1))
    return 0 if not info.get("problems") and not info.get("stale") else 2


# --------------------------------------------------------------------------- catálogo PT-BR
DEFAULT_L10N = PROJECT_ROOT / "l10n" / "pt-BR"


def _l10n_context(game: Path, root: Path):
    project = l10n.load_project(root / "project.json")
    tables, _ = load_tables(game)
    reference = {c: t.as_dict() for (c, lang), t in tables.items() if lang == project.reference_language}
    slot = {c: t.as_dict() for (c, lang), t in tables.items() if lang == project.target_slot}
    return project, l10n.load_catalogs(root), reference, slot


def cmd_l10n_add(args: argparse.Namespace) -> int:
    project = l10n.load_project(args.root / "project.json")
    tables, _ = load_tables(args.game_root)
    reference = tables[(args.category, project.reference_language)].as_dict()
    path = args.root / f"{args.category}.json"
    catalog = l10n.load_catalog(path) if path.is_file() else l10n.Catalog(args.category, project.locale)
    added, kept = l10n.add_pending(catalog, args.ids, reference)
    l10n.save_catalog(path, catalog)
    print(f"{args.category}: {len(added)} adicionadas (pending), {len(kept)} já existentes preservadas")
    return 0


def cmd_l10n_validate(args: argparse.Namespace) -> int:
    project, catalogs, reference, slot = _l10n_context(args.game_root, args.root)
    glyphs = game_supported_codepoints(args.game_root)
    failed = False
    summary: dict[str, Any] = {}
    for category, catalog in sorted(catalogs.items()):
        report = l10n.validate_l10n(catalog, reference.get(category, {}), slot.get(category, {}), glyphs=glyphs)
        failed |= not report.ok
        codes = Counter(f"{i.severity}:{i.code}" for i in report.issues)
        summary[category] = {"entries": len(catalog.entries), "states": report.counts,
                             "issues": [i.__dict__ for i in report.issues]}
        print(f"  {category}: {len(catalog.entries)} entradas {report.counts} problemas={dict(sorted(codes.items()))}")
        for issue in report.issues:
            print(f"    {issue.severity.upper()} {issue.code} {issue.id}: {issue.detail}")
    if args.report:
        dump_json(out_path(args.report, args.game_root), summary)
    print("Validação:", "FALHOU" if failed else "OK")
    return 2 if failed else 0


def cmd_l10n_sheet(args: argparse.Namespace) -> int:
    project, catalogs, reference, slot = _l10n_context(args.game_root, args.root)
    out = out_path(args.out, args.game_root)
    lines = ["# Planilha de revisão PT-BR (LOCAL: contém texto original; não versionar)", ""]
    for category, catalog in sorted(catalogs.items()):
        lines.append(f"## {category}")
        for entry_id, entry in sorted(catalog.entries.items()):
            lines += ["", f"### `{entry_id}` ({entry.translation_status}/{entry.review_status})",
                      f"- EN: `{reference.get(category, {}).get(entry_id)}`",
                      f"- ES (slot atual): `{slot.get(category, {}).get(entry_id)}`",
                      f"- PT-BR: `{entry.text}`"]
            if entry.location:
                lines.append(f"- Local: {entry.location}")
            if entry.context:
                lines.append(f"- Contexto: {entry.context}")
            if entry.terminology:
                lines.append(f"- Terminologia: {'; '.join(entry.terminology)}")
        lines.append("")
    write_text_atomic(out, "\n".join(lines) + "\n")
    print(f"Planilha: {out}")
    return 0


def cmd_l10n_promote(args: argparse.Namespace) -> int:
    project, catalogs, reference, slot = _l10n_context(args.game_root, args.root)
    glyphs = game_supported_codepoints(args.game_root)
    note = args.note or f"qa-lote:{args.origin}"
    total = 0
    for category, catalog in sorted(catalogs.items()):
        report = l10n.validate_l10n(catalog, reference.get(category, {}), slot.get(category, {}), glyphs=glyphs)
        failing = {i.id for i in report.errors}
        passing = [i for i in catalog.entries if i not in failing]
        promoted = l10n.promote(catalog, origin=args.origin, to=args.to, note=note, passing=passing)
        if promoted and args.execute:
            l10n.save_catalog(args.root / f"{category}.json", catalog)
        total += len(promoted)
        print(f"  {category}: {len(promoted)} entradas -> {args.to} ({'aplicado' if args.execute else 'DRY-RUN'})")
    print(f"Total: {total}; nota: {note}")
    return 0


def cmd_l10n_build(args: argparse.Namespace) -> int:
    game = args.game_root
    project, catalogs, reference, slot = _l10n_context(game, args.root)
    glyphs = game_supported_codepoints(game)
    for category, catalog in sorted(catalogs.items()):
        report = l10n.validate_l10n(catalog, reference.get(category, {}), slot.get(category, {}), glyphs=glyphs)
        selected = {i for i, e in catalog.entries.items() if e.is_applicable(args.policy)}
        blocking = [i for i in report.errors if i.id in selected]
        if blocking:
            for issue in blocking:
                print(f"  BLOQUEIO {issue.code} {category}/{issue.id}: {issue.detail}", file=sys.stderr)
            return 2
    selection = l10n.select_changes(project, catalogs, reference, slot, args.policy)
    patch = l10n.make_patch(project, args.name, selection.changes)
    out = out_path(PROJECT_ROOT / "work" / "shadow" / args.name, game)
    result = shadow.build_shadow(game, patch, out, build=game_build(game), reference=reference, glyphs=glyphs,
                                 exceptions=selection.exceptions)
    # Relatório de diferenças (local, contém texto original): só os recursos alterados.
    diff: dict[str, Any] = {"policy": args.policy, "patch": args.name, "files": {}, "skipped": selection.skipped}
    for rel in result.manifest["patched_files"]:
        category = rel.removeprefix("text_text_").removesuffix(f"_{project.target_slot}.txt.rfile")
        old = load_text_table((game / project.pack / rel).read_bytes(), category, project.target_slot)
        new = load_text_table((result.pack_dir / rel).read_bytes(), category, project.target_slot)
        changed = [k for (k, a), (_, b) in zip(old.entries, new.entries) if a != b]
        added = new.ids()[len(old.entries):]
        diff["files"][rel] = {
            "entries_total": len(old.entries), "entries_changed": len(changed),
            "ids_order_identical": old.ids() == new.ids()[:len(old.entries)],
            "entries_added": added,
            "bytes_before": (game / project.pack / rel).stat().st_size,
            "bytes_after": (result.pack_dir / rel).stat().st_size,
            "changes": [{"id": k, "slot_before": old.as_dict()[k], "pt_br": new.as_dict()[k]} for k in changed]
            + [{"id": k, "slot_before": None, "pt_br": new.as_dict()[k], "added": True} for k in added],
        }
    diff_path = out.with_name(out.name + "_diff.json")
    dump_json(diff_path, diff)
    print(f"Pack-sombra '{args.name}' em {result.root} (política {args.policy}, NÃO instalado)")
    for rel, info in diff["files"].items():
        print(f"  {rel}: {info['entries_changed']}/{info['entries_total']} entradas alteradas, "
              f"ordem dos IDs originais idêntica={info['ids_order_identical']}, "
              f"acrescentadas={len(info['entries_added'])}")
    print(f"  ignoradas pela política: { {k: len(v) for k, v in selection.skipped.items()} }")
    print(f"  diferenças: {diff_path}")
    return 0


# --------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME,
                        help="Instalação do Underkeep (somente leitura)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("roundtrip")
    p = sub.add_parser("extract")
    p.add_argument("--out", type=Path, default=PROJECT_ROOT / "work" / "extract")
    p.add_argument("--analysis", type=Path, default=PROJECT_ROOT / "audit" / "local" / "lang_analysis.json")
    sub.add_parser("gate-unchanged")
    p = sub.add_parser("build")
    p.add_argument("--catalog", type=Path, required=True)
    p.add_argument("--language", help="renomeia o slot (ex.: es)")
    p.add_argument("--out-dir", type=Path, default=PROJECT_ROOT / "work" / "build")
    p = sub.add_parser("pseudo")
    p.add_argument("--slot", default="es")
    p.add_argument("--out-dir", type=Path, default=PROJECT_ROOT / "work" / "pseudo")
    p.add_argument("--exceptions", type=Path, help="padrão: data/validation_exceptions.json")
    p = sub.add_parser("validate")
    p.add_argument("--catalog", type=Path, required=True)
    p.add_argument("--replaced", default="es")
    p.add_argument("--exceptions", type=Path, help="padrão: data/validation_exceptions.json")
    p.add_argument("--report", type=Path)
    p = sub.add_parser("inspect-db")
    p.add_argument("--report", type=Path, default=PROJECT_ROOT / "audit" / "local" / "def_inspect.json")
    default_shadow = PROJECT_ROOT / "work" / "shadow" / "fase1c_a_novo_jogo"
    p = sub.add_parser("shadow-build")
    p.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    p.add_argument("--out", type=Path, help="padrão: work/shadow/<nome do patch>")
    p = sub.add_parser("shadow-verify")
    p.add_argument("--shadow", type=Path, default=default_shadow)
    p = sub.add_parser("shadow-install")
    p.add_argument("--shadow", type=Path, default=default_shadow)
    p.add_argument("--documents", type=Path, help="padrão: pasta Documentos do Windows")
    p.add_argument("--execute", action="store_true", help="aplica de fato (sem isto: dry-run)")
    p = sub.add_parser("shadow-uninstall")
    p.add_argument("--pack", default="base")
    p.add_argument("--documents", type=Path, help="padrão: pasta Documentos do Windows")
    p.add_argument("--execute", action="store_true", help="aplica de fato (sem isto: dry-run)")
    p = sub.add_parser("shadow-status")
    p.add_argument("--pack", default="base")
    p.add_argument("--documents", type=Path, help="padrão: pasta Documentos do Windows")
    p = sub.add_parser("l10n-add")
    p.add_argument("--root", type=Path, default=DEFAULT_L10N)
    p.add_argument("--category", required=True, choices=l10n.CATEGORIES)
    p.add_argument("ids", nargs="+")
    p = sub.add_parser("l10n-validate")
    p.add_argument("--root", type=Path, default=DEFAULT_L10N)
    p.add_argument("--report", type=Path, default=PROJECT_ROOT / "audit" / "local" / "l10n_validate.json")
    p = sub.add_parser("l10n-sheet")
    p.add_argument("--root", type=Path, default=DEFAULT_L10N)
    p.add_argument("--out", type=Path, default=PROJECT_ROOT / "work" / "l10n" / "planilha_revisao.md")
    p = sub.add_parser("l10n-promote")
    p.add_argument("--root", type=Path, default=DEFAULT_L10N)
    p.add_argument("--origin", required=True, help="origem/lote, ex.: ia:lote-01")
    p.add_argument("--to", choices=("reviewed", "approved"), default="reviewed")
    p.add_argument("--note", help="padrão: qa-lote:<origem>")
    p.add_argument("--execute", action="store_true", help="grava (sem isto: dry-run)")
    p = sub.add_parser("l10n-build")
    p.add_argument("--root", type=Path, default=DEFAULT_L10N)
    p.add_argument("--policy", choices=l10n.POLICIES, default="approved")
    p.add_argument("--name", default="fase1c_b_amostra")
    args = parser.parse_args(argv)
    args.game_root = args.game_root.resolve()
    handlers = {"roundtrip": cmd_roundtrip, "extract": cmd_extract, "gate-unchanged": cmd_gate_unchanged,
                "build": cmd_build, "pseudo": cmd_pseudo, "validate": cmd_validate, "inspect-db": cmd_inspect_db,
                "shadow-build": cmd_shadow_build, "shadow-verify": cmd_shadow_verify,
                "shadow-install": cmd_shadow_install, "shadow-uninstall": cmd_shadow_uninstall,
                "shadow-status": cmd_shadow_status, "l10n-add": cmd_l10n_add,
                "l10n-validate": cmd_l10n_validate, "l10n-sheet": cmd_l10n_sheet, "l10n-build": cmd_l10n_build,
                "l10n-promote": cmd_l10n_promote}
    try:
        return handlers[args.command](args)
    except (ValueError, OSError, FormatError, shadow.ShadowError, l10n.CatalogError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
