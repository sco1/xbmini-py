from pathlib import Path

import pytest

SAMPLE_LOG_FILE = """\
;Title, http://www.gcdataconcepts.com, HAM-IMU+alt, MPU9250 BMP280
;Version, 2108, Build date, Jan  1 2022,  SN:ABC122345F0420
;Start_time, 2022-09-26, 08:13:29.030
;Uptime, 6,sec,  Vbat, 4086, mv, EOL, 3500, mv
;MPU, SR (Hz), Sens (counts/unit), FullScale (units), Units
;Accel, 225, 1000, 16, g
;Gyro, 225, 1, 250, dps
;Mag, 75, 1, 4900000, nT
;BMP280 SI, 0.500,s
;Deadband, 0, counts
;DeadbandTimeout, 5.000,sec
;Time, Ax, Ay, Az, Gx, Gy, Gz, Qw, Qx, Qy, Qz, Mx, My, Mz, P, T
0.01,1121,-15,24,-1,2,0,0.782,-0.028,-0.620,-0.039,7349,-68100,47099,98405,22431
"""

SAMPLE_LOG_FILE_2 = """\
;Title, http://www.gcdataconcepts.com, HAM-IMU+alt, MPU9250 BMP280
;Version, 2108, Build date, Jan  1 2022,  SN:ABC122345F0420
;Start_time, 2022-09-26, 08:13:29.030
;Uptime, 6,sec,  Vbat, 4086, mv, EOL, 3500, mv
;MPU, SR (Hz), Sens (counts/unit), FullScale (units), Units
;Accel, 225, 1000, 16, g
;Gyro, 225, 1, 250, dps
;Mag, 75, 1, 4900000, nT
;BMP280 SI, 0.500,s
;Deadband, 0, counts
;DeadbandTimeout, 5.000,sec
;Time, Ax, Ay, Az, Gx, Gy, Gz, Qw, Qx, Qy, Qz, Mx, My, Mz, P, T
0.02,1121,-15,24,-1,2,0,0.782,-0.028,-0.620,-0.039,7349,-68100,47099,98405,22431
"""


@pytest.fixture
def tmp_log(tmp_path: Path) -> Path:
    tmp_log = tmp_path / "log.CSV"
    tmp_log.write_text(SAMPLE_LOG_FILE)
    return tmp_log


@pytest.fixture
def tmp_multi_log(tmp_path: Path) -> list[Path]:
    tmp_log_1 = tmp_path / "log_1.CSV"
    tmp_log_1.write_text(SAMPLE_LOG_FILE)

    tmp_log_2 = tmp_path / "log_2.CSV"
    tmp_log_2.write_text(SAMPLE_LOG_FILE_2)

    return [tmp_log_1, tmp_log_2]
