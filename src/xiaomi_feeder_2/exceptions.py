"""Custom exceptions for Xiaomi Feeder library."""

from __future__ import annotations


class XiaomiFeederError(Exception):
    """Base exception for Xiaomi Feeder library errors."""


class XiaomiFeederConnectionError(XiaomiFeederError):
    """Raised when network communication with the feeder fails."""


class XiaomiFeederDeviceError(XiaomiFeederError):
    """Raised when the feeder reports an error code or device fault."""


class XiaomiFeederAuthError(XiaomiFeederError):
    """Raised when token authentication fails."""
