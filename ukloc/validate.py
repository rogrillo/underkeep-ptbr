"""Validação de catálogos de localização contra a referência (``en``) e o idioma substituído.

Cada problema vira um :class:`Issue` com código estável. Exceções só são aceitas com
justificativa documentada (arquivo JSON, ver :func:`load_exceptions`).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Iterable, Mapping

from . import markup

ERROR = "error"
WARNING = "warning"

# Caracteres sem cobertura nas fontes identificadas, bloqueados mesmo sem glyph set.
KNOWN_UNSUPPORTED = frozenset("…“”‘’–—€")
ALLOWED_CONTROL = frozenset("\r\n")


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    id: str
    detail: str = ""


@dataclass(frozen=True)
class ExceptionRule:
    id: str
    code: str
    justification: str


@dataclass
class ValidationResult:
    issues: list[Issue] = field(default_factory=list)
    suppressed: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == WARNING]

    def codes(self) -> Counter[str]:
        return Counter(i.code for i in self.issues)

    @property
    def ok(self) -> bool:
        return not self.errors


def load_exceptions(path: Path) -> list[ExceptionRule]:
    """Formato: ``[{"id": ..., "code": ..., "justification": ...}, ...]``."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return parse_exceptions(data)


def parse_exceptions(data: object) -> list[ExceptionRule]:
    if not isinstance(data, list):
        raise ValueError("arquivo de exceções deve ser uma lista")
    rules = []
    for raw in data:
        if not isinstance(raw, dict):
            raise ValueError("exceção deve ser objeto")
        justification = str(raw.get("justification", "")).strip()
        if not raw.get("id") or not raw.get("code"):
            raise ValueError("exceção exige 'id' e 'code'")
        if len(justification) < 10:
            raise ValueError(f"exceção {raw.get('id')}/{raw.get('code')} sem justificativa documentada")
        rules.append(ExceptionRule(str(raw["id"]), str(raw["code"]), justification))
    return rules


def _check_text(entry_id: str, text: str, ref: str | None,
                glyphs: frozenset[int] | None) -> list[Issue]:
    issues: list[Issue] = []
    for problem in markup.brace_problems(text):
        issues.append(Issue("MARKUP_MALFORMED", ERROR, entry_id, problem))
    breaks = markup.line_breaks(text)
    if breaks["bare_lf"] or breaks["bare_cr"]:
        issues.append(Issue("LINEBREAK_BARE", ERROR, entry_id,
                            "LF ou CR isolado (o jogo usa apenas CRLF ou \\n literal)"))
    bad_chars = sorted({ch for ch in text if ch in KNOWN_UNSUPPORTED
                        or (glyphs is not None and ord(ch) not in glyphs and ch not in ALLOWED_CONTROL)
                        or (ord(ch) < 32 and ch not in ALLOWED_CONTROL)})
    if bad_chars:
        issues.append(Issue("UNSUPPORTED_GLYPH", ERROR, entry_id,
                            " ".join(f"U+{ord(ch):04X}" for ch in bad_chars)))
    if ref is None:
        return issues
    if text.strip() == "" and ref.strip() != "":
        issues.append(Issue("EMPTY_VALUE", ERROR, entry_id, "vazio, mas a referência não é"))
    if markup.placeholders(text) != markup.placeholders(ref):
        issues.append(Issue("PLACEHOLDER_MISMATCH", ERROR, entry_id,
                            f"{dict(markup.placeholders(ref))} -> {dict(markup.placeholders(text))}"))
    ref_tags, tags = markup.tag_tokens(ref), markup.tag_tokens(text)
    if Counter(ref_tags) != Counter(tags):
        issues.append(Issue("MARKUP_MISMATCH", ERROR, entry_id,
                            f"tags diferentes da referência ({len(ref_tags)} -> {len(tags)})"))
    elif ref_tags != tags:
        issues.append(Issue("MARKUP_ORDER", WARNING, entry_id, "mesmas tags em outra ordem"))
    ref_breaks = markup.line_breaks(ref)
    if (breaks["escaped"], breaks["crlf"]) != (ref_breaks["escaped"], ref_breaks["crlf"]):
        issues.append(Issue("LINEBREAK_MISMATCH", WARNING, entry_id,
                            f"\\n {ref_breaks['escaped']}->{breaks['escaped']}, "
                            f"CRLF {ref_breaks['crlf']}->{breaks['crlf']}"))
    if text == ref and any(ch.isalpha() for ch in ref) and not entry_id.endswith("_no_localize"):
        issues.append(Issue("UNTRANSLATED", WARNING, entry_id, "idêntico à referência"))
    return issues


