# ml-hpi Whitepaper Outline
## Multi-Language Hierarchical Programming Interface: Unifying Verification APIs Across Environments

---

## 1. Introduction / Abstract (~0.5 page)

- Modern SoC verification requires the same functional intent to execute in radically different
  environments: block-level RTL simulation, subsystem integration, full-chip simulation, emulation,
  and silicon bring-up.
- Today, teams write separate test code for each level, burning time and introducing divergence.
- ml-hpi proposes a single, declarative interface specification that generates consistent,
  idiomatic bindings for every language involved (SystemVerilog, C/C++, Python, PSS), enabling
  one test to run unmodified across all environments.
- This paper motivates the problem, describes the ml-hpi design, and shows how it extends
  naturally to PSS-based portable stimulus.

---

## 2. The Reuse Problem: From Block to Subsystem (and Beyond) (~1 page)

### 2.1 Life of a Typical Block-Level Test

- Engineer writes a UVM virtual sequence, `do_transfer`, that carries out a DMA transfer:
  it grabs the driver, programs source/destination/length registers, and waits for the
  done interrupt — all via direct references into the block-level UVM environment hierarchy
  (`env.dma_agent.reg_driver`, `env.dma_agent.irq_monitor`, etc.).
- The sequence passes cleanly at block level because the environment hierarchy it expects
  is exactly what the block testbench provides.

### 2.2 Moving to Subsystem Integration

- At subsystem level the same DMA engine exists, but the UVM component hierarchy is completely
  different: different top-level agent, different path to the DMA handle, different timing model.
- The block-level test is unusable as-is; engineers copy-paste and adapt it, creating a fork
  that must be maintained in parallel forever.
- Root cause: the test was written against a concrete implementation, not an abstract interface.

### 2.3 The Interface Solution

- If the test had been written against a well-defined *interface* — a named set of operations
  with specified signatures — then any environment that provides an implementation of that
  interface can run the test unchanged.
- This is the classic "program to an interface, not an implementation" principle applied to
  hardware verification.
- The challenge: verification spans multiple languages (C, C++, SystemVerilog, Python, PSS),
  each with their own interface/class mechanisms. Defining the interface in one language does not
  automatically make it available in others.

---

## 3. Verification-Specific Interface Requirements (~1 page)

Naive application of a shared interface spec runs into two complications unique to verification
environments.

### 3.1 Hierarchical Context (The Multiple-Instance Problem)

- Real designs have multiple instances of the same IP block: 4 DMA channels, 8 PCIe ports,
  16 DRAM banks.
- A flat, global function API (`dma_write32(addr, data)`) cannot address a specific instance
  without either encoding the instance number in every function name or adding an opaque
  context/handle argument.
- The former explodes the API surface; the latter is error-prone and inconsistent.
- ml-hpi models interfaces as objects (classes in C++/Python, `interface class` in SV) that
  naturally carry per-instance state via the class handle. Arrays of sub-interfaces express
  multi-instance IP cleanly: `soc.dmas[2].start_transfer(...)`.
- The *interface path* mechanism encodes any position in the hierarchy as a single integer,
  allowing the client language to navigate to any sub-interface instance over a flat DPI/FFI
  boundary without sacrificing the OO model.

### 3.2 Blocking vs. Non-Blocking Calls

- The fundamental question for any interface method is: *must simulated time advance before
  the call returns?* A `do_transfer` that waits for a DMA done interrupt must consume
  simulation cycles; a `get_status` that reads a register modeled in zero time need not.
  This determines whether a method is blocking or non-blocking — it is a property of the
  operation, not of the language.
- Two axes shape how blocking character is expressed:
  - **User view**: what does the caller expect? A sequence writer calling `dma.do_transfer(...)`
    wants to write straight-line code and have execution resume only when the transfer is done.
  - **Implementation view**: what threading model does the platform provide? In SystemVerilog
    a blocking operation is naturally a `task`; in Python the same operation is best expressed
    as a coroutine (`async def` / `await`) so the event loop remains responsive. The *semantics*
    are identical; the *syntax* differs.
- ml-hpi captures the `blocking` attribute per method so each language binding emits the
  correct construct automatically: `pure virtual task` in SV, `async def` in Python,
  a callback-style completion import for C — without the interface author writing any
  binding code by hand.
- In PSS the same distinction maps to *target-time* (blocking, execution phase) vs.
  *solve-time* (non-blocking, constraint/data-computation phase), captured by the
  `target` / `solve` attributes.

