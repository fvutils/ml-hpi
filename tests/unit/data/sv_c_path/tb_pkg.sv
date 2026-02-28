// tb_pkg.sv — tb package declaration (must be compiled before tb_RegIf_dpi_pkg.sv)
package tb;
  interface class RegIf;
    pure virtual task write32(input longint unsigned addr, input int unsigned data);
    pure virtual task read32(output int unsigned rval, input longint unsigned addr);
  endclass
endpackage
