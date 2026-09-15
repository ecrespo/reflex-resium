"""Fail if pyproject.toml declares a classifier PyPI would reject.

``twine check`` does not validate classifiers; PyPI does, at upload time.

Usage: ``uv run --locked --only-group dev python scripts/check_classifiers.py``
"""

from __future__ import annotations

import sys
from pathlib import Path

import tomllib
from trove_classifiers import classifiers

pyproject = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())
invalid = [c for c in pyproject["project"].get("classifiers", []) if c not in classifiers]
if invalid:
    sys.exit("Invalid classifiers (not in trove-classifiers):\n" + "\n".join(f"  - {c}" for c in invalid))
print(f"{len(pyproject['project'].get('classifiers', []))} classifiers OK")
