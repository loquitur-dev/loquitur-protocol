"""Helpers the release-gate tests share."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tool(name: str):
    """tools/<name>.py, loaded by location once and registered in sys.modules under its name.

    Every test module that asks for a tool gets the same module, and so does a tool's own plain
    import of another tool beside it (tools/ on sys.path): a tool already imported that way is
    returned as it is, and one loaded here is what such an import finds.
    """
    path = (ROOT / "tools" / f"{name}.py").resolve()
    loaded = sys.modules.get(name)
    if loaded is not None and getattr(loaded, "__file__", None) and Path(loaded.__file__).resolve() == path:
        return loaded
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def release_gate():
    """tools/check_protocol_release.py."""
    return tool("check_protocol_release")


def release_files():
    """tools/release_files.py."""
    return tool("release_files")
