# ml-hpi

**Multi-Language Hierarchical Programming Interface**

ml-hpi defines a declarative, language-neutral specification for verification
APIs. From a single source — authored in YAML/JSON or derived from an existing
SystemVerilog `interface class` — ml-hpi generates correct, idiomatic bindings
for SystemVerilog, C++, Python, C, and PSS simultaneously.

## Motivation

SoC verification requires the same test intent to run across block-level
simulation, subsystem integration, full-chip simulation, emulation, and silicon
bring-up. Today, teams duplicate effort by rewriting tests for each environment
and each language. ml-hpi solves this by defining a shared interface contract
once: any environment that provides an implementation can run any test written
against that interface, unchanged.

Key features:
- **Hierarchical context** — interfaces are typed objects with field and array
  sub-interface members; tests navigate `chip.uarts_at(1).send(ch)` naturally
- **Blocking semantics** — `blocking`, `target`, and `solve` attributes per
  method; generators emit `task` in SV, `async def` in Python, etc. automatically
- **Derive from SV** — extract the IDL from an existing `interface class`
  hierarchy; C++, Python, C, and PSS bindings are generated with no manual work
- **PSS integration** — the same spec generates PSS `component` and
  `function import` declarations, bridging portable stimulus to existing
  UVM/C++ implementations

## Documentation

[https://fvutils.github.io/ml-hpi](https://fvutils.github.io/ml-hpi)

## License

Apache 2.0 — see [LICENSE](LICENSE).
