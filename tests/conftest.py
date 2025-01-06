import datetime as dt
from pathlib import Path

import polars as pl
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

TRUTH_DF = pl.DataFrame(
    {
        "time": [0.01],
        "accel_x": [1.121],
        "accel_y": [-0.015],
        "accel_z": [0.024],
        "gyro_x": [-1.0],
        "gyro_y": [2.0],
        "gyro_z": [0.0],
        "quat_w": [0.782693],
        "quat_x": [-0.0280248],
        "quat_y": [-0.620550],
        "quat_z": [-0.0390345],
        "mag_x": [7349.0],
        "mag_y": [-68100.0],
        "mag_z": [47099.0],
        "pressure": [98405],  # With a single data row (no Nones), this will be an int
        "temperature": [22.431],
        "total_accel": [1.121357],
        "total_accel_rolling": [1.121357],
    }
)

# Generated manually from above log
SAMPLE_LOG_FILE_PROCESSED = """\
;{"drop_location": null, "drop_id": null, "_is_merged": false, "_is_trimmed": false, "_ground_pressure": 101325, "total_rigged_weight": null, "analysis_dt": 1731702483.543413, "drop_date": null, "header_info": {"n_header_lines": 12, "firmware_version": 2108, "serial": "ABC122345F0420", "header_spec": ["time", "accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z", "quat_w", "quat_x", "quat_y", "quat_z", "mag_x", "mag_y", "mag_z", "pressure", "temperature"], "logger_type": "HAM-IMU+alt", "sensors": {"Accel": {"name": "Accel", "sample_rate": 225, "sensitivity": 1000, "full_scale": 16, "units": "g"}, "Gyro": {"name": "Gyro", "sample_rate": 225, "sensitivity": 1, "full_scale": 250, "units": "dps"}, "Mag": {"name": "Mag", "sample_rate": 75, "sensitivity": 1, "full_scale": 4900000, "units": "nT"}}}}
time,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,quat_w,quat_x,quat_y,quat_z,mag_x,mag_y,mag_z,total_accel,total_accel_rolling,pressure,temperature,press_alt_m,press_alt_ft
0.01,1.121,-0.015,0.024,-1.0,2.0,0.0,0.7826933821208445,-0.028024826981309012,-0.6205497403004138,-0.03903458043825184,7349.0,-68100.0,47099.0,1.1213572133802858,1.1213572133802858,98405,22.431,247.39859833055823,811.6653214028955
"""