---

## 4. The Fragmentation Tax: A Different API for Every Language × Methodology (~0.75 page)

### 4.1 Today's Landscape

- Without a shared spec, the same logical operation is expressed differently in every context:
  - C test bench: `dma_write(ctx, addr, data)` — flat C with explicit context pointer
  - C++ model: `dma->write(addr, data)` — virtual method on a custom class hierarchy
  - SystemVerilog UVM: `env.dma_agent.driver.write(addr, data)` — deep UVM path, task call
  - Python (cocotb / scbotb): `await dma.write(addr, data)` — coroutine
  - PSS: `dma_write_transfer.exec_body { ... }` — action body
- A team supporting all five contexts maintains five separate interface definitions,
  five sets of glue code, and five documentation artifacts — for each IP block.

### 4.2 Cost and Risk

- Any change to the underlying IP triggers updates across all five representations.
- Bugs in glue code cause test escapes that are hard to attribute.
- New team members must learn five interface styles before writing a single test.

### 4.3 A Common Semantic Model — Not Just a File Format

- The core of ml-hpi is a *semantic model*: a language-neutral description of interfaces,
  methods, types, hierarchy, and method attributes (blocking, target/solve).
- JSON/YAML is one way to express that model, but it is not the only way. The same semantic
  model can be expressed directly in a host language — a SystemVerilog `interface class`
  hierarchy *is* a valid representation of an ml-hpi spec, as is a C++ pure-virtual class
  hierarchy or a Python ABC.
- This means teams do not need to learn a new file format to adopt ml-hpi. A team whose
  primary language is SystemVerilog authors their interfaces in SV; the ml-hpi toolchain
  *derives* the JSON/YAML representation automatically, then generates bindings for all
  other languages from it.
- Because all representations share the same underlying model, the toolchain can also
  *compare* two specifications expressed in different languages — detecting drift between,
  say, a SV interface class and a C++ virtual class that are supposed to represent the
  same API.
- The JSON/YAML form acts as the portable interchange and storage format, but it is an
  implementation detail of the toolchain, not a user-facing artifact.

---

## 5. Test Portability in Practice: Block → Subsystem → SoC (~1 page)

### 5.1 Writing a Portable Test

- Define a `DmaIf` ml-hpi interface with a single blocking method `do_transfer(src, dst, len)`
  — one call that initiates the transfer and returns only when it completes.
- Generate SV bindings; write a UVM sequence that depends only on a `DmaIf` handle — no
  references to any specific UVM component path.
- The same sequence compiles and runs wherever a `DmaIf` implementation is registered.

### 5.2 Block-Level Environment

- The block testbench implements `DmaIf` as a UVM component that drives the DMA's register
  bus directly.
- The sequence is oblivious to this; it calls `dma_if.start_transfer(...)` and waits.

### 5.3 Subsystem-Level Environment

- The subsystem testbench implements `DmaIf` differently: it uses a system-bus VIP to
  reach the DMA over a shared interconnect; timing, width, and arbitration are all different.
- The sequence file is *identical* — zero changes.
- The subsystem team writes one `DmaIf` implementation; all existing block-level sequences
  become immediately available for integration testing.

### 5.4 SoC / Emulation / Silicon

- The same interface can be implemented in C++ for a virtual platform, or in Python for a
  cocotb environment, or against bare-metal driver calls in silicon bring-up.
- In every case the test logic is unchanged; only the implementation of `DmaIf` differs.

### 5.5 Return on Investment

- Test reuse compresses verification timelines at each integration level.
- Coverage accumulated at block level (hit at low cost) is structurally reusable at subsystem;
  teams spend integration resources finding integration bugs, not re-verifying block behavior.

---

## 6. Extending to Portable Stimulus (PSS) (~1 page)

### 6.1 PSS and the Need for Well-Defined Interfaces

- PSS (Portable Test and Stimulus Standard, IEEE 1647) describes verification intent as an
  action graph that can be compiled to any execution environment.
- PSS actions call out to "platform" functionality via `function import` declarations — the PSS
  side specifies the signature; the platform side (C, SV, Python) provides the body.
- Without ml-hpi, teams write `function import` declarations by hand, then write matching
  DPI/FFI implementations by hand, then write matching PSS exec-body calls by hand — three
  synchronized artefacts per function per platform.

### 6.2 ml-hpi as the PSS ↔ Platform Bridge

