// tb_reg_if.sv — User-supplied SV implementation + testbench
// Requires: tb_pkg.sv (tb package) and tb_RegIf_dpi_pkg.sv (generated) compiled first.

// Concrete implementation — user-written
class tb_RegIf_impl implements tb::RegIf;
  int unsigned mem[longint unsigned];

  virtual task write32(input longint unsigned addr, input int unsigned data);
    mem[addr] = data;
    $display("SV  write32 addr=%0h data=%0h", addr, data);
  endtask

  virtual task read32(output int unsigned rval, input longint unsigned addr);
    rval = mem.exists(addr) ? mem[addr] : 32'hdeadbeef;
    $display("SV  read32  addr=%0h rval=%0h", addr, rval);
  endtask
endclass

// Top-level testbench module
module tb_top;
  import tb_RegIf_dpi::*;

  // Import: C provides, SV calls to kick off the test
  import "DPI-C" function void ml_hpi_test_start(int root_id);

  // Export: SV provides, C calls to end simulation
  export "DPI-C" function ml_hpi_test_finish;
  function automatic void ml_hpi_test_finish();
    $finish;
  endfunction

  initial begin
    automatic tb_RegIf_impl impl = new();
    automatic int root_id = tb_RegIfRoot::register_inst(impl);
    ml_hpi_test_start(root_id);   // hand control to C
    #100000;
    $fatal(1, "timeout waiting for C test");
  end
endmodule
