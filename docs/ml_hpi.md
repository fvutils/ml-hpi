
# Multi-Language Hierarchical Programming Interface

In the functional verification space, multi-environment and multi-language
integration (eg SystemVerilog and C++) is performed via programming
interfaces defined by the language standard (eg VPI, DPI, PSS function imports). 
All of these APIs leverage the C ABI for portability. The challenge
is that UVM and PSS environments are hierarchical, and leverage 
object-oriented component hierarchies that group state (data) with 
operations. In contrast, existing programming interfaces are flat and
don't provide good support for capturing context. In addition, verification
environments often need to qualify function capabilities -- PSS 
solve vs target ; SystemVerilog blocking vs non-blocking. These
distinctions often drive mapping decisions.

The Multi-Language Hierarchical Programming Interface (ml-hpi) defines
a JSON schema for capturing hierarchical APIs, per-language bindings,
and tools and language integrations.

ml-hpi is purely focused on methods, in contrast to other specifications,
such as protobuf, that focus on data.

## ml-hpi Schema

ml-hpi defines interface types, each with methods and sub-interface 'fields'
that either point to an interface or an array of interfaces of the same type.
For example:

```yaml
ml-hpi:
  interfaces:
  - name: pkg.MyIf1
    methods:
    - name: foo
      rtype: void
      params:
      - name: abc
        type: int
      - name: def
        type: int
      attr:
      - solve: true
      - target: false
      - blocking: false
  - name: pkg.MyIf2
    # Could be methods here too
    members:
    - name: dma0
      kind: field
      type: pkg.MyIf1
    - name: dmas
      kind: array
      type: pkg.MyIf1
```

The goal is that each language sees a hierarchical (object-oriented) interface
that makes sense in the context of that language. For example, these interfaces
would look like this in SystemVerilog:

```verilog
package pkg;
  interface class MyIf1;
    pure virtual function void foo(int abc, int def);
  endclass

  interface class MyIf2;
    pure virtual function MyIf1 dma0();
    pure virtual function MyIf1 dmas_at(int idx);
    pure virtual function int dmas_size();
  endclass
endpackage
```

Note how methods are used to represent member fields and arrays to keep the
API purely functional.

Likewise, a C++ representation is:

```cpp
namespace pkg {
  class MyIf1 {
    virtual void foo(int abc, int def) = 0;
  };

  class MyIf2 {
    virtual MyIf1 *dma0() = 0;
    virtual MyIf1 *dmas_at(int idx) = 0;
    virtual int dmas_size() = 0;
  };
}
```

### Interface Inheritance

An interface may extend a single base interface using the `extends` field. The
derived interface inherits all methods and members of the base.

```yaml
ml-hpi:
  interfaces:
  - name: pkg.BaseIf
    methods:
    - name: init
      rtype: void
  - name: pkg.DerivedIf
    extends: pkg.BaseIf
    methods:
    - name: configure
      rtype: void
      params:
      - name: mode
        type: uint32
```

This maps to single-inheritance abstract classes in each target language:

```verilog
package pkg;
  interface class BaseIf;
    pure virtual function void init();
  endclass

  interface class DerivedIf extends BaseIf;
    pure virtual function void configure(int unsigned mode);
  endclass
endpackage
```

```cpp
namespace pkg {
  class BaseIf {
    virtual void init() = 0;
  };

  class DerivedIf : public virtual BaseIf {
    virtual void configure(uint32_t mode) = 0;
  };
}
```

Multiple inheritance is not supported; each interface may have at most one `extends` entry.

The key idea is that any environment can export, or expose, an API of this form
by providing an implementation of the proper language-specific interface classes. 
Because the classes are always pure virtual, these can be grafted onto existing
class hierarchies. A cross-language connection can be made simply by implementing
the shared interface in the client/requiring environment that calls that same 
interface implemented in the target/providing environment.

The following languages must be supported as both client and target environments:
- C++
- C
- Python
- SystemVerilog
- PSS


## Type System

ml-hpi defines a fixed set of built-in scalar types for method parameters and return values. All scalar types map to well-defined, aligned types in each target language. Interface types (defined in the `interfaces` section) are used only as sub-interface members, not as parameter or return types.

### Built-in Scalar Types

| ml-hpi type | Description |
|---|---|
| `void` | No value; valid as a return type only |
| `bool` | Boolean (true/false) |
| `int8` / `uint8` | 8-bit signed / unsigned integer |
| `int16` / `uint16` | 16-bit signed / unsigned integer |
| `int32` / `uint32` | 32-bit signed / unsigned integer |
| `int64` / `uint64` | 64-bit signed / unsigned integer |
| `addr` | Platform-width physical address; resolves to `addr32` or `addr64` at code-gen time |
| `addr32` | 32-bit physical address; semantically distinct from `uint32` |
| `addr64` | 64-bit physical address; semantically distinct from `uint64` |
| `uintptr` | Opaque pointer-sized unsigned integer (`uintptr_t`); platform-width |

