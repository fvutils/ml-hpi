"""Base parser infrastructure for ml-hpi."""
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from ml_hpi.model import MlHpiDoc, Method, Member


class Parser(ABC):
    """Abstract base for ml-hpi language parsers."""

    @abstractmethod
    def parse(self, source: Union[str, Path]) -> MlHpiDoc:
        """Parse language source and return an MlHpiDoc."""
        ...


# ------------------------------------------------------------------
# Reverse type maps: language type -> ml-hpi type
# ------------------------------------------------------------------

SV_TYPE_TO_ML: dict[str, str] = {
    "void":                "void",
    "bit":                 "bool",
    "byte":                "int8",
    "byte unsigned":       "uint8",
    "shortint":            "int16",
    "shortint unsigned":   "uint16",
    "int":                 "int32",
    "int unsigned":        "uint32",
    "longint":             "int64",
    "longint unsigned":    "uint64",
    "chandle":             "uintptr",
}

CPP_TYPE_TO_ML: dict[str, str] = {
    "void":       "void",
    "bool":       "bool",
    "int8_t":     "int8",
    "uint8_t":    "uint8",
    "int16_t":    "int16",
    "uint16_t":   "uint16",
    "int32_t":    "int32",
    "uint32_t":   "uint32",
    "int64_t":    "int64",
    "uint64_t":   "uint64",
    "uintptr_t":  "uintptr",
}

PSS_TYPE_TO_ML: dict[str, str] = {
    "void":          "void",
    "bool":          "bool",
    "addr_t":        "addr",
    "addr_handle_t": "addr",
    "chandle":       "uintptr",
}
# PSS bit<N>/int<N> are handled programmatically by pss_scalar_to_ml().

PYTHON_CTYPES_TO_ML: dict[str, str] = {
    "None":             "void",
    "ctypes.c_bool":    "bool",
    "ctypes.c_int8":    "int8",
    "ctypes.c_uint8":   "uint8",
    "ctypes.c_int16":   "int16",
    "ctypes.c_uint16":  "uint16",
    "ctypes.c_int32":   "int32",
    "ctypes.c_uint32":  "uint32",
    "ctypes.c_int64":   "int64",
    "ctypes.c_uint64":  "uint64",
    "ctypes.c_void_p":  "uintptr",
}


def pss_scalar_to_ml(pss_type: str) -> str:
    """Map a PSS scalar type string to its ml-hpi equivalent.

    Handles ``bit<N>`` and ``int<N>`` programmatically in addition to the
    static ``PSS_TYPE_TO_ML`` lookup.
    """
    if pss_type in PSS_TYPE_TO_ML:
        return PSS_TYPE_TO_ML[pss_type]

    # bit<N> -> uintN
    if pss_type.startswith("bit<") and pss_type.endswith(">"):
        width = pss_type[4:-1]
        return f"uint{width}"

    # int<N> -> intN
    if pss_type.startswith("int<") and pss_type.endswith(">"):
        width = pss_type[4:-1]
        return f"int{width}"

    return pss_type


def infer_member_accessors(
    methods: list[dict],
    interface_names: set[str],
) -> tuple[list[dict], list[dict]]:
    """Split raw parsed methods into proper methods and inferred members.

    Detects two patterns among *methods* (each a dict with at least ``name``,
    ``rtype``, ``params``):

    - **field**: zero-param method returning a type in *interface_names*.
    - **array**: a pair of ``{name}_at(int idx)`` returning an interface type
      and ``{name}_size()`` returning ``int``-like.

    Returns ``(remaining_methods, inferred_members)`` where each member is a
    dict with ``name``, ``kind`` (``"field"`` or ``"array"``), and ``type``.
    """
    by_name: dict[str, dict] = {m["name"]: m for m in methods}
    members: list[dict] = []
    consumed: set[str] = set()

    # Detect array pairs first (_at / _size)
    at_suffix = "_at"
    size_suffix = "_size"
    at_candidates = [n for n in by_name if n.endswith(at_suffix)]
    for at_name in at_candidates:
        base = at_name[: -len(at_suffix)]
        size_name = f"{base}{size_suffix}"
        if size_name not in by_name:
            continue
        at_m = by_name[at_name]
        if at_m["rtype"] in interface_names:
            members.append({
                "name": base,
                "kind": "array",
                "type": at_m["rtype"],
            })
            consumed.add(at_name)
            consumed.add(size_name)

    # Detect field accessors (zero params returning interface type)
    for m in methods:
        if m["name"] in consumed:
            continue
        if not m["params"] and m["rtype"] in interface_names:
            members.append({
                "name": m["name"],
                "kind": "field",
                "type": m["rtype"],
            })
            consumed.add(m["name"])

    remaining = [m for m in methods if m["name"] not in consumed]
    return remaining, members
