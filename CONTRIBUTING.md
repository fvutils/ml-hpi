# Contributing to ml-hpi

## Running the Test Suite

```bash
python -m pytest tests/unit/ -v
```

The existing end-to-end test (`test_sv_c_path.py`) requires a simulator
(`verilator`, `vcs`, or `vsim`) and is skipped automatically if none is
available.

## Adding a New Language Target

1. **Generator** -- Create `src/ml_hpi/gen/gen_<lang>.py` subclassing
   `Generator`. Implement `generate(outdir) -> list[Path]`.
2. **Type map** -- Add a `<lang>_type()` static method to `Generator` in
   `gen_base.py` covering all ml-hpi scalar types.
3. **Parser** -- Create `src/ml_hpi/parse/parse_<lang>.py` subclassing
   `Parser`. Implement `parse(source) -> MlHpiDoc`.
4. **Reverse type map** -- Add a `<LANG>_TYPE_TO_ML` dict to `parse_base.py`.
5. **Tests** -- Create `tests/unit/test_gen_<lang>.py` and
   `tests/unit/test_parse_<lang>.py`. Add the language to the parametrized
   round-trip test in `tests/unit/test_roundtrip.py`.
6. **CLI** -- Register the generator and parser in `src/ml_hpi/__main__.py`.
7. **Exports** -- Add the new classes to `gen/__init__.py` and
   `parse/__init__.py`.
8. **Documentation** -- Add `docs/bindings/<lang>.rst` and include it in
   `docs/language_bindings.rst`.

## Adding a New Type to the Type System

When adding a new scalar type (e.g. `float32`):

1. Add the type to every forward map in `gen_base.py` (`sv_type`, `c_type`,
   `cpp_type`, `python_type`, `pss_type`).
2. Add the reverse mapping to every reverse map in `parse_base.py`
   (`SV_TYPE_TO_ML`, `CPP_TYPE_TO_ML`, `PSS_TYPE_TO_ML`,
   `PYTHON_CTYPES_TO_ML`).
3. Update `pss_scalar_to_ml()` if the PSS representation requires
   programmatic handling.
4. Add the type to `ALL_TYPES` in `tests/unit/test_type_maps.py`.
5. Update every generator to handle the new type (most will work
   automatically via the type map).
6. Update every parser to handle the new type.
7. Add the type to the mapping tables in `docs/ml_hpi.md` and each
   `docs/bindings/*.rst` page.
8. Update the JSON schema (`schema/ml-hpi.schema.json`) if it enumerates
   valid types.

## Code Style

- Python source uses `from __future__ import annotations` for modern type
  hint syntax.
- Generator and parser modules follow the naming convention `gen_<lang>.py`
  and `parse_<lang>.py`.
- Each generator class is named `Gen<Lang>` (e.g. `GenPSS`, `GenCpp`).
  Each parser class is named `Parse<Lang>` (e.g. `ParseSV`, `ParseCpp`).
- Test files mirror source file names: `test_gen_<lang>.py`,
  `test_parse_<lang>.py`.
- Use `StringIO` for building generated output incrementally.
- Group interfaces by package prefix (`Interface.pkg()`) when generating
  one output file per package.