The `addr32` / `addr64` types are kept distinct from plain integer types so that language bindings and tools can apply address-specific handling (e.g., byte-enable generation, address space qualification, PSS `addr_t` mapping).

The `uintptr` type is intended for passing opaque handles across language boundaries where the receiving side treats the value as a pointer; the actual width is platform-dependent (32 or 64 bits).

### Language Type Mappings

| ml-hpi | C | C++ | Python (plain) | SystemVerilog | PSS |
|---|---|---|---|---|---|
| `void` | `void` | `void` | `None` | `void` | `void` |
| `bool` | `bool` | `bool` | `bool` | `bit` | `bool` |
| `int8` | `int8_t` | `int8_t` | `int` | `byte` | `int<8>` |
| `uint8` | `uint8_t` | `uint8_t` | `int` | `byte unsigned` | `bit<8>` |
| `int16` | `int16_t` | `int16_t` | `int` | `shortint` | `int<16>` |
| `uint16` | `uint16_t` | `uint16_t` | `int` | `shortint unsigned` | `bit<16>` |
| `int32` | `int32_t` | `int32_t` | `int` | `int` | `int<32>` |
| `uint32` | `uint32_t` | `uint32_t` | `int` | `int unsigned` | `bit<32>` |
| `int64` | `int64_t` | `int64_t` | `int` | `longint` | `int<64>` |
| `uint64` | `uint64_t` | `uint64_t` | `int` | `longint unsigned` | `bit<64>` |
| `addr` | `uint32_t`/`uint64_t` | `uint32_t`/`uint64_t` | `int` | `int unsigned`/`longint unsigned` | `addr_t` |
| `addr32` | `uint32_t` | `uint32_t` | `int` | `int unsigned` | `addr_t` (32-bit) |
| `addr64` | `uint64_t` | `uint64_t` | `int` | `longint unsigned` | `addr_t` (64-bit) |
| `uintptr` | `uintptr_t` | `uintptr_t` | `int` | `chandle` | `chandle` |

