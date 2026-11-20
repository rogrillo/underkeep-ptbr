"""Instalador da tradução para jogadores.

* Windows: empacotado com PyInstaller (``Instalar-Underkeep-PTBR.exe``), sem exigir Python.
* Linux/Steam Deck: roda pelo Python do sistema (``python3``), com a interface gráfica de
  :mod:`ukloc.gui` ou por este módulo no terminal. A pasta Documentos é a do prefixo Proton do jogo
  (``steamapps/compatdata/2411200/pfx/drive_c/users/steamuser/Documents``).

Fluxo (reaproveita o pipeline existente, sem atalhos de segurança):

1. localizar o jogo (:mod:`ukloc.steam`) ou aceitar a pasta escolhida pelo jogador;
2. conferir executável, build Steam e hashes dos arquivos de texto contra ``project.json``;
3. recusar se o jogo estiver aberto, se ``Documentos/Underkeep`` não existir ou se ``mods/base``
   pertencer a outro mod/versão;
4. gerar o pack-sombra num diretório temporário a partir dos arquivos ORIGINAIS do próprio jogador,
   aplicando apenas o catálogo PT-BR (:func:`ukloc.l10n.select_changes` + :func:`ukloc.shadow.build_shadow`);
5. instalar com :func:`ukloc.shadow.install` (staging + verificação de hashes + renomeação atômica);
6. apagar o diretório temporário.

A pasta da Steam, os saves e o ``game_config.txt`` nunca são escritos. A desinstalação usa o manifesto
do pack instalado e recusa qualquer pasta não gerenciada ou alterada.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Callable

from . import l10n, shadow, steam
from .fonts import game_supported_codepoints
from .formats import FormatError
from .textdb import find_text_tables, load_text_table

VERSION = "0.1.0-beta.3"
PATCH_NAME = f"underkeep-ptbr-{VERSION}"
POLICY = "translated"  # revisão humana completa ainda em andamento (ver README)
SAFETY_MARGIN = 64 * 1024 * 1024

Say = Callable[[str], None]


class InstallerError(Exception):
    """Falha segura: nada foi alterado quando esta exceção sobe."""


# --------------------------------------------------------------------------- recursos próprios
def default_l10n_root() -> Path:
    """Catálogo PT-BR: ``dados/pt-BR`` ao lado do executável; no repositório, ``l10n/pt-BR``."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "dados" / "pt-BR"
    return Path(__file__).resolve().parents[1] / "l10n" / "pt-BR"


def load_project(l10n_root: Path) -> l10n.Project:
    path = l10n_root / "project.json"
    if not path.is_file():
        raise InstallerError(f"arquivos da tradução não encontrados em {l10n_root} (extraia o ZIP inteiro)")
    try:
        return l10n.load_project(path)
    except (ValueError, OSError) as exc:
        raise InstallerError(f"project.json inválido: {exc}") from exc


# --------------------------------------------------------------------------- verificações
@dataclass
class GameCheck:
    game_root: Path
    build: str | None = None
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def normalize_game_path(raw: str) -> Path:
    """Aceita a pasta do jogo ou o caminho do ``underkeep.exe`` (com ou sem aspas)."""
    path = clean_path(raw)
    if path.name.lower() == steam.GAME_EXE:
        path = path.parent
    return path


def check_game(game_root: Path, project: l10n.Project) -> GameCheck:
    """Compara a instalação com a build suportada. Somente leitura."""
    check = GameCheck(game_root, steam.game_build(game_root))
    exe = game_root / steam.GAME_EXE
    if not exe.is_file():
        check.problems.append(f"{steam.GAME_EXE} não encontrado em {game_root}")
        return check
    if not (game_root / project.pack).is_dir():
        check.problems.append(f"pasta '{project.pack}' do jogo não encontrada em {game_root}")
        return check
    if shadow.file_sha256(exe) != project.expected_exe_sha256:
        check.problems.append("versão do jogo não suportada: o executável é diferente do esperado "
                              f"(esta tradução foi preparada para a build Steam {project.expected_build})")
    if project.expected_build and check.build and check.build != project.expected_build:
        check.problems.append(f"build Steam {check.build} diferente da suportada ({project.expected_build})")
    differing = [name for name, expected in sorted(project.expected_files.items())
                 if not (game_root / project.pack / name).is_file()
                 or shadow.file_sha256(game_root / project.pack / name) != expected]
    if differing:
        shown = ", ".join(differing[:2]) + (f" e mais {len(differing) - 2}" if len(differing) > 2 else "")
        check.problems.append(f"{len(differing)} arquivo(s) de texto do jogo diferente(s) do esperado ({shown}): "
                              "jogo atualizado ou modificado; verifique a integridade dos arquivos na Steam")
    return check


