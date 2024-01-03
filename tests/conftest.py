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


SAMPLE_GPS_LOG = """\
;Title, http://www.gcdataconcepts.com, LSM6DSM, BMP384, GPS
;Version, 2570, Build date, Jan  1 2022,  SN:ABC122345F0420
;Start_time, 2022-09-26, 08:13:29.030
;Uptime, 6,sec,  Vbat, 4198, mv, EOL, 3500, mv
;Deadband, 0, counts
;DeadbandTimeout, 0.000,sec
;BMP384, SI, 0.100,sec, Units, Pa, mdegC
;Alt Trigger disabled
;LSM6DSM, SR,104,Hz, Units, mG, mdps, fullscale gyro 250dps, accel 4g
;Magnetometer, SR,10,Hz, Units, nT, Temperature, 19,degC
;CAM_M8 Gps, SR,1,Hz
;Gps Sats, TOW, 123456789, ver, 1, numSat, 13
;, gnssId, svId, cno, elev, azmith, prRes, flags,inUse
;, GPS , 001, 26, 23, 219, 0, 0x00001213
;, GPS , 002, 33, 65, 318, 0, 0x00001213
;, GPS , 003, 00, 35, 298, 0, 0x00001211
;, GPS , 004, 00, 04, 283, 0, 0x00001211
;, GPS , 005, 00, 29, 151, 0, 0x00001211
;, GPS , 006, 00, 20, 210, 0, 0x00001911
;, GPS , 007, 00, 46, 121, 0, 0x00001911
;, GPS , 008, 00, 35, 043, 0, 0x00001211
;Time, Ax, Ay, Az, Gx, Gy, Gz, Mx, My, Mz, P, T, TOW, Lat,Lon, Height(m), MSL(m), hdop(m), vdop(m)
9433200.0,100,100,100,200,200,200,300,300,300,100000,20000, 300000.6, 33.6571,-117.7462, 429.0, 457.0, 1.0,2.0
"""


@pytest.fixture
def tmp_log_gps(tmp_path: Path) -> Path:
    tmp_log = tmp_path / "log.CSV"
    tmp_log.write_text(SAMPLE_GPS_LOG)
    return tmp_log
