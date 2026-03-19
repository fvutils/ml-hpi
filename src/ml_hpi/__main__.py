"""CLI entry point for ml-hpi: ``python -m ml_hpi``.

Usage:
    ml-hpi <spec> generate bindings --outdir DIR --lang LANGS [options]
    ml-hpi <spec> generate shim    --outdir DIR --lang LANGS
    ml-hpi <spec> generate ids     --outdir DIR [--lang LANGS]
    ml-hpi <spec> inspect          [--interfaces] [--methods] [--types]
    ml-hpi parse --lang LANG --input FILE --output FILE
"""
from __future__ import annotations
import argparse
import sys
import yaml
from pathlib import Path

from ml_hpi.gen.gen_base import load_spec


def _build_parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(
        prog="ml-hpi",
        description="Multi-Language Hierarchical Programming Interface tool",
    )
    sub = top.add_subparsers(dest="command")

    # -- parse (no spec) --------------------------------------------------
    par = sub.add_parser("parse", help="Parse language source to IDL YAML")
    par.add_argument(
        "--lang", required=True,
        choices=["sv", "cpp", "python", "pss"],
        help="Source language",
    )
    par.add_argument("--input", required=True, help="Input source file")
    par.add_argument("--output", required=True, help="Output YAML file")
    par.add_argument("--addr-bits", type=int, default=64, choices=[32, 64])

    # -- spec-based commands (generate, inspect) --------------------------
    # These share a common positional <spec> argument via a parent parser.
    spec_parent = argparse.ArgumentParser(add_help=False)
    spec_parent.add_argument("spec", help="Path to YAML/JSON spec file")

    # inspect
    insp = sub.add_parser("inspect", parents=[spec_parent],
                          help="Inspect a spec file")
    insp.add_argument("--interfaces", action="store_true",
                      help="List interfaces")
    insp.add_argument("--methods", action="store_true",
                      help="List methods for each interface")
    insp.add_argument("--types", action="store_true",
                      help="List all scalar types used in the spec")

    # generate (with sub-subcommands)
    gen = sub.add_parser("generate", parents=[spec_parent],
                         help="Generate code from a spec")
    gen_sub = gen.add_subparsers(dest="gen_command")

    # generate bindings
    bind = gen_sub.add_parser("bindings", help="Generate language bindings")
    bind.add_argument("--outdir", required=True, help="Output directory")
    bind.add_argument(
        "--lang", required=True,
        help="Comma-separated: sv,cpp,python,pss,c",
    )
    bind.add_argument("--root-if", default=None,
                      help="Root interface (for C/SV DPI generators)")
    bind.add_argument("--addr-bits", type=int, default=64, choices=[32, 64])
    bind.add_argument("--python-style", default="plain",
                      choices=["plain", "annotated", "ctypes"])
    bind.add_argument("--cpp-async", action="store_true", default=True)
    bind.add_argument("--no-cpp-async", dest="cpp_async",
                      action="store_false")

    # generate shim
    shim = gen_sub.add_parser("shim",
                              help="Generate logging shim classes")
    shim.add_argument("--outdir", required=True, help="Output directory")
    shim.add_argument(
        "--lang", required=True,
        help="Comma-separated: cpp,python,sv",
    )
    shim.add_argument("--addr-bits", type=int, default=64, choices=[32, 64])

    # generate ids
    ids = gen_sub.add_parser("ids",
                             help="Generate monitor ID tables")
    ids.add_argument("--outdir", required=True, help="Output directory")
    ids.add_argument(
        "--lang", default="cpp,python,sv",
        help="Comma-separated: cpp,python,sv (default: all)",
    )

    return top


def cmd_generate_bindings(doc, args: argparse.Namespace) -> int:
    from ml_hpi.gen import GenPSS, GenSVInterface, GenPython, GenCpp, GenSV, GenC

    langs = [l.strip() for l in args.lang.split(",")]
    all_files: list[Path] = []

    for lang in langs:
        if lang == "pss":
            files = GenPSS(doc, addr_bits=args.addr_bits).generate(args.outdir)
        elif lang == "sv":
            if args.root_if:
                files = GenSV(doc, args.root_if,
                              addr_bits=args.addr_bits).generate(args.outdir)
            else:
                files = GenSVInterface(doc,
                                       addr_bits=args.addr_bits).generate(args.outdir)
        elif lang == "python":
            files = GenPython(doc, style=args.python_style,
                              addr_bits=args.addr_bits).generate(args.outdir)
        elif lang == "cpp":
            files = GenCpp(doc, addr_bits=args.addr_bits,
                           emit_async=args.cpp_async).generate(args.outdir)
        elif lang == "c":
            if not args.root_if:
                print("error: --root-if required for C generator",
                      file=sys.stderr)
                return 1
            files = GenC(doc, args.root_if,
                         addr_bits=args.addr_bits).generate(args.outdir)
        else:
            print(f"error: unknown language {lang!r}", file=sys.stderr)
            return 1
        all_files.extend(files)

    for f in all_files:
        print(f)
    return 0


