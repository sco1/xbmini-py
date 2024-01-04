from pathlib import Path

import pytest

from xbmini.heading_parser import ParserError, extract_header

SAMPLE_LOG_FILE = """\
;Title, http://www.gcdataconcepts.com, HAM-IMU+alt, MPU9250 BMP280
;Version, 2108, Build date, Jan  1 2022,  SN:ABC122345F0420
0.001892,926,-40,344,0,0,0,0.824,-0.034,-0.564,-0.020,-34950,-54750,-46650,101485,22590
"""

TRUTH_HEADER_LINES = [
    "Title, http://www.gcdataconcepts.com, HAM-IMU+alt, MPU9250 BMP280",
    "Version, 2108, Build date, Jan  1 2022,  SN:ABC122345F0420",
]


def test_header_extract(tmp_path: Path) -> None:
    tmp_log = tmp_path / "log.CSV"
    tmp_log.write_text(SAMPLE_LOG_FILE)

    assert extract_header(tmp_log) == TRUTH_HEADER_LINES


def test_no_header_raises(tmp_path: Path) -> None:
    tmp_log = tmp_path / "log.CSV"
    tmp_log.write_text("Hello world!")

    with pytest.raises(ParserError):
        extract_header(tmp_log)


SAMPLE_SENSOR_FAULT = """\
;Title, http://www.gcdataconcepts.com, HAM-IMU+alt, MPU9250 BMP280
;Version, 2108, Build date, Jan  1 2022,  SN:ABC122345F0420
;Start_time, 2022-01-01, 04:20:34.497
;Uptime, 5,sec,  Vbat, 3754, mv, EOL, 3500, mv
MPU Fault
;BMP280 SI, 0.050,s
;Deadband, 0, counts
;DeadbandTimeout, 5.000,sec
;Time, Ax, Ay, Az, Gx, Gy, Gz, Qw, Qx, Qy, Qz, Mx, My, Mz, P, T
; 0.000 stopping logging: shutdown: switched off
"""


def test_sensor_fault_handling(tmp_path: Path) -> None:
    tmp_log = tmp_path / "log.CSV"
    tmp_log.write_text(SAMPLE_SENSOR_FAULT)

    with pytest.raises(ParserError):
        extract_header(tmp_log)
