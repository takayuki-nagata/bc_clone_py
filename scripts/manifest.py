# MicroPython frozen-module manifest for bc (paths are relative to this file).
for name in ("bc_clone", "bc_eval", "bc_math", "bc_parser", "bc_selftest"):
    module(name + ".py", base_path="..")  # type: ignore[name-defined]  # noqa: F821 - defined by the manifest loader
