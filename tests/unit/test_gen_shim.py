"""Unit tests for shim generator (Phases 3-5)."""
import ast
import sys
from pathlib import Path

import cxxheaderparser.simple
import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from ml_hpi.gen.gen_base import load_spec
from ml_hpi.gen.gen_shim import GenShim

DATA_DIR = Path(__file__).parent / "data"
SPEC = DATA_DIR / "full_spec_logging.yaml"


# ---- C++ tests ----

class TestCpp:
    @pytest.fixture
    def generated(self, tmp_path):
        doc = load_spec(SPEC)
        files = GenShim(doc, lang="cpp").generate(tmp_path)
        text = files[0].read_text()
        return text

    def test_cpp_basic(self, generated):
        assert len(generated) > 0

    def test_cpp_args_struct(self, generated):
        assert "struct RegIf_write32_args" in generated
        assert "uint64_t addr;" in generated
        assert "uint32_t data;" in generated

    def test_cpp_result_struct(self, generated):
        assert "struct RegIf_read32_result" in generated
        assert "rval;" in generated

    def test_cpp_no_result_void(self, generated):
        assert "RegIf_write32_result" not in generated

    def test_cpp_logger_interface(self, generated):
        assert "class RegIfLogger" in generated
        assert "on_enter" in generated
        assert "on_leave" in generated

    def test_cpp_shim_class(self, generated):
        assert "class RegIfLoggingShim" in generated

    def test_cpp_shim_delegates(self, generated):
        assert "inner_->write32" in generated

    def test_cpp_shim_threshold_check(self, generated):
        assert "threshold_" in generated

    def test_cpp_shim_result_capture(self, generated):
        # read32 should capture return value
        assert "RegIf_read32_result" in generated
        assert "ctx.result = &res;" in generated

    def test_cpp_member_passthrough(self, generated):
        assert "inner_->regs()" in generated
        assert "inner_->ports_at(idx)" in generated

    def test_cpp_cxxheaderparser(self, generated):
        cxxheaderparser.simple.parse_string(generated)

    def test_cpp_log_level_values(self, generated):
        # write32 has log_level=debug (4), reset has log_level=info (3)
        assert "if (logger_ && 4" in generated  # debug
        assert "if (logger_ && 3" in generated  # info


# ---- Python tests ----

class TestPython:
    @pytest.fixture
    def generated(self, tmp_path):
        doc = load_spec(SPEC)
        files = GenShim(doc, lang="python").generate(tmp_path)
        text = files[0].read_text()
        return text

    def test_python_basic(self, generated):
        assert len(generated) > 0

    def test_python_args_dataclass(self, generated):
        assert "class RegIf_write32_args:" in generated
        assert "@dataclasses.dataclass" in generated

    def test_python_result_dataclass(self, generated):
        assert "class RegIf_read32_result:" in generated

    def test_python_logger_protocol(self, generated):
        assert "class RegIfLogger" in generated
        assert "on_enter" in generated
        assert "on_leave" in generated

    def test_python_shim_async(self, generated):
        assert "async def write32" in generated

    def test_python_shim_result_capture(self, generated):
        assert "RegIf_read32_result(rval=result)" in generated

    def test_python_ast_parse(self, generated):
        ast.parse(generated)


# ---- SV tests ----

class TestSV:
    @pytest.fixture
    def generated(self, tmp_path):
        doc = load_spec(SPEC)
        files = GenShim(doc, lang="sv").generate(tmp_path)
        text = files[0].read_text()
        return text

    def test_sv_basic(self, generated):
        assert len(generated) > 0

    def test_sv_args_class(self, generated):
        assert "class RegIf_write32_args;" in generated

    def test_sv_logger_interface(self, generated):
        assert "interface class RegIfLogger;" in generated

    def test_sv_shim_task(self, generated):
        assert "virtual task write32" in generated

    def test_sv_shim_result_capture(self, generated):
        assert "RegIf_read32_result" in generated

    def test_sv_shim_class(self, generated):
        assert "class RegIfLoggingShim;" in generated
