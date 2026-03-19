"""Unit tests for SV parser (Phase 2.2)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from ml_hpi.gen.gen_base import load_spec
from ml_hpi.gen.gen_sv_ifc import GenSVInterface
from ml_hpi.parse.parse_sv import ParseSV

DATA_DIR = Path(__file__).parent / "data"
SPEC = DATA_DIR / "full_spec.yaml"


@pytest.fixture
def roundtrip(tmp_path):
    doc = load_spec(SPEC)
    files = GenSVInterface(doc).generate(tmp_path)
    parser = ParseSV()
    recovered = parser.parse(files[0])
    return doc, recovered


def test_parse_generated(roundtrip):
    _, recovered = roundtrip
    assert len(recovered.spec.interfaces) == 3


def test_roundtrip_methods(roundtrip):
    original, recovered = roundtrip
    orig_reg = next(i for i in original.spec.interfaces if i.short_name() == "RegIf")
    rec_reg = next(i for i in recovered.spec.interfaces if i.short_name() == "RegIf")

    orig_names = {m.name for m in orig_reg.methods}
    rec_names = {m.name for m in rec_reg.methods}
    assert orig_names == rec_names

    for om in orig_reg.methods:
        rm = next(m for m in rec_reg.methods if m.name == om.name)
        # Return type (addr64 -> uint64 is expected lossy)
        if om.rtype in ("addr", "addr32", "addr64"):
            pass  # lossy
        else:
            assert rm.rtype == om.rtype, f"{om.name} rtype mismatch"
        # Param count
        assert len(rm.params) == len(om.params), f"{om.name} param count mismatch"


def test_roundtrip_blocking(roundtrip):
    _, recovered = roundtrip
    rec_reg = next(i for i in recovered.spec.interfaces if i.short_name() == "RegIf")

    write32 = next(m for m in rec_reg.methods if m.name == "write32")
    read32 = next(m for m in rec_reg.methods if m.name == "read32")
    reset = next(m for m in rec_reg.methods if m.name == "reset")

    assert write32.is_blocking()
    assert read32.is_blocking()
    assert not reset.is_blocking()


def test_roundtrip_members(roundtrip):
    _, recovered = roundtrip
    bus = next(i for i in recovered.spec.interfaces if i.short_name() == "BusIf")

    mem_names = {m.name: m for m in bus.members}
    assert "regs" in mem_names
    assert mem_names["regs"].kind == "field"
    assert "ports" in mem_names
    assert mem_names["ports"].kind == "array"


def test_roundtrip_inheritance(roundtrip):
    _, recovered = roundtrip
    ext = next(i for i in recovered.spec.interfaces if i.short_name() == "ExtRegIf")
    assert ext.extends == "pkg.RegIf"


def test_type_mapping(roundtrip):
    _, recovered = roundtrip
    rec_reg = next(i for i in recovered.spec.interfaces if i.short_name() == "RegIf")
    read32 = next(m for m in rec_reg.methods if m.name == "read32")
    assert read32.rtype == "uint32"
