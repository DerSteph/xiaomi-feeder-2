"""Comprehensive unit tests for Xiaomi Smart Pet Food Feeder 2 controller and library."""

import json
from unittest.mock import MagicMock, patch
import pytest

from xiaomi_feeder import (
    FeederAIID,
    FeederPIID,
    FeederSIID,
    FeederStatus,
    XiaomiFeeder,
    XiaomiFeederConnectionError,
    XiaomiFeederDeviceError,
    XiaomiFeederError,
)
from xiaomi_feeder.cli import create_parser, format_schedule_output, format_status_output, main
import xiaomi_feeder


@pytest.fixture
def mock_device():
    with patch("xiaomi_feeder.client.Device") as mock_dev_cls:
        mock_instance = MagicMock()
        mock_dev_cls.return_value = mock_instance
        yield mock_instance


def test_package_exports():
    """Verify that xiaomi_feeder exports all public classes and constants."""
    assert hasattr(xiaomi_feeder, "XiaomiFeeder")
    assert hasattr(xiaomi_feeder, "FeederStatus")
    assert hasattr(xiaomi_feeder, "ScheduleMeal")
    assert hasattr(xiaomi_feeder, "SchedulePlan")
    assert hasattr(xiaomi_feeder, "XiaomiFeederError")
    assert hasattr(xiaomi_feeder, "FeederSIID")
    assert hasattr(xiaomi_feeder, "FeederPIID")
    assert hasattr(xiaomi_feeder, "FeederAIID")
    assert xiaomi_feeder.__version__ == "0.2.0"


def test_feeder_init_validation():
    with pytest.raises(ValueError, match="Both IP address and token are required"):
        XiaomiFeeder(ip="", token="12345678901234567890123456789012")

    with pytest.raises(ValueError, match="Invalid token length"):
        XiaomiFeeder(ip="192.168.1.50", token="invalid_short_token")

    # Valid init
    feeder = XiaomiFeeder(ip="192.168.1.50", token="a" * 32)
    assert feeder.ip == "192.168.1.50"
    assert feeder.token == "a" * 32


def test_feed_action(mock_device):
    feeder = XiaomiFeeder(ip="192.168.1.50", token="a" * 32)
    mock_device.send.return_value = {"code": 0, "out": []}

    res = feeder.feed(15)
    assert res["code"] == 0
    mock_device.send.assert_called_with(
        "action",
        {
            "did": "action",
            "siid": FeederSIID.PET_FEEDER,
            "aiid": FeederAIID.PET_FOOD_OUT,
            "in": [{"piid": FeederPIID.FEEDING_MEASURE, "value": 15}],
        },
    )

    # Invalid feed amount
    with pytest.raises(ValueError, match="outside safe range"):
        feeder.feed(0)

    with pytest.raises(ValueError, match="outside safe range"):
        feeder.feed(50)


def test_child_lock(mock_device):
    feeder = XiaomiFeeder(ip="192.168.1.50", token="a" * 32)
    mock_device.send.return_value = [{"did": "prop", "siid": 3, "piid": 1, "code": 0}]

    feeder.set_child_lock(True)
    mock_device.send.assert_called_with(
        "set_properties",
        [{"did": "prop", "siid": FeederSIID.PHYSICAL_LOCK, "piid": FeederPIID.PHYSICAL_LOCK, "value": True}],
    )

    feeder.set_child_lock(False)
    mock_device.send.assert_called_with(
        "set_properties",
        [{"did": "prop", "siid": FeederSIID.PHYSICAL_LOCK, "piid": FeederPIID.PHYSICAL_LOCK, "value": False}],
    )


def test_calibrate_scale(mock_device):
    feeder = XiaomiFeeder(ip="192.168.1.50", token="a" * 32)
    mock_device.send.return_value = {"code": 0, "out": []}

    res = feeder.calibrate_scale()
    assert res["code"] == 0
    mock_device.send.assert_called_once_with(
        "action",
        {
            "did": "action",
            "siid": FeederSIID.PET_FEEDER,
            "aiid": FeederAIID.WEIGH_CALIBRATE,
            "in": [],
        },
    )


