"""C++ parser for ml-hpi (abstract class headers -> IDL)."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Union

import cxxheaderparser.simple as cxxsimple
from cxxheaderparser.types import (
    FundamentalSpecifier, NameSpecifier, Pointer, TemplateSpecialization,
    FunctionType,
)

from ml_hpi.model import (
    Interface, Method, MethodAttr, Param, Member, MlHpiDoc, MlHpiSpec,
)
from .parse_base import Parser, CPP_TYPE_TO_ML, infer_member_accessors


class ParseCpp(Parser):
    """Parse C++ abstract class headers into an ``MlHpiDoc``."""

    def parse(self, source: Union[str, Path]) -> MlHpiDoc:
        source_str = str(source) if isinstance(source, Path) else source
        path = Path(source_str)
        if path.is_file():
            text = path.read_text()
        else:
            text = source_str

        self._pragmas = self._extract_pragmas(text)
        parsed = cxxsimple.parse_string(text)

        interfaces: list[Interface] = []
        for ns_name, ns_scope in parsed.namespace.namespaces.items():
            # Collect class names in this namespace for member detection
            class_names: set[str] = set()
            for cls in ns_scope.classes:
                class_names.add(cls.class_decl.typename.segments[-1].name)

            for cls in ns_scope.classes:
                iface = self._parse_class(cls, ns_name, class_names)
                interfaces.append(iface)

        return MlHpiDoc(spec=MlHpiSpec(interfaces=interfaces))

    def _parse_class(self, cls, ns_name: str, class_names: set[str]) -> Interface:
        short_name = cls.class_decl.typename.segments[-1].name
        qualified = f"{ns_name}.{short_name}" if ns_name else short_name

        # Determine extends from base classes
        extends = None
        for base in cls.class_decl.bases:
            base_name = base.typename.segments[-1].name
            if base_name not in ("", short_name):
                extends = f"{ns_name}.{base_name}" if ns_name else base_name
                break

        # Parse methods, separating sync and async overloads
        sync_methods: dict[str, dict] = {}
        async_methods: set[str] = set()
        raw_methods: list[dict] = []

        for m in cls.methods:
            if not m.pure_virtual:
                continue
            mname = m.name.segments[-1].name
            if mname.startswith("~"):
                continue

            rtype = self._extract_type(m.return_type, class_names)
            params = []
            is_async = False

            for p in m.parameters:
                ptype = self._extract_type(p.type, class_names)
                pname = p.name or f"arg{len(params)}"

                # Detect std::function callback parameter (async overload)
                if self._is_std_function(p.type):
                    is_async = True
                    continue

                params.append({"name": pname, "type": ptype})

            if is_async:
                async_methods.add(mname)
            else:
                entry = {
                    "name": mname,
                    "rtype": rtype,
                    "params": params,
                }
                sync_methods[mname] = entry
                raw_methods.append(entry)

        # Mark blocking: a method is blocking if it has both sync and async overloads
        for m in raw_methods:
            m["blocking"] = m["name"] in async_methods

        remaining, members = infer_member_accessors(raw_methods, class_names)

        methods = []
        for m in remaining:
            attrs = [MethodAttr(blocking=m.get("blocking", False))]
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
            if "." not in mem_type and ns_name:
                mem_type = f"{ns_name}.{mem_type}"
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

    def _extract_pragmas(self, text: str) -> dict[str, dict[str, str]]:
        """Extract // ml-hpi: key=value pragmas, keyed by method name on same line."""
        pragmas: dict[str, dict[str, str]] = {}
        for line in text.splitlines():
            m = re.search(r'//\s*ml-hpi:\s*(.+)', line)
            if not m:
                continue
            kvs = {}
            for part in m.group(1).split(","):
                part = part.strip()
                if "=" in part:
                    k, v = part.split("=", 1)
                    kvs[k.strip()] = v.strip()
            # Find method name on the same line
            mname_match = re.search(r'virtual\s+\S+\s+(\w+)\s*\(', line)
            if mname_match:
                name = mname_match.group(1)
                if name not in pragmas:
                    pragmas[name] = {}
                pragmas[name].update(kvs)
        return pragmas

    def _extract_type(self, type_obj, class_names: set[str]) -> str:
        """Extract the ml-hpi type string from a cxxheaderparser type object."""
        # Handle Pointer types (member accessors return Type*)
        if isinstance(type_obj, Pointer):
            inner = self._extract_type(type_obj.ptr_to, class_names)
            return inner

        # Get the type name from segments
        if hasattr(type_obj, "typename") and type_obj.typename:
            segments = type_obj.typename.segments
            if segments:
                last = segments[-1]
                if isinstance(last, FundamentalSpecifier):
                    name = last.name
                elif isinstance(last, NameSpecifier):
                    name = last.name
                else:
                    name = str(last)

                # Check if it's a class name
                if name in class_names:
                    return name

                # Map C++ type to ml-hpi
                if name in CPP_TYPE_TO_ML:
                    return CPP_TYPE_TO_ML[name]

                return name

        return "void"

    def _is_std_function(self, type_obj) -> bool:
        """Check if a parameter type is std::function<...>."""
        if not hasattr(type_obj, "typename") or not type_obj.typename:
            return False
        segments = type_obj.typename.segments
        if len(segments) >= 2:
            if (isinstance(segments[0], NameSpecifier) and segments[0].name == "std"
                    and isinstance(segments[1], NameSpecifier) and segments[1].name == "function"):
                return True
        return False
