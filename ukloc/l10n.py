"""Catálogo PT-BR versionável (Fase 1C-B).

Layout no repositório::

    l10n/pt-BR/project.json      alvo (pack, slot, idioma de referência) e hashes esperados da build
    l10n/pt-BR/<categoria>.json  entradas traduzidas, uma por ID

O catálogo **não** contém texto original do jogo: cada entrada guarda apenas o SHA-256 do texto
inglês de referência (``source_sha256``), que serve para detectar mudanças após atualizações.
Planilhas com o texto original para revisão humana são geradas sob demanda em ``work/``.

Estados (dois eixos, independentes):

* ``translation_status``: ``pending`` (sem texto) → ``translated`` | ``needs_review``
* ``review_status``: ``pending`` → ``reviewed`` → ``approved`` | ``needs_review``

Política de build (quais entradas viram alteração no slot de destino):

* ``approved``  (padrão): somente ``review_status == approved``;
* ``reviewed``: ``reviewed`` ou ``approved``;
* ``translated`` (experimental, explícito): ``translation_status == translated`` e revisão ≠ ``needs_review``.

Entradas ``pending`` ou ``needs_review`` nunca são aplicadas. Gerações automáticas só ACRESCENTAM
entradas ``pending``; uma tradução existente nunca é sobrescrita.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from . import markup
from .shadow import ABSENT_SHA256, Change, Patch, ShadowError
from .textdb import text_file_name
from .validate import ERROR, WARNING, ExceptionRule, Issue, validate_catalog

CATALOG_SCHEMA = "ukloc.l10n.catalog/1"
PROJECT_SCHEMA = "ukloc.l10n.project/1"
TRANSLATION_STATES = ("pending", "translated", "needs_review")
REVIEW_STATES = ("pending", "reviewed", "approved", "needs_review")
POLICIES = ("approved", "reviewed", "translated")
CATEGORIES = ("common", "game", "items", "skills")
ENTRY_FIELDS = ("source_sha256", "text", "translation_status", "review_status", "context",
                "terminology", "exceptions", "location", "origin", "review_note")


class CatalogError(ValueError):
    """Catálogo malformado (estrutura, estados ou campos)."""


def text_sha256(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- modelo
@dataclass
class Entry:
    source_sha256: str
    text: str | None = None
    translation_status: str = "pending"
    review_status: str = "pending"
    context: str = ""
    location: str = ""
    terminology: list[str] = field(default_factory=list)
    exceptions: list[dict[str, str]] = field(default_factory=list)
    origin: str = ""        # quem/que produziu o texto (ex.: "ia:lote-01", "humano")
    review_note: str = ""   # como a revisão aconteceu (ex.: "qa-lote:lote-01", "humano:amostragem")

    def is_applicable(self, policy: str) -> bool:
        if self.text is None or self.translation_status != "translated":
            return False
        if policy == "approved":
            return self.review_status == "approved"
        if policy == "reviewed":
            return self.review_status in ("reviewed", "approved")
        if policy == "translated":
            return self.review_status != "needs_review"
        raise CatalogError(f"política desconhecida: {policy!r}")

    def is_slot_addition(self) -> bool:
        """ID ausente no slot que deve ser acrescentado: exige exceção ``MISSING_IN_SLOT`` justificada."""
        return any(x.get("code") == "MISSING_IN_SLOT" for x in self.exceptions)

    def exception_rules(self, entry_id: str) -> list[ExceptionRule]:
        return [ExceptionRule(entry_id, item["code"], item["justification"]) for item in self.exceptions]


@dataclass
class Catalog:
    category: str
    locale: str = "pt-BR"
    entries: dict[str, Entry] = field(default_factory=dict)


@dataclass
class Project:
    locale: str
    reference_language: str
    target_slot: str
    pack: str
    expected_build: str | None
    expected_exe_sha256: str
    expected_files: dict[str, str]


# --------------------------------------------------------------------------- (de)serialização
def _entry_from_dict(entry_id: str, raw: Any) -> Entry:
    if not isinstance(raw, dict):
        raise CatalogError(f"{entry_id}: entrada deve ser objeto")
    unknown = set(raw) - set(ENTRY_FIELDS)
    if unknown:
        raise CatalogError(f"{entry_id}: campos desconhecidos {sorted(unknown)}")
    source = raw.get("source_sha256")
    if not isinstance(source, str) or len(source) != 64:
        raise CatalogError(f"{entry_id}: source_sha256 inválido")
    entry = Entry(
        source_sha256=source.lower(),
        text=raw.get("text"),
        translation_status=raw.get("translation_status", "pending"),
        review_status=raw.get("review_status", "pending"),
        context=raw.get("context", ""),
        location=raw.get("location", ""),
        terminology=list(raw.get("terminology", [])),
        exceptions=list(raw.get("exceptions", [])),
        origin=raw.get("origin", ""),
        review_note=raw.get("review_note", ""),
    )
    if entry.translation_status not in TRANSLATION_STATES:
        raise CatalogError(f"{entry_id}: translation_status inválido {entry.translation_status!r}")
    if entry.review_status not in REVIEW_STATES:
        raise CatalogError(f"{entry_id}: review_status inválido {entry.review_status!r}")
    if entry.text is not None and not isinstance(entry.text, str):
        raise CatalogError(f"{entry_id}: text deve ser string ou null")
    if entry.translation_status == "pending" and entry.text is not None:
        raise CatalogError(f"{entry_id}: entrada pending não pode ter texto")
    if entry.translation_status != "pending" and not entry.text:
        raise CatalogError(f"{entry_id}: {entry.translation_status} exige texto não vazio")
    if entry.review_status in ("reviewed", "approved") and entry.translation_status != "translated":
        raise CatalogError(f"{entry_id}: revisão {entry.review_status} exige translation_status translated")
    for item in entry.exceptions:
        if not isinstance(item, dict) or set(item) != {"code", "justification"} \
                or len(str(item.get("justification", "")).strip()) < 10:
            raise CatalogError(f"{entry_id}: exceção exige code + justification (>= 10 caracteres)")
    if not isinstance(entry.origin, str) or not isinstance(entry.review_note, str):
        raise CatalogError(f"{entry_id}: origin/review_note devem ser strings")
    if not all(isinstance(t, str) for t in entry.terminology):
        raise CatalogError(f"{entry_id}: terminology deve ser lista de strings")
    return entry


def catalog_from_dict(data: Any) -> Catalog:
    if not isinstance(data, dict) or data.get("schema") != CATALOG_SCHEMA:
        raise CatalogError(f"schema deve ser {CATALOG_SCHEMA!r}")
    category = data.get("category")
    if category not in CATEGORIES:
        raise CatalogError(f"categoria inválida: {category!r}")
    raw_entries = data.get("entries")
    if not isinstance(raw_entries, dict):
        raise CatalogError("entries deve ser objeto id -> entrada")
    entries = {}
    for entry_id, raw in raw_entries.items():
        if not isinstance(entry_id, str) or entry_id.strip() == "":
            raise CatalogError("ID vazio no catálogo")
        entries[entry_id] = _entry_from_dict(entry_id, raw)
    return Catalog(category, data.get("locale", "pt-BR"), entries)


def catalog_to_dict(catalog: Catalog) -> dict[str, Any]:
    entries: dict[str, Any] = {}
    for entry_id in sorted(catalog.entries):
        e = catalog.entries[entry_id]
        item: dict[str, Any] = {"source_sha256": e.source_sha256, "text": e.text,
                                "translation_status": e.translation_status, "review_status": e.review_status}
        if e.location:
            item["location"] = e.location
        if e.context:
            item["context"] = e.context
        if e.terminology:
            item["terminology"] = list(e.terminology)
        if e.exceptions:
            item["exceptions"] = [dict(x) for x in e.exceptions]
        if e.origin:
            item["origin"] = e.origin
        if e.review_note:
            item["review_note"] = e.review_note
        entries[entry_id] = item
    return {"schema": CATALOG_SCHEMA, "locale": catalog.locale, "category": catalog.category, "entries": entries}


def catalog_to_json(catalog: Catalog) -> str:
    """JSON determinístico: chaves ordenadas, indentação fixa, LF, UTF-8 sem escape."""
    return json.dumps(catalog_to_dict(catalog), ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def load_catalog(path: Path) -> Catalog:
    return catalog_from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_catalog(path: Path, catalog: Catalog) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(catalog_to_json(catalog), encoding="utf-8", newline="\n")
    tmp.replace(path)


def load_project(path: Path) -> Project:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != PROJECT_SCHEMA:
        raise CatalogError(f"project.json: schema deve ser {PROJECT_SCHEMA!r}")
    expected = data.get("expected") or {}
    try:
        return Project(data["locale"], data["reference_language"], data["target_slot"], data["pack"],
                       expected.get("game_build"), str(expected["exe_sha256"]).lower(),
                       {k: str(v).lower() for k, v in expected.get("files", {}).items()})
    except KeyError as exc:
        raise CatalogError(f"project.json: campo ausente {exc}") from exc


def load_catalogs(root: Path) -> dict[str, Catalog]:
    catalogs: dict[str, Catalog] = {}
    for category in CATEGORIES:
        path = root / f"{category}.json"
        if path.is_file():
            catalog = load_catalog(path)
            if catalog.category != category:
                raise CatalogError(f"{path.name}: categoria interna {catalog.category!r} difere do nome")
            catalogs[category] = catalog
    return catalogs


# --------------------------------------------------------------------------- geração (sem sobrescrever)
def add_pending(catalog: Catalog, ids: Iterable[str], reference: Mapping[str, str]) -> tuple[list[str], list[str]]:
    """Acrescenta entradas ``pending`` para IDs ausentes. Nunca altera entradas existentes."""
    added, kept = [], []
    for entry_id in ids:
        if entry_id in catalog.entries:
            kept.append(entry_id)
            continue
        if entry_id not in reference:
            raise CatalogError(f"{entry_id}: não existe na referência")
        catalog.entries[entry_id] = Entry(source_sha256=text_sha256(reference[entry_id]))
        added.append(entry_id)
    return added, kept


def stale_entries(catalog: Catalog, reference: Mapping[str, str]) -> list[str]:
    """IDs cujo texto de referência mudou (ou sumiu) desde a tradução."""
    return sorted(i for i, e in catalog.entries.items()
                  if i not in reference or text_sha256(reference[i]) != e.source_sha256)


def mark_stale(catalog: Catalog, reference: Mapping[str, str]) -> list[str]:
    """Marca entradas desatualizadas como ``needs_review`` (texto preservado)."""
    ids = stale_entries(catalog, reference)
    for entry_id in ids:
        entry = catalog.entries[entry_id]
        if entry.translation_status == "translated":
            entry.translation_status = "needs_review"
        if entry.review_status != "pending":
            entry.review_status = "needs_review"
    return ids


def promote(catalog: Catalog, *, origin: str, to: str, note: str,
            passing: Iterable[str] | None = None) -> list[str]:
    """Promove em lote entradas ``translated/pending`` de uma origem (lote) para ``reviewed``/``approved``.

    Rastreável: grava ``review_note`` (ex.: ``qa-lote:lote-01``), que distingue promoção por QA de revisão
    individual. Nunca toca entradas já revisadas/aprovadas, ``needs_review`` ou de outra origem. ``passing``
    restringe às entradas que passaram no QA (IDs sem erro do validador).
    """
    if to not in ("reviewed", "approved"):
        raise CatalogError("promoção só para reviewed ou approved")
    if not note.strip():
        raise CatalogError("promoção exige nota de rastreabilidade")
    allowed = None if passing is None else set(passing)
    promoted = []
    for entry_id, entry in sorted(catalog.entries.items()):
        if entry.origin != origin or entry.translation_status != "translated" or entry.review_status != "pending":
            continue
        if allowed is not None and entry_id not in allowed:
            continue
        entry.review_status = to
        entry.review_note = note
        promoted.append(entry_id)
    return promoted


# --------------------------------------------------------------------------- validação
def visible_length(text: str) -> int:
    """Comprimento sem tokens de marcação (aproxima o que aparece na tela)."""
    return sum(len(piece) for is_token, piece in markup.split_tokens(text) if not is_token)


@dataclass
class CatalogReport:
    issues: list[Issue] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == ERROR]

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_l10n(catalog: Catalog, reference: Mapping[str, str], slot: Mapping[str, str], *,
                  glyphs: frozenset[int] | None = None, length_tolerance: float = 1.15) -> CatalogReport:
    """Valida um catálogo contra a referência (``en``) e o slot de destino (``es``).

    Erros: ID inexistente na referência ou no slot, referência alterada (``STALE_SOURCE``) em entrada
    traduzida e todas as regras estruturais/textuais de :func:`ukloc.validate.validate_catalog`.
    Aviso ``LENGTH_OVER_SLOT``: texto visível mais longo que o do slot substituído além da tolerância.
    """
    report = CatalogReport()
    counts: dict[str, int] = {}
    for entry_id in sorted(catalog.entries):
        entry = catalog.entries[entry_id]
        key = f"{entry.translation_status}/{entry.review_status}"
        counts[key] = counts.get(key, 0) + 1
        if entry_id not in reference:
            report.issues.append(Issue("UNKNOWN_ID", ERROR, entry_id, "não existe na referência"))
            continue
        if entry_id not in slot:
            if entry.is_slot_addition():
                report.issues.append(Issue("SLOT_ADDITION", WARNING, entry_id,
                                           "ausente no slot de destino; será acrescentado (exceção justificada)"))
            else:
                report.issues.append(Issue("MISSING_IN_SLOT", ERROR, entry_id,
                                           "não existe no slot de destino; não pode ser aplicado"))
        if text_sha256(reference[entry_id]) != entry.source_sha256:
            severity = ERROR if entry.translation_status == "translated" else WARNING
            report.issues.append(Issue("STALE_SOURCE", severity, entry_id,
                                       "texto de referência mudou desde a tradução"))
        if entry.text is None:
            continue
        result = validate_catalog([(entry_id, entry.text)], {entry_id: reference[entry_id]}, glyphs=glyphs,
                                  exceptions=entry.exception_rules(entry_id))
        report.issues.extend(result.issues)
        length_waived = any(x["code"] == "LENGTH_OVER_SLOT" for x in entry.exceptions)
        if not length_waived:
            limit = max(visible_length(slot.get(entry_id, "")), visible_length(reference[entry_id]))
            if visible_length(entry.text) > limit * length_tolerance + 2:
                report.issues.append(Issue("LENGTH_OVER_SLOT", WARNING, entry_id,
                                           f"{visible_length(entry.text)} visíveis > {limit} (slot/ref)"))
    report.counts = dict(sorted(counts.items()))
    return report


# --------------------------------------------------------------------------- build
@dataclass
class Selection:
    changes: list[Change]
    exceptions: list[ExceptionRule]
    skipped: dict[str, list[str]]


def select_changes(project: Project, catalogs: Mapping[str, Catalog],
                   reference: Mapping[str, Mapping[str, str]], slot: Mapping[str, Mapping[str, str]],
                   policy: str = "approved") -> Selection:
    """Converte entradas aplicáveis em :class:`ukloc.shadow.Change` (hash do valor atual do slot)."""
    if policy not in POLICIES:
        raise CatalogError(f"política desconhecida: {policy!r}")
    changes: list[Change] = []
    rules: list[ExceptionRule] = []
    skipped: dict[str, list[str]] = {}
    for category in sorted(catalogs):
        ref, dst = reference.get(category, {}), slot.get(category, {})
        for entry_id, entry in sorted(catalogs[category].entries.items()):
            if not entry.is_applicable(policy):
                skipped.setdefault(f"{entry.translation_status}/{entry.review_status}", []).append(
                    f"{category}/{entry_id}")
                continue
            if entry_id not in ref or text_sha256(ref[entry_id]) != entry.source_sha256:
                raise ShadowError(f"{category}/{entry_id}: referência {project.reference_language} mudou "
                                  "(jogo atualizado?) — revise antes de gerar")
            if entry_id in dst:
                changes.append(Change(category, entry_id, text_sha256(dst[entry_id]), entry.text or ""))
            elif entry.is_slot_addition():
                changes.append(Change(category, entry_id, ABSENT_SHA256, entry.text or "", add=True))
            else:
                raise ShadowError(f"{category}/{entry_id}: ausente no slot {project.target_slot}")
            rules.extend(entry.exception_rules(entry_id))
    return Selection(changes, rules, skipped)


def make_patch(project: Project, name: str, changes: list[Change]) -> Patch:
    if not changes:
        raise ShadowError("nenhuma entrada aplicável com a política escolhida")
    files = {text_file_name(c.category, project.target_slot) for c in changes}
    missing = sorted(f for f in files if f not in project.expected_files)
    if missing:
        raise ShadowError(f"project.json sem hash esperado para {missing}")
    return Patch(name, project.pack, project.target_slot, project.expected_build, project.expected_exe_sha256,
                 dict(project.expected_files), tuple(changes))
