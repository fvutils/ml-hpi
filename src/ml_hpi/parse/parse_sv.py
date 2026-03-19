"""SystemVerilog parser for ml-hpi (SV interface class -> IDL)."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Union

import pyslang

from ml_hpi.model import (
    Interface, Method, MethodAttr, Param, Member, MlHpiDoc, MlHpiSpec,
)
from .parse_base import Parser, SV_TYPE_TO_ML, infer_member_accessors


class ParseSV(Parser):
    """Parse SystemVerilog ``interface class`` declarations into an
    ``MlHpiDoc``."""

    def parse(self, source: Union[str, Path]) -> MlHpiDoc:
        source = str(source) if isinstance(source, Path) else source
        path = Path(source)
        if path.is_file():
            text = path.read_text()
        else:
            text = source

        # Extract ml-hpi pragma comments from source text
        self._pragmas = self._extract_pragmas(text)

        tree = pyslang.SyntaxTree.fromText(text)
        comp = pyslang.Compilation()
        comp.addSyntaxTree(tree)
        root = comp.getRoot()

        # Collect all symbols via visit()
        symbols: list = []
        def visitor(sym):
            symbols.append(sym)
            return pyslang.VisitAction.Advance
        root.visit(visitor)

        # Build a map of class names to know which types are interfaces
        # (for member accessor detection)
        class_names: set[str] = set()
        pkg_for_class: dict[str, str] = {}
        current_pkg = ""

        for sym in symbols:
            kind = str(sym.kind)
            if kind == "SymbolKind.Package":
                current_pkg = sym.name
            elif kind == "SymbolKind.ClassType":
                if sym.isInterface:
                    class_names.add(sym.name)
                    pkg_for_class[sym.name] = current_pkg

        # Second pass: extract interfaces
        interfaces: list[Interface] = []
        current_pkg = ""
        current_class = None

        for sym in symbols:
            kind = str(sym.kind)

            if kind == "SymbolKind.Package":
                current_pkg = sym.name

            elif kind == "SymbolKind.ClassType":
                if not sym.isInterface:
                    continue

                # Finish previous class
                if current_class is not None:
                    interfaces.append(self._finalize_interface(current_class, class_names, current_pkg))

                # Determine extends from implementedInterfaces
                extends = None
                impl_ifaces = sym.implementedInterfaces
                if impl_ifaces:
                    base_name = impl_ifaces[0].name
                    base_pkg = pkg_for_class.get(base_name, current_pkg)
                    if base_pkg:
                        extends = f"{base_pkg}.{base_name}"
                    else:
                        extends = base_name

                qualified = f"{current_pkg}.{sym.name}" if current_pkg else sym.name
                current_class = {
                    "name": qualified,
                    "extends": extends,
                    "raw_methods": [],
                    "pkg": current_pkg,
                }

            elif kind == "SymbolKind.MethodPrototype":
                if current_class is None:
                    continue
                # Skip built-in methods (randomize, etc.)
                flags_str = str(getattr(sym, "flags", ""))
                if "Pure" not in flags_str:
                    continue

                is_task = str(sym.subroutineKind) == "SubroutineKind.Task"
                blocking = is_task

                rtype_str = str(sym.returnType)
                rtype_ml = self._map_sv_type(sym.returnType)

                # For tasks, check if first argument is output (return value)
                args = list(sym.arguments)
                actual_rtype = "void"
                actual_params = []

                if is_task and args:
                    first = args[0]
                    if str(first.direction) == "ArgumentDirection.Out":
                        actual_rtype = self._map_sv_type(first.type)
                        args = args[1:]
                    # Remaining args are inputs
                    for a in args:
                        actual_params.append({
                            "name": a.name,
                            "type": self._map_sv_type(a.type),
                        })
                else:
                    actual_rtype = rtype_ml
                    for a in args:
                        actual_params.append({
                            "name": a.name,
                            "type": self._map_sv_type(a.type),
                        })

                current_class["raw_methods"].append({
                    "name": sym.name,
                    "rtype": actual_rtype,
                    "params": actual_params,
                    "blocking": blocking,
                })

        # Finalize last class
        if current_class is not None:
            interfaces.append(self._finalize_interface(current_class, class_names, current_pkg))

        return MlHpiDoc(spec=MlHpiSpec(interfaces=interfaces))

    def _finalize_interface(
        self, cls_data: dict, class_names: set[str], pkg: str
    ) -> Interface:
        """Convert raw method list into methods + inferred members."""
        # Build qualified interface names for member detection
        qualified_names = set()
        for cn in class_names:
            qualified_names.add(cn)  # short names used in SV return types

        remaining, members = infer_member_accessors(
            cls_data["raw_methods"], qualified_names
        )

        methods = []
        for m in remaining:
            attrs = []
            if m.get("blocking"):
                attrs.append(MethodAttr(blocking=True))
            else:
                attrs.append(MethodAttr(blocking=False))
            # Apply log_level from pragma comments
            pragma_kvs = self._pragmas.get(m["name"], {})
            if "log_level" in pragma_kvs:
                attrs.append(MethodAttr(log_level=pragma_kvs["log_level"]))
            methods.append(Method(
                name=m["name"],
                rtype=m["rtype"],
                params=[Param(**p) for p in m["params"]],
                attr=attrs,
            ))

        mem_objs = []
        for mem in members:
            mem_type = mem["type"]
            # Qualify member type with package if not already qualified
            if "." not in mem_type and pkg:
                mem_type = f"{pkg}.{mem_type}"
            mem_objs.append(Member(
                name=mem["name"],
                kind=mem["kind"],
                type=mem_type,
            ))

        return Interface(
            name=cls_data["name"],
            extends=cls_data["extends"],
            methods=methods,
            members=mem_objs,
        )

    def _extract_pragmas(self, text: str) -> dict[str, dict[str, str]]:
        """Extract // ml-hpi: key=value pragmas, keyed by preceding method name."""
        pragmas: dict[str, dict[str, str]] = {}
        lines = text.splitlines()
        for i, line in enumerate(lines):
            m = re.search(r'//\s*ml-hpi:\s*(.+)', line)
            if not m:
                continue
            kvs = {}
            for part in m.group(1).split(","):
                part = part.strip()
                if "=" in part:
                    k, v = part.split("=", 1)
                    kvs[k.strip()] = v.strip()
            # Associate with the method on this line or preceding lines
            # Look for a method name pattern on the same line
            mname_match = re.search(r'(?:function|task)\s+(?:\S+\s+)?(\w+)\s*\(', line)
            if mname_match:
                pragmas[mname_match.group(1)] = kvs
            else:
                # Check previous lines for the method
                for j in range(i - 1, max(i - 3, -1), -1):
                    mname_match = re.search(r'(?:function|task)\s+(?:\S+\s+)?(\w+)\s*\(', lines[j])
                    if mname_match:
                        pragmas[mname_match.group(1)] = kvs
                        break
        return pragmas

    def _map_sv_type(self, sv_type) -> str:
        """Map a pyslang type object to an ml-hpi type string."""
        type_str = str(sv_type)

        # Check if it's a class/interface type
        if sv_type.isClass:
            return sv_type.name

        # Check chandle
        if sv_type.isCHandle:
            return "uintptr"

        # Use the string representation for lookup
        if type_str in SV_TYPE_TO_ML:
            return SV_TYPE_TO_ML[type_str]

        # Void
        if sv_type.isVoid:
            return "void"

        return type_str