> **Note:** `addr` resolves to `addr32` or `addr64` based on the platform address width configured at code-generation time. `uintptr` maps to `chandle` in SystemVerilog and PSS — the standard opaque-handle type in both languages for holding C pointers — and to `uintptr_t` in C and C++. See the [Python language mapping](#python) for `ctypes` and `Annotated[int, N]` alternatives.

### Schema File

The formal JSON Schema for ml-hpi YAML documents is defined in [`schema/ml-hpi.schema.json`](../schema/ml-hpi.schema.json).

### Interface Path

An **interface path** is a single non-negative integer that uniquely identifies any interface instance within a root interface hierarchy. Paths are a **runtime** concept — they are not part of the IDL schema, and they do not need to be computed until an implementation is created and registered. At that point every node in the hierarchy must be assigned a path so that a caller can navigate from root to any sub-interface using a single opaque integer handle.

#### Path Assignment Rules

Paths are assigned depth-first, left-to-right (in declaration order), using the following recursive size rules:

| Node kind | Size (slots) | Path of node |
|---|---|---|
| Leaf interface (no sub-interface members) | 1 | Cumulative offset of preceding siblings |
| `field` member of type T | `size(T)` | Cumulative offset of preceding members |
| `array` member of element type T | 1 + `n × size(T)` | 1 base-slot, then element `[i]` at `base + 1 + i × size(T)` |

A "leaf" interface is one whose `members` list is empty (i.e. it has only methods). Methods do not consume path slots — only sub-interface members do.

The **root interface** itself is not assigned a path; the caller holds it directly. Only its *children* are addressed via path.

#### Worked Example

Using the schema example from the Language Mappings section (`BusIf` with a `regs` field and a `ports` array, both of type `RegIf`):

```
RegIf  → leaf interface, no sub-interface members → size = 1

BusIf layout:
  regs         field, type RegIf (size 1)  → path 0
  ports        array, type RegIf (size 1)
    ports base                             → path 1  (array base-slot)
    ports[0]                               → path 2
    ports[1]                               → path 3
    ports[2]                               → path 4
    ports[k]                               → path 1 + 1 + k = 2 + k
```

The original terse formulation "dmas[2] is 4 (1 for dma0 + 3 for dmas[2])" decomposes as:

- **1 for dma0**: `regs`/`dma0` is a `field` of type `RegIf` (size 1), so it consumes 1 slot (path 0) and the array base begins at offset 1.
- **3 for dmas[2]**: array base-slot (path 1) + index 2 × size(RegIf) = 1 + 2 = 3 slots into the array section → path 4.

#### Nested Composite Example

```
MemCtrlIf members:
  dma0     field, type BusIf (size = 1 + 1 + 1 + ... = see below)
  uart     field, type BusIf

size(BusIf) = size(regs) + 1(array base) + size(ports[0..n-1])
            = 1 + 1 + n×1   (for n array elements at runtime)
```

Because array size is dynamic, the **total size of a composite interface containing arrays can only be determined at runtime**, once the number of array elements is known. This is why path assignment happens when constructing the implementation object, not at code-generation time.

#### Navigation Algorithm

Given a root interface handle and a path integer `p`, an implementation navigates as follows:

```
navigate(root, p):
  remaining = p
  for each member m in declaration order:
    if m is a field:
      if remaining < size(m.type):
        return navigate(root.m(), remaining)
      remaining -= size(m.type)
    if m is an array:
      remaining -= 1                          # skip array base-slot
      element_size = size(m.element_type)
      idx = remaining / element_size
      offset = remaining % element_size
      if offset == 0:
        return root.m_at(idx)
      return navigate(root.m_at(idx), offset - 1 ... )
```

#### Implementation Use

When a language binding creates a concrete implementation of a root interface, it typically:

1. **Allocates a flat array** of interface pointers sized to the total path space.
2. **Traverses the hierarchy** depth-first, populating each slot with a pointer to the corresponding sub-interface object.
3. **Stores the array** alongside the root handle so that any path lookup is an O(1) index into the array.

The C binding, for example, can store this as:

```c
typedef struct {
    pkg_BusIf_t  root;         /* the root interface struct */
    void        *path_table[]; /* flat array, indexed by path */
} pkg_BusIf_impl_t;
```

In Python and C++ the same concept applies using a `list` or `std::vector<void*>` respectively. The implementation populates the table once during construction; callers then use a path integer to retrieve the right sub-interface without re-traversing the tree.


## Language Mappings

All five languages are supported as both **client** (caller) and **target** (implementor) environments. The sections below specify how each ml-hpi construct maps to language-specific idioms. The worked examples all use the following interface definition as a reference:

```yaml
ml-hpi:
  interfaces:
  - name: pkg.RegIf
    methods:
    - name: write32
      rtype: void
      params:
      - name: addr
        type: addr
      - name: data
        type: uint32
      attr:
      - target: true
      - blocking: true
    - name: read32
      rtype: uint32
      params:
      - name: addr
        type: addr
      attr:
      - target: true
      - blocking: true
  - name: pkg.BusIf
    members:
    - name: regs
      kind: field
      type: pkg.RegIf
    - name: ports
      kind: array
      type: pkg.RegIf
  - name: pkg.ExtRegIf
    extends: pkg.RegIf
    methods:
    - name: reset
      rtype: void
      attr:
      - target: true
      - blocking: false
```

---

### SystemVerilog

#### Interface Definition

ml-hpi interfaces map to `interface class` declarations inside a `package` named after the ml-hpi package prefix. Interface classes carry no state; all methods are `pure virtual`.

#### Method Mapping

| Method attribute | SV construct | Notes |
|---|---|---|
| `blocking: false` | `pure virtual function` | Returns value directly |
| `blocking: true`, `rtype: void` | `pure virtual task` | Task with no output args |
| `blocking: true`, `rtype: T` | `pure virtual task` | Non-void return becomes `output T rval` as the **first** parameter |

#### Member Mapping

| Member kind | SV construct |
|---|---|
| `field` | `pure virtual function IfType name()` |
| `array` | `pure virtual function IfType name_at(int idx)` + `pure virtual function int name_size()` |

#### Inheritance

```verilog
interface class DerivedIf extends BaseIf;
```

#### Example

```verilog
package pkg;

  interface class RegIf;
    // blocking task, non-void return → output rval first
    pure virtual task write32(input longint unsigned addr, input int unsigned data);
    pure virtual task read32(output int unsigned rval, input longint unsigned addr);
  endclass

  interface class BusIf;
    pure virtual function RegIf regs();            // field
    pure virtual function RegIf ports_at(int idx); // array
    pure virtual function int   ports_size();
  endclass

  interface class ExtRegIf extends RegIf;
    pure virtual function void reset();            // non-blocking
  endclass

endpackage
```

### As a C-callable target environment

When SystemVerilog is the **target** (implementor) and C/C++ is the **client** (caller), the DPI export/import mechanism bridges the two environments. Because DPI is flat, the hierarchical interface structure is encoded in two extra arguments prepended to every exported function: a **root instance ID** and an **interface path**.

#### Overview

```
C caller                                   SystemVerilog target
---------                                  ----------------------
  pkg_RegIf_write32(root, path, ...) → export dispatches via path table
                                           → forks task (blocking method)
  pkg_RegIf_write32_complete(cb,...) ← import called on task completion
```

Registration is a pure SV concern. A generated **Root class** per interface type owns the instance registry. The user calls `BusIfRoot::register(impl)` from their testbench and receives a root_id, which they pass to C through whatever mechanism suits their flow (plusarg, VPI, a user-written DPI export, etc.).

#### Naming Convention

All generated DPI identifiers follow the pattern:

| Purpose | Name pattern | DPI direction |
|---|---|---|
| Method call (non-blocking) | `{pkg}_{IfName}_{method}` | `export` (SV provides) |
| Method call (blocking) | `{pkg}_{IfName}_{method}` | `export` (SV provides) |
| Blocking completion | `{pkg}_{IfName}_{method}_complete` | `import` (C provides) |

Package dots are replaced with underscores: `pkg.sub` → `pkg_sub_...`.

Root registration has no DPI identifier — it is handled entirely within SV.

#### The Root Class

For each interface type that may serve as a root, a `{IfName}Root` class is generated. It carries a static registry mapping integer IDs to interface instances and provides a single static method:

```systemverilog
class BusIfRoot;

  // Static registry: root_id → implementation handle
  static pkg::BusIf __registry[int];
  static int        __next_id = 0;

  // Register an implementation; returns a root_id for use by C callers
  static function int register(pkg::BusIf impl);
    int id = __next_id++;
    __registry[id] = impl;
    return id;
  endfunction

  // Internal: look up a registered instance
  static function pkg::BusIf get(int root_id);
    return __registry[root_id];
  endfunction

endclass
```

The user instantiates their concrete implementation class (which implements `pkg::BusIf`) and calls `BusIfRoot::register()` from an `initial` block:

```systemverilog
initial begin
  automatic my_bus_impl impl = new();
  automatic int root_id = BusIfRoot::register(impl);
  // Pass root_id to C — user chooses how (plusarg, VPI, user DPI export, etc.)
  $display("bus root_id = %0d", root_id);
end
```

`BusIfRoot` has no inheritance relationship with the interface class itself; it is a standalone utility class that only holds the registry.

#### Function Arguments

Every DPI export takes `root_id` and `path` as its first two parameters, followed by method parameters in declaration order. For blocking methods a `chandle cb` completion token is appended as the last parameter.

```
// Non-blocking:
export "DPI-C" function {pkg}_{If}_{method};
function automatic {rtype} {pkg}_{If}_{method}(
    int root_id,
    int path,
    {param0_type} {param0},
    ...
);

// Blocking:
export "DPI-C" function {pkg}_{If}_{method};
function automatic void {pkg}_{If}_{method}(
    int root_id,
    int path,
    {param0_type} {param0},
    ...,
    chandle cb      // completion token passed back to C on finish
);
```

Blocking DPI exports are always declared as `function` (not `task`) so that they return immediately to C — the actual task is forked internally.

#### Blocking Completion Imports

For each blocking method, C provides an import that SV calls when the forked task finishes:

```c
// void return:
void pkg_RegIf_write32_complete(void *cb);

// non-void return — result passed as final argument:
void pkg_RegIf_read32_complete(void *cb, uint32_t rval);
```

```systemverilog
// Generated imports
import "DPI-C" function void pkg_RegIf_write32_complete(chandle cb);
import "DPI-C" function void pkg_RegIf_read32_complete(chandle cb, int unsigned rval);
```

#### Navigation: Root ID + Path → Interface Instance

The generated navigation function looks up the root instance via `BusIfRoot::get()` and resolves the interface path depth-first.

```systemverilog
// SV-side generated navigation helper for pkg::BusIf → pkg::RegIf
function automatic pkg::RegIf navigate_BusIf_to_RegIf(int root_id, int path);
  automatic pkg::BusIf root = BusIfRoot::get(root_id);
  if (path == 0) return root.regs();   // path 0 → regs field (size 1)
  path -= 1; // consumed regs
  path -= 1; // consumed array base-slot
  return root.ports_at(path);          // remaining path = array index
endfunction
```

For deeper hierarchies the navigate function recurses into sub-interface roots in declaration order.

#### Complete Generated Example

Using the `pkg.RegIf` / `pkg.BusIf` schema from the Language Mappings reference:

```systemverilog
// ---------------------------------------------------------------
// Generated Root class for pkg::BusIf
// ---------------------------------------------------------------
class pkg_BusIfRoot;

  static pkg::BusIf __registry[int];
  static int        __next_id = 0;

  static function int register(pkg::BusIf impl);
    int id        = __next_id++;
    __registry[id] = impl;
    return id;
  endfunction

  static function pkg::BusIf get(int root_id);
    return __registry[root_id];
  endfunction

endclass

// ---------------------------------------------------------------
// Generated DPI package for pkg
// ---------------------------------------------------------------
package pkg_dpi;

  // Imports — C provides these (one per blocking method)
  import "DPI-C" function void pkg_RegIf_write32_complete(chandle cb);
  import "DPI-C" function void pkg_RegIf_read32_complete(chandle cb,
                                                         int unsigned rval);

  // Navigation helper
  function automatic pkg::RegIf navigate(int root_id, int path);
    automatic pkg::BusIf root = pkg_BusIfRoot::get(root_id);
    if (path == 0) return root.regs();
    path -= 1;
    path -= 1;
    return root.ports_at(path);
  endfunction

  // Non-blocking: ExtRegIf::reset
  export "DPI-C" function pkg_ExtRegIf_reset;
  function automatic void pkg_ExtRegIf_reset(int root_id, int path);
    automatic pkg::ExtRegIf iface = pkg::ExtRegIf'(navigate(root_id, path));
    iface.reset();
  endfunction

  // Blocking: RegIf::write32 (rtype void)
  export "DPI-C" function pkg_RegIf_write32;
  function automatic void pkg_RegIf_write32(
      int root_id, int path,
      longint unsigned addr,
      int unsigned    data,
      chandle         cb
  );
    automatic pkg::RegIf iface = navigate(root_id, path);
    fork
      begin
        iface.write32(addr, data);
        pkg_RegIf_write32_complete(cb);
      end
    join_none
  endfunction

  // Blocking: RegIf::read32 (rtype uint32)
  export "DPI-C" function pkg_RegIf_read32;
  function automatic void pkg_RegIf_read32(
      int root_id, int path,
      longint unsigned addr,
      chandle          cb
  );
    automatic pkg::RegIf iface = navigate(root_id, path);
    fork
      begin
        automatic int unsigned rval;
        iface.read32(rval, addr);
        pkg_RegIf_read32_complete(cb, rval);
      end
    join_none
  endfunction

endpackage

// ---------------------------------------------------------------
// User testbench: instantiate impl and register it
// ---------------------------------------------------------------
module tb;
  initial begin
    automatic my_bus_impl impl = new();
    automatic int root_id = pkg_BusIfRoot::register(impl);
    // hand root_id to C — e.g. via a user-written DPI export or plusarg
    $display("pkg::BusIf root_id = %0d", root_id);
  end
endmodule
```

#### C-Side Usage

C receives the root_id out-of-band (the mechanism is user-defined) and then calls the DPI exports directly:

```c
#include <stdint.h>

/* Provided by the generated C header (declarations only — SV exports these) */
extern void pkg_RegIf_write32(int root_id, int path,
                               uint64_t addr, uint32_t data, void *cb);
extern void pkg_RegIf_read32 (int root_id, int path,
                               uint64_t addr, void *cb);

/* State for a pending async call */
typedef struct { int done; uint32_t result; } pending_t;

/* Completion imports — C provides, SV calls when tasks finish */
void pkg_RegIf_write32_complete(void *cb) {
    ((pending_t *)cb)->done = 1;
}
void pkg_RegIf_read32_complete(void *cb, uint32_t rval) {
    pending_t *p = (pending_t *)cb;
    p->result = rval;
    p->done   = 1;
}

/* Example: synchronous-style blocking read using spin-wait */
uint32_t bus_read32(int root_id, uint64_t addr) {
    pending_t p = {0, 0};
    pkg_RegIf_read32(root_id, /*path=regs*/ 0, addr, &p);
    while (!p.done) { /* yield to scheduler */ }
    return p.result;
}
```

#### Summary of DPI Constraints

| Constraint | Consequence |
|---|---|
| DPI exports cannot be tasks at the C boundary | Blocking methods always export as `function void`; tasks are forked internally |
| DPI has no OOP | Hierarchy encoded via `root_id` + `path` arguments |
| Registration is SV-only | No C import for registration; `{IfName}Root::register()` is a pure SV static method |
| `chandle` is opaque | C can pass any pointer as `cb`; SV must not dereference it |
| `fork join_none` return timing | C receives control immediately; completion arrives asynchronously via import |
| Thread safety | SV is single-threaded within a time-step; concurrent blocking calls are serialized by the simulator scheduler |


### C++

#### Interface Definition

ml-hpi interfaces map to C++ abstract classes (all methods `= 0`) inside a namespace corresponding to the package prefix. Headers should include `<cstdint>` and `<functional>`.

#### Method Mapping

| Method attribute | C++ form | Notes |
|---|---|---|
| `blocking: false` | `virtual rtype name(params) = 0` | Returns value directly |
| `blocking: true` (sync) | `virtual rtype name(params) = 0` | Blocks internally; implementation may use pthread, coroutine, etc. |
| `blocking: true` (async) | `virtual void name(params, std::function<void(rtype)> cb) = 0` | Callback-based; return value delivered via `cb` |

Both sync and async blocking forms may be generated; the choice is a code-generation policy. The async form is omitted when `rtype` is `void`.

#### Member Mapping

| Member kind | C++ construct |
|---|---|
| `field` | `virtual IfType *name() = 0` |
| `array` | `virtual IfType *name_at(int idx) = 0` + `virtual int name_size() = 0` |

#### Inheritance

```cpp
class DerivedIf : public virtual BaseIf { ... };
```

Virtual inheritance is used to support diamond-safe composition.

#### Example

```cpp
#include <cstdint>
#include <functional>

namespace pkg {

  class RegIf {
  public:
    virtual ~RegIf() = default;
    // blocking – sync form
    virtual void     write32(uintptr_t addr, uint32_t data) = 0;
    virtual uint32_t read32(uintptr_t addr) = 0;
    // blocking – async form
    virtual void     write32(uintptr_t addr, uint32_t data,
                             std::function<void()> cb) = 0;
    virtual void     read32(uintptr_t addr,
                            std::function<void(uint32_t)> cb) = 0;
  };

  class BusIf {
  public:
    virtual ~BusIf() = default;
    virtual RegIf *regs() = 0;                  // field
    virtual RegIf *ports_at(int idx) = 0;       // array
    virtual int    ports_size() = 0;
  };

  class ExtRegIf : public virtual RegIf {
  public:
    virtual void reset() = 0;                   // non-blocking
  };

} // namespace pkg
```

---

### C

#### Interface Definition

ml-hpi interfaces map to C structs containing function pointers. Each function pointer takes `void *self` as its first argument to carry the implementation context. Sub-interface `field` members are direct struct pointers; `array` members use `_at` / `_size` function pointers. Type names follow the pattern `{pkg}_{Name}_t` (package dots replaced by underscores).

#### Method Mapping

All methods become function pointers with `void *self` as the first parameter:

```c
rtype (*method_name)(void *self, params...);
```

Blocking methods block internally; there is no separate async form in the C binding.

#### Member Mapping

| Member kind | C struct member |
|---|---|
| `field` | `pkg_IfType_t *name;` (direct pointer, set at initialisation time) |
| `array` | `pkg_IfType_t *(*name_at)(void *self, int idx);` + `int (*name_size)(void *self);` |

#### Inheritance

The derived struct embeds the base struct as its **first** member, enabling safe upcasting via pointer cast:

```c
typedef struct pkg_DerivedIf_s {
    pkg_BaseIf_t base;   /* MUST be first */
    ...
} pkg_DerivedIf_t;
```

#### Example

```c
#include <stdint.h>

/* Forward declarations */
typedef struct pkg_RegIf_s    pkg_RegIf_t;
typedef struct pkg_BusIf_s    pkg_BusIf_t;
typedef struct pkg_ExtRegIf_s pkg_ExtRegIf_t;

typedef struct pkg_RegIf_s {
    void     (*write32)(void *self, uintptr_t addr, uint32_t data);
    uint32_t (*read32) (void *self, uintptr_t addr);
} pkg_RegIf_t;

typedef struct pkg_BusIf_s {
    pkg_RegIf_t  *regs;                                    /* field  */
    pkg_RegIf_t *(*ports_at)  (void *self, int idx);       /* array  */
    int          (*ports_size)(void *self);
} pkg_BusIf_t;

typedef struct pkg_ExtRegIf_s {
    pkg_RegIf_t base;                          /* MUST be first */
    void (*reset)(void *self);
} pkg_ExtRegIf_t;
```

---

### Python

#### Interface Definition

ml-hpi interfaces map to `typing.Protocol` classes. Protocols use structural subtyping — any class implementing the required methods satisfies the interface without explicit subclassing.

Three type representation styles are supported for parameters and return values:

| Style | When to use |
|---|---|
| **Plain** (`int`, `bool`) | Simplest; no width or signedness information |
| **`ctypes`** (`ctypes.c_int32`, etc.) | When the implementation interacts with ctypes-based FFI |
| **`Annotated`** (`Annotated[int, N]`) | Lightweight width hint usable by code-generation tools |

For the `Annotated` style, the metadata integer `N` is the bit width. Signedness is not encoded in the annotation itself — use named type aliases (e.g. `Int32`, `UInt32`) to preserve that distinction. Both resolve to the same `Annotated[int, N]` at runtime.

#### Type Mapping

| ml-hpi | ctypes | Annotated | Plain |
|---|---|---|---|
| `void` | — | — | `None` |
| `bool` | `ctypes.c_bool` | `bool` | `bool` |
| `int8` | `ctypes.c_int8` | `Annotated[int, 8]` | `int` |
| `uint8` | `ctypes.c_uint8` | `Annotated[int, 8]` | `int` |
| `int16` | `ctypes.c_int16` | `Annotated[int, 16]` | `int` |
| `uint16` | `ctypes.c_uint16` | `Annotated[int, 16]` | `int` |
| `int32` | `ctypes.c_int32` | `Annotated[int, 32]` | `int` |
| `uint32` | `ctypes.c_uint32` | `Annotated[int, 32]` | `int` |
| `int64` | `ctypes.c_int64` | `Annotated[int, 64]` | `int` |
| `uint64` | `ctypes.c_uint64` | `Annotated[int, 64]` | `int` |
| `addr` | `ctypes.c_uint32` / `ctypes.c_uint64` | `Annotated[int, 32]` / `Annotated[int, 64]` | `int` |
| `addr32` | `ctypes.c_uint32` | `Annotated[int, 32]` | `int` |
| `addr64` | `ctypes.c_uint64` | `Annotated[int, 64]` | `int` |
| `uintptr` | `ctypes.c_void_p` | `ctypes.c_void_p` | `int` |

> **Note:** `addr` resolves at code-generation time based on platform address width. `uintptr` uses `ctypes.c_void_p` in both ctypes and Annotated styles, as it is an opaque pointer — not a general-purpose integer.

#### Method Mapping

| Method attribute | Python form |
|---|---|
| `blocking: false` | `def name(self, ...) -> rtype: ...` |
| `blocking: true` | `async def name(self, ...) -> rtype: ...` |

#### Member Mapping

| Member kind | Python construct |
|---|---|
| `field` | `def name(self) -> IfType: ...` |
| `array` | `def name_at(self, idx: int) -> IfType: ...` + `def name_size(self) -> int: ...` |

#### Inheritance

```python
class DerivedIf(BaseIf, typing.Protocol):
    ...
```

#### Example

All three styles generate equivalent Protocols. The `Annotated` aliases can be shared from a generated `ml_hpi_types` module.

**Plain style:**

```python
from __future__ import annotations
import typing


class RegIf(typing.Protocol):
    async def write32(self, addr: int, data: int) -> None: ...
    async def read32(self, addr: int) -> int: ...


class BusIf(typing.Protocol):
    def regs(self) -> RegIf: ...
    def ports_at(self, idx: int) -> RegIf: ...
    def ports_size(self) -> int: ...


class ExtRegIf(RegIf, typing.Protocol):
    def reset(self) -> None: ...
```

**`Annotated` style:**

```python
from __future__ import annotations
import typing
from typing import Annotated

# Named aliases — same Annotated[int, N] repr, distinct names for signed/unsigned
Addr   = Annotated[int, 64]   # platform-width; 32 on 32-bit targets
UInt32 = Annotated[int, 32]


class RegIf(typing.Protocol):
    async def write32(self, addr: Addr, data: UInt32) -> None: ...
    async def read32(self, addr: Addr) -> UInt32: ...


class BusIf(typing.Protocol):
    def regs(self) -> RegIf: ...
    def ports_at(self, idx: int) -> RegIf: ...
    def ports_size(self) -> int: ...


class ExtRegIf(RegIf, typing.Protocol):
    def reset(self) -> None: ...
```

**`ctypes` style:**

```python
from __future__ import annotations
import ctypes
import typing


class RegIf(typing.Protocol):
    async def write32(self, addr: ctypes.c_uint64, data: ctypes.c_uint32) -> None: ...
    async def read32(self, addr: ctypes.c_uint64) -> ctypes.c_uint32: ...


class BusIf(typing.Protocol):
    def regs(self) -> RegIf: ...
    def ports_at(self, idx: int) -> RegIf: ...
    def ports_size(self) -> int: ...


class ExtRegIf(RegIf, typing.Protocol):
    def reset(self) -> None: ...
```

---

### PSS

#### Interface Definition

ml-hpi interfaces map to PSS `component` types inside a `package`. Sub-interface members are declared as component sub-instances or arrays. Methods are declared as `function` prototypes; the `solve` and `target` attributes determine the execution context in which they may be called.

#### Method Mapping

| Attributes | PSS construct | Notes |
|---|---|---|
| `solve: true, target: false` | `function` | Callable from action solve/pre-solve context |
| `solve: false, target: true` | `target function` | Callable from exec/target context only |
| `solve: true, target: true` | `function` | Callable from both contexts |

#### Member Mapping

| Member kind | PSS construct |
|---|---|
| `field` | Component sub-instance: `pkg::IfType name;` |
| `array` | Component array: `array<pkg::IfType,*> name;` |

#### Inheritance

```pss
component pkg::DerivedIf : pkg::BaseIf {
    ...
};
```

#### Type Notes

- `addr` → `addr_t` (PSS native platform-width address type)
- `addr32` / `addr64` → `addr_t` annotated with explicit width via tool configuration
- `uintptr` → `chandle` (PSS 2.0 opaque handle type)

#### Example

```pss
package pkg;

component RegIf {
    // target:true → exec/target context
    target function void     write32(addr_t addr, bit<32> data);
    target function bit<32>  read32(addr_t addr);
};

component BusIf {
    RegIf          regs;          // field
    array<RegIf,*> ports;         // array
};

component ExtRegIf : RegIf {
    // non-blocking, target context
    target function void reset();
};

endpackage
```

## Comparative Analysis: Existing Tools and Approaches

### Overview

The core problem ml-hpi addresses — a **language-neutral, schema-driven IDL for hierarchical, method-focused cross-language APIs spanning C, C++, Python, SystemVerilog, and PSS** — is not fully solved by any single existing tool. The landscape is covered by several partial solutions, each with significant gaps.

---

### SystemVerilog DPI (Direct Programming Interface)

DPI is the industry-standard mechanism for calling C/C++ from SystemVerilog and vice versa. It is flat (no hierarchy), requires manual binding code, and only bridges SV ↔ C/C++. Python and PSS have no native DPI support. There is no schema or IDL; every interface must be hand-coded. DPI forms the low-level transport layer that higher-level tools build upon.

**Gap vs ml-hpi:** Flat API only, no hierarchy, no PSS, no Python, no schema, no method attributes.

---

### VPI (Verilog Procedural Interface)

VPI provides C-level callback and introspection access to the simulation hierarchy at runtime. It is event-driven and focused on signal-level and hierarchy access rather than method-call APIs. Tools like cocotb use VPI to drive simulation from Python, but at the signal level rather than the interface/method level.

**Gap vs ml-hpi:** Signal-level, not method-API level. No PSS. No schema.

---

### pysv

[pysv](https://github.com/Kuree/pysv) allows Python classes and functions to be compiled (via pybind11) into a shared library and exposed to SystemVerilog as DPI-callable objects. It supports object-oriented Python ↔ SV bindings and preserves class hierarchies. The Python class is the de-facto "schema."

**Gap vs ml-hpi:** Python-only source language (Python is the IDL). No C target. No PSS support. No method attributes (solve/target, blocking/non-blocking). Unidirectional design pattern (Python implements, SV calls).

---

### PyHDL-IF

[PyHDL-IF](https://github.com/fvutils/pyhdl-if) (also from fvutils) is the closest existing tool. It uses Python decorators (`@exp`, `@imp`) to define APIs that are exported to or imported from SystemVerilog, with automatic SV wrapper generation. It supports **bidirectional** calling (Python → SV and SV → Python) and generates hierarchical interface classes. It works at the API/method level rather than the signal level.

**Gap vs ml-hpi:** Python is the IDL (not a language-neutral schema). C is not a supported target language. PSS is not a first-class target. Method attributes specific to PSS (solve/target) and SV (blocking/non-blocking) are not represented. The schema lives in Python source code, making it inaccessible to non-Python tooling.

---

### SWIG (Simplified Wrapper and Interface Generator)

SWIG generates bindings from C/C++ headers to Python, Java, Tcl, and other scripting languages. It handles class hierarchies and inheritance. The SWIG `.i` interface file is a schema of sorts, but is C/C++-centric.

**Gap vs ml-hpi:** No SystemVerilog or PSS support. C/C++ is always the canonical source; other languages are consumers. No method attributes. No EDA-specific concepts.

---

### Apache Thrift / Protocol Buffers / Cap'n Proto

These IDL-based tools define cross-language **data** schemas and RPC interfaces. They generate bindings for many languages (C++, Python, Java, etc.) from a neutral schema. However, they are designed for network/process-boundary communication, focus on serializable data types, and have no concept of EDA languages (SystemVerilog, PSS) or verification-specific method attributes.

**Gap vs ml-hpi:** No SystemVerilog or PSS support. Focused on data serialization rather than in-process method dispatch. IPC/RPC overhead is inappropriate for tight simulation integration. No method attributes for verification semantics.

---

### Comparative Summary

| Feature | DPI | pysv | PyHDL-IF | SWIG | Thrift/Protobuf | **ml-hpi** |
|---|---|---|---|---|---|---|
| Language-neutral schema/IDL | ✗ | ✗ | ✗ | Partial (C-centric) | ✓ | ✓ |
| Hierarchical (OOP) interfaces | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ |
| C++ client & target | ✓ | Partial | Partial | ✓ | ✓ | ✓ |
| C client & target | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ |
| Python client & target | ✗ | Partial | ✓ | ✓ | ✓ | ✓ |
| SystemVerilog client & target | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| PSS client & target | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| PSS solve/target attributes | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| SV blocking/non-blocking attrs | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Method-focused (not data) | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |

---

### Conclusion

No existing tool satisfies all of ml-hpi's requirements. **PyHDL-IF** is the closest in spirit — bidirectional, method-focused, hierarchical, SV+Python — but uses Python source code as its implicit IDL rather than a portable schema, and lacks C and PSS support. **DPI** and **pysv** address subsets of the language matrix. General-purpose IDL tools (SWIG, Thrift, Protobuf) cover more languages but have no EDA language support and no verification-specific method semantics.

ml-hpi's unique contribution is a **language-neutral YAML/JSON schema** that captures hierarchical method interfaces with verification-specific attributes, from which correct per-language bindings can be generated for all five environments (C, C++, Python, SystemVerilog, PSS) as both client and target.

