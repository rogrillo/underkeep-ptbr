"""Pack-sombra: cópia local integral de um pack com alterações mínimas de texto.

Base (Fase 1B, ``docs/FASE_1B_RELATORIO.md`` §4–5): ``_DeterminePackType`` resolve o pack
``<p>`` procurando primeiro ``<Documentos>/Underkeep/mods/<p>/cache/pc/<p>``, depois
``<Documentos>/Underkeep/mods/<p>/<p>`` e só então a pasta do jogo. O diretório escolhido
SUBSTITUI o pack inteiro, portanto o pack-sombra precisa ser completo.

Layout gerado (igual no build em ``work/`` e no destino instalado)::

    <raiz>/mods/<p>/<p>/...               arquivos do pack (cópia + alterados)
    <raiz>/mods/<p>/ukloc_shadow_manifest.json
    <raiz>/mods/<p>/ukloc_install.json    (somente após instalação)

Regras de segurança:

* nada aqui escreve na instalação do jogo (a origem é apenas lida);
* build só em diretórios ignorados pelo Git (verificado pelo chamador/CLI);
* ``install``/``uninstall`` são *dry-run* por padrão; executar exige ``execute=True``;
* instalação transacional (staging + ``os.replace``) e verificação por hash;
* desinstalação só remove o que o manifesto descreve, com hashes intactos.

O manifesto nunca contém texto original do jogo: apenas nomes de arquivo, hashes e o texto novo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable, Iterable

from .formats import FormatError
from .textdb import TextTable, build_text_table_bytes, load_text_table, text_file_name
from .validate import ExceptionRule, Issue, validate_catalog

PATCH_SCHEMA = "ukloc.patch/1"
MANIFEST_SCHEMA = "ukloc.shadow/1"
INSTALL_SCHEMA = "ukloc.install/1"
MANIFEST_NAME = "ukloc_shadow_manifest.json"
INSTALL_RECORD_NAME = "ukloc_install.json"
APP_NAME = "Underkeep"  # AppName observado em FUN_1401a7d00
GAME_EXE = "underkeep.exe"
STAGING_PREFIX = ".ukloc_staging_"


class ShadowError(Exception):
    """Falha segura: nada foi alterado no destino quando esta exceção sobe."""


# --------------------------------------------------------------------------- patch
@dataclass(frozen=True)
class Change:
    category: str
    id: str
    source_text_sha256: str
    text: str


@dataclass(frozen=True)
class Patch:
    name: str
    pack: str
    slot: str
    expected_build: str | None
    expected_exe_sha256: str
    expected_files: dict[str, str]
    changes: tuple[Change, ...]

    def changed_files(self) -> list[str]:
        return sorted({text_file_name(c.category, self.slot) for c in self.changes})


def _require_str(raw: dict, key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise ShadowError(f"patch: campo {key!r} ausente ou vazio")
    return value


def parse_patch(data: object) -> Patch:
    if not isinstance(data, dict) or data.get("schema") != PATCH_SCHEMA:
        raise ShadowError(f"patch: schema deve ser {PATCH_SCHEMA!r}")
    expected = data.get("expected")
    if not isinstance(expected, dict):
        raise ShadowError("patch: bloco 'expected' ausente")
    files = expected.get("files", {})
    if not isinstance(files, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in files.items()):
        raise ShadowError("patch: expected.files deve mapear nome -> sha256")
    raw_changes = data.get("changes")
    if not isinstance(raw_changes, list) or not raw_changes:
        raise ShadowError("patch: lista 'changes' vazia")
    changes = []
    seen: set[tuple[str, str]] = set()
    for raw in raw_changes:
        if not isinstance(raw, dict):
            raise ShadowError("patch: alteração deve ser objeto")
        change = Change(_require_str(raw, "category"), _require_str(raw, "id"),
                        _require_str(raw, "source_text_sha256"), _require_str(raw, "text"))
        if (change.category, change.id) in seen:
            raise ShadowError(f"patch: alteração repetida para {change.id}")
        seen.add((change.category, change.id))
        changes.append(change)
    pack, slot = _require_str(data, "pack"), _require_str(data, "slot")
    if "/" in pack or "\\" in pack or pack in {".", ".."}:
        raise ShadowError("patch: nome de pack inválido")
    patch = Patch(_require_str(data, "name"), pack, slot, expected.get("game_build"),
                  _require_str(expected, "exe_sha256").lower(),
                  {k: v.lower() for k, v in files.items()}, tuple(changes))
    missing = [f for f in patch.changed_files() if f not in patch.expected_files]
    if missing:
        raise ShadowError(f"patch: hash esperado ausente para arquivo alterado: {missing}")
    return patch


def load_patch(path: Path) -> Patch:
    return parse_patch(json.loads(path.read_text(encoding="utf-8")))


# --------------------------------------------------------------------------- hashes
def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_sha256(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def hash_tree(root: Path, *, exclude: Iterable[str] = ()) -> dict[str, str]:
    """Hash de todos os arquivos sob ``root`` (caminhos relativos POSIX, ordenados)."""
    skip = set(exclude)
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ShadowError(f"link simbólico não suportado: {path}")
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            if rel not in skip:
                result[rel] = file_sha256(path)
    return result


# --------------------------------------------------------------------------- preflight
@dataclass
class SourceInfo:
    game_root: Path
    pack_dir: Path
    exe_sha256: str
    build: str | None
    files: dict[str, str]


def preflight_source(game_root: Path, patch: Patch, *, build: str | None = None) -> SourceInfo:
    """Confere build/hash do executável e dos arquivos esperados. Somente leitura."""
    exe = game_root / GAME_EXE
    pack_dir = game_root / patch.pack
    if not exe.is_file() or not pack_dir.is_dir():
        raise ShadowError(f"instalação não encontrada em {game_root}")
    exe_hash = file_sha256(exe)
    if exe_hash != patch.expected_exe_sha256:
        raise ShadowError(f"executável diferente do esperado ({exe_hash[:16]}…): build atualizada? abortando")
    if patch.expected_build and build is not None and build != patch.expected_build:
        raise ShadowError(f"build Steam {build} diferente da esperada {patch.expected_build}")
    files = hash_tree(pack_dir)
    for name, expected in patch.expected_files.items():
        if files.get(name) != expected:
            raise ShadowError(f"{patch.pack}/{name} diferente do esperado: abortando")
    return SourceInfo(game_root, pack_dir, exe_hash, build, files)


# --------------------------------------------------------------------------- alteração
@dataclass
class ChangedTable:
    file_name: str
    data: bytes
    changed_ids: list[str]
    issues: list[Issue] = field(default_factory=list)


def apply_changes(original: bytes, category: str, slot: str, changes: Iterable[Change], *,
                  reference: dict[str, str] | None = None,
                  glyphs: frozenset[int] | None = None,
                  exceptions: Iterable[ExceptionRule] = ()) -> ChangedTable:
    """Aplica alterações a uma tabela de texto, preservando ordem/IDs e verificando invariantes."""
    table = load_text_table(original, category, slot)
    index = {key: i for i, (key, _) in enumerate(table.entries)}
    entries = list(table.entries)
    changed: list[str] = []
    for change in changes:
        if change.id not in index:
            raise ShadowError(f"ID {change.id!r} não existe em {category}_{slot}")
        position = index[change.id]
        if text_sha256(entries[position][1]) != change.source_text_sha256:
            raise ShadowError(f"texto de origem de {change.id!r} mudou (hash diferente): abortando")
        entries[position] = (change.id, change.text)
        changed.append(change.id)
    new_table = TextTable(category, slot, table.version, entries)
    data = build_text_table_bytes(new_table)
    back = load_text_table(data, category, slot)  # round-trip do resultado
    if back.entries != entries:
        raise ShadowError("tabela reconstruída difere do esperado")
    if back.ids() != table.ids():
        raise ShadowError("ordem/conjunto de IDs alterado")
    untouched = set(table.ids()) - set(changed)
    old, new = table.as_dict(), back.as_dict()
    if any(old[i] != new[i] for i in untouched):
        raise ShadowError("entrada não alterada mudou de valor")
    # Validação: estrutura da tabela inteira + regras de texto nas entradas alteradas.
    structural = validate_catalog(back.entries, {}, glyphs=None)
    issues = [i for i in structural.issues if i.code in {"EMPTY_ID", "NON_STRING_VALUE", "DUPLICATE_ID"}]
    if reference is not None:
        sub_ref = {i: reference[i] for i in changed if i in reference}
        textual = validate_catalog([(i, new[i]) for i in changed], sub_ref, glyphs=glyphs,
                                   exceptions=list(exceptions))
        issues.extend(textual.issues)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        raise ShadowError("validação falhou: " + "; ".join(f"{i.code}:{i.id} {i.detail}" for i in errors))
    return ChangedTable(text_file_name(category, slot), data, changed, issues)


# --------------------------------------------------------------------------- build
@dataclass
class BuildResult:
    root: Path
    pack_dir: Path
    manifest_path: Path
    manifest: dict


def shadow_paths(root: Path, pack: str) -> tuple[Path, Path, Path]:
    mod_dir = root / "mods" / pack
    return mod_dir, mod_dir / pack, mod_dir / MANIFEST_NAME


def _rmtree_owned(path: Path) -> None:
    """Remove ``path`` apenas se for um diretório de build nosso (contém manifesto)."""
    if not path.exists():
        return
    if not any(path.rglob(MANIFEST_NAME)):
        raise ShadowError(f"{path} existe e não foi criado pelo ukloc: recusando sobrescrever")
    shutil.rmtree(path)


def build_shadow(game_root: Path, patch: Patch, out_root: Path, *, build: str | None = None,
                 reference: dict[str, dict[str, str]] | None = None,
                 glyphs: frozenset[int] | None = None,
                 exceptions: Iterable[ExceptionRule] = ()) -> BuildResult:
    """Gera o pack-sombra completo em ``out_root`` (diretório de trabalho, nunca o jogo)."""
    game = game_root.resolve()
    out = out_root.resolve()
    if out == game or game in out.parents:
        raise ShadowError("saída não pode ficar dentro da instalação do jogo")
    source = preflight_source(game_root, patch, build=build)
    by_category: dict[str, list[Change]] = {}
    for change in patch.changes:
        by_category.setdefault(change.category, []).append(change)
    changed_tables: dict[str, ChangedTable] = {}
    rules = list(exceptions)
    for category, changes in sorted(by_category.items()):
        name = text_file_name(category, patch.slot)
        ref = (reference or {}).get(category)
        changed_tables[name] = apply_changes((source.pack_dir / name).read_bytes(), category, patch.slot,
                                             changes, reference=ref, glyphs=glyphs,
                                             exceptions=rules)
    staging = out.with_name(out.name + ".tmp")
    if staging.exists():  # sobra de execução interrompida; o nome é derivado de ``out``
        shutil.rmtree(staging)
    try:
        mod_dir, pack_dir, manifest_path = shadow_paths(staging, patch.pack)
        pack_dir.mkdir(parents=True)
        for rel in source.files:
            target = pack_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if rel in changed_tables:
                target.write_bytes(changed_tables[rel].data)
            else:
                shutil.copyfile(source.pack_dir / rel, target)
        shadow_files = hash_tree(pack_dir)
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "patch": patch.name,
            "pack": patch.pack,
            "slot": patch.slot,
            "app_name": APP_NAME,
            "source": {"game_build": source.build, "exe_sha256": source.exe_sha256,
                       "files": source.files},
            "shadow_files": shadow_files,
            "patched_files": sorted(changed_tables),
            "changes": [{"category": c.category, "id": c.id, "source_text_sha256": c.source_text_sha256,
                         "new_text": c.text, "new_text_sha256": text_sha256(c.text)}
                        for c in patch.changes],
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                 encoding="utf-8", newline="\n")
        problems = verify_shadow(staging, manifest)
        if problems:
            raise ShadowError("verificação do build falhou: " + "; ".join(problems))
        _rmtree_owned(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, out)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise
    mod_dir, pack_dir, manifest_path = shadow_paths(out, patch.pack)
    return BuildResult(out, pack_dir, manifest_path, manifest)


def read_manifest(mod_dir: Path) -> dict:
    path = mod_dir / MANIFEST_NAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ShadowError(f"manifesto ilegível em {path}: {exc}") from exc
    if data.get("schema") != MANIFEST_SCHEMA:
        raise ShadowError(f"manifesto com schema inesperado em {path}")
    return data


def verify_shadow(root: Path, manifest: dict) -> list[str]:
    """Problemas encontrados no pack-sombra sob ``root`` (lista vazia = íntegro)."""
    problems: list[str] = []
    _, pack_dir, _ = shadow_paths(root, manifest["pack"])
    if not pack_dir.is_dir():
        return [f"diretório do pack ausente: {pack_dir}"]
    actual = hash_tree(pack_dir)
    expected = manifest["shadow_files"]
    source = manifest["source"]["files"]
    patched = set(manifest["patched_files"])
    if set(actual) != set(expected):
        extra, missing = sorted(set(actual) - set(expected)), sorted(set(expected) - set(actual))
        problems.append(f"conjunto de arquivos difere (extras={extra[:5]}, faltando={missing[:5]})")
    if set(expected) != set(source):
        problems.append("pack-sombra não tem exatamente os arquivos do pack original")
    for rel, digest in expected.items():
        if actual.get(rel) not in (None, digest):
            problems.append(f"hash divergente: {rel}")
        if rel in patched:
            if digest == source.get(rel):
                problems.append(f"arquivo marcado como alterado está idêntico à origem: {rel}")
        elif digest != source.get(rel):
            problems.append(f"arquivo não alterado difere da origem: {rel}")
    for rel in patched:
        category_slot = rel.removeprefix("text_text_").removesuffix(".txt.rfile")
        try:
            category, slot = category_slot.rsplit("_", 1)
            table = load_text_table((pack_dir / rel).read_bytes(), category, slot).as_dict()
        except (OSError, ValueError, FormatError) as exc:
            problems.append(f"{rel} não abre como tabela de texto: {exc}")
            continue
        for change in manifest["changes"]:
            if text_file_name(change["category"], manifest["slot"]) == rel:
                if text_sha256(table.get(change["id"], "")) != change["new_text_sha256"]:
                    problems.append(f"alteração {change['id']} não encontrada em {rel}")
    return problems


def stale_against_game(manifest: dict, game_root: Path) -> list[str]:
    """Diferenças entre a instalação atual e a origem do pack-sombra (atualização do jogo)."""
    problems: list[str] = []
    exe = game_root / GAME_EXE
    if not exe.is_file() or file_sha256(exe) != manifest["source"]["exe_sha256"]:
        problems.append("executável do jogo mudou desde o build do pack-sombra")
    pack_dir = game_root / manifest["pack"]
    if not pack_dir.is_dir():
        problems.append(f"pack original {pack_dir} ausente")
    elif hash_tree(pack_dir) != manifest["source"]["files"]:
        problems.append(f"pack original {manifest['pack']} mudou desde o build do pack-sombra")
    return problems


# --------------------------------------------------------------------------- destino
def documents_dir() -> Path:
    """Pasta Documentos como o jogo a obtém (``SHGetFolderPathW`` CSIDL_PERSONAL)."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        result = ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer)  # CSIDL_PERSONAL
        if result == 0 and buffer.value:
            return Path(buffer.value)
    return Path.home() / "Documents"


