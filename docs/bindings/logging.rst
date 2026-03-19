Logging and Call Monitoring
===========================

ml-hpi can generate logging shim classes that intercept every call through
an interface, notify a language-specific logger, and delegate to the real
implementation.  This enables call tracing, latency measurement, protocol
checking, and coverage collection without modifying user code.

Log-Level Annotations
---------------------

Methods and interfaces can carry a ``log_level`` annotation that declares
the default verbosity of each operation.

**In YAML:**

.. code-block:: yaml

   ml-hpi:
     interfaces:
     - name: pkg.RegIf
       log_level: debug           # interface-level default
       methods:
       - name: write32
         rtype: void
         attr:
         - log_level: debug       # method-level override
       - name: reset
         rtype: void
         attr:
         - log_level: info

**As pragma comments** in any language:

.. code-block:: cpp

   virtual void write32(uint64_t addr, uint32_t data) = 0;  // ml-hpi: log_level=debug

Valid levels: ``off`` (0), ``error`` (1), ``warning`` (2), ``info`` (3,
default), ``debug`` (4), ``trace`` (5).

Generated Artifacts
-------------------

The shim generator (``--lang shim-cpp``, ``shim-python``, ``shim-sv``)
produces per interface:

- **Argument packs** -- a struct/dataclass per method holding all parameter
  values with a ``to_string()`` method.
- **Result packs** -- a struct/dataclass per non-void method holding the
  return value.
- **Call context** -- carries interface/method IDs, path, log level,
  argument pack, and result pack.
- **Logger interface** -- ``on_enter(ctx)`` / ``on_leave(ctx)``.
- **Logging shim class** -- implements the interface, delegates to an inner
  implementation, calls the logger on enter/leave.

The ID table generator (``--lang ids``) produces constant tables mapping
interface and method names to stable numeric IDs.

Usage
-----

.. code-block:: console

   $ python -m ml_hpi generate --spec spec.yaml --outdir gen/ \
       --lang cpp,shim-cpp,ids

**C++ example:**

.. code-block:: cpp

   #include "pkg.hpp"
   #include "pkg_shim.hpp"

   class MyPrintLogger : public pkg::RegIfLogger {
   public:
       void on_enter(const pkg::RegIf_call_context &ctx) override {
           std::cout << "[ENTER] " << ctx.to_string() << std::endl;
       }
       void on_leave(const pkg::RegIf_call_context &ctx) override {
           std::cout << "[LEAVE] " << ctx.to_string() << std::endl;
       }
   };

   // Wrap an implementation:
   MyRegIfImpl impl;
   MyPrintLogger logger;
   pkg::RegIfLoggingShim shim(&impl, &logger, 4 /* debug threshold */);
   shim.write32(0x1000, 0xDEAD);
   // Output:
   //   [ENTER] RegIf.write32(addr=4096, data=57005)
   //   [LEAVE] RegIf.write32(addr=4096, data=57005)

Fan-Out
~~~~~~~

Each shim holds a single logger.  To notify multiple listeners, use a
``DispatchLogger`` that forwards to sub-loggers:

.. code-block:: cpp

   class RegIfDispatchLogger : public RegIfLogger {
       std::vector<RegIfLogger *> subs_;
   public:
       void add(RegIfLogger *s) { subs_.push_back(s); }
       void on_enter(const RegIf_call_context &ctx) override {
           for (auto *s : subs_) s->on_enter(ctx);
       }
       void on_leave(const RegIf_call_context &ctx) override {
           for (auto *s : subs_) s->on_leave(ctx);
       }
   };

Limitations
-----------

- Member accessors (``regs()``, ``ports_at()``) are passed through without
  interception.  Wrap sub-interfaces with their own shims for full-hierarchy
  logging.
- ``to_string()`` on argument/result packs is available but not called by
  the shim itself.  Loggers should call it only when they intend to emit
  output.
- Thread safety is the logger's responsibility.
- Timestamp capture is the logger's responsibility.
