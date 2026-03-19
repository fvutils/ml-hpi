"""Unit tests for SV interface class generator (Phase 1.2)."""
import sys
from pathlib import Path

import pyslang
import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from ml_hpi.gen.gen_base import load_spec
from ml_hpi.gen.gen_sv_ifc import GenSVInterface

DATA_DIR = Path(__file__).parent / "data"
SPEC = DATA_DIR / "full_spec.yaml"


@pytest.fixture
def generated(tmp_path):
    doc = load_spec(SPEC)
    files = GenSVInterface(doc).generate(tmp_path)
    assert files
    text = files[0].read_text()
    return text, files


def test_basic(generated):
    text, files = generated
    assert files[0].exists()
    assert len(text) > 0


def test_interface_class(generated):
    text, _ = generated
    assert "interface class RegIf;" in text


def test_blocking_void_task(generated):
    text, _ = generated
    # write32 is blocking + void return -> task with params only
    assert "pure virtual task write32(" in text


def test_blocking_nonvoid_task(generated):
    text, _ = generated
    assert "pure virtual task read32(output int unsigned rval, input longint unsigned addr)" in text


def test_nonblocking_function(generated):
    text, _ = generated
    assert "pure virtual function void reset();" in text


def test_member_field(generated):
    text, _ = generated
    assert "pure virtual function RegIf regs();" in text


def test_member_array(generated):
    text, _ = generated
    assert "pure virtual function RegIf ports_at(int idx);" in text
    assert "pure virtual function int ports_size();" in text


def test_inheritance(generated):
    text, _ = generated
    assert "interface class ExtRegIf extends RegIf;" in text


def test_type_mapping(generated):
    text, _ = generated
    assert "longint unsigned" in text  # addr64
    assert "int unsigned" in text      # uint32


def test_pyslang_compile(generated):
    """Generated SV compiles cleanly with pyslang."""
    text, _ = generated
    tree = pyslang.SyntaxTree.fromText(text)
    comp = pyslang.Compilation()
    comp.addSyntaxTree(tree)
    diags = comp.getAllDiagnostics()
    assert not diags, f"pyslang diagnostics: {diags}"