@dataclass
class TargetState:
    kind: str  # absent | current | other | damaged | foreign
    target: Path
    patch: str | None = None
    problems: list[str] = field(default_factory=list)


def target_state(documents: Path, pack: str) -> TargetState:
    target = shadow.install_target(documents, pack)
    if target.is_symlink():
        return TargetState("foreign", target)  # nunca seguir nem apagar links simbólicos
    if not target.exists():
        return TargetState("absent", target)
    try:
        manifest = shadow.read_manifest(target)
    except shadow.ShadowError:
        return TargetState("foreign", target)
    problems = shadow._verify_mod_dir(target, manifest)  # noqa: SLF001 — mesma verificação da desinstalação
    if problems:
        return TargetState("damaged", target, manifest.get("patch"), problems)
    kind = "current" if manifest.get("patch") == PATCH_NAME else "other"
    return TargetState(kind, target, manifest.get("patch"))


def other_mods(documents: Path, pack: str) -> list[str]:
    mods = shadow.game_user_dir(documents) / "mods"
    if not mods.is_dir():
        return []
    return sorted(p.name for p in mods.iterdir() if p.name != pack and not p.name.startswith(shadow.STAGING_PREFIX))


def pack_size(game_root: Path, pack: str) -> int:
    return sum(p.stat().st_size for p in (game_root / pack).rglob("*") if p.is_file())


def free_space(path: Path) -> int:
    probe = path
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    return shutil.disk_usage(probe).free


def _same_volume(a: Path, b: Path) -> bool:
    def anchor(p: Path) -> str:
        while not p.exists() and p.parent != p:
            p = p.parent
        try:
            return str(os.stat(p).st_dev)
        except OSError:
            return p.anchor.lower()
    return anchor(a) == anchor(b)


# --------------------------------------------------------------------------- plano
@dataclass
class InstallPlan:
    game: GameCheck
    state: TargetState
    workdir: Path
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def plan_install(game_root: Path, documents: Path, project: l10n.Project, *,
                 running: Callable[[], bool] | None = None, workdir: Path | None = None) -> InstallPlan:
    running = running or shadow.is_game_running
    game = check_game(game_root, project)
    state = target_state(documents, project.pack)
    work = workdir or Path(tempfile.gettempdir())
    plan = InstallPlan(game, state, work, problems=list(game.problems))
    user_dir = shadow.game_user_dir(documents)
    if not user_dir.is_dir():
        plan.problems.append(f"{user_dir} não existe: abra o Underkeep uma vez pela Steam e feche-o antes de instalar")
    elif not os.access(user_dir, os.W_OK):
        plan.problems.append(f"sem permissão de escrita em {user_dir}")
    if state.kind == "current":
        plan.problems.append(f"a tradução {VERSION} já está instalada em {state.target}")
    elif state.kind == "other":
        plan.problems.append(f"outra versão da tradução ({state.patch}) está instalada: desinstale-a primeiro")
    elif state.kind == "damaged":
        plan.problems.append(f"a instalação existente em {state.target} foi alterada fora do instalador "
                             f"({'; '.join(state.problems[:2])}); não será sobrescrita")
    elif state.kind == "foreign":
        plan.problems.append(f"{state.target} pertence a outro mod ou foi criado manualmente; "
                             "o instalador não sobrescreve pastas desconhecidas")
    if running():
        plan.problems.append("o Underkeep está aberto: feche o jogo antes de continuar")
    if game.ok:
        size = pack_size(game_root, project.pack)
        need_docs = need_tmp = size + SAFETY_MARGIN
        if _same_volume(work, documents):
            need_docs = need_tmp = 2 * size + SAFETY_MARGIN
        if free_space(work) < need_tmp:
            plan.problems.append(f"espaço insuficiente em {work} (necessário ~{need_tmp // 2**20} MB)")
        elif free_space(documents) < need_docs:
            plan.problems.append(f"espaço insuficiente em {documents} (necessário ~{need_docs // 2**20} MB)")
    for name in other_mods(documents, project.pack):
        plan.warnings.append(f"outro mod detectado em mods/{name}: não será alterado")
    return plan


