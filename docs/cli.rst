Command-Line Interface
======================

ml-hpi provides a CLI via ``python -m ml_hpi`` with three top-level
commands: ``generate``, ``inspect``, and ``parse``.

The ``generate`` and ``inspect`` commands take a spec file as a positional
argument.  ``parse`` operates on language source files and does not require
a spec.

Generate
--------

Generate code from a spec.  The spec file is a positional argument,
followed by a sub-command selecting what to generate.

Generate Bindings
~~~~~~~~~~~~~~~~~

Generate language-specific interface declarations.

.. code-block:: text

   ml-hpi generate <spec> bindings --outdir DIR --lang LANGS [options]

**Required arguments:**

``--outdir DIR``
   Output directory for generated files.

``--lang LANGS``
   Comma-separated list of target languages: ``sv``, ``cpp``, ``python``,
   ``pss``, ``c``.

**Optional arguments:**

``--root-if NAME``
   Fully qualified root interface name (e.g. ``pkg.RegIf``).  Required for
   the ``c`` and ``sv`` (DPI) generators.  When ``--lang sv`` is used
   without ``--root-if``, the interface class generator is used instead of
   the DPI glue generator.

``--addr-bits {32,64}``
   Address width for ``addr`` type resolution.  Default: ``64``.

``--python-style {plain,annotated,ctypes}``
   Python type annotation style.  Default: ``plain``.

``--cpp-async / --no-cpp-async``
   Emit ``std::function`` async overloads for blocking methods in C++.
   Default: enabled.

**Examples:**

.. code-block:: console

   $ python -m ml_hpi generate spec.yaml bindings \
       --outdir gen/ --lang sv,cpp,python,pss

   $ python -m ml_hpi generate spec.yaml bindings \
       --outdir gen/ --lang python --python-style annotated

   $ python -m ml_hpi generate spec.yaml bindings \
       --outdir gen/ --lang sv,c --root-if pkg.RegIf

Generate Shim
~~~~~~~~~~~~~

Generate logging shim classes, argument packs, and logger interfaces.

.. code-block:: text

   ml-hpi generate <spec> shim --outdir DIR --lang LANGS

``--lang LANGS``
   Comma-separated: ``cpp``, ``python``, ``sv``.

``--addr-bits {32,64}``
   Address width.  Default: ``64``.

**Example:**

.. code-block:: console

   $ python -m ml_hpi generate spec.yaml shim \
       --outdir gen/ --lang cpp,python,sv

Generate IDs
~~~~~~~~~~~~

Generate monitor ID constant tables.

.. code-block:: text

   ml-hpi generate <spec> ids --outdir DIR [--lang LANGS]

``--lang LANGS``
   Comma-separated: ``cpp``, ``python``, ``sv``.  Default: all three.

**Example:**

.. code-block:: console

   $ python -m ml_hpi generate spec.yaml ids --outdir gen/

Inspect
-------

Inspect a spec file without generating any code.

.. code-block:: text

   ml-hpi inspect <spec> [--interfaces] [--methods] [--types]

With no flags, shows all interfaces with their methods and members.

``--interfaces``
   List interface names, inheritance, and log levels.

``--methods``
   Include method details (parameters, return types, attributes).

``--types``
   List all scalar types used in the spec.

**Examples:**

.. code-block:: console

   $ python -m ml_hpi inspect spec.yaml

   $ python -m ml_hpi inspect spec.yaml --types

Parse
-----

Parse language source back to an ml-hpi YAML spec.  This command does not
take a spec file as input.

.. code-block:: text

   ml-hpi parse --lang LANG --input FILE --output FILE

``--lang {sv,cpp,python,pss}``
   Source language to parse.

``--input PATH``
   Input source file.

``--output PATH``
   Output YAML file.

``--addr-bits {32,64}``
   Address width hint.  Default: ``64``.

**Examples:**

.. code-block:: console

   $ python -m ml_hpi parse --lang sv --input pkg.sv --output recovered.yaml

   $ python -m ml_hpi generate spec.yaml bindings --outdir gen/ --lang cpp
   $ python -m ml_hpi parse --lang cpp --input gen/pkg.hpp --output rt.yaml
