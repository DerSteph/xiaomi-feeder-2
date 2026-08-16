# Xiaomi Smart Pet Food Feeder 2 Controller (`xiaomi.feeder.iv2001`)

[![Test](https://github.com/DerSteph/xiaomi-feeder-2/actions/workflows/test.yml/badge.svg)](https://github.com/DerSteph/xiaomi-feeder-2/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/xiaomi-feeder-2)](https://pypi.org/project/xiaomi-feeder-2/)
[![Python Versions](https://img.shields.io/pypi/pyversions/xiaomi-feeder-2)](https://pypi.org/project/xiaomi-feeder-2/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Built with Google Antigravity](https://img.shields.io/badge/Built%20with-Google%20Antigravity-4285F4?style=flat&logo=google&logoColor=white)](https://deepmind.google)

A lightweight, reliable Python controller and CLI for the **Xiaomi Smart Pet Food Feeder 2** (`xiaomi.feeder.iv2001`).

Communicates directly and locally with the feeder over your LAN using Xiaomi's MIOT protocol via `python-miio`.

---

## Features

- **Dispense Food**: Trigger feeding portions/grams instantly.
- **Full Status Monitoring**: Food hopper level (empty/low/normal), daily food intake (grams), busy status, hopper jam/clog alert, error codes, and food heap/overflow detection.
- **Child Lock**: Lock and unlock physical dispenser buttons to prevent pet tampering.
- **Scale Calibration**: Trigger manual tare / zero-calibration for the weighing scale.
- **Display Modes**: Configure the front display screen (remaining grams, eaten grams, or percentage).
- **Advanced Features**: Toggle anti-stacking and automatic grain compensation.
- **CLI & Python Library**: Use directly from terminal or import as a module into Python scripts & automations.

---

## 💡 Why This Project Exists (Motivation)

Generic Xiaomi integrations for Home Assistant (such as *Xiaomi Miot Auto* / generic MIoT components) attempt to support thousands of devices with auto-generated templates. However, for the **Xiaomi Smart Pet Food Feeder 2 (`xiaomi.feeder.iv2001`)**, this created serious usability and safety issues:

1. **The Overfeeding Problem (Portions vs. Grams)**:
   Generic integrations often treat feeding inputs as grams or pass ambiguous numbers to the MIoT action. On the Feeder 2 hardware, the dispense parameter is strictly **portions** (1 portion = 180° rotor rotation ≈ 10–12g). Entering "25" intended as 25 grams resulted in dispensing 25 full portions (~300 grams!), dangerously overflowing the bowl.
2. **Ambiguous Generic Entities**:
   Many distinct hardware properties were generated with generic names like `status` or obscure property numbers, leaving users in the dark about what each entity represented.
3. **Spec Reverse-Engineering & Validation**:
   Certain MIoT template properties (such as desiccant countdown) return static dummy `0` values over local LAN because Xiaomi calculates them exclusively in their cloud UI. Meanwhile, valuable hardware capabilities—such as the offline RTC EEPROM schedule, scale tare calibration, live motor progress tracking, and food pile/heap detection—were unhandled.
4. **100% Reliable Local Control**:
   This library was built from the ground up by testing and validating every single register (`SIID`, `PIID`, `AIID`) directly against real feeder hardware. It serves as a reliable, fully local Python core to power a dedicated, native **Home Assistant / HACS** integration.

---

## Setup & Prerequisites

### 1. Requirements
Ensure you have `uv` installed (or Python 3.10+ with `pip`).

### 2. Obtain Feeder IP and Token
To communicate locally with your feeder, you need its local IP address and 32-character MIoT encryption token.

Use the popular [Xiaomi Cloud Tokens Extractor](https://github.com/piotrmachowski/xiaomi-cloud-tokens-extractor) tool to easily retrieve credentials from your Xiaomi / Mi Home account:

```bash
# Option A: Run standalone with Python (no installation required)
bash <(curl -sL https://raw.githubusercontent.com/piotrmachowski/xiaomi-cloud-tokens-extractor/master/run.sh)

# Option B: Run via Docker
docker run -it --rm ghcr.io/piotrmachowski/xiaomi-cloud-tokens-extractor
```

Log in with your Xiaomi account and server region (e.g. `de`, `cn`, `us`). The tool will output the **IP Address** and **Token** for your `xiaomi.feeder.iv2001`.

*(Alternatively, if you use Home Assistant with the Xiaomi integration, tokens can be found in `.storage/core.config_entries`).*

### 3. Configure Environment
Copy `.env.example` to `.env` and fill in your device details:

```bash
cp .env.example .env
```

Edit `.env`:
```ini
FEEDER_IP=192.168.1.100
FEEDER_TOKEN=a1b2c3d4e5f60718293a4b5c6d7e8f90
```

---

## CLI Usage

Run with `uv run feeder` (or `python -m xiaomi_feeder`):

### Check Feeder Status
```bash
uv run feeder status
```
Example Output:
```text
╔═══════════════════════════════════════════════════════════════╗
║            Xiaomi Smart Pet Food Feeder 2 Status              ║
╠═══════════════════════════════════════════════════════════════╣
║ Current Bowl Food Weight:  0 g                                ║
║ Daily Food Intake (Total): 0 g                                ║
║ Last Meal Session Intake:  0 g                                ║
║ Previous Session Intake:   0 g                                ║
║ Food Hopper Level:         Normal                             ║
║ Dispenser Active:          No (Idle)                          ║
║ Target Portion Setting:    1 portion(s)                       ║
╟───────────────────────────────────────────────────────────────╢
║ Device Fault:              ✅ OK                               ║
║ Food Stuck / Jam:          ✅ Normal                           ║
║ Food Dispense Error:       ✅ Normal                           ║
║ Food Heap Detected:        ✅ No                               ║
╟───────────────────────────────────────────────────────────────╢
║ Hardware Schedule (EEPROM):Active (2 meal(s) in EEPROM)       ║
║ Device RTC Timezone:       UTC+2 (DST)                        ║
║ Child Lock:                🔓 Unlocked (Off)                   ║
║ Screen Metric Display:     Eaten-gram-display                 ║
║ Screen on during Feed:     Enabled (On during feed)           ║
║ Anti-Stacking Protection:  Enabled                            ║
║ Grain Compensation:        Enabled                            ║
║ Backup Battery:            None / Disconnected                ║
╚═══════════════════════════════════════════════════════════════╝
```

Get JSON output for scripts / jq:
```bash
uv run feeder status --json
```

### Dispense Food (Manual Feeding)
```bash
# Dispense 1 portion (~10-15g)
uv run feeder feed 1

# Dispense 2 portions and monitor live progress & bowl scale
uv run feeder feed 2 --watch

# Set default target portion setting in device memory (without dispensing immediately)
uv run feeder target-portions 5
```
> **Note:** Target portions (`SIID 2, PIID 7`) is stored in volatile RAM (used for manual feeding defaults). If the device suffers a complete power loss (unplugged with no backup batteries), this value resets to the factory default of `10`. Hardware schedules, however, are stored in non-volatile EEPROM and are not affected.

### Child Lock (Physical Button)
```bash
uv run feeder lock on
uv run feeder lock off
```

### Calibrate Weighing Scale (Tare)
```bash
uv run feeder calibrate
```

### Configure Screen Display
```bash
# Choose what metric to display:
uv run feeder screen left    # Left-gram-display (Remaining bowl food)
uv run feeder screen eaten   # Eaten-gram-display (Intake today)
uv run feeder screen percent # Percentage-display (Target plan progress)

# Turn screen off when idle (auto-sleep mode):
uv run feeder screen-sleep on   # Screen stays OFF when idle
uv run feeder screen-sleep off  # Screen stays ALWAYS ON

# Turn screen on dynamically during feeding (shows live dispensing progress)
uv run feeder screen-progress on
uv run feeder screen-progress off
```

### Configure Hopper Refill Reminder
```bash
# Enable reminder with custom interval cycle in hours (e.g. 6, 8, 12, 24)
uv run feeder refill-reminder on --hours 6

# Turn off refill reminder
uv run feeder refill-reminder off

# Acknowledge / clear active refill reminder alert flag
uv run feeder clear-refill-alert
```

### Abnormal / Low Food Intake Alarm
Alerts if the pet's total daily intake is below a target percentage of their daily food plan (0–100%):
```bash
# Enable low intake alarm (alert if daily intake < 25% of plan)
uv run feeder intake-alarm on --threshold 25

# Turn off low intake alarm
uv run feeder intake-alarm off

# Acknowledge / clear active low intake alert flag
uv run feeder clear-intake-alert
```

### Onboard Hardware EEPROM Schedule (Offline Feeding Plan)
The feeder contains non-volatile storage and an RTC to dispense food automatically without needing Wi-Fi or a computer:

- **View active hardware schedule in device memory**:
  ```bash
  uv run feeder schedule-get
  uv run feeder schedule-get --json
  ```

- **Set/upload offline feeding schedule directly to device EEPROM**:
  ```bash
  # Sets 08:00 (2 portions, once) and 21:30 (1 portion, daily)
  uv run feeder schedule-set 08:00=2:once 21:30=1:daily

  # Or using simple default (daily)
  uv run feeder schedule-set 07:30=1 13:00=2 19:30=2
  ```

- **Clear hardware schedule from device memory**:
  ```bash
  uv run feeder schedule-clear
  ```

- **Enable / Disable hardware schedule switch**:
  ```bash
  uv run feeder schedule-enable on
  uv run feeder schedule-enable off
  ```

### Raw MIOT Property / Action Query
```bash
# Query SIID 2, PIID 1 (Device Fault)
uv run feeder raw-get 2 1

# Set SIID 3, PIID 1 (Child Lock) to true
uv run feeder raw-set 3 1 true
```

---

## Installation & Library Usage

### Install from PyPI
```bash
pip install xiaomi-feeder-2
# or with uv
uv add xiaomi-feeder-2
```

### Python API Usage (Synchronous)

```python
from xiaomi_feeder_2 import XiaomiFeeder

# Initialize connection
feeder = XiaomiFeeder(ip="192.168.1.100", token="your_32_character_token")

# Get device status
status = feeder.status()
print(f"Food hopper status: {status.food_level}")
print(f"Current bowl weight: {status.bowl_food_weight}g")
print(f"Food stuck error: {status.food_stuck}")

# Dispense 2 portions of food (~24g)
feeder.feed(2)

# Lock physical buttons
feeder.set_child_lock(True)

# Calibrate scale
feeder.calibrate_scale()
```

### Async API Usage (Home Assistant & AsyncIO)

```python
import asyncio
from xiaomi_feeder_2 import XiaomiFeeder, XiaomiFeederError

async def main():
    feeder = XiaomiFeeder(ip="192.168.1.100", token="your_32_character_token")
    
    try:
        # Non-blocking status fetch
        status = await feeder.async_status()
        print(f"Bowl weight: {status.bowl_food_weight}g, Hopper: {status.food_level}")
        
        # Non-blocking feed
        await feeder.async_feed(1)
    except XiaomiFeederError as err:
        print(f"Feeder communication error: {err}")

asyncio.run(main())
```

### Home Assistant / HACS Integration

To use this library in a custom component manifest (`custom_components/<domain>/manifest.json`):
```json
{
  "domain": "xiaomi_feeder_2",
  "name": "Xiaomi Smart Pet Food Feeder 2",
  "requirements": ["xiaomi-feeder-2>=0.2.0"]
}
```

---

## ℹ️ Note on Desiccant Tracking

On the **Xiaomi Smart Pet Food Feeder 2 (`xiaomi.feeder.iv2001`)**, desiccant life is **not tracked in the device firmware/hardware registers**:
- The device has no physical chemical sensor for silica gel.
- Even though the standard MIoT spec template includes Service 6 (`desiccant`), the microcontroller registers (`SIID 6, PIID 1 & 2`) always return `0` over local MIoT.
- The official Xiaomi Home app manages the 30-day desiccant countdown exclusively in the **Xiaomi Cloud / App UI** based on the recorded replacement date.
- Consequently, local desiccant tracking is not supported by the physical hardware.

---

## Specification Reference

- Model: `xiaomi.feeder.iv2001`
- MIOT Type: `urn:miot-spec-v2:device:pet-feeder:0000A06C:xiaomi-iv2001:2`
- Official Spec: [home.miot-spec.com/spec/xiaomi.feeder.iv2001](https://home.miot-spec.com/spec/xiaomi.feeder.iv2001)

---

## License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0-or-later)**. See the [LICENSE](LICENSE) file for details.


