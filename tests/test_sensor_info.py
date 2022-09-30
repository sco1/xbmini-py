from xbmini.parser import SensorInfo

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
