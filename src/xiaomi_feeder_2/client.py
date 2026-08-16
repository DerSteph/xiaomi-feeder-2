"""Client for controlling Xiaomi Smart Pet Food Feeder 2."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Union
import warnings

# Suppress benign third-party deprecation warnings from python-miio on Python 3.13+
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from miio.device import Device
from miio.exceptions import DeviceException

from .const import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_TIMEOUT,
    FeederAIID,
    FeederPIID,
    FeederSIID,
)
from .exceptions import (
    XiaomiFeederConnectionError,
    XiaomiFeederDeviceError,
    XiaomiFeederError,
)
from .models import FeederStatus, ScheduleMeal, SchedulePlan


class XiaomiFeeder:
    """Controller for the Xiaomi Smart Pet Food Feeder 2 (xiaomi.feeder.iv2001)."""

    def __init__(self, ip: str, token: str, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize the feeder client.

        :param ip: IP address of the feeder on the local network.
        :param token: 32-character hexadecimal token.
        :param timeout: Network timeout in seconds.
        """
        if not ip or not token:
            raise ValueError("Both IP address and token are required to connect to the feeder.")
        if len(token) != 32:
            raise ValueError(f"Invalid token length ({len(token)}). Xiaomi tokens must be 32 characters.")

        self.ip = ip
        self.token = token
        self._timeout = timeout
        self._device = Device(ip=ip, token=token, timeout=timeout)

    # --------------------------------------------------------------------------
    # Low-Level MIOT Primitives
    # --------------------------------------------------------------------------
    def get_properties(self, prop_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Query multiple MIOT properties in batch (automatically chunked to stay within device limits).

        :param prop_requests: List of dicts, e.g. [{"did": "p1", "siid": 2, "piid": 1}]
        :return: List of result dicts containing 'code', 'value', 'siid', 'piid'.
        """
        results: List[Dict[str, Any]] = []
        chunk_size = DEFAULT_CHUNK_SIZE
        try:
            for i in range(0, len(prop_requests), chunk_size):
                chunk = prop_requests[i : i + chunk_size]
                res = self._device.send("get_properties", chunk)
                if isinstance(res, list):
                    results.extend(res)
            return results
        except DeviceException as err:
            raise XiaomiFeederConnectionError(f"Failed to query feeder properties: {err}") from err
        except Exception as err:
            raise XiaomiFeederError(f"Unexpected error querying feeder properties: {err}") from err

    def set_property(self, siid: int, piid: int, value: Any, did: str = "prop") -> Dict[str, Any]:
        """
        Set a single MIOT property.

        :param siid: Service IID
        :param piid: Property IID
        :param value: Value to set
        :param did: Device ID alias
        :return: Result dict with return code
        """
        try:
            res = self._device.send(
                "set_properties", [{"did": did, "siid": siid, "piid": piid, "value": value}]
            )
            if isinstance(res, list) and len(res) > 0:
                item = res[0]
                code = item.get("code", 0)
                if code != 0:
                    raise XiaomiFeederDeviceError(
                        f"Failed to set property (siid={siid}, piid={piid}) to {value}: code {code}"
                    )
                return item
            return {"code": 0, "result": res}
        except XiaomiFeederDeviceError:
            raise
        except DeviceException as err:
            raise XiaomiFeederConnectionError(f"Connection error setting property {siid}.{piid}: {err}") from err
        except Exception as err:
            raise XiaomiFeederError(f"Unexpected error setting property {siid}.{piid}: {err}") from err

    def call_action(
        self, siid: int, aiid: int, in_params: Optional[List[Any]] = None, did: str = "action"
    ) -> Dict[str, Any]:
        """
        Execute a MIOT action.

        :param siid: Service IID
        :param aiid: Action IID
        :param in_params: List of input parameters
        :param did: Device ID alias
        :return: Action result dict
        """
        payload = {
            "did": did,
            "siid": siid,
            "aiid": aiid,
            "in": in_params or [],
        }
        try:
            res = self._device.send("action", payload)
            code = res.get("code", 0) if isinstance(res, dict) else 0
            if code != 0:
                raise XiaomiFeederDeviceError(
                    f"Failed to execute action (siid={siid}, aiid={aiid}, in={in_params}): code {code}"
                )
            return res
        except XiaomiFeederDeviceError:
            raise
        except DeviceException as err:
            raise XiaomiFeederConnectionError(f"Connection error executing action {siid}.{aiid}: {err}") from err
        except Exception as err:
            raise XiaomiFeederError(f"Unexpected error executing action {siid}.{aiid}: {err}") from err

    # --------------------------------------------------------------------------
    # Synchronous High-Level Feeder Operations
    # --------------------------------------------------------------------------
    def feed(self, portions: int) -> Dict[str, Any]:
        """
        Dispense pet food by portion count.

        NOTE: On Xiaomi Pet Feeders, the unit is PORTIONS (1 portion = 180° rotor turn; 2 portions = 360° full circle).
        1 portion yields ~7-12 grams of kibble.

        :param portions: Number of portions to dispense (1 - 30)
        :return: MIOT action execution response
        """
        if portions <= 0 or portions > 30:
            raise ValueError(f"Feed portions {portions} is outside safe range (1 - 30 portions). 1 portion ≈ 7-12g.")

        # Update target feeding measure property (SIID 2, PIID 7)
        try:
            self.set_property(
                siid=FeederSIID.PET_FEEDER,
                piid=FeederPIID.TARGET_FEEDING_MEASURE,
                value=portions,
            )
        except Exception:
            pass

        # Trigger feeding action with PIID 8 parameter (SIID 2, AIID 1)
        return self.call_action(
            siid=FeederSIID.PET_FEEDER,
            aiid=FeederAIID.PET_FOOD_OUT,
            in_params=[{"piid": FeederPIID.FEEDING_MEASURE, "value": portions}],
        )

    def set_target_portions(self, portions: int) -> Dict[str, Any]:
        """
        Set the default manual target feeding portions (SIID 2, PIID 7).

        :param portions: Number of portions (1 - 30)
        :return: MIOT set_properties response
        """
        if portions <= 0 or portions > 30:
            raise ValueError(f"Target portions {portions} is outside safe range (1 - 30 portions).")

        return self.set_property(
            siid=FeederSIID.PET_FEEDER,
            piid=FeederPIID.TARGET_FEEDING_MEASURE,
            value=int(portions),
        )

    def calibrate_scale(self) -> Dict[str, Any]:
        """Trigger manual weight scale calibration / tare."""
        return self.call_action(
            siid=FeederSIID.PET_FEEDER,
            aiid=FeederAIID.WEIGH_CALIBRATE,
            in_params=[],
        )

    def set_child_lock(self, locked: bool) -> Dict[str, Any]:
        """
        Lock or unlock the physical dispensing button on the feeder.

        :param locked: True to lock (disable physical button), False to unlock.
        """
        return self.set_property(
            siid=FeederSIID.PHYSICAL_LOCK,
            piid=FeederPIID.PHYSICAL_LOCK,
            value=bool(locked),
        )

    def set_screen_display(self, mode: Union[int, str]) -> Dict[str, Any]:
        """
        Set the feeder screen display mode.

        :param mode: 0 or 'left' (Left-gram-display),
                     1 or 'eaten' (Eaten-gram-display),
                     2 or 'percent' (Percentage-display)
        """
        mode_mapping = {
            "left": 0,
            "eaten": 1,
            "percent": 2,
            "percentage": 2,
        }
        if isinstance(mode, str):
            val = mode_mapping.get(mode.lower())
            if val is None:
                raise ValueError(f"Invalid screen mode '{mode}'. Choose from: left, eaten, percent")
        else:
            val = int(mode)
            if val not in (0, 1, 2):
                raise ValueError(f"Invalid screen mode integer {val}. Must be 0, 1, or 2.")

        return self.set_property(
            siid=FeederSIID.CUSTOM,
            piid=FeederPIID.SCREEN_DISPLAY,
            value=val,
        )

    def set_screen_auto_sleep(self, enabled: bool) -> Dict[str, Any]:
        """
        Enable or disable automatic screen sleep / turn off mode.
        When enabled (True), the LED display stays off and only turns on when food is dispensed or button is pressed.

        :param enabled: True for auto-sleep (screen off when idle), False for always-on screen.
        """
        return self.set_property(
            siid=FeederSIID.PHYSICAL_LOCK,
            piid=FeederPIID.LOCK_MODE,
            value=1 if enabled else 0,
        )

    def set_screen_progress_display(self, enabled: bool) -> Dict[str, Any]:
        """
        Enable or disable illuminating the screen to show feeding progress when food is given out.

        :param enabled: True to turn display on during dispensing, False to keep it off/default.
        """
        return self.set_property(
            siid=FeederSIID.CUSTOM,
            piid=FeederPIID.PLAN_PROGRESS_DISPLAY,
            value=bool(enabled),
        )

    def set_anti_stacking(self, enabled: bool) -> Dict[str, Any]:
        """Enable or disable anti-stacking / food pile prevention."""
        return self.set_property(
            siid=FeederSIID.CUSTOM,
            piid=FeederPIID.PREVENT_STACKING,
            value=1 if enabled else 0,
        )

    def set_grain_compensation(self, enabled: bool) -> Dict[str, Any]:
        """Enable or disable automatic grain / portion compensation."""
        return self.set_property(
            siid=FeederSIID.CUSTOM,
            piid=FeederPIID.GRAIN_COMPENSATION,
            value=1 if enabled else 0,
        )

    def set_refill_reminder(self, enabled: bool, interval_hours: int = 6) -> Dict[str, Any]:
        """
        Configure the hopper food refill reminder on the feeder hardware.

        :param enabled: True to enable refill reminders, False to disable.
        :param interval_hours: Reminder interval cycle in hours (e.g. 6, 8, 12, 24).
        :return: MIOT action response
        """
        if interval_hours <= 0 or interval_hours > 72:
            raise ValueError(f"Invalid refill reminder interval {interval_hours}h (must be 1-72 hours)")

        return self.call_action(
            siid=FeederSIID.CUSTOM,
            aiid=FeederAIID.ADD_MEAL_SETTING,
            in_params=[
                {"piid": FeederPIID.ADD_MEAL_STATE, "value": bool(enabled)},
                {"piid": FeederPIID.ADD_MEAL_CYCLE, "value": int(interval_hours)},
            ],
        )

    def set_intake_alarm(self, enabled: bool, threshold_pct: int = 10) -> Dict[str, Any]:
        """
        Configure the Abnormal / Low Food Intake Alarm (SIID 5, AIID 1).
        Alerts when the pet consumes less than the configured percentage of their daily food plan.

        :param enabled: True to enable alarm, False to disable
        :param threshold_pct: Intake percentage threshold (0 - 100%, default 10%)
        :return: Action result dict
        """
        if threshold_pct < 0 or threshold_pct > 100:
            raise ValueError(f"Intake threshold {threshold_pct}% is out of valid range (0 - 100%)")

        return self.call_action(
            siid=FeederSIID.CUSTOM,
            aiid=FeederAIID.FOOD_INTAKE_SETTING,
            in_params=[
                {"piid": FeederPIID.FOOD_INTAKE_RATE, "value": int(threshold_pct)},
                {"piid": FeederPIID.FOOD_INTAKE_STATE, "value": bool(enabled)},
            ],
        )

    def clear_intake_alert(self) -> Dict[str, Any]:
        """
        Acknowledge and clear the Abnormal / Low Food Intake alert (SIID 5, AIID 5).

        :return: Action result dict
        """
        return self.call_action(
            siid=FeederSIID.CUSTOM,
            aiid=FeederAIID.FOOD_INTAKE_LOW_SET,
            in_params=[{"piid": 9, "value": 0}],
        )

    def clear_refill_alert(self) -> Dict[str, Any]:
        """
        Acknowledge and clear the Hopper Refill reminder alert (SIID 5, AIID 6).

        :return: Action result dict
        """
        return self.call_action(
            siid=FeederSIID.CUSTOM,
            aiid=FeederAIID.ADD_MEAL_STATE_SET,
            in_params=[{"piid": 9, "value": 0}],
        )

    # --------------------------------------------------------------------------
    # Onboard Hardware EEPROM Schedule (Offline Feeding Plan)
    # --------------------------------------------------------------------------
    def get_hardware_schedule(self) -> Dict[str, Any]:
        """
        Get the offline hardware feeding schedule stored in the feeder's internal EEPROM/flash.

        :return: Dict containing 'enabled', 'meals' list, and 'raw_string'.
        """
        props = self.get_properties([
            {"did": "p_sched", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.FEEDING_PROGRAM},
            {"did": "p_state", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.FEEDING_PLAN_SWITCH},
        ])
        data = {p["did"]: p.get("value") for p in props}
        raw_str = data.get("p_sched", "[0]")
        enabled = bool(data.get("p_state", 0) == 1)

        meals: List[Dict[str, Any]] = []
        try:
            trimmed = raw_str.strip("[] \t\r\n")
            if trimmed and trimmed != "0":
                tokens = [t.strip() for t in trimmed.split(",") if t.strip()]
                if len(tokens) > 1 and tokens[0] == "1":
                    for item in tokens[1:]:
                        s = str(item).zfill(8)
                        hour = int(s[0:2])
                        minute = int(s[2:4])
                        portions = int(s[4:6])
                        repeat = int(s[6:8])
                        meals.append({
                            "time": f"{hour:02d}:{minute:02d}",
                            "portions": portions,
                            "repeat": repeat,
                            "raw": s,
                        })
        except Exception:
            pass

        return {
            "enabled": enabled,
            "meals": meals,
            "raw_string": raw_str,
        }

    def set_hardware_schedule(self, meals: List[Dict[str, Any]], enable: bool = True) -> Dict[str, Any]:
        """
        Upload and write an offline feeding schedule into the feeder's EEPROM / flash.
        The schedule runs 100% autonomously from the device's internal RTC and backup batteries.

        :param meals: List of dicts, e.g. [{"time": "08:00", "portions": 2, "repeat": 1}, ...]
        :param enable: Whether to activate the hardware feeding schedule switch.
        :return: MIOT action execution response
        """
        if not meals:
            return self.clear_hardware_schedule()

        encoded_meals: List[str] = []
        for m in meals:
            if isinstance(m, (tuple, list)):
                time_str = str(m[0])
                portions = int(m[1])
                repeat = int(m[2]) if len(m) > 2 else 1
            elif isinstance(m, dict):
                time_str = str(m.get("time", "08:00"))
                portions = int(m.get("portions", 1))
                repeat = int(m.get("repeat", 1))
            else:
                raise ValueError(f"Invalid meal item format: {m}")

            parts = time_str.split(":")
            if len(parts) != 2:
                raise ValueError(f"Invalid time format '{time_str}' (must be HH:MM in 24h format)")
            hour = int(parts[0])
            minute = int(parts[1])

            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError(f"Invalid time '{time_str}' (hour must be 0-23, minute 0-59)")
            if portions < 1 or portions > 30:
                raise ValueError(f"Invalid portions {portions} (must be 1-30 portions, 1 portion ≈ 10-15g)")

            encoded = f"{hour:02d}{minute:02d}{portions:02d}{repeat:02d}"
            encoded_meals.append(encoded)

        # Sort chronologically as required by feeder firmware
        encoded_meals.sort()
        payload_str = f"[1,{','.join(encoded_meals)}]"

        # Execute MIoT action to flash the schedule into internal memory
        res = self.call_action(
            siid=FeederSIID.CUSTOM,
            aiid=FeederAIID.UPDATE_FEEDING_PROGRAM,
            in_params=[{"piid": FeederPIID.FEEDING_PROGRAM, "value": payload_str}],
        )

        # Ensure schedule switch is enabled
        if enable:
            try:
                self.set_property(
                    siid=FeederSIID.CUSTOM,
                    piid=FeederPIID.FEEDING_PLAN_SWITCH,
                    value=1,
                )
            except Exception:
                pass

        return res

    def clear_hardware_schedule(self) -> Dict[str, Any]:
        """Clear all internal hardware schedules from EEPROM / flash."""
        res = self.call_action(
            siid=FeederSIID.CUSTOM,
            aiid=FeederAIID.UPDATE_FEEDING_PROGRAM,
            in_params=[{"piid": FeederPIID.FEEDING_PROGRAM, "value": "[0]"}],
        )
        try:
            self.set_property(
                siid=FeederSIID.CUSTOM,
                piid=FeederPIID.FEEDING_PLAN_SWITCH,
                value=0,
            )
        except Exception:
            pass
        return res

    def enable_hardware_schedule(self, enabled: bool = True) -> Dict[str, Any]:
        """Toggle the master switch for the onboard hardware feeding schedule."""
        return self.set_property(
            siid=FeederSIID.CUSTOM,
            piid=FeederPIID.FEEDING_PLAN_SWITCH,
            value=1 if enabled else 0,
        )

    def status(self) -> FeederStatus:
        """
        Fetch and parse complete status from the pet feeder.

        :return: FeederStatus instance
        """
        props_to_fetch = [
            # Pet Feeder (SIID 2)
            {"did": "p_fault", "siid": FeederSIID.PET_FEEDER, "piid": FeederPIID.DEVICE_FAULT},
            {"did": "p_food_left", "siid": FeederSIID.PET_FEEDER, "piid": FeederPIID.FOOD_LEFT_LEVEL},
            {"did": "p_target_measure", "siid": FeederSIID.PET_FEEDER, "piid": FeederPIID.TARGET_FEEDING_MEASURE},
            {"did": "p_food_stuck", "siid": FeederSIID.PET_FEEDER, "piid": FeederPIID.FOOD_STUCK_STATUS},
            {"did": "p_food_out", "siid": FeederSIID.PET_FEEDER, "piid": FeederPIID.FOOD_OUT_STATUS},
            {"did": "p_heap", "siid": FeederSIID.PET_FEEDER, "piid": FeederPIID.FOOD_HEAP_STATUS},
            {"did": "p_daily_eaten", "siid": FeederSIID.PET_FEEDER, "piid": FeederPIID.DAILY_EATEN_FOOD},
            {"did": "p_last_eaten", "siid": FeederSIID.PET_FEEDER, "piid": 20},
            {"did": "p_prev_eaten", "siid": FeederSIID.PET_FEEDER, "piid": 23},
            {"did": "p_bowl_weight", "siid": FeederSIID.PET_FEEDER, "piid": FeederPIID.REALTIME_BOWL_WEIGHT},
            {"did": "p_busy26", "siid": FeederSIID.PET_FEEDER, "piid": FeederPIID.FEEDER_STATUS_26},
            {"did": "p_level_detail", "siid": FeederSIID.PET_FEEDER, "piid": FeederPIID.FOOD_LEVEL_DETAIL},
            {"did": "p_busy32", "siid": FeederSIID.PET_FEEDER, "piid": FeederPIID.FEEDER_STATUS_32},
            # Child Lock & Screen Auto-Sleep Mode (SIID 3)
            {"did": "p_lock", "siid": FeederSIID.PHYSICAL_LOCK, "piid": FeederPIID.PHYSICAL_LOCK},
            {"did": "p_sleep", "siid": FeederSIID.PHYSICAL_LOCK, "piid": FeederPIID.LOCK_MODE},
            # Battery (SIID 4)
            {"did": "p_batt", "siid": FeederSIID.BATTERY, "piid": FeederPIID.BATTERY_LEVEL},
            # Custom (SIID 5)
            {"did": "p_anti_stack", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.PREVENT_STACKING},
            {"did": "p_grain_comp", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.GRAIN_COMPENSATION},
            {"did": "p_screen", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.SCREEN_DISPLAY},
            {"did": "p_screen_prog", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.PLAN_PROGRESS_DISPLAY},
            {"did": "p_add_state", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.ADD_MEAL_STATE},
            {"did": "p_add_cycle", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.ADD_MEAL_CYCLE},
            {"did": "p_sched", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.FEEDING_PROGRAM},
            {"did": "p_sched_sw", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.FEEDING_PLAN_SWITCH},
            {"did": "p_tz", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.DEVICE_TIMEZONE},
            {"did": "p_dst", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.DST_OFFSET},
            {"did": "p_intake_rate", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.FOOD_INTAKE_RATE},
            {"did": "p_intake_state", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.FOOD_INTAKE_STATE},
        ]

        raw_results = self.get_properties(props_to_fetch)
        data: Dict[str, Any] = {}
        for r in raw_results:
            key = f"{r.get('siid')}_{r.get('piid')}"
            data[key] = r.get("value")

        # Map food level (SIID 2, PIID 6: 0=Normal, 1=Low)
        lvl_food = data.get(f"{FeederSIID.PET_FEEDER}_{FeederPIID.FOOD_LEFT_LEVEL}")
        if lvl_food == 0:
            food_level_str = "Normal"
        elif lvl_food == 1:
            food_level_str = "Low / Empty"
        else:
            food_level_str = "Unknown"

        # Busy status (check both PIID 26 and 32)
        busy26 = data.get(f"{FeederSIID.PET_FEEDER}_{FeederPIID.FEEDER_STATUS_26}") == 1
        busy32 = data.get(f"{FeederSIID.PET_FEEDER}_{FeederPIID.FEEDER_STATUS_32}") == 1
        is_busy = busy26 or busy32

        # Screen display mode
        screen_raw = data.get(f"{FeederSIID.CUSTOM}_{FeederPIID.SCREEN_DISPLAY}")
        screen_modes = {0: "Left-gram-display", 1: "Eaten-gram-display", 2: "Percentage-display"}
        screen_mode_str = screen_modes.get(screen_raw) if screen_raw is not None else None

        # Screen auto-sleep (SIID 3, PIID 3)
        screen_sleep_raw = data.get(f"{FeederSIID.PHYSICAL_LOCK}_{FeederPIID.LOCK_MODE}")
        screen_sleep_bool = bool(screen_sleep_raw == 1) if screen_sleep_raw is not None else None

        # Screen progress display
        screen_prog_raw = data.get(f"{FeederSIID.CUSTOM}_{FeederPIID.PLAN_PROGRESS_DISPLAY}")
        screen_prog_bool = bool(screen_prog_raw in (1, True)) if screen_prog_raw is not None else None

        # Anti-stacking & Grain compensation
        anti_stack_raw = data.get(f"{FeederSIID.CUSTOM}_{FeederPIID.PREVENT_STACKING}")
        grain_comp_raw = data.get(f"{FeederSIID.CUSTOM}_{FeederPIID.GRAIN_COMPENSATION}")

        # Refill reminder
        add_state_raw = data.get(f"{FeederSIID.CUSTOM}_{FeederPIID.ADD_MEAL_STATE}")
        add_cycle_raw = data.get(f"{FeederSIID.CUSTOM}_{FeederPIID.ADD_MEAL_CYCLE}")
        refill_rem_enabled = bool(add_state_raw in (1, True)) if add_state_raw is not None else None
        refill_rem_hours = int(add_cycle_raw) if add_cycle_raw is not None else None

        # Hardware schedule switch & count
        sched_sw_raw = data.get(f"{FeederSIID.CUSTOM}_{FeederPIID.FEEDING_PLAN_SWITCH}")
        sched_str = str(data.get(f"{FeederSIID.CUSTOM}_{FeederPIID.FEEDING_PROGRAM}", "[0]"))
        sched_count = 0
        try:
            trimmed = sched_str.strip("[] \t\r\n")
            if trimmed and trimmed != "0":
                tokens = [t.strip() for t in trimmed.split(",") if t.strip()]
                if len(tokens) > 1 and tokens[0] == "1":
                    sched_count = len(tokens) - 1
        except Exception:
            pass

        return FeederStatus(
            device_fault=bool(data.get(f"{FeederSIID.PET_FEEDER}_{FeederPIID.DEVICE_FAULT}", 0) == 1),
            food_stuck=bool(data.get(f"{FeederSIID.PET_FEEDER}_{FeederPIID.FOOD_STUCK_STATUS}", 0) == 1),
            food_out_error=bool(data.get(f"{FeederSIID.PET_FEEDER}_{FeederPIID.FOOD_OUT_STATUS}", 0) == 1),
            food_heap_detected=bool(data.get(f"{FeederSIID.PET_FEEDER}_{FeederPIID.FOOD_HEAP_STATUS}", 0) == 1),
            food_level=food_level_str,
            food_level_raw=lvl_food,
            bowl_food_weight=data.get(f"{FeederSIID.PET_FEEDER}_{FeederPIID.REALTIME_BOWL_WEIGHT}"),
            daily_eaten_weight=data.get(f"{FeederSIID.PET_FEEDER}_{FeederPIID.DAILY_EATEN_FOOD}"),
            last_meal_intake=data.get(f"{FeederSIID.PET_FEEDER}_20"),
            previous_meal_intake=data.get(f"{FeederSIID.PET_FEEDER}_23"),
            is_busy=is_busy,
            target_feeding_portions=data.get(f"{FeederSIID.PET_FEEDER}_{FeederPIID.TARGET_FEEDING_MEASURE}"),
            child_lock=bool(data.get(f"{FeederSIID.PHYSICAL_LOCK}_{FeederPIID.PHYSICAL_LOCK}", False)),
            battery_level=data.get(f"{FeederSIID.BATTERY}_{FeederPIID.BATTERY_LEVEL}"),
            screen_display_mode=screen_mode_str,
            screen_auto_sleep=screen_sleep_bool,
            screen_progress_display=screen_prog_bool,
            anti_stacking=bool(anti_stack_raw == 1) if anti_stack_raw is not None else None,
            grain_compensation=bool(grain_comp_raw == 1) if grain_comp_raw is not None else None,
            hardware_schedule_active=bool(sched_sw_raw == 1) if sched_sw_raw is not None else None,
            hardware_schedule_count=sched_count,
            refill_reminder_enabled=refill_rem_enabled,
            refill_reminder_hours=refill_rem_hours,
            device_timezone_sec=data.get(f"{FeederSIID.CUSTOM}_{FeederPIID.DEVICE_TIMEZONE}"),
            dst_active=bool(data.get(f"{FeederSIID.CUSTOM}_{FeederPIID.DST_OFFSET}") == 1)
            if data.get(f"{FeederSIID.CUSTOM}_{FeederPIID.DST_OFFSET}") is not None
            else None,
            intake_alarm_enabled=bool(data.get(f"{FeederSIID.CUSTOM}_{FeederPIID.FOOD_INTAKE_STATE}", 0) == 1),
            intake_alarm_threshold=data.get(f"{FeederSIID.CUSTOM}_{FeederPIID.FOOD_INTAKE_RATE}"),
            raw_properties=data,
        )

    # --------------------------------------------------------------------------
    # Asynchronous High-Level Operations (for Home Assistant & AsyncIO Callers)
    # --------------------------------------------------------------------------
    async def _async_run(self, func, *args, **kwargs) -> Any:
        """Run a blocking function in the default executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def async_status(self) -> FeederStatus:
        """Asynchronously fetch and parse feeder status."""
        return await self._async_run(self.status)

    async def async_feed(self, portions: int) -> Dict[str, Any]:
        """Asynchronously dispense food."""
        return await self._async_run(self.feed, portions)

    async def async_set_target_portions(self, portions: int) -> Dict[str, Any]:
        """Asynchronously set default target portions."""
        return await self._async_run(self.set_target_portions, portions)

    async def async_calibrate_scale(self) -> Dict[str, Any]:
        """Asynchronously calibrate scale tare."""
        return await self._async_run(self.calibrate_scale)

    async def async_set_child_lock(self, locked: bool) -> Dict[str, Any]:
        """Asynchronously toggle child lock."""
        return await self._async_run(self.set_child_lock, locked)

    async def async_set_screen_display(self, mode: Union[int, str]) -> Dict[str, Any]:
        """Asynchronously configure screen mode."""
        return await self._async_run(self.set_screen_display, mode)

    async def async_set_screen_auto_sleep(self, enabled: bool) -> Dict[str, Any]:
        """Asynchronously toggle screen auto sleep."""
        return await self._async_run(self.set_screen_auto_sleep, enabled)

    async def async_set_screen_progress_display(self, enabled: bool) -> Dict[str, Any]:
        """Asynchronously toggle screen progress display."""
        return await self._async_run(self.set_screen_progress_display, enabled)

    async def async_set_anti_stacking(self, enabled: bool) -> Dict[str, Any]:
        """Asynchronously toggle anti-stacking protection."""
        return await self._async_run(self.set_anti_stacking, enabled)

    async def async_set_grain_compensation(self, enabled: bool) -> Dict[str, Any]:
        """Asynchronously toggle grain compensation."""
        return await self._async_run(self.set_grain_compensation, enabled)

    async def async_set_refill_reminder(self, enabled: bool, interval_hours: int = 6) -> Dict[str, Any]:
        """Asynchronously configure refill reminder."""
        return await self._async_run(self.set_refill_reminder, enabled, interval_hours)

    async def async_clear_refill_alert(self) -> Dict[str, Any]:
        """Asynchronously clear refill reminder alert."""
        return await self._async_run(self.clear_refill_alert)

    async def async_set_intake_alarm(self, enabled: bool, threshold_pct: int = 10) -> Dict[str, Any]:
        """Asynchronously configure low intake alarm."""
        return await self._async_run(self.set_intake_alarm, enabled, threshold_pct)

    async def async_clear_intake_alert(self) -> Dict[str, Any]:
        """Asynchronously clear low intake alarm."""
        return await self._async_run(self.clear_intake_alert)

    async def async_get_hardware_schedule(self) -> Dict[str, Any]:
        """Asynchronously get hardware EEPROM schedule."""
        return await self._async_run(self.get_hardware_schedule)

    async def async_set_hardware_schedule(
        self, meals: List[Dict[str, Any]], enable: bool = True
    ) -> Dict[str, Any]:
        """Asynchronously upload hardware schedule."""
        return await self._async_run(self.set_hardware_schedule, meals, enable)

    async def async_clear_hardware_schedule(self) -> Dict[str, Any]:
        """Asynchronously clear hardware schedule."""
        return await self._async_run(self.clear_hardware_schedule)

    async def async_enable_hardware_schedule(self, enabled: bool = True) -> Dict[str, Any]:
        """Asynchronously enable/disable hardware schedule switch."""
        return await self._async_run(self.enable_hardware_schedule, enabled)