def game_user_dir(documents: Path) -> Path:
    return documents / APP_NAME


def install_target(documents: Path, pack: str) -> Path:
    return game_user_dir(documents) / "mods" / pack


def _cmdline_runs_game(args: list[str]) -> bool:
    """``True`` se algum argumento é o executável do jogo, com caminho POSIX ou do Windows/Wine."""
    return any(arg.replace("\\", "/").rsplit("/", 1)[-1].lower() == GAME_EXE for arg in args)


def linux_game_running(proc: Path = Path("/proc"), ignore: Iterable[int] = ()) -> bool:
    """Procura o jogo entre os processos do Linux (no Proton/Wine ele aparece como ``underkeep.exe``).

    Inclui os processos auxiliares da Steam que carregam o caminho do executável (falha segura).
    ``ignore`` exclui o próprio instalador e seu processo pai, cujos argumentos podem citar o jogo.
    """
    skip = {str(pid) for pid in ignore}
    try:
        entries = list(proc.iterdir())
    except OSError:
        return True  # sem lista de processos: na dúvida, falha segura
    for entry in entries:
        if not entry.name.isdigit() or entry.name in skip:
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue  # processo encerrado ou de outro usuário
        if _cmdline_runs_game([a.decode("utf-8", errors="replace") for a in raw.split(b"\x00") if a]):
            return True
    return False


