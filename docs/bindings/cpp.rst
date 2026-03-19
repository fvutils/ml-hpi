C++ Bindings
============

``GenCpp`` produces one ``.hpp`` header per package containing abstract
classes with pure virtual methods inside a namespace.

Generated Artifacts
-------------------

.. code-block:: console

   $ python -m ml_hpi generate --spec spec.yaml --outdir gen/ --lang cpp

For a spec whose interfaces share the package prefix ``pkg``, the generator
produces ``pkg.hpp``:

.. code-block:: cpp

   #pragma once

   #include <cstdint>
   #include <functional>

   namespace pkg {

   class RegIf;
   class BusIf;
   class ExtRegIf;

   class RegIf {
   public:
       virtual ~RegIf() = default;
       virtual void write32(uint64_t addr, uint32_t data) = 0;
       virtual void write32(uint64_t addr, uint32_t data, std::function<void()> cb) = 0;
       virtual uint32_t read32(uint64_t addr) = 0;
       virtual void read32(uint64_t addr, std::function<void(uint32_t)> cb) = 0;
       virtual void reset() = 0;
   };

   class BusIf {
   public:
       virtual ~BusIf() = default;
       virtual RegIf *regs() = 0;
       virtual RegIf *ports_at(int idx) = 0;
       virtual int ports_size() = 0;
   };

   class ExtRegIf : public virtual RegIf {
   public:
       virtual ~ExtRegIf() = default;
       virtual void configure(uint32_t mode) = 0;
   };

   } // namespace pkg

Blocking methods are emitted in two forms: a synchronous signature and an
asynchronous callback overload using ``std::function``.  Pass
``--no-cpp-async`` to suppress the callback overloads.

Method Mapping
--------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ml-hpi construct
     - C++ output
   * - Method (non-blocking)
     - ``virtual {rtype} {name}({params}) = 0;``
   * - Method (blocking, sync)
     - ``virtual {rtype} {name}({params}) = 0;``
   * - Method (blocking, async)
     - ``virtual void {name}({params}, std::function<void({rtype})> cb) = 0;``
   * - Member (field)
     - ``virtual {IfType} *{name}() = 0;``
   * - Member (array)
     - | ``virtual {IfType} *{name}_at(int idx) = 0;``
       | ``virtual int {name}_size() = 0;``
   * - Inheritance
     - ``class Derived : public virtual Base``

Type Mapping
------------

.. list-table::
   :header-rows: 1
   :widths: 20 30

   * - ml-hpi
     - C++
   * - ``void``
     - ``void``
   * - ``bool``
     - ``bool``
   * - ``int8`` / ``uint8``
     - ``int8_t`` / ``uint8_t``
   * - ``int16`` / ``uint16``
     - ``int16_t`` / ``uint16_t``
   * - ``int32`` / ``uint32``
     - ``int32_t`` / ``uint32_t``
   * - ``int64`` / ``uint64``
     - ``int64_t`` / ``uint64_t``
   * - ``addr`` / ``addr32`` / ``addr64``
     - ``uint32_t`` or ``uint64_t`` (based on ``--addr-bits``)
   * - ``uintptr``
     - ``uintptr_t``

C++ Parser
----------

``ParseCpp`` uses ``cxxheaderparser`` to parse abstract class headers back
to an ``MlHpiDoc``.

.. code-block:: console

   $ python -m ml_hpi parse --lang cpp --input pkg.hpp --output recovered.yaml

**Limitations:**

- ``target`` / ``solve`` attributes cannot be inferred from C++ and default
  to unset.
- ``blocking`` is inferred only when both sync and async overloads exist for
  the same method name.  If the header was generated with ``--no-cpp-async``,
  blocking cannot be recovered.
- ``addr`` vs concrete integer width (``uint64``) is ambiguous.
