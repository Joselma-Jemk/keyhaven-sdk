"""Constants vendored into the SDK so it has zero server-side imports.

Mirrors the server's default account id (same value); the SDK defines its own
copy so it can be extracted and published as a fully standalone package.
"""

from __future__ import annotations

DEFAULT_ACCOUNT_ID = "default"
