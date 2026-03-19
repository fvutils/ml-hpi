Python Bindings
===============

``GenPython`` produces one ``.py`` file per package containing
``typing.Protocol`` classes.  Three annotation styles are supported.

Generated Artifacts
-------------------

.. code-block:: console

   $ python -m ml_hpi generate --spec spec.yaml --outdir gen/ --lang python
   $ python -m ml_hpi generate --spec spec.yaml --outdir gen/ --lang python \
       --python-style annotated

Annotation Styles
-----------------

**Plain** (default) -- bare Python types:

.. code-block:: python

   class RegIf(typing.Protocol):
       async def write32(self, addr: int, data: int) -> None: ...
       async def read32(self, addr: int) -> int: ...
       def reset(self) -> None: ...

**Annotated** -- ``Annotated[int, ...]`` aliases that preserve ml-hpi type
width information:

.. code-block:: python

   from typing import Annotated

   Addr64 = Annotated[int, "addr64"]
   UInt32 = Annotated[int, "uint32"]

   class RegIf(typing.Protocol):
       async def write32(self, addr: Addr64, data: UInt32) -> None: ...
       async def read32(self, addr: Addr64) -> UInt32: ...
       def reset(self) -> None: ...

**ctypes** -- ``ctypes.c_*`` types for FFI-oriented code:

.. code-block:: python

   import ctypes

   class RegIf(typing.Protocol):
       async def write32(self, addr: ctypes.c_uint64, data: ctypes.c_uint32) -> None: ...
       async def read32(self, addr: ctypes.c_uint64) -> ctypes.c_uint32: ...
       def reset(self) -> None: ...

Method Mapping
--------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ml-hpi construct
     - Python output
   * - Method (non-blocking)
     - ``def {name}(self, ...) -> rtype: ...``
   * - Method (blocking)
     - ``async def {name}(self, ...) -> rtype: ...``
   * - Member (field)
     - ``def {name}(self) -> IfType: ...``
   * - Member (array)
     - | ``def {name}_at(self, idx: int) -> IfType: ...``
       | ``def {name}_size(self) -> int: ...``
   * - Inheritance
     - ``class Derived(Base, typing.Protocol):``

Type Mapping
------------

.. list-table::
   :header-rows: 1
   :widths: 15 15 20 20

   * - ml-hpi
     - Plain
     - Annotated
     - ctypes
   * - ``void``
     - ``None``
     - ``None``
     - ``None``
   * - ``bool``
     - ``bool``
     - ``bool``
     - ``ctypes.c_bool``
   * - ``int32``
     - ``int``
     - ``Int32``
     - ``ctypes.c_int32``
   * - ``uint32``
     - ``int``
     - ``UInt32``
     - ``ctypes.c_uint32``
   * - ``int64``
     - ``int``
     - ``Int64``
     - ``ctypes.c_int64``
   * - ``uint64``
     - ``int``
     - ``UInt64``
     - ``ctypes.c_uint64``
   * - ``addr64``
     - ``int``
     - ``Addr64``
     - ``ctypes.c_uint64``
   * - ``uintptr``
     - ``int``
     - ``UIntPtr``
     - ``ctypes.c_void_p``

Python Parser
-------------

``ParsePython`` uses Python's ``ast`` module to parse Protocol classes back
to an ``MlHpiDoc``.  The parser auto-detects the annotation style from
imports.

.. code-block:: console

   $ python -m ml_hpi parse --lang python --input pkg.py --output recovered.yaml

**Limitations:**

- Plain-style ``int`` is ambiguous (could be any integer width); the parser
  defaults to ``int32`` and emits a warning.  Use the annotated style for
  lossless round-trip fidelity.
- ``target`` / ``solve`` attributes are not expressible in Python and
  default to unset.
- The parser performs static analysis only; it does not execute the file.
