"""Entry point for `python -m xiaomi_feeder`."""

from __future__ import annotations

import sys
from xiaomi_feeder.cli import main

if __name__ == "__main__":
    sys.exit(main())