# --------------------------------------------------------------------------- build e instalação
def _game_tables(game_root: Path, project: l10n.Project) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    reference: dict[str, dict[str, str]] = {}
    slot: dict[str, dict[str, str]] = {}
    for (category, lang), path in find_text_tables(game_root / project.pack).items():
        if lang == project.reference_language:
            reference[category] = load_text_table(path.read_bytes(), category, lang).as_dict()
        elif lang == project.target_slot:
            slot[category] = load_text_table(path.read_bytes(), category, lang).as_dict()
    if not reference or not slot:
        raise InstallerError("tabelas de texto do jogo não encontradas")
    return reference, slot


def build_pack(game_root: Path, l10n_root: Path, project: l10n.Project, out_root: Path) -> shadow.BuildResult:
    """Gera o pack-sombra traduzido a partir dos arquivos do jogo (mesmas regras de ``l10n-build``)."""
    reference, slot = _game_tables(game_root, project)
    glyphs = game_supported_codepoints(game_root)
    catalogs = l10n.load_catalogs(l10n_root)
    if not catalogs:
        raise InstallerError(f"nenhum catálogo de tradução em {l10n_root}")
    for category, catalog in sorted(catalogs.items()):
        report = l10n.validate_l10n(catalog, reference.get(category, {}), slot.get(category, {}), glyphs=glyphs)
        selected = {i for i, e in catalog.entries.items() if e.is_applicable(POLICY)}
        blocking = [i for i in report.errors if i.id in selected]
        if blocking:
            first = blocking[0]
            raise InstallerError(f"catálogo inválido ({len(blocking)} erros; ex.: {first.code} {category}/{first.id})")
    selection = l10n.select_changes(project, catalogs, reference, slot, POLICY)
    patch = l10n.make_patch(project, PATCH_NAME, selection.changes)
    return shadow.build_shadow(game_root, patch, out_root, build=steam.game_build(game_root),
                               reference=reference, glyphs=glyphs, exceptions=selection.exceptions)


@dataclass
class Outcome:
    plan: InstallPlan
    executed: bool = False
    changes: int = 0


def install(game_root: Path, documents: Path, l10n_root: Path, *, execute: bool = False,
            running: Callable[[], bool] | None = None, workdir: Path | None = None,
            say: Say = lambda _msg: None) -> Outcome:
    project = load_project(l10n_root)
    plan = plan_install(game_root, documents, project, running=running, workdir=workdir)
    outcome = Outcome(plan)
    if not execute or not plan.ok:
        return outcome
    tmp = Path(tempfile.mkdtemp(prefix="underkeep_ptbr_", dir=plan.workdir))
    try:
        say("Gerando os arquivos traduzidos a partir da sua instalação (pode levar um minuto)...")
        result = build_pack(game_root, l10n_root, project, tmp / "shadow")
        say("Instalando e conferindo os arquivos...")
        installed = shadow.install(result.root, documents, game_root, execute=True, running=running)
        if not installed.executed:
            raise InstallerError("instalação recusada: " + "; ".join(installed.problems))
        outcome.executed = True
        outcome.changes = len(result.manifest["changes"])
    except (shadow.ShadowError, l10n.CatalogError, FormatError, ValueError, OSError) as exc:
        raise InstallerError(str(exc)) from exc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return outcome


def uninstall(documents: Path, pack: str = "base", *, execute: bool = False,
              running: Callable[[], bool] | None = None) -> shadow.Plan:
    """Remove somente uma instalação gerenciada e íntegra (ver :func:`ukloc.shadow.uninstall`)."""
    return shadow.uninstall(documents, pack, execute=execute, running=running)


