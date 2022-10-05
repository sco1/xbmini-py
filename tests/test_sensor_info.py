import pytest

from xbmini.parser import SensorInfo, SensorParseError

SAMPLE_HEADER_LINE = "Accel, 225, 1000, 16, g"
TRUTH_SENSOR_INFO = SensorInfo(
    name="Accel",
    sample_rate=225,
    sensitivity=1000,
    full_scale=16,
    units="g",
)


def test_from_header_line() -> None:
    assert SensorInfo.from_header_line(SAMPLE_HEADER_LINE) == TRUTH_SENSOR_INFO


SAMPLE_LEGACY_HEADER = """\
MPU SR, 200,Hz,  Accel sens, 2048,counts/g, Gyro sens, 16,counts/dps,  Mag SR, 10,Hz,  Mag sens, 1666,counts/mT
"""
TRUTH_LEGACY_SENSOR_INFO = {
    "Accel": SensorInfo(
        name="Accel",
        sample_rate=200,
        sensitivity=2048,
        full_scale=-1,
        units="g",
    ),
    "Gyro": SensorInfo(
        name="Gyro",
        sample_rate=200,
        sensitivity=16,
        full_scale=-1,
        units="dps",
    ),
    "Mag": SensorInfo(
        name="Mag",
        sample_rate=10,
        sensitivity=1666,
        full_scale=-1,
        units="mT",
    ),
}


def test_legacy_sensor_info() -> None:
    assert SensorInfo.from_legacy_header(SAMPLE_LEGACY_HEADER) == TRUTH_LEGACY_SENSOR_INFO


SAMPLE_LEGACY_HEADER_BAD_MPU_NAME = """\
MPOO SR, 200,Hz,  Accel sens, 2048,counts/g, Gyro sens, 16,counts/dps,  Mag SR, 10,Hz,  Mag sens, 1666,counts/mT
"""


def test_legacy_header_bad_mpu_name_raises() -> None:
    with pytest.raises(SensorParseError):
        SensorInfo.from_legacy_header(SAMPLE_LEGACY_HEADER_BAD_MPU_NAME)


SAMPLE_LEGACY_HEADER_BAD_SENSOR_NAME = """\
MPU SR, 200,Hz,  Accello sens, 2048,counts/g, Gyro sens, 16,counts/dps,  Mag SR, 10,Hz,  Mag sens, 1666,counts/mT
"""


def test_legacy_header_bad_sensor_name_raises() -> None:
    with pytest.raises(SensorParseError):
        SensorInfo.from_legacy_header(SAMPLE_LEGACY_HEADER_BAD_SENSOR_NAME)


SAMPLE_LEGACY_HEADER_BAD_MAG_NAME = """\
MPU SR, 200,Hz,  Accel sens, 2048,counts/g, Gyro sens, 16,counts/dps,  Magoo SR, 10,Hz,  Mag sens, 1666,counts/mT
"""


def test_legacy_header_bad_mag_name_raises() -> None:
    with pytest.raises(SensorParseError):
        SensorInfo.from_legacy_header(SAMPLE_LEGACY_HEADER_BAD_MAG_NAME)