def test_set_screen_display(mock_device):
    feeder = XiaomiFeeder(ip="192.168.1.50", token="a" * 32)
    mock_device.send.return_value = [{"code": 0}]

    feeder.set_screen_display("left")
    mock_device.send.assert_called_with(
        "set_properties",
        [{"did": "prop", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.SCREEN_DISPLAY, "value": 0}],
    )

    feeder.set_screen_display("eaten")
    mock_device.send.assert_called_with(
        "set_properties",
        [{"did": "prop", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.SCREEN_DISPLAY, "value": 1}],
    )

    feeder.set_screen_display("percent")
    mock_device.send.assert_called_with(
        "set_properties",
        [{"did": "prop", "siid": FeederSIID.CUSTOM, "piid": FeederPIID.SCREEN_DISPLAY, "value": 2}],
    )

    with pytest.raises(ValueError, match="Invalid screen mode"):
        feeder.set_screen_display("invalid_mode")


def test_toggles(mock_device):
    feeder = XiaomiFeeder(ip="192.168.1.50", token="a" * 32)
    mock_device.send.return_value = [{"code": 0}]

    feeder.set_screen_auto_sleep(True)
    feeder.set_screen_progress_display(True)
    feeder.set_anti_stacking(True)
    feeder.set_grain_compensation(True)
    assert mock_device.send.call_count == 4


def test_status_parsing(mock_device):
    feeder = XiaomiFeeder(ip="192.168.1.50", token="a" * 32)

    mock_device.send.return_value = [
        {"siid": 2, "piid": 1, "value": 0, "code": 0},   # fault
        {"siid": 2, "piid": 6, "value": 0, "code": 0},   # food left normal
        {"siid": 2, "piid": 7, "value": 2, "code": 0},   # target measure
        {"siid": 2, "piid": 10, "value": 0, "code": 0},  # food stuck
        {"siid": 2, "piid": 11, "value": 0, "code": 0},  # food out status
        {"siid": 2, "piid": 15, "value": 0, "code": 0},  # heap
        {"siid": 2, "piid": 18, "value": 45, "code": 0}, # daily eaten
        {"siid": 2, "piid": 20, "value": 12, "code": 0}, # last eaten
        {"siid": 2, "piid": 23, "value": 5, "code": 0},  # prev eaten
        {"siid": 2, "piid": 22, "value": 120, "code": 0},# bowl weight
        {"siid": 2, "piid": 26, "value": 0, "code": 0},  # busy26
        {"siid": 2, "piid": 31, "value": 2, "code": 0},  # level detail
        {"siid": 2, "piid": 32, "value": 0, "code": 0},  # busy32
        {"siid": 3, "piid": 1, "value": False, "code": 0}, # lock
        {"siid": 3, "piid": 3, "value": 1, "code": 0},   # sleep
        {"siid": 4, "piid": 1, "value": True, "code": 0}, # battery
        {"siid": 5, "piid": 14, "value": 1, "code": 0},  # anti stack
        {"siid": 5, "piid": 12, "value": 1, "code": 0},  # grain comp
        {"siid": 5, "piid": 18, "value": 1, "code": 0},  # screen mode: eaten
        {"siid": 5, "piid": 4, "value": 1, "code": 0},   # screen prog
        {"siid": 5, "piid": 3, "value": 1, "code": 0},   # add state
        {"siid": 5, "piid": 10, "value": 6, "code": 0},  # add cycle
        {"siid": 5, "piid": 1, "value": "[1,08000201]", "code": 0}, # schedule
        {"siid": 5, "piid": 8, "value": 1, "code": 0},   # schedule switch
        {"siid": 5, "piid": 17, "value": 7200, "code": 0}, # tz UTC+2
        {"siid": 5, "piid": 19, "value": 1, "code": 0},  # dst
        {"siid": 5, "piid": 5, "value": 10, "code": 0},  # intake rate
        {"siid": 5, "piid": 6, "value": 1, "code": 0},   # intake state
    ]

    status = feeder.status()

    assert not status.device_fault
    assert not status.food_stuck
    assert not status.food_out_error
    assert not status.food_heap_detected
    assert not status.has_error
    assert not status.is_food_low
    assert status.food_level == "Normal"
    assert status.bowl_food_weight == 120
    assert status.daily_eaten_weight == 45
    assert not status.is_busy
    assert status.target_feeding_portions == 2
    assert not status.child_lock
    assert status.battery_level is True
    assert status.screen_display_mode == "Eaten-gram-display"
    assert status.screen_auto_sleep is True
    assert status.anti_stacking is True
    assert status.grain_compensation is True
    assert status.hardware_schedule_active is True
    assert status.hardware_schedule_count == 1
    assert status.refill_reminder_enabled is True
    assert status.refill_reminder_hours == 6
    assert status.device_timezone_sec == 7200
    assert status.dst_active is True

    # Test format table
    table = format_status_output(status)
    assert "Xiaomi Smart Pet Food Feeder 2 Status" in table
    assert "120 g" in table
    assert "Eaten-gram-display" in table