SAMPLE_LOG_FILE_MULTI_SAMPLE = """\
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
0.02,1121,-15,24,-1,2,0,0.782,-0.028,-0.620,-0.039,7349,-68100,47099,98405,22431
0.03,1121,-15,24,-1,2,0,0.782,-0.028,-0.620,-0.039,7349,-68100,47099,98405,22431
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
def tmp_log_multi_sample(tmp_path: Path) -> Path:
    tmp_log = tmp_path / "log.CSV"
    tmp_log.write_text(SAMPLE_LOG_FILE_MULTI_SAMPLE)
    return tmp_log


@pytest.fixture
def tmp_proc_log(tmp_path: Path) -> Path:
    tmp_log = tmp_path / "log.CSV"
    tmp_log.write_text(SAMPLE_LOG_FILE_PROCESSED)
    return tmp_log


@pytest.fixture
def tmp_multi_log(tmp_path: Path) -> list[Path]:
    tmp_log_1 = tmp_path / "log_1.CSV"
    tmp_log_1.write_text(SAMPLE_LOG_FILE)

    tmp_log_2 = tmp_path / "log_2.CSV"
    tmp_log_2.write_text(SAMPLE_LOG_FILE_2)

    return [tmp_log_1, tmp_log_2]


SAMPLE_LOG_FILE_POWER_OFF = """\
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
; 12.34 stopping logging: shutdown: switched off
"""

SAMPLE_LOG_FILE_LOW_BATTERY = """\
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
; 12.34 stopping logging: shutdown: low battery: 3490 mv
"""


@pytest.fixture
def tmp_multi_session(tmp_path: Path) -> list[Path]:
    tmp_log_1 = tmp_path / "log_1.CSV"
    tmp_log_1.write_text(SAMPLE_LOG_FILE)

    tmp_log_2 = tmp_path / "log_2.CSV"
    tmp_log_2.write_text(SAMPLE_LOG_FILE_POWER_OFF)

    tmp_log_3 = tmp_path / "log_3.CSV"
    tmp_log_3.write_text(SAMPLE_LOG_FILE_LOW_BATTERY)

    return [tmp_log_1, tmp_log_2, tmp_log_3]


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

TRUTH_DF_GPS = pl.DataFrame(
    {
        "time": [9433200.0],
        "accel_x": [0.1],
        "accel_y": [0.1],
        "accel_z": [0.1],
        "gyro_x": [0.2],
        "gyro_y": [0.2],
        "gyro_z": [0.2],
        "mag_x": [300],
        "mag_y": [300],
        "mag_z": [300],
        "pressure": [100000],  # With a single data row (no Nones), this will be an int
        "temperature": [20.0],
        "time_of_week": [300000.6],
        "latitude": [33.6571],
        "longitude": [-117.7462],
        "height_ellipsoid": [429.0],
        "height_msl": [457.0],
        "hdop": [1.0],
        "vdop": [2.0],
        "utc_timestamp": [dt.datetime.fromtimestamp(9433200, tz=dt.timezone.utc)],
        "total_accel": [0.03 ** (1 / 2)],
        "total_accel_rolling": [0.03 ** (1 / 2)],
    }
)

# Generated manually from above log
SAMPLE_GPS_LOG_PROCESSED = """\
;{"drop_location": null, "drop_id": null, "_is_merged": true, "_is_trimmed": false, "_ground_pressure": 101325, "total_rigged_weight": null, "analysis_dt": 1704489848.43016, "drop_date": null, "header_info": {"n_header_lines": 22, "firmware_version": 2570, "serial": "ABC122345F0420", "header_spec": ["time", "accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z", "mag_x", "mag_y", "mag_z", "pressure", "temperature", "time_of_week", "latitude", "longitude", "height_ellipsoid", "height_msl", "hdop", "vdop"], "logger_type": "GPS", "sensors": null}}
time,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,mag_x,mag_y,mag_z,total_accel,total_accel_rolling,pressure,temperature,press_alt_m,press_alt_ft,time_of_week,latitude,longitude,height_ellipsoid,height_msl,hdop,vdop,utc_timestamp

0 days,0.1,0.1,0.1,0.2,0.2,0.2,300,300,300,0.17320508075688776,0.17320508075688776,100000,20.0,111.53699607696909,365.9305767293202,300000.6,33.6571,-117.7462,429.0,457.0,1.0,2.0,1970-04-20 04:20:00+00:00
"""

SAMPLE_GPS_LOG_MULTI_SAMPLE = """\
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
9433200.00,100,100,100,200,200,200,300,300,300,100000,20000, 300000.6, 33.6571,-117.7462, 429.0, 457.0, 1.0,2.0
9433200.01,100,100,100,200,200,200,300,300,300,100000,20000, 300000.6, 33.6571,-117.7462, 429.0, 457.0, 1.0,2.0
9433200.02,100,100,100,200,200,200,300,300,300,100000,20000, 300000.6, 33.6571,-117.7462, 429.0, 457.0, 1.0,2.0
"""


@pytest.fixture
def tmp_log_gps(tmp_path: Path) -> Path:
    tmp_log = tmp_path / "log.CSV"
    tmp_log.write_text(SAMPLE_GPS_LOG)
    return tmp_log


@pytest.fixture
def tmp_log_gps_multi_sample(tmp_path: Path) -> Path:
    tmp_log = tmp_path / "log.CSV"
    tmp_log.write_text(SAMPLE_GPS_LOG_MULTI_SAMPLE)
    return tmp_log
