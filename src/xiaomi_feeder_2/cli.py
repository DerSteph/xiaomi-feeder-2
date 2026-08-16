"""CLI entry point and output formatters for Xiaomi Pet Feeder 2."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from .client import XiaomiFeeder
from .models import FeederStatus


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="feeder",
        description="CLI utility for Xiaomi Smart Pet Food Feeder 2 (xiaomi.feeder.iv2001)",
    )
    parser.add_argument(
        "--ip",
        default=os.getenv("FEEDER_IP"),
        help="Device IP address (defaults to FEEDER_IP env variable)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("FEEDER_TOKEN"),
        help="Device 32-char token (defaults to FEEDER_TOKEN env variable)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to execute")

    # Command: status
    status_parser = subparsers.add_parser("status", help="Get feeder status")
    status_parser.add_argument("--json", action="store_true", help="Output status as JSON")

    # Command: feed
    feed_parser = subparsers.add_parser("feed", help="Dispense food (in portions)")
    feed_parser.add_argument(
        "portions", type=int, help="Number of portions to dispense (1 portion ≈ 10-15g, safe max: 30)"
    )
    feed_parser.add_argument(
        "--watch", action="store_true", help="Monitor live motor dispensing progress and bowl weight"
    )

    # Command: target-portions
    target_parser = subparsers.add_parser(
        "target-portions", help="Set default manual target feeding portions (without dispensing)"
    )
    target_parser.add_argument("portions", type=int, help="Default target portions (1 - 30)")

    # Command: lock
    lock_parser = subparsers.add_parser("lock", help="Configure child lock (physical button)")
    lock_parser.add_argument("state", choices=["on", "off"], help="Lock state: on (locked) or off (unlocked)")

    # Command: calibrate
    subparsers.add_parser("calibrate", help="Calibrate / tare the weighing scale")

    # Command: screen
    screen_parser = subparsers.add_parser("screen", help="Configure screen display mode")
    screen_parser.add_argument("mode", choices=["left", "eaten", "percent"], help="Display mode")

    # Command: screen-sleep
    screen_sleep_parser = subparsers.add_parser(
        "screen-sleep",
        help="Configure screen auto-sleep (turn screen off when idle, only on during feed/dispense)",
    )
    screen_sleep_parser.add_argument(
        "state", choices=["on", "off"], help="State: on (screen off when idle) or off (always on)"
    )

    # Command: screen-progress
    screen_prog_parser = subparsers.add_parser(
        "screen-progress",
        help="Turn screen on during feeding to show live progress",
    )
    screen_prog_parser.add_argument("state", choices=["on", "off"], help="State: on or off")

    # Command: anti-stack
    anti_stack_parser = subparsers.add_parser("anti-stack", help="Configure anti-stacking / food pile prevention")
    anti_stack_parser.add_argument("state", choices=["on", "off"], help="State: on or off")

    # Command: grain-comp
    grain_comp_parser = subparsers.add_parser("grain-comp", help="Configure automatic grain/portion compensation")
    grain_comp_parser.add_argument("state", choices=["on", "off"], help="State: on or off")

    # Command: refill-reminder
    refill_parser = subparsers.add_parser("refill-reminder", help="Configure hopper food refill reminder")
    refill_parser.add_argument("state", choices=["on", "off"], help="State: on or off")
    refill_parser.add_argument("--hours", type=int, default=6, help="Reminder interval cycle in hours (default: 6)")

    # Command: clear-refill-alert
    subparsers.add_parser("clear-refill-alert", help="Acknowledge and clear hopper refill reminder alert")

    # Command: intake-alarm
    intake_parser = subparsers.add_parser("intake-alarm", help="Configure abnormal/low pet food intake alarm")
    intake_parser.add_argument("state", choices=["on", "off"], help="State: on or off")
    intake_parser.add_argument(
        "--threshold", type=int, default=10, help="Alert threshold percentage of daily plan (default: 10%%)"
    )

    # Command: clear-intake-alert
    subparsers.add_parser("clear-intake-alert", help="Acknowledge and clear abnormal low food intake alert")

    # Command: schedule-get
    sched_get_parser = subparsers.add_parser("schedule-get", help="Get offline hardware schedule from feeder EEPROM")
    sched_get_parser.add_argument("--json", action="store_true", help="Output raw JSON")

    # Command: schedule-set
    sched_set_parser = subparsers.add_parser(
        "schedule-set",
        help="Write offline feeding plan to feeder EEPROM (e.g. '08:00=2, 18:30=1' or '08:00:2:1')",
    )
    sched_set_parser.add_argument(
        "meals",
        nargs="+",
        help="Meals in format 'HH:MM=portions' or 'HH:MM:portions:repeat' (e.g. 08:00=2 21:30=1)",
    )

    # Command: schedule-clear
    subparsers.add_parser("schedule-clear", help="Clear all offline schedules from feeder EEPROM")

    # Command: schedule-enable
    sched_en_parser = subparsers.add_parser("schedule-enable", help="Enable or disable hardware schedule execution")
    sched_en_parser.add_argument("state", choices=["on", "off"], help="State: on or off")

    # Command: raw-get
    raw_get_parser = subparsers.add_parser("raw-get", help="Query raw MIOT property")
    raw_get_parser.add_argument("siid", type=int, help="Service IID")
    raw_get_parser.add_argument("piid", type=int, help="Property IID")

    # Command: raw-set
    raw_set_parser = subparsers.add_parser("raw-set", help="Set raw MIOT property")
    raw_set_parser.add_argument("siid", type=int, help="Service IID")
    raw_set_parser.add_argument("piid", type=int, help="Property IID")
    raw_set_parser.add_argument("value", help="Value (integer, boolean, or string)")

    return parser


def format_status_output(status: FeederStatus) -> str:
    """Format FeederStatus as an ASCII table."""
    bowl_weight_str = f"{status.bowl_food_weight} g" if status.bowl_food_weight is not None else "N/A"
    daily_eaten_str = f"{status.daily_eaten_weight} g" if status.daily_eaten_weight is not None else "N/A"
    last_eaten_str = f"{status.last_meal_intake} g" if status.last_meal_intake is not None else "N/A"
    prev_eaten_str = f"{status.previous_meal_intake} g" if status.previous_meal_intake is not None else "N/A"
    target_str = f"{status.target_feeding_portions} portion(s)" if status.target_feeding_portions is not None else "N/A"
    busy_str = "Yes (Busy)" if status.is_busy else "No (Idle)"
    fault_str = "⚠️ ERROR" if status.device_fault else "✅ OK"
    stuck_str = "⚠️ JAMMED" if status.food_stuck else "✅ Normal"
    out_error_str = "⚠️ ERROR" if status.food_out_error else "✅ Normal"
    heap_str = "⚠️ YES (Overflow)" if status.food_heap_detected else "✅ No"
    lock_str = "🔒 Locked (On)" if status.child_lock else "🔓 Unlocked (Off)"
    batt_str = (
        "Present"
        if status.battery_level is True
        else ("None / Disconnected" if status.battery_level is False else str(status.battery_level))
    )
    screen_str = str(status.screen_display_mode) if status.screen_display_mode else "N/A"
    screen_sleep_str = "Enabled (Off when idle)" if status.screen_auto_sleep else "Disabled (Always On)"
    screen_prog_str = "Enabled (On during feed)" if status.screen_progress_display else "Disabled (Off)"
    anti_stack_str = "Enabled" if status.anti_stacking else ("Disabled" if status.anti_stacking is False else "N/A")
    grain_comp_str = "Enabled" if status.grain_compensation else ("Disabled" if status.grain_compensation is False else "N/A")

    if status.refill_reminder_enabled:
        refill_str = f"Enabled (Every {status.refill_reminder_hours or 6}h)"
    else:
        refill_str = "Disabled (Off)"

    if status.hardware_schedule_active:
        sched_summary = f"Active ({status.hardware_schedule_count} meal(s) in EEPROM)"
    else:
        sched_summary = "Disabled / Inactive"

    if status.device_timezone_sec is not None:
        tz_h = status.device_timezone_sec / 3600.0
        tz_sign = "+" if tz_h >= 0 else ""
        dst_tag = " (DST)" if status.dst_active else " (STD)"
        tz_str = f"UTC{tz_sign}{tz_h:g}{dst_tag}"
    else:
        tz_str = "N/A"

    if status.intake_alarm_enabled:
        intake_str = f"Enabled (< {status.intake_alarm_threshold or 10}% of daily plan)"
    else:
        intake_str = "Disabled (Off)"

    lines = [
        "╔═══════════════════════════════════════════════════════════════╗",
        "║            Xiaomi Smart Pet Food Feeder 2 Status              ║",
        "╠═══════════════════════════════════════════════════════════════╣",
        f"║ Current Bowl Food Weight:  {bowl_weight_str:<35}║",
        f"║ Daily Food Intake (Total): {daily_eaten_str:<35}║",
        f"║ Last Meal Session Intake:  {last_eaten_str:<35}║",
        f"║ Previous Session Intake:   {prev_eaten_str:<35}║",
        f"║ Food Hopper Level:         {status.food_level:<35}║",
        f"║ Dispenser Active:          {busy_str:<35}║",
        f"║ Target Portion Setting:    {target_str:<35}║",
        "╟───────────────────────────────────────────────────────────────╢",
        f"║ Device Fault:              {fault_str:<35}║",
        f"║ Food Stuck / Jam:          {stuck_str:<35}║",
        f"║ Food Dispense Error:       {out_error_str:<35}║",
        f"║ Food Heap Detected:        {heap_str:<35}║",
        "╟───────────────────────────────────────────────────────────────╢",
        f"║ Hardware Schedule (EEPROM):{sched_summary:<35}║",
        f"║ Device RTC Timezone:       {tz_str:<35}║",
        f"║ Child Lock:                {lock_str:<35}║",
        f"║ Screen Metric Display:     {screen_str:<35}║",
        f"║ Screen Auto-Sleep (Off):   {screen_sleep_str:<35}║",
        f"║ Screen on during Feed:     {screen_prog_str:<35}║",
        f"║ Hopper Refill Reminder:    {refill_str:<35}║",
        f"║ Low Intake Alarm:          {intake_str:<35}║",
        f"║ Anti-Stacking Protection:  {anti_stack_str:<35}║",
        f"║ Grain Compensation:        {grain_comp_str:<35}║",
        f"║ Backup Battery:            {batt_str:<35}║",
        "╚═══════════════════════════════════════════════════════════════╝",
    ]
    return "\n".join(lines)


def format_schedule_output(data: Dict[str, Any]) -> str:
    """Format hardware EEPROM schedule as an ASCII table."""
    enabled_str = "✅ Enabled (Active)" if data.get("enabled") else "❌ Disabled (Off)"
    meals = data.get("meals", [])

    lines = [
        "╔═══════════════════════════════════════════════════════════════╗",
        "║          Xiaomi Feeder Onboard Hardware Schedule              ║",
        "╠═══════════════════════════════════════════════════════════════╣",
        f"║ Schedule Master Switch:    {enabled_str:<35}║",
        f"║ Raw Hardware String:       {data.get('raw_string', 'N/A'):<35}║",
        "╟───────────────────────────────────────────────────────────────╢",
    ]
    if not meals:
        lines.append("║ No scheduled meals configured in device EEPROM.              ║")
    else:
        lines.append("║ Meal # | Time (24h) | Portions (~Grams)   | Repeat Mode       ║")
        lines.append("╟────────┼────────────┼─────────────────────┼───────────────────╢")
        for idx, m in enumerate(meals, 1):
            if m["repeat"] == 1:
                repeat_name = "Daily / Everyday"
            elif m["repeat"] == 0:
                repeat_name = "Once (One-time)"
            else:
                repeat_name = f"Mode {m['repeat']}"
            t_str = m["time"]
            p_str = f"{m['portions']} portion(s) (~{m['portions']*12}g)"
            lines.append(f"║ {idx:<6} │ {t_str:<10} │ {p_str:<19} │ {repeat_name:<17} ║")

    lines.append("╚═══════════════════════════════════════════════════════════════╝")
    return "\n".join(lines)


def main(args: Optional[List[str]] = None) -> int:
    """Main CLI execution handler."""
    parser = create_parser()
    opts = parser.parse_args(args)

    if not opts.ip or not opts.token:
        print(
            "Error: Feeder IP and Token must be provided via arguments (--ip, --token) "
            "or environment variables (FEEDER_IP, FEEDER_TOKEN in .env).",
            file=sys.stderr,
        )
        return 1

    try:
        feeder = XiaomiFeeder(ip=opts.ip, token=opts.token)

        if opts.command == "status":
            st = feeder.status()
            if opts.json:
                print(json.dumps(st.to_dict(), indent=2))
            else:
                print(format_status_output(st))

        elif opts.command == "feed":
            print(f"Dispensing {opts.portions} portion(s) of food (~{opts.portions * 12}g)...")
            res = feeder.feed(opts.portions)
            print("✅ Feed command sent successfully:", res)
            if opts.watch:
                print("⏳ Monitoring live dispensing progress...")
                start_t = time.time()
                while time.time() - start_t < 15.0:
                    time.sleep(0.3)
                    props = feeder.get_properties([
                        {"did": "p11", "siid": 5, "piid": 11},
                        {"did": "busy26", "siid": 2, "piid": 26},
                        {"did": "busy32", "siid": 2, "piid": 32},
                        {"did": "weight", "siid": 2, "piid": 22},
                    ])
                    vals = {r["did"]: r.get("value") for r in props if "did" in r}
                    prog = vals.get("p11", 0) or 0
                    is_busy = bool(vals.get("busy26") == 1 or vals.get("busy32") == 1)
                    cur_w = vals.get("weight", 0)
                    elapsed = time.time() - start_t

                    bar_len = 20
                    filled = int(bar_len * (prog / 100))
                    bar = "█" * filled + "░" * (bar_len - filled)
                    print(
                        f"   [{elapsed:4.1f}s] [{bar}] {prog:3d}% | Motor: {'Active' if is_busy else 'Idle'} | Bowl: {cur_w}g"
                    )

                    if prog >= 100 and not is_busy and elapsed > 2.0:
                        print("🎉 Dispense completed successfully!")
                        break

        elif opts.command == "target-portions":
            feeder.set_target_portions(opts.portions)
            print(f"✅ Default target feeding portions set to {opts.portions} portion(s) (~{opts.portions * 12}g).")

        elif opts.command == "lock":
            lock_state = opts.state == "on"
            feeder.set_child_lock(lock_state)
            print(f"✅ Child lock turned {'ON' if lock_state else 'OFF'}.")

        elif opts.command == "calibrate":
            print("Triggering scale calibration / tare...")
            res = feeder.calibrate_scale()
            print("✅ Scale calibration triggered successfully:", res)

        elif opts.command == "screen":
            feeder.set_screen_display(opts.mode)
            print(f"✅ Screen display mode set to '{opts.mode}'.")

        elif opts.command == "screen-sleep":
            enabled = opts.state == "on"
            feeder.set_screen_auto_sleep(enabled)
            print(
                f"✅ Screen auto-sleep mode turned {'ON (Screen stays off when idle)' if enabled else 'OFF (Screen always on)'}."
            )

        elif opts.command == "screen-progress":
            enabled = opts.state == "on"
            feeder.set_screen_progress_display(enabled)
            print(
                f"✅ Screen feeding progress display turned {'ON (Screen illuminates during dispensing)' if enabled else 'OFF'}."
            )

        elif opts.command == "anti-stack":
            enabled = opts.state == "on"
            feeder.set_anti_stacking(enabled)
            print(f"✅ Anti-stacking turned {'ON' if enabled else 'OFF'}.")

        elif opts.command == "grain-comp":
            enabled = opts.state == "on"
            feeder.set_grain_compensation(enabled)
            print(f"✅ Grain compensation turned {'ON' if enabled else 'OFF'}.")

        elif opts.command == "refill-reminder":
            enabled = opts.state == "on"
            hours = opts.hours
            feeder.set_refill_reminder(enabled=enabled, interval_hours=hours)
            if enabled:
                print(f"✅ Hopper refill reminder turned ON (Interval: every {hours} hours).")
            else:
                print("✅ Hopper refill reminder turned OFF.")

        elif opts.command == "clear-refill-alert":
            res = feeder.clear_refill_alert()
            print("✅ Hopper refill reminder alert cleared successfully:", res)

        elif opts.command == "intake-alarm":
            enabled = opts.state == "on"
            threshold = opts.threshold
            feeder.set_intake_alarm(enabled=enabled, threshold_pct=threshold)
            if enabled:
                print(f"✅ Abnormal low food intake alarm turned ON (Threshold: < {threshold}% of daily plan).")
            else:
                print("✅ Abnormal low food intake alarm turned OFF.")

        elif opts.command == "clear-intake-alert":
            res = feeder.clear_intake_alert()
            print("✅ Abnormal low food intake alert cleared successfully:", res)

        elif opts.command == "schedule-get":
            sched = feeder.get_hardware_schedule()
            if opts.json:
                print(json.dumps(sched, indent=2))
            else:
                print(format_schedule_output(sched))

        elif opts.command == "schedule-set":
            meals_to_set = []
            for item in opts.meals:
                cleaned = item.replace("=", ":")
                parts = cleaned.split(":")
                if len(parts) >= 2:
                    t = f"{int(parts[0]):02d}:{int(parts[1]):02d}"
                    p = int(parts[2]) if len(parts) >= 3 else 1
                    r_val = 1
                    if len(parts) >= 4:
                        raw_r = parts[3].lower()
                        if raw_r in ("once", "one-time", "single", "0"):
                            r_val = 0
                        elif raw_r in ("daily", "everyday", "repeat", "1"):
                            r_val = 1
                        else:
                            try:
                                r_val = int(raw_r)
                            except ValueError:
                                r_val = 1
                    meals_to_set.append({"time": t, "portions": p, "repeat": r_val})
                else:
                    raise ValueError(
                        f"Invalid meal argument '{item}'. Use format HH:MM=portions (e.g. 08:00=2 or 08:00=2:once)"
                    )

            print(f"Writing {len(meals_to_set)} meal(s) to feeder EEPROM...")
            res = feeder.set_hardware_schedule(meals_to_set, enable=True)
            print("✅ Hardware schedule saved successfully:", res)
            print("\nUpdated Feeder Hardware Schedule:")
            print(format_schedule_output(feeder.get_hardware_schedule()))

        elif opts.command == "schedule-clear":
            print("Clearing hardware schedule from feeder EEPROM...")
            res = feeder.clear_hardware_schedule()
            print("✅ Hardware schedule cleared:", res)

        elif opts.command == "schedule-enable":
            enabled = opts.state == "on"
            feeder.enable_hardware_schedule(enabled)
            print(f"✅ Hardware schedule switch turned {'ON' if enabled else 'OFF'}.")

        elif opts.command == "raw-get":
            res = feeder.get_properties([{"did": "raw", "siid": opts.siid, "piid": opts.piid}])
            print(json.dumps(res, indent=2))

        elif opts.command == "raw-set":
            val: Any = opts.value
            if val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            else:
                try:
                    val = int(val)
                except ValueError:
                    try:
                        val = float(val)
                    except ValueError:
                        pass
            res = feeder.set_property(opts.siid, opts.piid, val)
            print("✅ Property set response:", res)

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