@pytest.mark.asyncio
async def test_async_methods(mock_device):
    feeder = XiaomiFeeder(ip="192.168.1.50", token="a" * 32)
    mock_device.send.return_value = {"code": 0, "out": []}

    feed_res = await feeder.async_feed(2)
    assert feed_res["code"] == 0

    cal_res = await feeder.async_calibrate_scale()
    assert cal_res["code"] == 0

    mock_device.send.return_value = [{"code": 0}]
    await feeder.async_set_child_lock(True)
    await feeder.async_set_anti_stacking(True)
    await feeder.async_set_grain_compensation(True)


def test_hardware_schedule_parser(mock_device):
    feeder = XiaomiFeeder(ip="192.168.1.50", token="a" * 32)

    mock_device.send.return_value = [
        {"did": "p_sched", "value": "[1,08000201,18300101,22000100]"},
        {"did": "p_state", "value": 1},
    ]

    sched = feeder.get_hardware_schedule()
    assert sched["enabled"] is True
    assert len(sched["meals"]) == 3
    assert sched["meals"][0] == {"time": "08:00", "portions": 2, "repeat": 1, "raw": "08000201"}
    assert sched["meals"][1] == {"time": "18:30", "portions": 1, "repeat": 1, "raw": "18300101"}
    assert sched["meals"][2] == {"time": "22:00", "portions": 1, "repeat": 0, "raw": "22000100"}

    table = format_schedule_output(sched)
    assert "08:00" in table
    assert "Daily / Everyday" in table
    assert "Once (One-time)" in table


def test_cli_parser():
    parser = create_parser()

    args = parser.parse_args(["--ip", "1.2.3.4", "--token", "a" * 32, "status"])
    assert args.command == "status"
    assert args.ip == "1.2.3.4"
    assert args.token == "a" * 32

    args = parser.parse_args(["--ip", "1.2.3.4", "--token", "a" * 32, "feed", "3", "--watch"])
    assert args.command == "feed"
    assert args.portions == 3
    assert args.watch is True


def test_cli_main_status(mock_device, capsys):
    mock_device.send.return_value = [
        {"siid": 2, "piid": 1, "value": 0, "code": 0},
        {"siid": 2, "piid": 6, "value": 0, "code": 0},
        {"siid": 2, "piid": 7, "value": 1, "code": 0},
        {"siid": 2, "piid": 10, "value": 0, "code": 0},
        {"siid": 2, "piid": 11, "value": 0, "code": 0},
        {"siid": 2, "piid": 15, "value": 0, "code": 0},
        {"siid": 2, "piid": 18, "value": 0, "code": 0},
        {"siid": 2, "piid": 20, "value": 0, "code": 0},
        {"siid": 2, "piid": 23, "value": 0, "code": 0},
        {"siid": 2, "piid": 22, "value": 50, "code": 0},
        {"siid": 2, "piid": 26, "value": 0, "code": 0},
        {"siid": 2, "piid": 31, "value": 2, "code": 0},
        {"siid": 2, "piid": 32, "value": 0, "code": 0},
        {"siid": 3, "piid": 1, "value": False, "code": 0},
        {"siid": 3, "piid": 3, "value": 0, "code": 0},
        {"siid": 4, "piid": 1, "value": True, "code": 0},
        {"siid": 5, "piid": 14, "value": 1, "code": 0},
        {"siid": 5, "piid": 12, "value": 1, "code": 0},
        {"siid": 5, "piid": 18, "value": 0, "code": 0},
        {"siid": 5, "piid": 4, "value": 0, "code": 0},
        {"siid": 5, "piid": 3, "value": 0, "code": 0},
        {"siid": 5, "piid": 10, "value": 6, "code": 0},
        {"siid": 5, "piid": 1, "value": "[0]", "code": 0},
        {"siid": 5, "piid": 8, "value": 0, "code": 0},
        {"siid": 5, "piid": 17, "value": 0, "code": 0},
        {"siid": 5, "piid": 19, "value": 0, "code": 0},
        {"siid": 5, "piid": 5, "value": 10, "code": 0},
        {"siid": 5, "piid": 6, "value": 0, "code": 0},
    ]

    ret = main(["--ip", "1.2.3.4", "--token", "a" * 32, "status", "--json"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["bowl_food_weight"] == 50
