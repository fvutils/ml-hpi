SystemVerilog Bindings
======================

ml-hpi produces two distinct SystemVerilog outputs from a single spec:

1. **Interface class declarations** (``GenSVInterface``) -- the SV-native
   hierarchical API.
2. **DPI glue package** (``GenSV``) -- a flat DPI bridge that lets C code
   call into the SV interface hierarchy.

This page documents both.

Interface Class Generator
-------------------------

``GenSVInterface`` emits one ``.sv`` file per package containing
``interface class`` declarations.  Each ml-hpi interface becomes a
SystemVerilog ``interface class``; methods become ``pure virtual function``
or ``pure virtual task`` declarations; members become accessor methods.

Generated Artifacts
~~~~~~~~~~~~~~~~~~~

For a spec whose interfaces share the package prefix ``pkg``, the generator
produces ``pkg.sv``:

.. code-block:: console

   $ python -m ml_hpi generate --spec spec.yaml --outdir gen/ --lang sv

Output structure:

.. code-block:: systemverilog

   package pkg;
     interface class RegIf;
       pure virtual task write32(longint unsigned addr, int unsigned data);
       pure virtual task read32(output int unsigned rval, input longint unsigned addr);
       pure virtual function void reset();
     endclass

     interface class BusIf;
       pure virtual function RegIf regs();
       pure virtual function RegIf ports_at(int idx);
       pure virtual function int ports_size();
     endclass

     interface class ExtRegIf extends RegIf;
       pure virtual function void configure(int unsigned mode);
     endclass
   endpackage

Method Mapping
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ml-hpi construct
     - SystemVerilog output
   * - Method (non-blocking)
     - ``pure virtual function {rtype} {name}({params});``
   * - Method (blocking, void return)
     - ``pure virtual task {name}({params});``
   * - Method (blocking, non-void return)
     - ``pure virtual task {name}(output {rtype} rval, input {params});``
   * - Member (field)
     - ``pure virtual function {IfType} {name}();``
   * - Member (array)
     - | ``pure virtual function {IfType} {name}_at(int idx);``
       | ``pure virtual function int {name}_size();``
   * - Inheritance
     - ``interface class Derived extends Base;``

Type Mapping
~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 30

   * - ml-hpi
     - SystemVerilog
   * - ``void``
     - ``void``
   * - ``bool``
     - ``bit``
   * - ``int8``
     - ``byte``
   * - ``uint8``
     - ``byte unsigned``
   * - ``int16``
     - ``shortint``
   * - ``uint16``
     - ``shortint unsigned``
   * - ``int32``
     - ``int``
   * - ``uint32``
     - ``int unsigned``
   * - ``int64``
     - ``longint``
   * - ``uint64``
     - ``longint unsigned``
   * - ``addr`` / ``addr32``
     - ``int unsigned``
   * - ``addr`` / ``addr64``
     - ``longint unsigned``
   * - ``uintptr``
     - ``chandle``

DPI Glue Generator
------------------

``GenSV`` produces a DPI bridge package that allows C code to invoke SV
interface methods through the DPI-C mechanism.  It emits a root registry
class, a ``navigate()`` function, and DPI export wrappers.

This generator requires a ``--root-if`` argument identifying the root
interface of the hierarchy:

.. code-block:: console

   $ python -m ml_hpi generate --spec spec.yaml --outdir gen/ --lang sv \
       --root-if pkg.RegIf

See the :doc:`C bindings <c>` page for the matching C header.

SV Parser
---------

``ParseSV`` uses ``pyslang`` to parse ``interface class`` declarations back
to an ``MlHpiDoc``.

.. code-block:: console

   $ python -m ml_hpi parse --lang sv --input pkg.sv --output recovered.yaml

**Limitations:**

- ``target`` / ``solve`` attributes are not expressible in SV interface class
  syntax and default to unset in the parsed output.  Add
  ``// ml-hpi:target=true`` pragma comments to preserve them.
- ``addr64`` vs ``uint64`` ambiguity: the parser defaults to ``uint64``.
- ``pyslang`` is a hard requirement; no fallback parser is provided.
