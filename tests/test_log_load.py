from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from tests.conftest import TRUTH_DF, TRUTH_DF_GPS
from xbmini.heading_parser import SensorInfo, SensorSpec
from xbmini.log_parser import PRESS_TEMP_COLS, XBMLog, _split_cols, load_log


def test_log_loader(tmp_log: Path) -> None:
    df, _ = load_log(tmp_log)
    assert_frame_equal(df, TRUTH_DF, check_exact=False)


def test_gps_log_loader(tmp_log_gps: Path) -> None:
    df, _ = load_log(tmp_log_gps)
    assert_frame_equal(df, TRUTH_DF_GPS, check_exact=False)


SENS_OVERRIDE: SensorSpec = {
    "Accel": SensorInfo(
        name="Accel",
        sample_rate=225,
        sensitivity=10,
        full_scale=-1,
        units="g",
    ),
    "Gyro": SensorInfo(
        name="Gyro",
        sample_rate=225,
        sensitivity=10,
        full_scale=-1,
        units="dps",
    ),
    "Mag": SensorInfo(
        name="Mag",
        sample_rate=75,
        sensitivity=10,
        full_scale=-1,
        units="mT",
    ),
}

TRUTH_DF_SENS_OVERRIDE = pl.DataFrame(
    {
        "time": [0.01],
        "accel_x": [112.1],
        "accel_y": [-001.5],
        "accel_z": [2.4],
        "gyro_x": [-0.10],
        "gyro_y": [0.20],
        "gyro_z": [0.0],
        "quat_w": [0.782693],
        "quat_x": [-0.0280248],
        "quat_y": [-0.620550],
        "quat_z": [-0.0390345],
        "mag_x": [734.90],
        "mag_y": [-6810.0],
        "mag_z": [4709.9],
        "pressure": [98405],  # With a single data row (no Nones), this will be an int
        "temperature": [22.431],
        "total_accel": [112.1357],
        "total_accel_rolling": [112.1357],
    }
)


def test_log_loader_sens_override(tmp_log: Path) -> None:
    df, _ = load_log(tmp_log, sensitivity_override=SENS_OVERRIDE)
    assert_frame_equal(df, TRUTH_DF_SENS_OVERRIDE, check_exact=False)


TRUTH_DF_MULTILINE = pl.DataFrame(
    {
        "time": [0.1, 0.2, 0.3],
        "accel_x": [1, 2, 3],
        "pressure": [98405.0, None, 98406.0],
        "temperature": [22, 23, 24],
    }
)

TRUTH_MPU_SPLIT = pl.DataFrame(
    {
        "time": [0.1, 0.2, 0.3],
        "accel_x": [1, 2, 3],
    }
)

TRUTH_PRESS_TEMP_SPLIT = pl.DataFrame(
    {
        "time": [0.1, 0.3],
        "pressure": [98405.0, 98406.0],
        "temperature": [22, 24],
    }
)


def test_split_cols() -> None:
    press_temp, mpu = _split_cols(TRUTH_DF_MULTILINE, columns=PRESS_TEMP_COLS)
    assert_frame_equal(
        press_temp, TRUTH_PRESS_TEMP_SPLIT, check_exact=False, check_column_order=False
    )
    assert_frame_equal(mpu, TRUTH_MPU_SPLIT, check_exact=False, check_column_order=False)


DUMMY_LOG_NO_SENSORS = """\
;Title, http://www.gcdataconcepts.com, HAM-IMU+alt, MPU9250 BMP280
;Version, 2108, Build date, Jan  1 2022,  SN:ABC122345F0420
;Start_time, 2022-09-26, 08:13:29.030
;Uptime, 6,sec,  Vbat, 4086, mv, EOL, 3500, mv
;BMP280 SI, 0.500,s
;Deadband, 0, counts
;DeadbandTimeout, 5.000,sec
;Time, Ax, Ay, Az, Gx, Gy, Gz, Qw, Qx, Qy, Qz, Mx, My, Mz, P, T
0.01,1121,-15,24,-1,2,0,0.782,-0.028,-0.620,-0.039,7349,-68100,47099,98405,22431
"""


def test_log_no_sensors_no_override_raises(tmp_path: Path) -> None:
    tmp_log = tmp_path / "log.CSV"
    tmp_log.write_text(DUMMY_LOG_NO_SENSORS)

    with pytest.raises(ValueError, match="No IMU sensor information"):
        _ = load_log(tmp_log, raise_on_missing_sensor=False)


def test_log_no_sensors_with_override(tmp_path: Path) -> None:
    tmp_log = tmp_path / "log.CSV"
    tmp_log.write_text(DUMMY_LOG_NO_SENSORS)

    df, _ = load_log(tmp_log, raise_on_missing_sensor=False, sensitivity_override=SENS_OVERRIDE)
    assert_frame_equal(df, TRUTH_DF_SENS_OVERRIDE, check_exact=False)


def test_log_no_sensors_bad_override_raises(tmp_path: Path) -> None:
    tmp_log = tmp_path / "log.CSV"
    tmp_log.write_text(DUMMY_LOG_NO_SENSORS)

    with pytest.raises(ValueError, match="SensorInfo"):
        _ = load_log(
            tmp_log,
            raise_on_missing_sensor=False,
            sensitivity_override={"Accel": []},  # type: ignore[arg-type]
        )


def test_load_processed_new_override(tmp_proc_log: Path) -> None:
    log_obj = XBMLog.from_processed_csv(tmp_proc_log, sensitivity_override=SENS_OVERRIDE)
    df = log_obj._full_dataframe
    df = df.drop(("press_alt_m", "press_alt_ft"))  # Derived quantities & not relevant here

    assert_frame_equal(df, TRUTH_DF_SENS_OVERRIDE, check_exact=False, check_column_order=False)
