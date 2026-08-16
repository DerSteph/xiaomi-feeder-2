"""MIOT specification mappings and constants for xiaomi.feeder.iv2001."""

from __future__ import annotations


class FeederSIID:
    """Service Instance IDs for Xiaomi Feeder 2."""
    DEVICE_INFO = 1
    PET_FEEDER = 2
    PHYSICAL_LOCK = 3
    BATTERY = 4
    CUSTOM = 5


class FeederPIID:
    """Property Instance IDs for Xiaomi Feeder 2."""
    # Device Information (SIID 1)
    MANUFACTURER = 1
    MODEL = 2
    DEVICE_ID = 3
    FIRMWARE_VERSION = 4
    SERIAL_NUMBER = 5

    # Pet Feeder Service (SIID 2)
    DEVICE_FAULT = 1          # 0=No Faults, 1=Faults
    FOOD_LEFT_LEVEL = 6       # 0=Normal, 1=Low (Hopper)
    TARGET_FEEDING_MEASURE = 7 # 0-150 (portions/target)
    FEEDING_MEASURE = 8       # 0-150 (Action input)
    FOOD_STUCK_STATUS = 10    # 0=Normal, 1=Abnormal
    FOOD_OUT_STATUS = 11      # 0=Normal, 1=Abnormal
    ADD_MEAL_NOTIFY = 13      # 0=Normal, 1=Abnormal
    FOOD_HEAP_STATUS = 15     # 0=No, 1=Yes (heap/pile accumulation alert)
    DAILY_EATEN_FOOD = 18     # Daily eaten food measurement (grams)
    DAILY_BOWL_REMAINING = 20 # Daily bowl food remaining (grams)
    REALTIME_BOWL_WEIGHT = 22 # Real-time current food bowl scale weight (grams)
    EATEN_DIFF_PREV_DAY = 23  # Intake difference vs previous day
    FEEDER_STATUS_26 = 26     # 0=Idle, 1=Busy
    PLAN_PROGRESS_PCT = 29    # Feeding plan progress (0-100%)
    FOOD_LEVEL_DETAIL = 31    # 0=Empty, 1=Low, 2=Normal (Hopper)
    FEEDER_STATUS_32 = 32     # 0=Idle, 1=Busy

    # Physical Control Locked (SIID 3)
    PHYSICAL_LOCK = 1         # bool: True/False
    LOCK_MODE = 3             # 0=Off, 1=On (Screen sleep mode)

    # Battery (SIID 4)
    BATTERY_LEVEL = 1         # bool / uint8

    # Custom Specification (SIID 5)
    FEEDING_PROGRAM = 1
    ADD_MEAL_STATE = 3
    PLAN_PROGRESS_DISPLAY = 4
    FOOD_INTAKE_RATE = 5
    FOOD_INTAKE_STATE = 6
    FEEDING_PLAN_SWITCH = 8   # 0=Off, 1=On
    ADD_MEAL_CYCLE = 10
    FEEDING_PROGRESS_LIVE = 11
    GRAIN_COMPENSATION = 12   # 0=Off, 1=On
    PREVENT_STACKING = 14     # 0=Off, 1=On
    DEVICE_TIMEZONE = 17      # Offset in seconds
    SCREEN_DISPLAY = 18       # 0=Left-gram, 1=Eaten-gram, 2=Percentage
    DST_OFFSET = 19           # Daylight saving time active (0=Off, 1=On)


class FeederAIID:
    """Action Instance IDs for Xiaomi Feeder 2."""
    # Pet Feeder Service (SIID 2)
    PET_FOOD_OUT = 1          # In: [Feeding Measure (PIID 8)]
    WEIGH_CALIBRATE = 2       # In: []

    # Custom Specification (SIID 5)
    FOOD_INTAKE_SETTING = 1    # In: [Food Intake Rate (PIID 5), Food Intake State (PIID 6)]
    UPDATE_FEEDING_PROGRAM = 2 # In: [Feeding Program (PIID 1)]
    ADD_MEAL_SETTING = 3       # In: [Add Meal State (PIID 3), Add Meal Cycle (PIID 10)]
    SCHEDULE_DISPLAY_SET = 4   # In: [Plan Process Display (PIID 4)]
    FOOD_INTAKE_LOW_SET = 5    # In: [Status (PIID 9)]
    ADD_MEAL_STATE_SET = 6     # In: [Status (PIID 9)]


DEFAULT_TIMEOUT = 5
DEFAULT_CHUNK_SIZE = 12
MODEL_NAME = "xiaomi.feeder.iv2001"
MIOT_URN = "urn:miot-spec-v2:device:pet-feeder:0000A06C:xiaomi-iv2001:2"