# --------------------------------------------------------------------------- interface (console, PT-BR)
EXIT_OK, EXIT_BLOCKED, EXIT_ERROR = 0, 2, 1


class Console:
    def __init__(self, *, assume_yes: bool, input_fn: Callable[[str], str] = input, out: Say = print) -> None:
        self.assume_yes = assume_yes
        self.input_fn = input_fn
        self.out = out

    def ask(self, prompt: str, default: str = "") -> str:
        if self.assume_yes:
            return default
        try:
            return self.input_fn(prompt)
        except EOFError:
            return default

    def confirm(self, prompt: str) -> bool:
        if self.assume_yes:
            return True
        return self.ask(f"{prompt} [s/N] ").strip().lower() in {"s", "sim", "y", "yes"}

    def progress(self, message: str) -> None:
        self.out(message)

    def choose_path(self, found: list[Path], *, missing: str, manual: str) -> Path | None:
        """Confirma a pasta encontrada, escolhe entre várias ou pede o caminho digitado."""
        if len(found) == 1:
            self.out(f"  Encontrado: {found[0]}")
            typed = self.ask("  Pressione Enter para usar esta pasta ou digite outro caminho: ")
            return clean_path(typed) if typed.strip() else found[0]
        if found:
            for n, path in enumerate(found, 1):
                self.out(f"  [{n}] {path}")
            typed = self.ask("  Escolha o número da pasta ou digite outro caminho: ", "1").strip()
            if typed.isdigit() and 1 <= int(typed) <= len(found):
                return found[int(typed) - 1]
            return clean_path(typed) if typed else None
        self.out(f"  {missing}")
        typed = self.ask(f"  {manual}: ")
        return clean_path(typed) if typed.strip() else None


def clean_path(raw: str) -> Path:
    """Caminho digitado ou colado (aceita aspas e ``~``)."""
    return Path(raw.strip().strip('"').strip("'")).expanduser()


def choose_game(console: Console, explicit: Path | None, steam_roots: list[Path] | None = None) -> Path | None:
    if explicit is not None:
        return normalize_game_path(str(explicit))
    console.out("Procurando o Underkeep nas bibliotecas da Steam...")
    chosen = console.choose_path(steam.find_game_dirs(steam_roots), missing="Não encontrei o jogo automaticamente.",
                                 manual="Digite (ou cole) a pasta do Underkeep, onde fica o underkeep.exe")
    return normalize_game_path(str(chosen)) if chosen is not None else None


def is_windows() -> bool:
    return sys.platform == "win32"


PROTON_HINT = ".../steamapps/compatdata/2411200/pfx/drive_c/users/steamuser/Documents"


def resolve_documents(console: Console, explicit: Path | None, game_root: Path | None,
                      steam_roots: list[Path] | None = None) -> Path | None:
    """Pasta Documentos que o jogo usa.

    Windows: a do usuário (mesma API do jogo). Linux/Steam Deck: a do prefixo Proton do jogo, escolhida
    automaticamente só quando a correspondência com a instalação é inequívoca; nos demais casos o
    jogador escolhe. Em modo não interativo (``--sim``), uma escolha incerta é recusada.
    """
    if explicit is not None:
        return clean_path(str(explicit))
    if is_windows():
        return shadow.documents_dir()
    found = steam.find_proton_documents(game_root, steam_roots)
    if found.matched is not None:
        console.out(f"Pasta Documentos do Proton (prefixo do jogo): {found.matched}")
        return found.matched
    if console.assume_yes:
        detail = f"{len(found.candidates)} candidatas" if found.candidates else "nenhuma encontrada"
        raise InstallerError(f"não foi possível escolher com segurança a pasta Documentos do Proton ({detail}); "
                             f"informe-a com --documentos ({PROTON_HINT})")
    console.out("Procurando a pasta Documentos do Proton (prefixo do Underkeep)...")
    return console.choose_path(
        found.candidates,
        missing="Não encontrei o prefixo Proton do Underkeep. Abra o jogo uma vez pela Steam e feche-o.",
        manual=f"Digite (ou cole) a pasta Documents do prefixo ({PROTON_HINT})")


