"""Data models for Xiaomi Smart Pet Food Feeder 2."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Union


@dataclass
class ScheduleMeal:
    """Represents a scheduled meal configured in internal EEPROM."""
    time: str
    portions: int
    repeat: int
    raw: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SchedulePlan:
    """Represents the complete offline hardware schedule."""
    enabled: bool
    meals: List[ScheduleMeal]
    raw_string: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "meals": [m.to_dict() for m in self.meals],
            "raw_string": self.raw_string,
        }


@dataclass
class FeederStatus:
    """Represents the complete parsed hardware status of the Xiaomi Pet Feeder 2."""
    # Health & Alerts
    device_fault: bool
    food_stuck: bool
    food_out_error: bool
    food_heap_detected: bool

    # Measurements & Weights
    food_level: str
    food_level_raw: Optional[int]
    bowl_food_weight: Optional[int]
    daily_eaten_weight: Optional[int]
    last_meal_intake: Optional[int]
    previous_meal_intake: Optional[int]

    # Operation State
    is_busy: bool
    target_feeding_portions: Optional[int]
    child_lock: bool
    battery_level: Optional[Union[bool, int]]

    # Display & Preferences
    screen_display_mode: Optional[str]
    screen_auto_sleep: Optional[bool]
    screen_progress_display: Optional[bool]
    anti_stacking: Optional[bool]
    grain_compensation: Optional[bool]
    hardware_schedule_active: Optional[bool]
    hardware_schedule_count: Optional[int]
    refill_reminder_enabled: Optional[bool]
    refill_reminder_hours: Optional[int]
    device_timezone_sec: Optional[int]
    dst_active: Optional[bool]
    intake_alarm_enabled: Optional[bool]
    intake_alarm_threshold: Optional[int]

    # Raw property dictionary
    raw_properties: Dict[str, Any]

    @property
    def is_food_low(self) -> bool:
        """Helper to indicate if food hopper level is low or empty."""
        return self.food_level_raw == 1 or self.food_level.startswith("Low")

    @property
    def has_error(self) -> bool:
        """Helper to indicate if any device fault or jamming occurred."""
        return self.device_fault or self.food_stuck or self.food_out_error

    def to_dict(self) -> Dict[str, Any]:
        """Convert status to a serializable dictionary."""
        return asdict(self)
