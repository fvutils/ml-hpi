"""Unit tests for Python generator (Phase 1.3)."""
import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from ml_hpi.gen.gen_base import load_spec
from ml_hpi.gen.gen_python import GenPython

DATA_DIR = Path(__file__).parent / "data"
SPEC = DATA_DIR / "full_spec.yaml"


@pytest.fixture(params=["plain", "annotated", "ctypes"])
def generated(request, tmp_path):
    style = request.param
    doc = load_spec(SPEC)
    files = GenPython(doc, style=style).generate(tmp_path)
    assert files
    text = files[0].read_text()
    return text, files, style


def test_syntax_valid(generated):
    text, _, style = generated
    ast.parse(text)


def test_protocol_class(generated):
    text, _, _ = generated
    assert "class RegIf(typing.Protocol):" in text


def test_blocking_async(generated):
    text, _, _ = generated
    assert "async def write32(" in text
    assert "async def read32(" in text


def test_nonblocking_sync(generated):
    text, _, _ = generated
    assert "    def reset(self)" in text
    assert "async def reset" not in text


def test_member_field(generated):
    text, _, _ = generated
    assert "def regs(self) -> RegIf:" in text


def test_member_array(generated):
    text, _, _ = generated
    assert "def ports_at(self, idx: int) -> RegIf:" in text
    assert "def ports_size(self) -> int:" in text


def test_inheritance(generated):
    text, _, _ = generated
    assert "class ExtRegIf(RegIf, typing.Protocol):" in text


class TestPlainStyle:
    def test_plain_types(self, tmp_path):
        doc = load_spec(SPEC)
        text = GenPython(doc, style="plain").generate(tmp_path)[0].read_text()
        # Plain style uses bare int/bool/None
        assert "addr: int" in text
        assert "data: int" in text


class TestAnnotatedStyle:
    def test_annotated_aliases(self, tmp_path):
        doc = load_spec(SPEC)
        text = GenPython(doc, style="annotated").generate(tmp_path)[0].read_text()
        assert "from typing import Annotated" in text
        assert "Addr64 = Annotated[int" in text
        assert "addr: Addr64" in text
        assert "data: UInt32" in text


class TestCtypesStyle:
    def test_ctypes_types(self, tmp_path):
        doc = load_spec(SPEC)
        text = GenPython(doc, style="ctypes").generate(tmp_path)[0].read_text()
        assert "import ctypes" in text
        assert "ctypes.c_uint64" in text
        assert "ctypes.c_uint32" in text
