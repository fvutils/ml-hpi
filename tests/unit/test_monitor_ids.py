"""Unit tests for monitor ID table generator (Phase 2)."""
import ast
import sys
from pathlib import Path

import cxxheaderparser.simple
import pyslang
import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from ml_hpi.gen.gen_base import load_spec
from ml_hpi.gen.gen_monitor_ids import GenMonitorIds

DATA_DIR = Path(__file__).parent / "data"
SPEC = DATA_DIR / "full_spec.yaml"


def test_cpp_ids(tmp_path):
    doc = load_spec(SPEC)
    files = GenMonitorIds(doc, lang="cpp").generate(tmp_path)
    text = files[0].read_text()
    cxxheaderparser.simple.parse_string(text)
    assert "constexpr uint32_t RegIf = 0;" in text
    assert "constexpr uint32_t BusIf = 1;" in text
    assert "constexpr uint32_t ExtRegIf = 2;" in text


def test_python_ids(tmp_path):
    doc = load_spec(SPEC)
    files = GenMonitorIds(doc, lang="python").generate(tmp_path)
    text = files[0].read_text()
    ast.parse(text)
    ns = {}
    exec(text, ns)
    assert ns["REGIF"] == 0
    assert ns["BUSIF"] == 1
    assert ns["EXTREGIF"] == 2
    assert ns["IFACE_NAMES"][0] == "RegIf"
    assert ns["METHOD_NAMES"][(0, 0)] == "write32"


def test_sv_ids(tmp_path):
    doc = load_spec(SPEC)
    files = GenMonitorIds(doc, lang="sv").generate(tmp_path)
    text = files[0].read_text()
    tree = pyslang.SyntaxTree.fromText(text)
    comp = pyslang.Compilation()
    comp.addSyntaxTree(tree)
    diags = comp.getAllDiagnostics()
    assert not diags, f"pyslang diagnostics: {diags}"


def test_deterministic(tmp_path):
    doc = load_spec(SPEC)
    t1 = tmp_path / "run1"
    t2 = tmp_path / "run2"
    text1 = GenMonitorIds(doc, lang="cpp").generate(t1)[0].read_text()
    text2 = GenMonitorIds(doc, lang="cpp").generate(t2)[0].read_text()
    assert text1 == text2


def test_id_values(tmp_path):
    doc = load_spec(SPEC)
    files = GenMonitorIds(doc, lang="python").generate(tmp_path)
    ns = {}
    exec(files[0].read_text(), ns)
    assert ns["REGIF_WRITE32"] == 0
    assert ns["REGIF_READ32"] == 1
    assert ns["REGIF_RESET"] == 2
    assert ns["EXTREGIF_CONFIGURE"] == 0
