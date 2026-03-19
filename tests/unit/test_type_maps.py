"""Unit tests for type mapping methods (Phase 0.2)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from ml_hpi.gen.gen_base import Generator
from ml_hpi.parse.parse_base import (
    SV_TYPE_TO_ML, CPP_TYPE_TO_ML, PSS_TYPE_TO_ML,
    PYTHON_CTYPES_TO_ML, pss_scalar_to_ml,
)

# All ml-hpi scalar types
ALL_TYPES = [
    "void", "bool",
    "int8", "uint8", "int16", "uint16",
    "int32", "uint32", "int64", "uint64",
    "addr", "addr32", "addr64", "uintptr",
]


class TestForwardMaps:
    """Generator forward type maps cover all ml-hpi types."""

    def test_sv_type_covers_all(self):
        for t in ALL_TYPES:
            result = Generator.sv_type(t)
            assert result is not None, f"sv_type({t!r}) unmapped"

    def test_c_type_covers_all(self):
        for t in ALL_TYPES:
            result = Generator.c_type(t)
            assert result is not None, f"c_type({t!r}) unmapped"

    def test_cpp_type_covers_all(self):
        for t in ALL_TYPES:
            result = Generator.cpp_type(t)
            assert result is not None, f"cpp_type({t!r}) unmapped"

    def test_pss_type_covers_all(self):
        for t in ALL_TYPES:
            result = Generator.pss_type(t)
            assert result is not None, f"pss_type({t!r}) unmapped"

    def test_python_type_plain_covers_all(self):
        for t in ALL_TYPES:
            result = Generator.python_type(t, "plain")
            assert result is not None, f"python_type({t!r}, 'plain') unmapped"

    def test_python_type_annotated_covers_all(self):
        for t in ALL_TYPES:
            result = Generator.python_type(t, "annotated")
            assert result is not None, f"python_type({t!r}, 'annotated') unmapped"

    def test_python_type_ctypes_covers_all(self):
        for t in ALL_TYPES:
            result = Generator.python_type(t, "ctypes")
            assert result is not None, f"python_type({t!r}, 'ctypes') unmapped"

    def test_addr_bits_32(self):
        assert Generator.sv_type("addr", 32) == "int unsigned"
        assert Generator.c_type("addr", 32) == "uint32_t"
        assert Generator.pss_type("addr", 32) == "addr_t"
        assert Generator.python_type("addr", "ctypes", 32) == "ctypes.c_uint32"

    def test_addr_bits_64(self):
        assert Generator.sv_type("addr", 64) == "longint unsigned"
        assert Generator.c_type("addr", 64) == "uint64_t"
        assert Generator.python_type("addr", "ctypes", 64) == "ctypes.c_uint64"


class TestReverseMaps:
    """Reverse type maps cover all entries in forward maps."""

    def test_sv_reverse_consistency(self):
        """Every SV type produced by sv_type() has a reverse mapping."""
        for t in ALL_TYPES:
            sv = Generator.sv_type(t)
            if sv == "void":
                continue
            assert sv in SV_TYPE_TO_ML, f"SV type {sv!r} (from {t!r}) not in SV_TYPE_TO_ML"

    def test_cpp_reverse_consistency(self):
        for t in ALL_TYPES:
            cpp = Generator.cpp_type(t)
            if cpp == "void":
                continue
            assert cpp in CPP_TYPE_TO_ML, f"C++ type {cpp!r} (from {t!r}) not in CPP_TYPE_TO_ML"

    def test_pss_reverse_via_scalar(self):
        """pss_scalar_to_ml covers all PSS types from pss_type()."""
        for t in ALL_TYPES:
            pss = Generator.pss_type(t)
            if pss == "void":
                continue
            ml = pss_scalar_to_ml(pss)
            assert ml is not None, f"pss_scalar_to_ml({pss!r}) returned unmapped {ml!r}"

    def test_python_ctypes_reverse_consistency(self):
        for t in ALL_TYPES:
            py = Generator.python_type(t, "ctypes")
            assert py in PYTHON_CTYPES_TO_ML, \
                f"Python ctypes {py!r} (from {t!r}) not in PYTHON_CTYPES_TO_ML"

    def test_pss_bit_int_programmatic(self):
        assert pss_scalar_to_ml("bit<8>") == "uint8"
        assert pss_scalar_to_ml("bit<16>") == "uint16"
        assert pss_scalar_to_ml("bit<32>") == "uint32"
        assert pss_scalar_to_ml("bit<64>") == "uint64"
        assert pss_scalar_to_ml("int<8>") == "int8"
        assert pss_scalar_to_ml("int<16>") == "int16"
        assert pss_scalar_to_ml("int<32>") == "int32"
        assert pss_scalar_to_ml("int<64>") == "int64"
