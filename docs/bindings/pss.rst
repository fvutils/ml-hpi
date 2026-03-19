PSS Bindings
============

``GenPSS`` produces one ``.pss`` file per package containing ``component``
declarations with ``function`` prototypes, suitable for use with PSS tools
such as ``zuspec``.

Generated Artifacts
-------------------

.. code-block:: console

   $ python -m ml_hpi generate --spec spec.yaml --outdir gen/ --lang pss

For a spec whose interfaces share the package prefix ``pkg``, the generator
produces ``pkg.pss``:

.. code-block:: text

   package pkg {

     component RegIf {
       target function void write32(addr_t addr, bit<32> data);  // ml-hpi: blocking=true
       target function bit<32> read32(addr_t addr);  // ml-hpi: blocking=true
       target function void reset();  // ml-hpi: blocking=false
     }

     component BusIf {
       RegIf regs;
       array<RegIf, *> ports;
     }

     component ExtRegIf : RegIf {
       target function void configure(bit<32> mode);  // ml-hpi: blocking=false
     }

   } // package pkg

Method Mapping
--------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ml-hpi construct
     - PSS output
   * - Method (target)
     - ``target function {rtype} {name}({params});``
   * - Method (non-target)
     - ``function {rtype} {name}({params});``
   * - Member (field)
     - ``{Type} {name};`` (component sub-instance)
   * - Member (array)
     - ``array<{Type}, *> {name};``
   * - Inheritance
     - ``component Derived : Base``

The ``blocking`` attribute is not a PSS language keyword.  The generator
encodes it as a trailing ``// ml-hpi: blocking=true|false`` comment so the
parser can recover it on round-trip.

Type Mapping
------------

.. list-table::
   :header-rows: 1
   :widths: 20 30

   * - ml-hpi
     - PSS
   * - ``void``
     - ``void``
   * - ``bool``
     - ``bool``
   * - ``int8``
     - ``int<8>``
   * - ``uint8``
     - ``bit<8>``
   * - ``int16``
     - ``int<16>``
   * - ``uint16``
     - ``bit<16>``
   * - ``int32``
     - ``int<32>``
   * - ``uint32``
     - ``bit<32>``
   * - ``int64``
     - ``int<64>``
   * - ``uint64``
     - ``bit<64>``
   * - ``addr`` / ``addr32`` / ``addr64``
     - ``addr_t``
   * - ``uintptr``
     - ``chandle``

PSS Parser
----------

``ParsePSS`` parses PSS ``component`` declarations back to an ``MlHpiDoc``.
It handles the structured output produced by ``GenPSS``, including
``// ml-hpi:`` pragma comments for round-trip fidelity.

.. code-block:: console

   $ python -m ml_hpi parse --lang pss --input pkg.pss --output recovered.yaml

**Limitations:**

- ``addr_t`` maps back to the generic ``addr`` type; the specific width
  (``addr32`` / ``addr64``) is lost.
- ``blocking`` is recovered from ``// ml-hpi:`` pragma comments.  Without
  these comments, the parser defaults to ``True`` for target functions.
- PSS ``action`` types are not part of the ml-hpi interface model and are
  skipped.