def is_game_running() -> bool:
    if sys.platform.startswith("linux"):
        return linux_game_running(ignore=(os.getpid(), os.getppid()))
    if sys.platform != "win32":
        return False
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {GAME_EXE}", "/NH"],
                             capture_output=True, text=True, timeout=30, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return True  # na dúvida, falha segura
    return GAME_EXE.lower() in out.lower()


@dataclass
class Plan:
    action: str
    target: Path
    steps: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    executed: bool = False

    @property
    def ok(self) -> bool:
        return not self.problems


def plan_install(shadow_root: Path, documents: Path, game_root: Path, *,
                 running: Callable[[], bool] | None = None) -> Plan:
    running = running or is_game_running
    manifests = sorted((shadow_root / "mods").glob(f"*/{MANIFEST_NAME}"))
    if len(manifests) != 1:
        raise ShadowError(f"esperado exatamente 1 pack-sombra em {shadow_root / 'mods'}")
    manifest = read_manifest(manifests[0].parent)
    pack = manifest["pack"]
    target = install_target(documents, pack)
    plan = Plan("install", target)
    plan.problems += verify_shadow(shadow_root, manifest)
    plan.problems += stale_against_game(manifest, game_root)
    user_dir = game_user_dir(documents)
    if not user_dir.is_dir():
        plan.problems.append(f"{user_dir} não existe (o jogo nunca rodou nesta conta?)")
    if target.exists() or target.is_symlink():
        plan.problems.append(f"destino já existe: {target} (desinstale ou remova antes)")
    if running():
        plan.problems.append("o jogo está em execução: feche-o antes")
    mods_dir = target.parent
    plan.steps = [
        f"{'usar' if mods_dir.is_dir() else 'criar'} {mods_dir}",
        f"copiar {len(manifest['shadow_files'])} arquivos para {mods_dir / (STAGING_PREFIX + pack)}",
        "verificar hashes no staging",
        f"renomear staging -> {target} (atômico)",
        f"gravar {INSTALL_RECORD_NAME} e verificar destino",
    ]
    return plan