def _print_block(console: Console, title: str, items: list[str]) -> None:
    if items:
        console.out(title)
        for item in items:
            console.out(f"  - {item}")


def run_install(args: argparse.Namespace, console: Console, documents: Path | None, l10n_root: Path,
                running: Callable[[], bool] | None) -> int:
    game_root = choose_game(console, args.jogo)
    if game_root is None:
        console.out("Nenhuma pasta informada. Nada foi alterado.")
        return EXIT_BLOCKED
    documents = resolve_documents(console, documents, game_root)
    if documents is None:
        console.out("Nenhuma pasta Documentos informada. Nada foi alterado.")
        return EXIT_BLOCKED
    project = load_project(l10n_root)
    console.out(f"Verificando o jogo em {game_root} (versão e arquivos)...")
    plan = plan_install(game_root, documents, project, running=running)
    if plan.state.kind == "other" and plan.game.ok:
        console.out(f"Há outra versão da tradução instalada ({plan.state.patch}).")
        if not args.verificar and console.confirm("Desinstalar a versão anterior e instalar esta?"):
            removed = uninstall(documents, project.pack, execute=True, running=running)
            if not removed.executed:
                _print_block(console, "Não foi possível desinstalar:", removed.problems)
                return EXIT_BLOCKED
            console.out("Versão anterior removida.")
            plan = plan_install(game_root, documents, project, running=running)
    _print_block(console, "Avisos:", plan.warnings)
    if not plan.ok:
        _print_block(console, "Instalação bloqueada (nada foi alterado):", plan.problems)
        if not plan.game.ok and plan.state.kind in {"current", "other"}:
            console.out("Se o jogo foi atualizado, desinstale a tradução para ele voltar a usar os arquivos originais.")
        return EXIT_BLOCKED
    console.out(f"Jogo compatível (build Steam {plan.game.build or project.expected_build}).")
    console.out(f"A tradução será instalada em: {plan.state.target}")
    console.out("A pasta da Steam, os saves e as configurações do jogo não serão alterados.")
    if args.verificar:
        console.out("Modo verificação: tudo pronto para instalar. Nada foi alterado.")
        return EXIT_OK
    if not console.confirm("Instalar a tradução agora?"):
        console.out("Cancelado. Nada foi alterado.")
        return EXIT_BLOCKED
    outcome = install(game_root, documents, l10n_root, execute=True, running=running, say=console.progress)
    console.out(f"Pronto! Tradução {VERSION} instalada ({outcome.changes} textos).")
    console.out("No jogo, abra Opções > Idioma e escolha \"Español\": esse idioma passa a exibir o português.")
    return EXIT_OK


