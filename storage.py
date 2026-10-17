"""Compatibility alias preserving storage paths and patchable module state."""

import sys
from backend import storage as _storage

sys.modules[__name__] = _storage