def install(shadow_root: Path, documents: Path, game_root: Path, *, execute: bool = False,
            running: Callable[[], bool] | None = None) -> Plan:
    plan = plan_install(shadow_root, documents, game_root, running=running)
    if not execute or not plan.ok:
        return plan
    manifest = read_manifest(next((shadow_root / "mods").glob(f"*/{MANIFEST_NAME}")).parent)
    pack = manifest["pack"]
    source_mod_dir, _, _ = shadow_paths(shadow_root, pack)
    target = plan.target
    mods_dir = target.parent
    created_mods_dir = not mods_dir.exists()
    staging = mods_dir / (STAGING_PREFIX + pack)
    try:
        mods_dir.mkdir(parents=True, exist_ok=True)
        if staging.exists():
            shutil.rmtree(staging)
        shutil.copytree(source_mod_dir, staging)
        staged_problems = _verify_mod_dir(staging, manifest)
        if staged_problems:
            raise ShadowError("verificação do staging falhou: " + "; ".join(staged_problems))
        record = {"schema": INSTALL_SCHEMA, "patch": manifest["patch"], "pack": pack,
                  "created_mods_dir": created_mods_dir, "created_app_dir": False}
        (staging / INSTALL_RECORD_NAME).write_text(json.dumps(record, indent=1, sort_keys=True) + "\n",
                                                   encoding="utf-8", newline="\n")
        os.replace(staging, target)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        if created_mods_dir and mods_dir.is_dir() and not any(mods_dir.iterdir()):
            mods_dir.rmdir()
        raise
    final = _verify_mod_dir(target, manifest)
    if final:
        raise ShadowError("instalado, mas a verificação final falhou (rode uninstall): " + "; ".join(final))
    plan.executed = True
    return plan