- The user defines verification intent in PSS: actions that call `dma.do_transfer(...)`,
  navigate `soc.dmas[2]`, and compose into larger scenarios. The PSS model is written in
  terms of `DmaIf` — a component tree of HPI interfaces, just as it would be in SV.
- Because the ml-hpi semantic model is shared, the PSS HPI declaration can be *derived*
  from the SV `interface class` that the team already maintains, keeping the two in sync
  automatically.
- At execution time, the PSS runtime resolves each call through whatever platform
  implementation is registered — UVM in RTL simulation, a C++ fast model in a virtual
  platform, a Python cocotb driver in an emulation harness — without any change to the
  PSS model itself.
- The `target: true` / `blocking: true` attributes map to PSS target-time exec body
  semantics; `blocking: false` / `solve: true` maps to solve-time operations. These
  attributes are already present in the shared semantic model, so no additional annotation
  is needed when generating PSS stubs.

### 6.3 The Practical Workflow: SV → IDL → PSS (IDL as Hidden Intermediary)

- In practice, a team already has their DMA interface expressed as a SystemVerilog
  `interface class` — the artifact they maintain and review.
- The ml-hpi IDL is *derived* from that SV source automatically as part of the build flow;
  it is an intermediate representation the user never directly authors or edits.
- From the derived IDL, the toolchain generates PSS `function import` declarations and the
  corresponding platform-side binding stubs in one step.
- The visible workflow is simply: *write SV interface → get PSS stubs for free*.
- The IDL is the hidden connective tissue that makes this possible without any bespoke
  SV-to-PSS translator; the same derivation + generation pipeline that produces C++ and
  Python bindings also produces the PSS infrastructure at no extra cost.

### 6.3 Reusing Existing Implementations

- The DmaIf SystemVerilog implementation from Section 5.2 (block level) is reused without
  change as the PSS target-time platform for a PSS-driven test in the same environment.
- The DmaIf C++ implementation from the virtual platform likewise serves as the PSS
  target-time platform in a standalone PSS simulation.
- The PSS model itself never changes; only the registered `DmaIf` implementation differs
  across execution contexts — exactly the same portability story as plain test reuse.

### 6.4 Hierarchy in PSS

- PSS scenarios often model multi-instance IP naturally (e.g., allocate transfers across
  any available DMA channel).
- ml-hpi's interface-path mechanism gives PSS actions a way to reference a specific DMA
  instance without encoding instance topology in the PSS model itself.
- The root handle + path integer passed to each PSS action's exec body is resolved by the
  platform to the correct sub-interface object at runtime.

---

## 7. Architecture Summary (~0.5 page)

- **Schema**: YAML/JSON declaration of interfaces, methods, types, hierarchy, and per-method
  attributes (blocking, target, solve).
- **Code generators**: Per-language emitters produce abstract interface declarations
  (SV `interface class`, C++ pure-virtual class, Python ABC, PSS `function import`) and
  glue/binding code (DPI exports, ctypes wrappers, FFI stubs).
- **Runtime path table**: Generated registration classes resolve integer paths to concrete
  sub-interface pointers at O(1) cost, bridging the flat DPI/FFI boundary to the OO interface
  model.
- **No runtime library dependency**: Generated code uses only standard language features and
  the platform's own FFI; no ml-hpi runtime is required on the target.

---

## 8. Conclusion (~0.25 page)

- Verification teams lose enormous effort duplicating interface definitions and adapting tests
  across integration levels.
- ml-hpi addresses this by providing a single declarative source of truth for hierarchical
  verification APIs, generating correct, idiomatic bindings for every language in the toolchain.
- By capturing verification-specific attributes (blocking, target/solve) and the hierarchical
  context of real designs (multi-instance sub-interfaces, interface paths), ml-hpi produces
  interfaces that are genuinely usable — not just theoretically portable.
- Existing test assets written against an ml-hpi interface flow freely from block to subsystem
  to SoC, and the same interface spec doubles as the PSS ↔ platform bridge, giving teams PSS
  portability without a second set of hand-written stubs.

---

## Appendix / Figures (as needed)

- **Figure 1**: Block → Subsystem → SoC test reuse diagram showing DmaIf implementations at
  each level, single test sequence at top.
- **Figure 2**: ml-hpi toolchain: YAML spec → code generators → per-language bindings.
- **Figure 3**: PSS action graph calling DmaIf stubs; same stubs resolved to SV, C++, or
  Python implementations at execution time.
- **Table 1**: Language × methodology matrix showing which interface mechanism ml-hpi generates
  for each combination.
