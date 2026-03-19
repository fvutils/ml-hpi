"""Unit tests for Python parser (Phase 2.3)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from ml_hpi.gen.gen_base import load_spec
from ml_hpi.gen.gen_python import GenPython
from ml_hpi.parse.parse_python import ParsePython

DATA_DIR = Path(__file__).parent / "data"
SPEC = DATA_DIR / "full_spec.yaml"


def _roundtrip(tmp_path, style):
    doc = load_spec(SPEC)
    files = GenPython(doc, style=style).generate(tmp_path)
    parser = ParsePython()
    recovered = parser.parse(files[0])
    return doc, recovered


def test_parse_plain(tmp_path):
    _, recovered = _roundtrip(tmp_path, "plain")
    assert len(recovered.spec.interfaces) == 3


def test_parse_annotated(tmp_path):
    _, recovered = _roundtrip(tmp_path, "annotated")
    assert len(recovered.spec.interfaces) == 3


def test_parse_ctypes(tmp_path):
    _, recovered = _roundtrip(tmp_path, "ctypes")
    assert len(recovered.spec.interfaces) == 3


def test_roundtrip_methods(tmp_path):
    """Annotated style gives unambiguous types for full round-trip."""
    original, recovered = _roundtrip(tmp_path, "annotated")
    orig_reg = next(i for i in original.spec.interfaces if i.short_name() == "RegIf")
    rec_reg = next(i for i in recovered.spec.interfaces if i.short_name() == "RegIf")

    orig_names = {m.name for m in orig_reg.methods}
    rec_names = {m.name for m in rec_reg.methods}
    assert orig_names == rec_names

    for om in orig_reg.methods:
        rm = next(m for m in rec_reg.methods if m.name == om.name)
        assert rm.rtype == om.rtype, f"{om.name} rtype mismatch: {rm.rtype} != {om.rtype}"
        assert len(rm.params) == len(om.params)
        for op, rp in zip(om.params, rm.params):
            assert rp.type == op.type, f"{om.name}.{op.name} type mismatch: {rp.type} != {op.type}"


def test_roundtrip_blocking(tmp_path):
    _, recovered = _roundtrip(tmp_path, "annotated")
    rec_reg = next(i for i in recovered.spec.interfaces if i.short_name() == "RegIf")

    write32 = next(m for m in rec_reg.methods if m.name == "write32")
    reset = next(m for m in rec_reg.methods if m.name == "reset")

    assert write32.is_blocking()
    assert not reset.is_blocking()


def test_roundtrip_members(tmp_path):
    _, recovered = _roundtrip(tmp_path, "annotated")
    bus = next(i for i in recovered.spec.interfaces if i.short_name() == "BusIf")

    mem_names = {m.name: m for m in bus.members}
    assert "regs" in mem_names
    assert mem_names["regs"].kind == "field"
    assert "ports" in mem_names
    assert mem_names["ports"].kind == "array"


def test_roundtrip_inheritance(tmp_path):
    _, recovered = _roundtrip(tmp_path, "annotated")
    ext = next(i for i in recovered.spec.interfaces if i.short_name() == "ExtRegIf")
    assert ext.extends == "pkg.RegIf"
