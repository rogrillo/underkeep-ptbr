"""Formatos binários observados na engine de Underkeep (build Steam 26592006)."""


class FormatError(ValueError):
    """Os bytes não correspondem ao formato observado."""


class UnknownTypeError(FormatError):
    """Byte de tipo nunca observado; o tamanho do valor é desconhecido, então o parse para."""

    def __init__(self, container: str, type_byte: int, offset: int) -> None:
        super().__init__(f"{container}: tipo desconhecido 0x{type_byte:02x} no offset {offset}")
        self.container = container
        self.type_byte = type_byte
        self.offset = offset


class NonCanonicalError(FormatError):
    """Arquivo válido, mas fora da forma canônica observada (round-trip não garantido)."""
