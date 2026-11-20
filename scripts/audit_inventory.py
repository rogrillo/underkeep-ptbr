#!/usr/bin/env python3
"""Inventario de instalacao Underkeep — leitura estrita do jogo, JSON fora dela.

Nao extrai strings, assets ou quaisquer bytes do jogo para a saida; so metadados (caminho, tamanho,
SHA-256). Usado para comparar duas builds quando o jogo e atualizado (ver docs/DESENVOLVIMENTO.md).
Saida padrao: audit/local/inventory.json, ou <UKLOC_LOCAL_DIR>/audit/inventory.json se a variavel
estiver definida.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ukloc.catalog import local_roots  # noqa: E402

LOCALIZATION_HINTS = (
    "lang", "localiz", "translat", "locale", "strings", "text", "dialog",
    "subtitle", "french", "german", "polish", "czech", "russian", "spanish",
    "english", "_en", "_fr", "_de", "_pl", "_cz", "_cs", "_ru", "_es",
)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def detect_engine(paths: list[str]) -> list[dict[str, str]]:
    """Indicadores fracos, nunca confirmacao automatica de engine."""
    names = [p.lower() for p in paths]
    rules = [
        ("Unity", any(p.endswith("unityplayer.dll") or p.endswith("globalgamemanagers") for p in names)),
        ("Unreal", any(p.endswith((".pak", ".ucas", ".utoc")) for p in names)),
        ("Godot", any(p.endswith(".pck") for p in names)),
        ("GameMaker", any(p.endswith("data.win") for p in names)),
        ("RPG Maker", any("www/data/" in p or p.endswith("rpg_core.js") for p in names)),
        ("Electron", any(p.endswith("app.asar") for p in names)),
    ]
    return [{"candidate": name, "status": "indicator_only"} for name, hit in rules if hit]


def inventory(game_root: Path) -> dict:
    if not game_root.is_dir():
        raise ValueError(f"Diretorio do jogo nao encontrado: {game_root}")
    files: list[dict] = []
    errors: list[dict[str, str]] = []
    extension_counts: Counter[str] = Counter()
    for current, dirs, filenames in os.walk(game_root, followlinks=False):
        # Nunca acompanhar atalhos ou links para fora do jogo.
        dirs[:] = [d for d in sorted(dirs) if not (Path(current) / d).is_symlink()]
        for filename in sorted(filenames):
            path = Path(current) / filename
            if path.is_symlink():
                continue
            relative = path.relative_to(game_root).as_posix()
            try:
                info = {"path": relative, "size_bytes": path.stat().st_size,
                        "sha256": file_sha256(path)}
                files.append(info)
                extension_counts[path.suffix.lower() or "[no_extension]"] += 1
            except (OSError, PermissionError) as exc:
                errors.append({"path": relative, "error": type(exc).__name__})
    files.sort(key=lambda item: item["path"].lower())
    file_names = [item["path"] for item in files]
    candidates = [n for n in file_names if any(tag in n.lower() for tag in LOCALIZATION_HINTS)]
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "game_app_id": 2411200,
        "note": "Somente metadados; detectar engine requer verificacao humana.",
        "file_count": len(files),
        "total_size_bytes": sum(item["size_bytes"] for item in files),
        "extensions": dict(sorted(extension_counts.items())),
        "engine_indicators": detect_engine(file_names),
        "localization_candidate_paths": candidates,
        "files": files,
        "read_errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", required=True, type=Path,
                        help="Pasta da instalacao do Underkeep — somente leitura")
    parser.add_argument("--output", type=Path,
                        help="Saida JSON local (padrao: audit/local/inventory.json ou UKLOC_LOCAL_DIR/audit)")
    args = parser.parse_args(argv)
    if args.output is None:
        try:
            args.output = local_roots(PROJECT_ROOT)[1] / "inventory.json"
        except ValueError as exc:
            parser.error(str(exc))
    game_root = args.game_root.resolve()
    output = args.output.resolve()
    if output == game_root or game_root in output.parents:
        parser.error("A saida nao pode ficar dentro da instalacao original do jogo.")
    try:
        data = inventory(game_root)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except (ValueError, OSError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    print(f"Inventario: {data['file_count']} arquivos, {data['total_size_bytes']:,} bytes")
    print(f"Candidatos a localizacao: {len(data['localization_candidate_paths'])}")
    print(f"Indicadores de engine (nao conclusivos): {data['engine_indicators']}")
    print(f"Relatorio local: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
