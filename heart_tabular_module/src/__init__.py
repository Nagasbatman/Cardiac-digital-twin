"""
src — Heart tabular module source package.
Adds the module root (heart_tabular_module/) to sys.path so that
`from common import ...` resolves correctly from any working directory.
"""
import sys
from pathlib import Path

_MODULE_ROOT = str(Path(__file__).resolve().parents[1])
if _MODULE_ROOT not in sys.path:
    sys.path.append(_MODULE_ROOT)
