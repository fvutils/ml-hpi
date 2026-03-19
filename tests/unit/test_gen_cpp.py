"""Unit tests for C++ generator (Phase 1.4)."""
import sys
from pathlib import Path

import cxxheaderparser.simple
import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from ml_hpi.gen.gen_base import load_spec
from ml_hpi.gen.gen_cpp import GenCpp

DATA_DIR = Path(__file__).parent / "data"
SPEC = DATA_DIR / "full_spec.yaml"


@pytest.fixture
def generated(tmp_path):
    doc = load_spec(SPEC)
    files = GenCpp(doc).generate(tmp_path)
    assert files
    text = files[0].read_text()
    return text, files


@pytest.fixture
def generated_no_async(tmp_path):
    doc = load_spec(SPEC)
    files = GenCpp(doc, emit_async=False).generate(tmp_path)
    text = files[0].read_text()
    return text, files


def test_basic(generated):
    text, files = generated
    assert files[0].exists()
    assert files[0].suffix == ".hpp"


def test_pragma_once(generated):
    text, _ = generated
    assert "#pragma once" in text


def test_namespace(generated):
    text, _ = generated
    assert "namespace pkg {" in text


def test_abstract_class(generated):
    text, _ = generated
    assert "class RegIf {" in text
    assert "virtual ~RegIf() = default;" in text


def test_pure_virtual_method(generated):
    text, _ = generated
    assert "virtual void write32(uint64_t addr, uint32_t data) = 0;" in text


def test_async_overload(generated):
    text, _ = generated
    assert "virtual void write32(uint64_t addr, uint32_t data, std::function<void()> cb) = 0;" in text
    assert "virtual void read32(uint64_t addr, std::function<void(uint32_t)> cb) = 0;" in text


def test_no_async(generated_no_async):
    text, _ = generated_no_async
    assert "std::function" not in text
    assert "#include <functional>" not in text


def test_return_type(generated):
    text, _ = generated
    assert "virtual uint32_t read32(uint64_t addr) = 0;" in text


def test_member_field(generated):
    text, _ = generated
    assert "virtual RegIf *regs() = 0;" in text


def test_member_array(generated):
    text, _ = generated
    assert "virtual RegIf *ports_at(int idx) = 0;" in text
    assert "virtual int ports_size() = 0;" in text


def test_inheritance(generated):
    text, _ = generated
    assert "class ExtRegIf : public virtual RegIf {" in text


def test_cxxheaderparser_parse(generated):
    """Generated C++ parses cleanly with cxxheaderparser."""
    text, _ = generated
    parsed = cxxheaderparser.simple.parse_string(text)
    assert len(parsed.namespace.namespaces) == 1
    ns = list(parsed.namespace.namespaces.values())[0]
    class_names = [
        cls.class_decl.typename.segments[-1].name for cls in ns.classes
    ]
    assert "RegIf" in class_names
    assert "BusIf" in class_names
    assert "ExtRegIf" in class_names
