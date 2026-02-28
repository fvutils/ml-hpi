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
