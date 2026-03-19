"""Python parser for ml-hpi (typing.Protocol classes -> IDL)."""
from __future__ import annotations
import ast
import re
from pathlib import Path
from typing import Union

from ml_hpi.model import (
    Interface, Method, MethodAttr, Param, Member, MlHpiDoc, MlHpiSpec,
)
from .parse_base import Parser, PYTHON_CTYPES_TO_ML, infer_member_accessors


# Reverse map for annotated-style aliases
_ANNOTATED_TO_ML: dict[str, str] = {
    "Int8":    "int8",
    "UInt8":   "uint8",
    "Int16":   "int16",
    "UInt16":  "uint16",
    "Int32":   "int32",
    "UInt32":  "uint32",
    "Int64":   "int64",
    "UInt64":  "uint64",
    "Addr":    "addr",
    "Addr32":  "addr32",
    "Addr64":  "addr64",
    "UIntPtr": "uintptr",
}


class ParsePython(Parser):
    """Parse Python ``typing.Protocol`` subclasses into an ``MlHpiDoc``."""

    def __init__(self, pkg_prefix: str = ""):
        """*pkg_prefix* is prepended to class names (e.g. ``"pkg"``)."""
        self.pkg_prefix = pkg_prefix

    def parse(self, source: Union[str, Path]) -> MlHpiDoc:
        source_str = str(source) if isinstance(source, Path) else source
        path = Path(source_str)
        if path.is_file():
            text = path.read_text()
        else:
            text = source_str

        # Extract # ml-hpi: pragmas keyed by line number (1-based)
        self._line_pragmas: dict[int, dict[str, str]] = {}
        for lineno, line in enumerate(text.splitlines(), 1):
            m = re.search(r'#\s*ml-hpi:\s*(.+)', line)
            if m:
                kvs = {}
                for part in m.group(1).split(","):
                    part = part.strip()
                    if "=" in part:
                        k, v = part.split("=", 1)
                        kvs[k.strip()] = v.strip()
                self._line_pragmas[lineno] = kvs

        tree = ast.parse(text)

        # Detect style from imports
        style = self._detect_style(tree)

        # Collect all Protocol class names for member detection
        class_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and self._is_protocol(node):
                class_names.add(node.name)

        # Determine package prefix from file name if not set
        pkg = self.pkg_prefix
        if not pkg and path.is_file():
            pkg = path.stem

        interfaces: list[Interface] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and self._is_protocol(node):
                iface = self._parse_class(node, class_names, style, pkg)
                interfaces.append(iface)

        return MlHpiDoc(spec=MlHpiSpec(interfaces=interfaces))

    def _detect_style(self, tree: ast.Module) -> str:
        """Detect annotation style from imports."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "ctypes":
                        return "ctypes"
            if isinstance(node, ast.ImportFrom):
                if node.module == "typing":
                    for alias in node.names:
                        if alias.name == "Annotated":
                            return "annotated"
        return "plain"

    def _is_protocol(self, node: ast.ClassDef) -> bool:
        for base in node.bases:
            base_str = ast.unparse(base)
            if base_str in ("typing.Protocol", "Protocol"):
                return True
        return False

    def _parse_class(
        self, node: ast.ClassDef, class_names: set[str], style: str, pkg: str
    ) -> Interface:
        short_name = node.name
        qualified = f"{pkg}.{short_name}" if pkg else short_name

        # Determine extends
        extends = None
        for base in node.bases:
            base_str = ast.unparse(base)
            if base_str not in ("typing.Protocol", "Protocol"):
                if pkg:
                    extends = f"{pkg}.{base_str}"
                else:
                    extends = base_str

        raw_methods: list[dict] = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if item.name == "__init__":
                    continue
                blocking = isinstance(item, ast.AsyncFunctionDef)

                # Return type
                rtype = "void"
                if item.returns:
                    rtype = self._map_annotation(item.returns, style, class_names)

                # Parameters (skip self)
                params = []
                for arg in item.args.args[1:]:  # skip self
                    ptype = "int32"  # default for plain
                    if arg.annotation:
                        ptype = self._map_annotation(arg.annotation, style, class_names)
                    params.append({"name": arg.arg, "type": ptype})

                # Check for log_level pragma on this method's line
                log_level = None
                pragma_kvs = self._line_pragmas.get(item.lineno, {})
                if "log_level" in pragma_kvs:
                    log_level = pragma_kvs["log_level"]

                raw_methods.append({
                    "name": item.name,
                    "rtype": rtype,
                    "params": params,
                    "blocking": blocking,
                    "log_level": log_level,
                })

        remaining, members = infer_member_accessors(raw_methods, class_names)

        methods = []
        for m in remaining:
            attrs = [MethodAttr(blocking=m["blocking"])]
            if "log_level" in m:
                attrs.append(MethodAttr(log_level=m["log_level"]))
            methods.append(Method(
                name=m["name"],
                rtype=m["rtype"],
                params=[Param(**p) for p in m["params"]],
                attr=attrs,
            ))

        mem_objs = []
        for mem in members:
            mem_type = mem["type"]
            if "." not in mem_type and pkg:
                mem_type = f"{pkg}.{mem_type}"
            mem_objs.append(Member(
                name=mem["name"],
                kind=mem["kind"],
                type=mem_type,
            ))

        return Interface(
            name=qualified,
            extends=extends,
            methods=methods,
            members=mem_objs,
        )

    def _map_annotation(
        self, node: ast.expr, style: str, class_names: set[str]
    ) -> str:
        """Map a Python type annotation AST node to an ml-hpi type."""
        ann_str = ast.unparse(node)

        # None -> void
        if ann_str == "None":
            return "void"

        # Check if it's a known class name (interface type)
        if ann_str in class_names:
            return ann_str

        if style == "ctypes":
            if ann_str in PYTHON_CTYPES_TO_ML:
                return PYTHON_CTYPES_TO_ML[ann_str]

        if style == "annotated":
            if ann_str in _ANNOTATED_TO_ML:
                return _ANNOTATED_TO_ML[ann_str]

        if style == "plain":
            if ann_str == "bool":
                return "bool"
            if ann_str == "int":
                return "int32"

        # Fall through: return as-is
        return ann_str
