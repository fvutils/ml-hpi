"""Cross-language round-trip integration tests (Phase 4.1).

For each language, generates from the full_spec, parses back, and compares
against the original IDL -- excluding documented lossy fields.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from ml_hpi.gen.gen_base import load_spec
from ml_hpi.gen.gen_pss import GenPSS
from ml_hpi.gen.gen_sv_ifc import GenSVInterface
from ml_hpi.gen.gen_python import GenPython
from ml_hpi.gen.gen_cpp import GenCpp
from ml_hpi.parse.parse_pss import ParsePSS
from ml_hpi.parse.parse_sv import ParseSV
from ml_hpi.parse.parse_python import ParsePython
from ml_hpi.parse.parse_cpp import ParseCpp

DATA_DIR = Path(__file__).parent / "data"
SPEC = DATA_DIR / "full_spec.yaml"

# Known lossy fields per language
# addr types (addr/addr32/addr64) lose specificity in most languages
ADDR_TYPES = {"addr", "addr32", "addr64"}


def _types_match(orig_type: str, rec_type: str, lang: str) -> bool:
    """Check if types match allowing for known lossy mappings."""
    if orig_type == rec_type:
        return True
    # addr64 -> uint64 (SV, C++, Python ctypes)
    if orig_type in ADDR_TYPES and rec_type in ("uint32", "uint64", "addr"):
        return True
    return False


def _do_roundtrip(tmp_path, lang):
    original = load_spec(SPEC)

    if lang == "pss":
        gen = GenPSS(original)
        parser = ParsePSS()
        ext = "pss"
    elif lang == "sv":
        gen = GenSVInterface(original)
        parser = ParseSV()
        ext = "sv"
    elif lang == "python":
        gen = GenPython(original, style="annotated")
        parser = ParsePython()
        ext = "py"
    elif lang == "cpp":
        gen = GenCpp(original, emit_async=True)
        parser = ParseCpp()
        ext = "hpp"
    else:
        raise ValueError(f"Unknown lang: {lang}")

    files = gen.generate(tmp_path)
    recovered = parser.parse(files[0])
    return original, recovered


@pytest.mark.parametrize("lang", ["pss", "sv", "python", "cpp"])
def test_roundtrip_interface_count(lang, tmp_path):
    original, recovered = _do_roundtrip(tmp_path, lang)
    assert len(recovered.spec.interfaces) == len(original.spec.interfaces)


@pytest.mark.parametrize("lang", ["pss", "sv", "python", "cpp"])
def test_roundtrip_interface_names(lang, tmp_path):
    original, recovered = _do_roundtrip(tmp_path, lang)
    orig_names = {i.name for i in original.spec.interfaces}
    rec_names = {i.name for i in recovered.spec.interfaces}
    assert orig_names == rec_names


@pytest.mark.parametrize("lang", ["pss", "sv", "python", "cpp"])
def test_roundtrip_method_names(lang, tmp_path):
    original, recovered = _do_roundtrip(tmp_path, lang)
    for orig_if in original.spec.interfaces:
        if not orig_if.methods:
            continue
        rec_if = next(i for i in recovered.spec.interfaces if i.name == orig_if.name)
        orig_mnames = {m.name for m in orig_if.methods}
        rec_mnames = {m.name for m in rec_if.methods}
        assert orig_mnames == rec_mnames, f"{lang}: {orig_if.name} method names differ"


@pytest.mark.parametrize("lang", ["pss", "sv", "python", "cpp"])
def test_roundtrip_method_types(lang, tmp_path):
    original, recovered = _do_roundtrip(tmp_path, lang)
    for orig_if in original.spec.interfaces:
        rec_if = next(i for i in recovered.spec.interfaces if i.name == orig_if.name)
        for om in orig_if.methods:
            rm = next(m for m in rec_if.methods if m.name == om.name)
            assert _types_match(om.rtype, rm.rtype, lang), \
                f"{lang}: {orig_if.name}.{om.name} rtype: {om.rtype} -> {rm.rtype}"
            assert len(rm.params) == len(om.params), \
                f"{lang}: {orig_if.name}.{om.name} param count"
            for op, rp in zip(om.params, rm.params):
                assert _types_match(op.type, rp.type, lang), \
                    f"{lang}: {orig_if.name}.{om.name}.{op.name}: {op.type} -> {rp.type}"


@pytest.mark.parametrize("lang", ["pss", "sv", "python", "cpp"])
def test_roundtrip_members(lang, tmp_path):
    original, recovered = _do_roundtrip(tmp_path, lang)
    for orig_if in original.spec.interfaces:
        if not orig_if.members:
            continue
        rec_if = next(i for i in recovered.spec.interfaces if i.name == orig_if.name)
        assert len(rec_if.members) == len(orig_if.members), \
            f"{lang}: {orig_if.name} member count"
        rec_by_name = {m.name: m for m in rec_if.members}
        for om in orig_if.members:
            assert om.name in rec_by_name, f"{lang}: {orig_if.name}.{om.name} missing"
            rm = rec_by_name[om.name]
            assert rm.kind == om.kind
            assert rm.type == om.type


@pytest.mark.parametrize("lang", ["pss", "sv", "python", "cpp"])
def test_roundtrip_inheritance(lang, tmp_path):
    original, recovered = _do_roundtrip(tmp_path, lang)
    for orig_if in original.spec.interfaces:
        rec_if = next(i for i in recovered.spec.interfaces if i.name == orig_if.name)
        assert rec_if.extends == orig_if.extends, \
            f"{lang}: {orig_if.name} extends: {orig_if.extends} -> {rec_if.extends}"
