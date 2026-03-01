Motivation
==========

Why ml-hpi Exists
-----------------

Modern SoC verification demands that the same test intent execute across a
chain of increasingly complex environments: block-level RTL simulation,
subsystem integration, full-chip simulation, emulation, and silicon bring-up.
Today, teams handle this by duplicating effort — rewriting the same test logic
in each environment, maintaining diverging copies, and rebuilding interface
glue every time a new language or methodology enters the flow.

The root cause is the absence of a shared interface contract. A UVM sequence
that drives a DMA engine at block level typically reaches into the UVM
component hierarchy directly — ``env.dma_agent.reg_driver``,
``env.dma_agent.irq_monitor`` — so it cannot compile in any other environment.
The typical response is copy-paste: clone the sequence, patch every
environment reference, and maintain a second fork forever.

The fix is well-known in software engineering: *program to an interface, not
an implementation*. If the sequence interacts with the environment through a
``DmaIf`` handle — an object that exposes ``do_transfer`` as a method — then
any environment capable of providing a ``DmaIf`` implementation can run the
sequence unchanged. Block-level, subsystem, SoC, virtual platform, and
emulation environments each supply a different implementation of the same
interface; the test logic is never touched.

The Multi-Language Challenge
-----------------------------

Applying this principle to hardware verification introduces one further
complication: verification spans multiple languages. Defining ``DmaIf`` in
SystemVerilog does not make it available in C++, Python, or PSS. Without a
language-neutral specification, each new language context requires a
hand-written interface definition and a hand-written binding layer — and the
two must be kept in sync forever.

ml-hpi solves this with a *semantic model*: a language-neutral description of
interfaces, methods, types, hierarchy, and per-method attributes. The model
can be recorded in YAML/JSON, but it can equally be *expressed* in a host
language. A SystemVerilog ``interface class`` hierarchy is a complete, valid
representation of the same model; an ml-hpi extraction tool derives the
YAML/JSON form automatically. From that derived representation the toolchain
generates idiomatic bindings for all target languages in one step — the user
maintains one source artifact and gets everything else for free.

Verification-Specific Requirements
------------------------------------

Two requirements specific to verification environments go beyond what a
generic IDL can provide:

**Hierarchical context.**
Real designs contain many instances of the same IP block — four DMA channels,
eight PCIe ports. ml-hpi models interfaces as class hierarchies with named
*field* members (a single sub-interface) and *array* members (an indexed
collection). A test navigates naturally: ``chip.uarts_at(1).send(ch)``.
Each instance is a typed object; no handle bookkeeping is required. The
generated binding layer handles the mechanics of crossing flat DPI/FFI
boundaries while preserving the object model transparently.

**Blocking vs. non-blocking calls.**
Whether a method must consume simulated time before returning is a property of
the *operation*, not the language. ml-hpi captures a ``blocking`` attribute
per method. Generators emit the correct construct for each language: a
``pure virtual task`` in SystemVerilog, an ``async def`` coroutine in Python,
a callback-based completion import in C. In PSS, the same attribute drives the
target-time / solve-time distinction. The interface author states *what* each
method does; the generator handles *how* each language expresses it.

Extending to PSS
----------------

The same interface spec that enables UVM sequence reuse across integration
levels also serves as the bridge to PSS (Portable Test and Stimulus Standard,
IEEE 1647). PSS actions call platform functionality through ``function import``
declarations that must be kept in sync with DPI stubs and platform dispatch
logic — hand work spread across three languages. Because ml-hpi already
captures all attributes PSS needs (``blocking``, ``target``, ``solve``), the
toolchain generates the complete PSS ``component`` and ``function import``
declarations in the same step that produces C++ and Python bindings.

The practical workflow is:

.. code-block:: text

   SV interface class  --> (ml-hpi derives IDL)  -->  PSS component + function imports
                                                  +-->  C++ / Python / C bindings

The IDL is a hidden intermediary — the SV ``interface class`` remains the
single maintained artifact, and the PSS infrastructure is never hand-written.
