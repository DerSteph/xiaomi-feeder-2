"""Xiaomi Smart Pet Food Feeder 2 (xiaomi.feeder.iv2001) Python Controller & Library."""

from __future__ import annotations

from .client import XiaomiFeeder
from .const import (
    DEFAULT_TIMEOUT,
    MODEL_NAME,
    FeederAIID,
    FeederPIID,
    FeederSIID,
)
from .exceptions import (
    XiaomiFeederAuthError,
    XiaomiFeederConnectionError,
    XiaomiFeederDeviceError,
    XiaomiFeederError,
)
from .models import FeederStatus, ScheduleMeal, SchedulePlan

__version__ = "0.2.0"

__all__ = [
    "XiaomiFeeder",
    "FeederStatus",
    "ScheduleMeal",
    "SchedulePlan",
    "XiaomiFeederError",
    "XiaomiFeederConnectionError",
    "XiaomiFeederDeviceError",
    "XiaomiFeederAuthError",
    "FeederSIID",
    "FeederPIID",
    "FeederAIID",
    "MODEL_NAME",
    "DEFAULT_TIMEOUT",
    "__version__",
]