def _verify_mod_dir(mod_dir: Path, manifest: dict) -> list[str]:
    """Verifica ``mods/<p>`` (pack + manifesto) contra o manifesto, sem exigir a origem."""
    problems: list[str] = []
    pack_dir = mod_dir / manifest["pack"]
    if not pack_dir.is_dir():
        return [f"pack ausente em {mod_dir}"]
    if hash_tree(pack_dir) != manifest["shadow_files"]:
        problems.append("arquivos do pack não batem com o manifesto")
    allowed_top = {manifest["pack"], MANIFEST_NAME, INSTALL_RECORD_NAME}
    extras = sorted(p.name for p in mod_dir.iterdir() if p.name not in allowed_top)
    if extras:
        problems.append(f"itens não gerenciados em {mod_dir}: {extras[:5]}")
    return problems


def plan_uninstall(documents: Path, pack: str, *, running: Callable[[], bool] | None = None) -> Plan:
    running = running or is_game_running
    target = install_target(documents, pack)
    plan = Plan("uninstall", target)
    if target.is_symlink():
        plan.problems.append(f"{target} é um link simbólico; por segurança não será removido")
        return plan
    if not target.exists():
        plan.problems.append(f"nada instalado em {target}")
        return plan
    try:
        manifest = read_manifest(target)
    except ShadowError as exc:
        plan.problems.append(f"{exc} — destino não gerenciado pelo ukloc; não será removido")
        return plan
    plan.problems += _verify_mod_dir(target, manifest)
    if running():
        plan.problems.append("o jogo está em execução: feche-o antes")
    plan.steps = [f"remover {target} ({len(manifest['shadow_files'])} arquivos + manifesto)"]
    record_path = target / INSTALL_RECORD_NAME
    if record_path.is_file():
        try:
            if json.loads(record_path.read_text(encoding="utf-8")).get("created_mods_dir"):
                plan.steps.append(f"remover {target.parent} se ficar vazio")
        except ValueError:
            plan.problems.append(f"{INSTALL_RECORD_NAME} ilegível")
    return plan


def uninstall(documents: Path, pack: str, *, execute: bool = False,
              running: Callable[[], bool] | None = None) -> Plan:
    plan = plan_uninstall(documents, pack, running=running)
    if not execute or not plan.ok:
        return plan
    target = plan.target
    record_path = target / INSTALL_RECORD_NAME
    created_mods_dir = False
    if record_path.is_file():
        created_mods_dir = bool(json.loads(record_path.read_text(encoding="utf-8")).get("created_mods_dir"))
    shutil.rmtree(target)
    mods_dir = target.parent
    if created_mods_dir and mods_dir.is_dir() and not any(mods_dir.iterdir()):
        mods_dir.rmdir()
    plan.executed = True
    return plan


def status(documents: Path, pack: str, game_root: Path) -> dict:
    target = install_target(documents, pack)
    info: dict = {"target": str(target), "installed": target.exists()}
    if target.exists():
        try:
            manifest = read_manifest(target)
        except ShadowError as exc:
            info["managed"] = False
            info["problems"] = [str(exc)]
            return info
        info["managed"] = True
        info["patch"] = manifest["patch"]
        info["problems"] = _verify_mod_dir(target, manifest)
        info["stale"] = stale_against_game(manifest, game_root)
    return info
