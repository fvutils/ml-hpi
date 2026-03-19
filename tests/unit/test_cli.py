"""Unit tests for CLI entry point."""
import subprocess
import sys
from pathlib import Path

import pytest

SPEC = Path(__file__).parent / "data" / "full_spec.yaml"
SPEC_LOG = Path(__file__).parent / "data" / "full_spec_logging.yaml"
PYTHON = sys.executable


def _run(*args):
    return subprocess.run(
        [PYTHON, "-m", "ml_hpi"] + list(args),
        capture_output=True, text=True,
        cwd=str(Path(__file__).parents[2]),
    )


# -- help --

def test_help():
    r = _run("--help")
    assert r.returncode == 0
    assert "generate" in r.stdout
    assert "inspect" in r.stdout
    assert "parse" in r.stdout


# -- generate bindings --

def test_generate_bindings_all(tmp_path):
    r = _run("generate", str(SPEC), "bindings",
             "--outdir", str(tmp_path), "--lang", "sv,cpp,python,pss")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "pkg.sv").exists()
    assert (tmp_path / "pkg.hpp").exists()
    assert (tmp_path / "pkg.py").exists()
    assert (tmp_path / "pkg.pss").exists()


def test_generate_bindings_single(tmp_path):
    r = _run("generate", str(SPEC), "bindings",
             "--outdir", str(tmp_path), "--lang", "pss")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "pkg.pss").exists()
    assert not (tmp_path / "pkg.sv").exists()


# -- generate shim --

def test_generate_shim(tmp_path):
    r = _run("generate", str(SPEC_LOG), "shim",
             "--outdir", str(tmp_path), "--lang", "cpp,python,sv")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "pkg_shim.hpp").exists()
    assert (tmp_path / "pkg_shim.py").exists()
    assert (tmp_path / "pkg_shim.sv").exists()


# -- generate ids --

def test_generate_ids(tmp_path):
    r = _run("generate", str(SPEC), "ids",
             "--outdir", str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "pkg_monitor_ids.hpp").exists()
    assert (tmp_path / "pkg_monitor_ids.py").exists()
    assert (tmp_path / "pkg_monitor_ids_pkg.sv").exists()


# -- inspect --

def test_inspect_default(tmp_path):
    r = _run("inspect", str(SPEC_LOG))
    assert r.returncode == 0, r.stderr
    assert "pkg.RegIf" in r.stdout
    assert "write32" in r.stdout


def test_inspect_interfaces_only():
    r = _run("inspect", str(SPEC), "--interfaces")
    assert r.returncode == 0, r.stderr
    assert "pkg.RegIf" in r.stdout
    # Without --methods, method details should not appear
    # (but with --interfaces and no --methods, we only list interface names)


def test_inspect_types():
    r = _run("inspect", str(SPEC), "--types")
    assert r.returncode == 0, r.stderr
    assert "addr64" in r.stdout
    assert "uint32" in r.stdout


# -- parse --

def test_parse_sv(tmp_path):
    gen_dir = tmp_path / "gen"
    _run("generate", str(SPEC), "bindings",
         "--outdir", str(gen_dir), "--lang", "sv")

    out_yaml = tmp_path / "recovered.yaml"
    r = _run("parse", "--lang", "sv",
             "--input", str(gen_dir / "pkg.sv"),
             "--output", str(out_yaml))
    assert r.returncode == 0, r.stderr
    assert out_yaml.exists()
    assert "interfaces" in out_yaml.read_text()


def test_roundtrip_cli(tmp_path):
    gen_dir = tmp_path / "gen"
    _run("generate", str(SPEC), "bindings",
         "--outdir", str(gen_dir), "--lang", "cpp")

    out_yaml = tmp_path / "recovered.yaml"
    r = _run("parse", "--lang", "cpp",
             "--input", str(gen_dir / "pkg.hpp"),
             "--output", str(out_yaml))
    assert r.returncode == 0, r.stderr

    import yaml
    data = yaml.safe_load(out_yaml.read_text())
    ifaces = data["ml-hpi"]["interfaces"]
    names = [i["name"] for i in ifaces]
    assert "pkg.RegIf" in names
    assert "pkg.BusIf" in names
    assert "pkg.ExtRegIf" in names


def test_missing_spec(tmp_path):
    r = _run("generate", "/nonexistent/spec.yaml", "bindings",
             "--outdir", str(tmp_path), "--lang", "pss")
    assert r.returncode != 0