def _single_game(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return normalize_game_path(str(explicit))
    found = steam.find_game_dirs()
    return found[0] if len(found) == 1 else None


def run_uninstall(args: argparse.Namespace, console: Console, documents: Path | None,
                  running: Callable[[], bool] | None) -> int:
    documents = resolve_documents(console, documents, _single_game(args.jogo))
    if documents is None:
        console.out("Nenhuma pasta Documentos informada. Nada foi alterado.")
        return EXIT_BLOCKED
    plan = uninstall(documents, "base", execute=False, running=running)
    if not plan.ok:
        _print_block(console, "Desinstalação bloqueada (nada foi alterado):", plan.problems)
        if plan.target.exists() and any("manifesto" in p or "não gerenciad" in p for p in plan.problems):
            console.out(f"A pasta {plan.target} foi modificada ou não foi criada por este instalador. Por segurança "
                        "ela não é apagada automaticamente; se tiver certeza, feche o jogo e apague-a manualmente.")
        return EXIT_BLOCKED
    console.out(f"Será removida a pasta da tradução: {plan.target}")
    if args.verificar:
        console.out("Modo verificação: nada foi alterado.")
        return EXIT_OK
    if not console.confirm("Remover a tradução agora?"):
        console.out("Cancelado. Nada foi alterado.")
        return EXIT_BLOCKED
    done = uninstall(documents, "base", execute=True, running=running)
    if not done.executed:
        _print_block(console, "Desinstalação bloqueada:", done.problems)
        return EXIT_BLOCKED
    console.out("Tradução removida. O jogo volta a usar apenas os arquivos originais da Steam.")
    return EXIT_OK


def run_status(console: Console, documents: Path | None, game_root: Path | None) -> int:
    documents = resolve_documents(console, documents, game_root)
    if documents is None:
        console.out("Nenhuma pasta Documentos informada.")
        return EXIT_BLOCKED
    state = target_state(documents, "base")
    labels = {"absent": "não instalada", "current": f"instalada ({VERSION})",
              "other": f"outra versão instalada ({state.patch})", "damaged": "instalação alterada/danificada",
              "foreign": "pasta mods/base de outro mod"}
    console.out(f"Tradução: {labels[state.kind]} — {state.target}")
    _print_block(console, "Problemas:", state.problems)
    if game_root is not None and state.kind in {"current", "other"}:
        stale = shadow.stale_against_game(shadow.read_manifest(state.target), game_root)
        _print_block(console, "O jogo mudou desde a instalação (desinstale e reinstale uma versão compatível):", stale)
    return EXIT_OK if state.kind in {"absent", "current"} and not state.problems else EXIT_BLOCKED


def guarded(out: Say, action: Callable[[], int]) -> int:
    """Executa uma ação da interface convertendo falhas em mensagens (código ``EXIT_ERROR``)."""
    try:
        return action()
    except InstallerError as exc:
        out(f"ERRO: {exc}")
        out("Salvo indicação contrária na mensagem acima, nada foi alterado (operações parciais são desfeitas).")
    except (shadow.ShadowError, l10n.CatalogError, FormatError, ValueError, OSError) as exc:
        out(f"ERRO inesperado: {exc}")
        out("Salvo indicação contrária na mensagem acima, nada foi alterado. Relate o problema no GitHub do projeto.")
    except KeyboardInterrupt:
        out("Interrompido. Nenhuma instalação parcial é mantida.")
    return EXIT_ERROR


def dispatch(args: argparse.Namespace, console: Console, running: Callable[[], bool] | None) -> int:
    if args.desinstalar:
        return run_uninstall(args, console, args.documentos, running)
    if args.status:
        game = normalize_game_path(str(args.jogo)) if args.jogo else next(iter(steam.find_game_dirs()), None)
        return run_status(console, args.documentos, game)
    l10n_root = (args.traducao or default_l10n_root()).expanduser()
    return run_install(args, console, args.documentos, l10n_root, running)


def build_parser(prog: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description=f"Underkeep PT-BR {VERSION} — tradução comunitária, não oficial.")
    parser.add_argument("--jogo", type=Path, help="pasta do Underkeep (padrão: detectar na Steam)")
    parser.add_argument("--documentos", type=Path,
                        help="pasta Documentos que contém 'Underkeep' (avançado; padrão: Documentos do Windows "
                             "ou, no Linux/Steam Deck, a do prefixo Proton do jogo)")
    parser.add_argument("--traducao", type=Path, help="pasta com os catálogos pt-BR (padrão: dados/pt-BR)")
    parser.add_argument("--verificar", action="store_true", help="só verifica; não altera nada")
    parser.add_argument("--sim", action="store_true", help="não pergunta (responde sim; para uso avançado)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--desinstalar", action="store_true", help="remove a tradução instalada")
    mode.add_argument("--status", action="store_true", help="mostra o estado da instalação")
    parser.add_argument("--version", action="version", version=VERSION)
    return parser


def main(argv: list[str] | None = None, *, prog: str = "Underkeep-PTBR", input_fn: Callable[[str], str] = input,
         out: Say = print, running: Callable[[], bool] | None = None, pause: bool | None = None) -> int:
    args = build_parser(prog).parse_args(argv)
    console = Console(assume_yes=args.sim, input_fn=input_fn, out=out)
    out(f"Underkeep PT-BR {VERSION} — tradução comunitária e não oficial (sem afiliação com a Rake in Grass)")
    code = guarded(out, lambda: dispatch(args, console, running))
    should_pause = pause if pause is not None else (not args.sim and sys.stdin is not None and sys.stdin.isatty())
    if should_pause:
        try:
            input_fn("Pressione Enter para sair.")
        except EOFError:
            pass
    return code


if __name__ == "__main__":
    sys.exit(main())
