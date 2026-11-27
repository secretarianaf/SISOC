"""Reparación conservadora de texto UTF-8 interpretado como una página ANSI."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

MOJIBAKE_MARKERS = ("Ã", "Â", "â", "ð", "ï", "�")
DEFAULT_MAX_REPAIR_PASSES = 3
TITLE_CASED_UTF8_LEAD_BYTES = {"ã": 0xC3}
# Referencias numéricas HTML guardadas como texto, por ejemplo ``MU&#209;OZ``.
NUMERIC_CHARACTER_REFERENCE = re.compile(
    r"&#(?:(?P<decimal>[0-9]{2,7})|[xX](?P<hex>[0-9A-Fa-f]{2,6}));"
)
# Además de letras y marcas, sólo signos habituales en nombres y domicilios.
DECODABLE_REFERENCE_SIGNS = frozenset("'’´°")


def _single_legacy_byte(character: str) -> int | None:
    """Devuelve el byte Windows-1252/Latin-1 representado por un carácter."""

    for encoding in ("cp1252", "latin-1"):
        try:
            encoded = character.encode(encoding)
        except UnicodeEncodeError:
            continue
        if len(encoded) == 1:
            return encoded[0]
    return None


def _utf8_sequence_length(first_byte: int) -> int | None:
    if 0xC2 <= first_byte <= 0xDF:
        return 2
    if 0xE0 <= first_byte <= 0xEF:
        return 3
    if 0xF0 <= first_byte <= 0xF4:
        return 4
    return None


def _repair_once(text: str) -> tuple[str, bool]:
    repaired: list[str] = []
    changed = False
    index = 0

    while index < len(text):
        first_byte = _single_legacy_byte(text[index])
        sequence_length = (
            _utf8_sequence_length(first_byte) if first_byte is not None else None
        )
        if sequence_length and index + sequence_length <= len(text):
            byte_values = [first_byte]
            for character in text[index + 1 : index + sequence_length]:
                byte_value = _single_legacy_byte(character)
                if byte_value is None:
                    break
                byte_values.append(byte_value)

            if len(byte_values) == sequence_length and all(
                0x80 <= byte_value <= 0xBF for byte_value in byte_values[1:]
            ):
                try:
                    decoded = bytes(byte_values).decode("utf-8", errors="strict")
                except UnicodeDecodeError:
                    decoded = ""
                if decoded:
                    repaired.append(decoded)
                    index += sequence_length
                    changed = True
                    continue

        repaired.append(text[index])
        index += 1

    return "".join(repaired), changed


def _title_affected_tokens(text: str, positions: list[int]) -> str:
    result = text
    for position in positions:
        start = position
        while start > 0 and result[start - 1].isalpha():
            start -= 1

        end = position
        while end < len(result) and result[end].isalpha():
            end += 1

        result = f"{result[:start]}{result[start:end].title()}{result[end:]}"
    return result


def _repair_title_cased_once(text: str) -> tuple[str, bool]:
    """Invierte mojibake cuando hay evidencia del límite creado por title()."""

    repaired: list[str] = []
    affected_positions: list[int] = []
    changed = False
    index = 0

    while index < len(text):
        first_byte = TITLE_CASED_UTF8_LEAD_BYTES.get(text[index])
        if first_byte is not None and index + 1 < len(text):
            continuation_byte = _single_legacy_byte(text[index + 1])
            if continuation_byte is not None and 0x80 <= continuation_byte <= 0xBF:
                try:
                    decoded = bytes((first_byte, continuation_byte)).decode(
                        "utf-8", errors="strict"
                    )
                except UnicodeDecodeError:
                    decoded = ""
                category = unicodedata.category(decoded) if decoded else ""
                is_uppercase = category == "Lu"
                is_lowercase_with_title_boundary = (
                    category == "Ll"
                    and index > 0
                    and text[index - 1].isalpha()
                    and index + 2 < len(text)
                    and text[index + 2].isupper()
                )
                if is_uppercase or is_lowercase_with_title_boundary:
                    affected_positions.append(len(repaired))
                    repaired.append(decoded)
                    index += 2
                    changed = True
                    continue

        repaired.append(text[index])
        index += 1

    result = "".join(repaired)
    return _title_affected_tokens(result, affected_positions), changed


def _repair_stranded_title_boundary_once(text: str) -> tuple[str, bool]:
    """Corrige un segundo inicio de palabra dejado tras reparar el mojibake."""

    affected_positions = []
    for index, character in enumerate(text[:-2]):
        is_token_start = index == 0 or not text[index - 1].isalpha()
        decomposition = unicodedata.normalize("NFD", character)
        is_latin1_uppercase = (
            0x00C0 <= ord(character) <= 0x00DE
            and unicodedata.category(character) == "Lu"
            and any(unicodedata.category(part) == "Mn" for part in decomposition[1:])
        )
        if (
            is_token_start
            and is_latin1_uppercase
            and text[index + 1].isupper()
            and text[index + 2].islower()
        ):
            affected_positions.append(index)

    return _title_affected_tokens(text, affected_positions), bool(affected_positions)


def _referenced_character(match: re.Match[str]) -> str | None:
    """Carácter de una referencia numérica, sólo si es texto de un nombre."""

    if match["decimal"]:
        code_point = int(match["decimal"])
    else:
        code_point = int(match["hex"], 16)
    try:
        character = chr(code_point)
    except (ValueError, OverflowError):
        return None
    if character in DECODABLE_REFERENCE_SIGNS:
        return character
    if unicodedata.category(character)[0] in {"L", "M"}:
        return character
    return None


def _decode_character_references_once(text: str) -> tuple[str, bool]:
    """Decodifica referencias como ``&#209;`` sin generar marcado HTML.

    No toca entidades con nombre ni referencias a símbolos (``<``, ``>``,
    ``&``): el resultado nunca agrega marcado ni nuevas referencias. Si
    ``title()`` partió la palabra en la referencia (``Mu&#241;Oz``), normaliza
    sólo ese token.
    """

    repaired: list[str] = []
    affected_positions: list[int] = []
    changed = False
    index = 0

    for match in NUMERIC_CHARACTER_REFERENCE.finditer(text):
        character = _referenced_character(match)
        if character is None:
            continue
        repaired.append(text[index : match.start()])
        position = sum(len(part) for part in repaired)
        before = text[match.start() - 1] if match.start() else ""
        after = text[match.end()] if match.end() < len(text) else ""
        if before.islower() and after.isupper():
            affected_positions.append(position)
        repaired.append(character)
        index = match.end()
        changed = True

    repaired.append(text[index:])
    result = "".join(repaired)
    return _title_affected_tokens(result, affected_positions), changed


def repair_utf8_mojibake(
    text: str, *, max_passes: int = DEFAULT_MAX_REPAIR_PASSES
) -> str:
    """Repara sólo secuencias que reconstruyen bytes UTF-8 estrictamente válidos.

    También decodifica referencias numéricas HTML de letras (``&#209;``) que
    quedaron guardadas como texto.

    El recorrido por secuencias evita recodificar la cadena completa, porque un
    mismo campo puede mezclar caracteres correctos y mojibake. Varias pasadas
    acotadas permiten reparar texto que fue recodificado más de una vez.
    """

    current = text
    for _ in range(max(0, max_passes)):
        current, references_changed = _decode_character_references_once(current)
        current, title_cased_changed = _repair_title_cased_once(current)
        current, changed = _repair_once(current)
        current, stranded_title_changed = _repair_stranded_title_boundary_once(current)
        if not (
            references_changed
            or title_cased_changed
            or changed
            or stranded_title_changed
        ):
            break
    return current


def contains_mojibake_marker(text: str) -> bool:
    """Indica si quedan marcadores frecuentes, incluso si no son reparables."""

    return any(marker in text for marker in MOJIBAKE_MARKERS)


def repair_utf8_mojibake_values(value: Any) -> Any:
    """Repara recursivamente strings de un payload sin modificar sus claves."""

    if isinstance(value, str):
        return repair_utf8_mojibake(value)
    if isinstance(value, dict):
        return {
            key: repair_utf8_mojibake_values(item_value)
            for key, item_value in value.items()
        }
    if isinstance(value, list):
        return [repair_utf8_mojibake_values(item) for item in value]
    if isinstance(value, tuple):
        return tuple(repair_utf8_mojibake_values(item) for item in value)
    return value


def normalize_text(value: object) -> str:
    """Normaliza NFKD, diacríticos, espacios y mayúsculas para comparación."""
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(
        "".join(char for char in normalized if not unicodedata.combining(char)).split()
    ).casefold()
