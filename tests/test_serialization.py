import io
from dataclasses import fields
from pathlib import Path

import pandas as pd
import pytest

from xbmini.heading_parser import HeaderInfo, LoggerType, SensorInfo, SensorSpec
from xbmini.log_parser import XBMLog

# Start with round-trips and drill into components later if necessary

DUMMY_SENSOR = SensorInfo(
    name="The Best Sensor",
    sample_rate=200,
    sensitivity=2048,
    full_scale=16,
    units="g",
)


def test_sensor_info_roundtrip() -> None:
    assert SensorInfo.from_json(DUMMY_SENSOR.to_json()) == DUMMY_SENSOR


DUMMY_SENSORS: SensorSpec = {"Accel": DUMMY_SENSOR, "Gyro": DUMMY_SENSOR, "Mag": DUMMY_SENSOR}
DUMMY_HEADER = HeaderInfo(
    n_header_lines=13,
    logger_type=LoggerType.HAM_IMU_ALT,
    firmware_version=42,
    serial="ABC123",
    sensors=DUMMY_SENSORS,
    header_spec=["foo", "bar", "baz"],
)


def test_header_info_roundtrip() -> None:
    assert HeaderInfo.from_json(DUMMY_HEADER.to_json()) == DUMMY_HEADER


DUMMY_HEADER_NO_SENSORS = HeaderInfo(
    n_header_lines=13,
    logger_type=LoggerType.HAM_IMU_ALT,
    firmware_version=42,
    serial="ABC123",
    sensors=None,
    header_spec=["foo", "bar", "baz"],
)


def test_header_info_no_sensors_roundtrip() -> None:
    assert HeaderInfo.from_json(DUMMY_HEADER_NO_SENSORS.to_json()) == DUMMY_HEADER_NO_SENSORS


DUMMY_HEADER_BAD_SENSORS = HeaderInfo(
    n_header_lines=13,
    logger_type=LoggerType.HAM_IMU_ALT,
    firmware_version=42,
    serial="ABC123",
    sensors={"Accel": []},  # type: ignore[arg-type]
    header_spec=["foo", "bar", "baz"],
)


def test_header_info_bad_sensor_info_raises() -> None:
    with pytest.raises(ValueError, match="SensorInfo"):
        _ = DUMMY_HEADER_BAD_SENSORS.to_dict()


def test_xbm_csv_roundtrip(tmp_log: Path) -> None:
    log = XBMLog.from_raw_log_file(tmp_log)
    tmp_csv = tmp_log.parent / "test_csv.csv"
    log.to_csv(tmp_csv)

    # Test dataframes separately since XBMLog doesn't have a custom __eq__
    # Will throw warnings about ambiguous DF comparisons otherwise
    test_log = XBMLog.from_processed_csv(tmp_csv)
    for field in fields(log):
        if isinstance(getattr(test_log, field.name), pd.DataFrame):
            pd.testing.assert_frame_equal(getattr(log, field.name), getattr(test_log, field.name))
        else:
            assert getattr(log, field.name) == getattr(test_log, field.name)


def test_xbm_stringio_roundtrip(tmp_log: Path) -> None:
    log = XBMLog.from_raw_log_file(tmp_log)
    buff = io.StringIO()
    buff.write(log._to_string())
    buff.seek(0)

    # Test dataframes separately since XBMLog doesn't have a custom __eq__
    # Will throw warnings about ambiguous DF comparisons otherwise
    test_log = XBMLog.from_processed_csv(buff)
    for field in fields(log):
        if isinstance(getattr(test_log, field.name), pd.DataFrame):
            pd.testing.assert_frame_equal(getattr(log, field.name), getattr(test_log, field.name))
        else:
            assert getattr(log, field.name) == getattr(test_log, field.name)
