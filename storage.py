"""Compatibility alias preserving storage paths and patchable module state."""

import sys  # Access the loaded-module registry.
from backend import storage as _storage  # Load the canonical storage module under a private name.

sys.modules[__name__] = _storage  # Share the canonical storage module and its patchable state.
