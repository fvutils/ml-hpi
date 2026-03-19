"""Base generator infrastructure for ml-hpi."""
from __future__ import annotations
import yaml
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union
from ml_hpi.model import MlHpiDoc


def load_spec(source: Union[str, Path, dict]) -> MlHpiDoc:
    """Load an ml-hpi spec from a YAML file path, YAML string, or dict."""
    if isinstance(source, dict):
        return MlHpiDoc.from_dict(source)
    path = Path(source)
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f)
        return MlHpiDoc.from_dict(data)
    # Treat as YAML string
    data = yaml.safe_load(source)
    return MlHpiDoc.from_dict(data)


class Generator(ABC):
    """Abstract base for ml-hpi code generators."""

    def __init__(self, doc: MlHpiDoc):
        self.doc = doc

    @abstractmethod
    def generate(self, outdir: Union[str, Path]) -> list[Path]:
        """Generate files into outdir; return list of generated Paths."""
        ...

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def sv_qualified(ml_name: str) -> str:
        """Convert ml-hpi dotted name to SV package-qualified name: tb.RegIf → tb::RegIf"""
        parts = ml_name.rsplit(".", 1)
        if len(parts) == 2:
            return f"{parts[0]}::{parts[1]}"
        return ml_name

    @staticmethod
    def pkg_to_flat(qualified_name: str) -> str:
        """'a.b.MyIf' -> 'a_b_MyIf'"""
        return qualified_name.replace(".", "_")

    @staticmethod
    def sv_type(ml_type: str, addr_bits: int = 64) -> str:
        """Map an ml-hpi scalar type to its SystemVerilog DPI type string."""
        _map = {
            "void":    "void",
            "bool":    "bit",
            "int8":    "byte",
            "uint8":   "byte unsigned",
            "int16":   "shortint",
            "uint16":  "shortint unsigned",
            "int32":   "int",
            "uint32":  "int unsigned",
            "int64":   "longint",
            "uint64":  "longint unsigned",
            "addr":    "longint unsigned" if addr_bits == 64 else "int unsigned",
            "addr32":  "int unsigned",
            "addr64":  "longint unsigned",
            "uintptr": "chandle",
        }
        return _map.get(ml_type, ml_type)

    @staticmethod
    def c_type(ml_type: str, addr_bits: int = 64) -> str:
        """Map an ml-hpi scalar type to its C type string."""
        _map = {
            "void":    "void",
            "bool":    "bool",
            "int8":    "int8_t",
            "uint8":   "uint8_t",
            "int16":   "int16_t",
            "uint16":  "uint16_t",
            "int32":   "int32_t",
            "uint32":  "uint32_t",
            "int64":   "int64_t",
            "uint64":  "uint64_t",
            "addr":    "uint64_t" if addr_bits == 64 else "uint32_t",
            "addr32":  "uint32_t",
            "addr64":  "uint64_t",
            "uintptr": "uintptr_t",
        }
        return _map.get(ml_type, ml_type)

    @staticmethod
    def cpp_type(ml_type: str, addr_bits: int = 64) -> str:
        """Map an ml-hpi scalar type to its C++ type string.

        Identical to c_type() since C++ uses the same <cstdint> types.
        """
        return Generator.c_type(ml_type, addr_bits)

    @staticmethod
    def python_type(ml_type: str, style: str = "plain", addr_bits: int = 64) -> str:
        """Map an ml-hpi scalar type to its Python type string.

        *style* is one of ``"plain"``, ``"annotated"``, or ``"ctypes"``.
        """
        if style == "ctypes":
            _map = {
                "void":    "None",
                "bool":    "ctypes.c_bool",
                "int8":    "ctypes.c_int8",
                "uint8":   "ctypes.c_uint8",
                "int16":   "ctypes.c_int16",
                "uint16":  "ctypes.c_uint16",
                "int32":   "ctypes.c_int32",
                "uint32":  "ctypes.c_uint32",
                "int64":   "ctypes.c_int64",
                "uint64":  "ctypes.c_uint64",
                "addr":    f"ctypes.c_uint{addr_bits}",
                "addr32":  "ctypes.c_uint32",
                "addr64":  "ctypes.c_uint64",
                "uintptr": "ctypes.c_void_p",
            }
            return _map.get(ml_type, ml_type)

        if style == "annotated":
            _map = {
                "void":    "None",
                "bool":    "bool",
                "int8":    "Int8",
                "uint8":   "UInt8",
                "int16":   "Int16",
                "uint16":  "UInt16",
                "int32":   "Int32",
                "uint32":  "UInt32",
                "int64":   "Int64",
                "uint64":  "UInt64",
                "addr":    "Addr",
                "addr32":  "Addr32",
                "addr64":  "Addr64",
                "uintptr": "UIntPtr",
            }
            return _map.get(ml_type, ml_type)

        # plain
        _map = {
            "void":    "None",
            "bool":    "bool",
            "int8":    "int",
            "uint8":   "int",
            "int16":   "int",
            "uint16":  "int",
            "int32":   "int",
            "uint32":  "int",
            "int64":   "int",
            "uint64":  "int",
            "addr":    "int",
            "addr32":  "int",
            "addr64":  "int",
            "uintptr": "int",
        }
        return _map.get(ml_type, ml_type)

    @staticmethod
    def pss_type(ml_type: str, addr_bits: int = 64) -> str:
        """Map an ml-hpi scalar type to its PSS type string."""
        _map = {
            "void":    "void",
            "bool":    "bool",
            "int8":    "int<8>",
            "uint8":   "bit<8>",
            "int16":   "int<16>",
            "uint16":  "bit<16>",
            "int32":   "int<32>",
            "uint32":  "bit<32>",
            "int64":   "int<64>",
            "uint64":  "bit<64>",
            "addr":    "addr_t",
            "addr32":  "addr_t",
            "addr64":  "addr_t",
            "uintptr": "chandle",
        }
        return _map.get(ml_type, ml_type)
