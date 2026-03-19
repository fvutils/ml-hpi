"""Unit tests for PSS generator (Phase 1.1)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from ml_hpi.gen.gen_base import load_spec
from ml_hpi.gen.gen_pss import GenPSS

DATA_DIR = Path(__file__).parent / "data"
SPEC = DATA_DIR / "full_spec.yaml"


@pytest.fixture
def generated(tmp_path):
    doc = load_spec(SPEC)
    files = GenPSS(doc).generate(tmp_path)
    assert files
    text = files[0].read_text()
    return text, files


def test_basic(generated):
    text, files = generated
    assert files[0].exists()
    assert len(text) > 0


def test_component_declaration(generated):
    text, _ = generated
    assert "component RegIf {" in text


def test_target_function(generated):
    text, _ = generated
    assert "target function void write32(addr_t addr, bit<32> data);" in text


def test_non_target_reset(generated):
    """reset has target: true, so it should still be 'target function'."""
    text, _ = generated
    assert "target function void reset();" in text


def test_type_mapping(generated):
    text, _ = generated
    assert "addr_t" in text
    assert "bit<32>" in text


def test_member_field(generated):
    text, _ = generated
    assert "RegIf regs;" in text


def test_member_array(generated):
    text, _ = generated
    assert "array<RegIf, *> ports;" in text


def test_inheritance(generated):
    text, _ = generated
    assert "component ExtRegIf : RegIf {" in text


def test_blocking_comment(generated):
    text, _ = generated
    assert "// ml-hpi: blocking=true" in text
    assert "// ml-hpi: blocking=false" in text
