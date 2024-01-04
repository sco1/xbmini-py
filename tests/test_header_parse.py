import pytest

from xbmini.heading_parser import HeaderInfo, LoggerType, ParserError, SensorInfo, parse_header

SAMPLE_HAM_IMU_HEADER = [
    "Title, http://www.gcdataconcepts.com, HAM-IMU+alt, MPU9250 BMP280",
    "Version, 2108, Build date, Jan  1 2022,  SN:ABC122345F0420",
    "Start_time, 2007-01-01, 00:00:46.824",
    "Uptime, 5,sec,  Vbat, 3172, mv, EOL, 3500, mv",
    "MPU, SR (Hz), Sens (counts/unit), FullScale (units), Units",
    "Accel, 227, 1000, 16, g",
    "Gyro, 227, 1, 250, dps",
    "Mag, 75, 1, 4900000, nT",
    "BMP280 SI, 0.050,s",
    "Deadband, 0, counts",
    "DeadbandTimeout, 5.000,sec",
    "Time, P, T",
]

TRUTH_HEADER_INFO = HeaderInfo(
    n_header_lines=12,
    logger_type=LoggerType.HAM_IMU_ALT,
    firmware_version=2108,
    serial="ABC122345F0420",
    header_spec=["time", "pressure", "temperature"],
    sensors={
        "Accel": SensorInfo(
            name="Accel", sample_rate=227, sensitivity=1000, full_scale=16, units="g"
        ),
        "Gyro": SensorInfo(
            name="Gyro", sample_rate=227, sensitivity=1, full_scale=250, units="dps"
        ),
        "Mag": SensorInfo(
            name="Mag", sample_rate=75, sensitivity=1, full_scale=4900000, units="nT"
        ),
    },
)


def test_header_parse() -> None:
    assert parse_header(SAMPLE_HAM_IMU_HEADER) == TRUTH_HEADER_INFO


SAMPLE_HEADER_BAD_VERSION = ["Version, beta, 2108, Build date, Jan  1 2022,  SN:ABC122345F0420"]


def test_bad_ver_raises() -> None:
    with pytest.raises(ParserError, match="Version"):
        parse_header(SAMPLE_HEADER_BAD_VERSION)


SAMPLE_HEADER_MISSING_TITLE_LINE = [
    "Version, 2108, Build date, Jan  1 2022,  SN:ABC122345F0420",
    "MPU, SR (Hz), Sens (counts/unit), FullScale (units), Units",
    "Accel, 227, 1000, 16, g",
    "Gyro, 227, 1, 250, dps",
    "Mag, 75, 1, 4900000, nT",
    "Time, P, T",
]


def test_missing_version_raises() -> None:
    with pytest.raises(ParserError, match="logger type"):
        parse_header(SAMPLE_HEADER_MISSING_TITLE_LINE)


SAMPLE_HAM_IMU_HEADER_MISSING_SENSOR = [
    "Title, http://www.gcdataconcepts.com, HAM-IMU+alt, MPU9250 BMP280",
    "Version, 2108, Build date, Jan  1 2022,  SN:ABC122345F0420",
    "Start_time, 2007-01-01, 00:00:46.824",
    "Uptime, 5,sec,  Vbat, 3172, mv, EOL, 3500, mv",
    "MPU, SR (Hz), Sens (counts/unit), FullScale (units), Units",
    "Accel, 227, 1000, 16, g",
    "Gyro, 227, 1, 250, dps",
    "BMP280 SI, 0.050,s",
    "Deadband, 0, counts",
    "DeadbandTimeout, 5.000,sec",
    "Time, P, T",
]


def test_missing_ham_imu_sensor_raises() -> None:
    with pytest.raises(ParserError, match="configuration"):
        parse_header(SAMPLE_HAM_IMU_HEADER_MISSING_SENSOR)


def test_missing_ham_imu_sensor_skip_error() -> None:
    hi = parse_header(SAMPLE_HAM_IMU_HEADER_MISSING_SENSOR, raise_on_missing_sensor=False)
    assert hi.sensors is None


SAMPLE_GPS_HEADER = [
    "Title, http://www.gcdataconcepts.com, LSM6DSM, BMP384, GPS",
    "Version, 2570, Build date, Jan  1 2022,  SN:ABC122345F0420",
    "Start_time, 2022-09-26, 08:13:29.030",
    "Uptime, 6,sec,  Vbat, 4198, mv, EOL, 3500, mv",
    "Deadband, 0, counts",
    "DeadbandTimeout, 0.000,sec",
    "BMP384, SI, 0.100,sec, Units, Pa, mdegC",
    "Alt Trigger disabled",
    "LSM6DSM, SR,104,Hz, Units, mG, mdps, fullscale gyro 250dps, accel 4g",
    "Magnetometer, SR,10,Hz, Units, nT, Temperature, 19,degC",
    "CAM_M8 Gps, SR,1,Hz",
    "Gps Sats, TOW, 123456789, ver, 1, numSat, 13",
    ", gnssId, svId, cno, elev, azmith, prRes, flags,inUse",
    ", GPS , 001, 26, 23, 219, 0, 0x00001213",
    "Time, P, T",
]

TRUTH_GPS_HEADER_INFO = HeaderInfo(
    n_header_lines=15,
    logger_type=LoggerType.IMU_GPS,
    firmware_version=2570,
    serial="ABC122345F0420",
    header_spec=["time", "pressure", "temperature"],
)


def test_gps_header_parse() -> None:
    assert parse_header(SAMPLE_GPS_HEADER) == TRUTH_GPS_HEADER_INFO
