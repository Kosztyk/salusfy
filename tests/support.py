"""Load protocol modules without importing Home Assistant's integration setup."""

import importlib
from pathlib import Path
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "salus_under_test"
if PACKAGE not in sys.modules:
    package = ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components/salus")]
    sys.modules[PACKAGE] = package


def load(name):
    return importlib.import_module(f"{PACKAGE}.{name}")