def cmd_generate_shim(doc, args: argparse.Namespace) -> int:
    from ml_hpi.gen import GenShim

    langs = [l.strip() for l in args.lang.split(",")]
    all_files: list[Path] = []

    for lang in langs:
        if lang not in ("cpp", "python", "sv"):
            print(f"error: unknown shim language {lang!r}", file=sys.stderr)
            return 1
        files = GenShim(doc, lang=lang,
                        addr_bits=args.addr_bits).generate(args.outdir)
        all_files.extend(files)

    for f in all_files:
        print(f)
    return 0


def cmd_generate_ids(doc, args: argparse.Namespace) -> int:
    from ml_hpi.gen import GenMonitorIds

    langs = [l.strip() for l in args.lang.split(",")]
    all_files: list[Path] = []

    for lang in langs:
        if lang not in ("cpp", "python", "sv"):
            print(f"error: unknown ids language {lang!r}", file=sys.stderr)
            return 1
        files = GenMonitorIds(doc, lang=lang).generate(args.outdir)
        all_files.extend(files)

    for f in all_files:
        print(f)
    return 0


def cmd_inspect(doc, args: argparse.Namespace) -> int:
    show_all = not (args.interfaces or args.methods or args.types)

    if show_all or args.interfaces:
        print("Interfaces:")
        for iface in doc.spec.interfaces:
            ext = f" extends {iface.extends}" if iface.extends else ""
            ll = f" (log_level={iface.log_level})" if iface.log_level else ""
            print(f"  {iface.name}{ext}{ll}")
            if show_all or args.methods:
                for meth in iface.methods:
                    attrs = []
                    if meth.is_blocking():
                        attrs.append("blocking")
                    if meth.is_target():
                        attrs.append("target")
                    ml = meth.get_log_level()
                    if ml:
                        attrs.append(f"log_level={ml}")
                    attr_str = f" [{', '.join(attrs)}]" if attrs else ""
                    params = ", ".join(f"{p.name}: {p.type}" for p in meth.params)
                    print(f"    {meth.name}({params}) -> {meth.rtype}{attr_str}")
                for mem in iface.members:
                    print(f"    {mem.name}: {mem.kind} {mem.type}")

    if args.types:
        types_used: set[str] = set()
        for iface in doc.spec.interfaces:
            for meth in iface.methods:
                if meth.rtype != "void":
                    types_used.add(meth.rtype)
                for p in meth.params:
                    types_used.add(p.type)
        print("Types:")
        for t in sorted(types_used):
            print(f"  {t}")

    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    from ml_hpi.parse import ParseSV, ParsePython, ParseCpp, ParsePSS

    parsers = {
        "sv": ParseSV,
        "python": ParsePython,
        "cpp": ParseCpp,
        "pss": ParsePSS,
    }

    parser_cls = parsers[args.lang]
    parser = parser_cls()
    doc = parser.parse(args.input)

    out_data = {"ml-hpi": doc.spec.model_dump(exclude_none=True,
                                               exclude_defaults=True)}
    outpath = Path(args.output)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(yaml.dump(out_data, default_flow_style=False,
                                  sort_keys=False))
    print(f"Wrote {outpath}")
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "parse":
        return cmd_parse(args)

    if args.command in ("generate", "inspect"):
        doc = load_spec(args.spec)

        if args.command == "inspect":
            return cmd_inspect(doc, args)

        if args.command == "generate":
            if args.gen_command == "bindings":
                return cmd_generate_bindings(doc, args)
            elif args.gen_command == "shim":
                return cmd_generate_shim(doc, args)
            elif args.gen_command == "ids":
                return cmd_generate_ids(doc, args)
            else:
                print("error: specify a generate sub-command: "
                      "bindings, shim, or ids", file=sys.stderr)
                return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
