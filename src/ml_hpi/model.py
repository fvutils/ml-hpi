"""Pydantic models for the ml-hpi IDL schema."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel


LOG_LEVELS = {
    "off": 0,
    "error": 1,
    "warning": 2,
    "info": 3,
    "debug": 4,
    "trace": 5,
}


class MethodAttr(BaseModel):
    solve: Optional[bool] = None
    target: Optional[bool] = None
    blocking: Optional[bool] = None
    log_level: Optional[str] = None


class Param(BaseModel):
    name: str
    type: str


class Method(BaseModel):
    name: str
    rtype: str
    params: List[Param] = []
    attr: List[MethodAttr] = []

    def is_blocking(self) -> bool:
        for a in self.attr:
            if a.blocking is not None:
                return a.blocking
        return False

    def is_target(self) -> bool:
        for a in self.attr:
            if a.target is not None:
                return a.target
        return False

    def is_solve(self) -> bool:
        for a in self.attr:
            if a.solve is not None:
                return a.solve
        return False

    def get_log_level(self) -> Optional[str]:
        """Return the method-level log_level if set, else None."""
        for a in self.attr:
            if a.log_level is not None:
                return a.log_level
        return None

    def effective_log_level(self, iface_log_level: Optional[str] = None) -> str:
        """Return resolved log level: method -> interface -> 'info'."""
        ml = self.get_log_level()
        if ml is not None:
            return ml
        if iface_log_level is not None:
            return iface_log_level
        return "info"


class Member(BaseModel):
    name: str
    kind: str   # "field" or "array"
    type: str   # qualified interface type name


class Interface(BaseModel):
    name: str
    extends: Optional[str] = None
    methods: List[Method] = []
    members: List[Member] = []
    log_level: Optional[str] = None

    def pkg(self) -> str:
        """Return the package prefix (everything before the last dot)."""
        parts = self.name.rsplit(".", 1)
        return parts[0] if len(parts) == 2 else ""

    def short_name(self) -> str:
        """Return the unqualified interface name."""
        return self.name.rsplit(".", 1)[-1]


class MlHpiSpec(BaseModel):
    interfaces: List[Interface] = []


class MlHpiDoc(BaseModel):
    """Top-level document model matching the YAML root key 'ml-hpi:'."""
    model_config = {"populate_by_name": True}

    spec: MlHpiSpec

    @classmethod
    def from_dict(cls, data: dict) -> "MlHpiDoc":
        raw = data.get("ml-hpi", data)
        return cls(spec=MlHpiSpec(**raw))
