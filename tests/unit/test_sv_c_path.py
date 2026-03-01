"""
End-to-end test: C → SystemVerilog DPI path.

Compile order:
  1. ml_hpi.sv          (ml_hpi package — built-in)
  2. tb_pkg.sv          (tb::RegIf interface class — user-supplied)
  3. <generated>.sv     (tb_RegIfRoot class + tb_RegIf_dpi package)
  4. tb_test_pkg.sv     (tb_test package: test control DPI — user-supplied)
  5. tb_reg_if.sv       (tb_RegIf_impl class + tb_top module — user-supplied)
  6. tb_dpi_test.c      (C test driver — user-supplied)
"""
import os
import asyncio
import shutil
import sys
import pytest

from pathlib import Path
from dv_flow.mgr import TaskListenerLog, TaskSetRunner, PackageLoader
from dv_flow.mgr.task_graph_builder import TaskGraphBuilder

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from ml_hpi.gen.gen_sv import GenSV
from ml_hpi.gen.gen_c import GenC
from ml_hpi.gen.gen_base import load_spec

DATA_DIR = Path(__file__).parent / "data" / "sv_c_path"
SHARE_SV  = Path(__file__).parents[2] / "src" / "ml_hpi" / "share" / "sv"
SPEC_FILE = DATA_DIR / "reg_if.yaml"
ROOT_IF   = "tb.RegIf"


def get_available_sims():
    sims = []
    for exe, sim in {"verilator": "vlt", "vcs": "vcs", "vsim": "mti"}.items():
        if shutil.which(exe) is not None:
            sims.append(sim)
    return sims


@pytest.mark.parametrize("sim", get_available_sims())
def test_sv_c_path(tmpdir, sim):
    gen_dir = Path(tmpdir) / "generated"

    # ------------------------------------------------------------------ #
    # 1. Generate SV + C header                                            #
    # ------------------------------------------------------------------ #
    doc      = load_spec(SPEC_FILE)
    sv_files = GenSV(doc, ROOT_IF).generate(gen_dir)
    c_files  = GenC(doc, ROOT_IF).generate(gen_dir)

    assert sv_files and sv_files[0].exists()
    assert c_files  and c_files[0].exists()

    # Copy generated header next to the C source so #include finds it
    shutil.copy(c_files[0], DATA_DIR / c_files[0].name)

    # ------------------------------------------------------------------ #
    # 2. Build dv-flow task graph                                          #
    # ------------------------------------------------------------------ #
    rundir = os.path.join(tmpdir, "rundir")

    def marker_listener(marker):
        raise Exception("marker")

    builder = TaskGraphBuilder(
        PackageLoader(marker_listeners=[marker_listener]).load_rgy(
            ["std", f"hdlsim.{sim}"]),
        rundir)

    ml_hpi_sv = builder.mkTaskNode(
        "std.FileSet",
        name="ml_hpi_sv",
        type="systemVerilogSource",
        base=str(SHARE_SV),
        include="ml_hpi.sv")

    tb_pkg_sv = builder.mkTaskNode(
        "std.FileSet",
        name="tb_pkg_sv",
        type="systemVerilogSource",
        base=str(DATA_DIR),
        include="tb_pkg.sv")

    gen_sv_node = builder.mkTaskNode(
        "std.FileSet",
        name="gen_sv",
        type="systemVerilogSource",
        base=str(gen_dir),
        include=sv_files[0].name)

    tb_test_sv = builder.mkTaskNode(
        "std.FileSet",
        name="tb_test_sv",
        type="systemVerilogSource",
        base=str(DATA_DIR),
        include="tb_test_pkg.sv")

    user_sv = builder.mkTaskNode(
        "std.FileSet",
        name="user_sv",
        type="systemVerilogSource",
        base=str(DATA_DIR),
        include="tb_reg_if.sv")

    user_c = builder.mkTaskNode(
        "std.FileSet",
        name="user_c",
        type="cSource",
        base=str(DATA_DIR),
        include="tb_dpi_test.c")

    sim_img = builder.mkTaskNode(
        f"hdlsim.{sim}.SimImage",
        name="sim_img",
        needs=[ml_hpi_sv, tb_pkg_sv, gen_sv_node, tb_test_sv, user_sv, user_c],
        top=["tb_top"])

    sim_run = builder.mkTaskNode(
        f"hdlsim.{sim}.SimRun",
        name="sim_run",
        needs=[sim_img])

    # ------------------------------------------------------------------ #
    # 3. Run                                                               #
    # ------------------------------------------------------------------ #
    runner = TaskSetRunner(rundir)
    runner.add_listener(TaskListenerLog().event)
    asyncio.run(runner.run([sim_run]))

    assert runner.status == 0, "Simulation task failed"

    # ------------------------------------------------------------------ #
    # 4. Verify simulation output                                          #
    # ------------------------------------------------------------------ #
    from dv_flow.mgr import TaskSetRunner as _unused  # noqa — keep import tidy

    # Locate sim.log
    log_path = None
    for root, _, files in os.walk(rundir):
        if "sim.log" in files:
            log_path = os.path.join(root, "sim.log")
            break

    assert log_path is not None, "sim.log not found in rundir"
    sim_log = Path(log_path).read_text()
    assert "RESULT: PASS" in sim_log, \
        f"Expected 'RESULT: PASS' in sim.log:\n{sim_log}"
