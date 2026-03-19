"""Unit tests for log-level model extensions (Phase 1.1)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from ml_hpi.model import MethodAttr, Method, Interface, LOG_LEVELS
from ml_hpi.gen.gen_base import load_spec

DATA_DIR = Path(__file__).parent / "data"


def test_method_attr_log_level():
    a = MethodAttr(log_level="debug")
    assert a.log_level == "debug"
    d = a.model_dump(exclude_none=True)
    assert d == {"log_level": "debug"}
    a2 = MethodAttr(**d)
    assert a2.log_level == "debug"


def test_interface_log_level():
    iface = Interface(name="pkg.Foo", log_level="trace")
    assert iface.log_level == "trace"


def test_effective_log_level_method_override():
    m = Method(name="foo", rtype="void", attr=[MethodAttr(log_level="trace")])
    assert m.effective_log_level("debug") == "trace"


def test_effective_log_level_interface_default():
    m = Method(name="foo", rtype="void")
    assert m.effective_log_level("debug") == "debug"


def test_effective_log_level_global_default():
    m = Method(name="foo", rtype="void")
    assert m.effective_log_level(None) == "info"


def test_log_level_numeric():
    assert LOG_LEVELS["off"] == 0
    assert LOG_LEVELS["error"] == 1
    assert LOG_LEVELS["warning"] == 2
    assert LOG_LEVELS["info"] == 3
    assert LOG_LEVELS["debug"] == 4
    assert LOG_LEVELS["trace"] == 5


def test_load_spec_with_log_level():
    doc = load_spec(DATA_DIR / "full_spec_logging.yaml")
    reg = next(i for i in doc.spec.interfaces if i.short_name() == "RegIf")
    assert reg.log_level == "debug"
    w32 = next(m for m in reg.methods if m.name == "write32")
    assert w32.get_log_level() == "debug"
    r32 = next(m for m in reg.methods if m.name == "read32")
    assert r32.get_log_level() is None
    assert r32.effective_log_level(reg.log_level) == "debug"
    reset = next(m for m in reg.methods if m.name == "reset")
    assert reset.get_log_level() == "info"
    assert reset.effective_log_level(reg.log_level) == "info"


def test_load_spec_without_log_level():
    """Existing specs without log_level still load fine."""
    doc = load_spec(DATA_DIR / "full_spec.yaml")
    reg = next(i for i in doc.spec.interfaces if i.short_name() == "RegIf")
    assert reg.log_level is None
    for m in reg.methods:
        assert m.get_log_level() is None
        assert m.effective_log_level(None) == "info"
