
package ml_hpi;

  // -------------------------------------------------------------------------
  // Type aliases used by generated DPI packages
  // -------------------------------------------------------------------------
  // (none needed at package level — types are declared per-generated package)

  // -------------------------------------------------------------------------
  // Root base class
  //
  // Generated code produces a concrete {IfName}Root class per root interface
  // type.  This class is intentionally NOT a base class of the interface
  // itself; it is a standalone registry utility.
  //
  // Usage (generated specialisation example for pkg::BusIf):
  //
  //   class pkg_BusIfRoot;
  //     static pkg::BusIf __registry[int];
  //     static int        __next_id = 0;
  //     static function int register(pkg::BusIf impl);
  //       int id = __next_id++;
  //       __registry[id] = impl;
  //       return id;
  //     endfunction
  //     static function pkg::BusIf get(int root_id);
  //       return __registry[root_id];
  //     endfunction
  //   endclass
  //
  // -------------------------------------------------------------------------

endpackage