def validate_catalog(
    entries: Iterable[tuple[str, str]],
    reference: Mapping[str, str],
    *,
    replaced: Mapping[str, str] | None = None,
    glyphs: frozenset[int] | None = None,
    exceptions: Iterable[ExceptionRule] = (),
    other_category_ids: Iterable[str] = (),
) -> ValidationResult:
    """Valida ``(id, texto)`` de uma categoria.

    * ``reference``: tabela do idioma de referência (``en``) da mesma categoria.
    * ``replaced``: tabela do idioma cujo slot será substituído (``es``), para
      relatar divergências de conjunto de chaves.
    * ``other_category_ids``: IDs das outras categorias do mesmo idioma (o jogo funde
      as 4 tabelas e rejeita IDs repetidos).
    """
    entries = list(entries)
    issues: list[Issue] = []
    # Bloqueios estruturais: no jogo, ID vazio é erro FATAL em _MergeLanguageTexts
    # (FUN_1400ed960) para QUALQUER idioma, mesmo que não esteja em uso; valor não
    # textual é descartado com log. Ver docs/FASE_1B_RELATORIO.md, seção 4.
    structural_bad = False
    for position, (entry_id, text) in enumerate(entries):
        if not isinstance(entry_id, str) or entry_id.strip() == "":
            issues.append(Issue("EMPTY_ID", ERROR, f"#{position}", "ID vazio/não textual derruba o jogo"))
            structural_bad = True
        if not isinstance(text, str):
            issues.append(Issue("NON_STRING_VALUE", ERROR, str(entry_id),
                                f"valor {type(text).__name__} (o jogo exige string)"))
            structural_bad = True
    if structural_bad:
        result = ValidationResult()
        result.issues.extend(issues)  # sem exceções possíveis para bloqueios estruturais
        return result
    counts = Counter(entry_id for entry_id, _ in entries)
    for entry_id, n in sorted(counts.items()):
        if n > 1:
            issues.append(Issue("DUPLICATE_ID", ERROR, entry_id, f"{n} ocorrências"))
    others = set(other_category_ids)
    for entry_id in sorted(counts.keys() & others):
        issues.append(Issue("DUPLICATE_ID_CROSS_CATEGORY", ERROR, entry_id,
                            "ID repetido em outra categoria do mesmo idioma"))
    present = set(counts)
    for entry_id in sorted(set(reference) - present):
        issues.append(Issue("MISSING_ID", ERROR, entry_id, "ausente em relação à referência"))
    for entry_id in sorted(present - set(reference)):
        issues.append(Issue("EXTRA_ID", WARNING, entry_id, "não existe na referência"))
    if replaced is not None:
        for entry_id in sorted(set(replaced) - present):
            issues.append(Issue("MISSING_VS_REPLACED", WARNING, entry_id,
                                "existe no idioma substituído, ausente no catálogo"))
    for entry_id, text in entries:
        ref = reference.get(entry_id)
        issues.extend(_check_text(entry_id, text, ref, glyphs))
        if entry_id.endswith("_no_localize") and ref is not None and text != ref:
            issues.append(Issue("NO_LOCALIZE_CHANGED", ERROR, entry_id,
                                "chave _no_localize deve manter o texto original"))
    allowed = {(rule.id, rule.code) for rule in exceptions}
    result = ValidationResult()
    for issue in issues:
        (result.suppressed if (issue.id, issue.code) in allowed else result.issues).append(issue)
    return result
