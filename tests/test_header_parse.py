import pytest

from xbmini.heading_parser import HeaderInfo, LoggerType, ParserError, parse_header

SAMPLE_HEADER = [
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
)


def test_header_parse() -> None:
    assert parse_header(SAMPLE_HEADER) == TRUTH_HEADER_INFO


SAMPLE_HEADER_MISSING_INFO = [
    "Version, 2108, Build date, Jan  1 2022,  SN:ABC122345F0420",
    "MPU, SR (Hz), Sens (counts/unit), FullScale (units), Units",
    "Accel, 227, 1000, 16, g",
    "Gyro, 227, 1, 250, dps",
    "Mag, 75, 1, 4900000, nT",
    "Time, P, T",
]


def test_missing_info_raises() -> None:
    with pytest.raises(ParserError):
        parse_header(SAMPLE_HEADER_MISSING_INFO)
