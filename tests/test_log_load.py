import datetime as dt
import math
from pathlib import Path

import pandas as pd

from xbmini.heading_parser import SensorInfo
from xbmini.log_parser import _split_press_temp, load_log


def test_log_loader(tmp_log: Path) -> None:
    df, _ = load_log(tmp_log)
    pd.testing.assert_frame_equal(df, TRUTH_DF, check_exact=False)


TRUTH_DF = pd.DataFrame(
    {
        "time": [dt.timedelta(seconds=0.01)],
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
        "pressure": [98405],  # With a single data row (no NaNs), this will be an int
        "temperature": [22.431],
        "total_accel": [1.121357],
        "total_accel_rolling": [1.121357],
    }
).set_index("time")


SENS_OVERRIDE = {
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

TRUTH_DF_SENS_OVERRIDE = pd.DataFrame(
    {
        "time": [dt.timedelta(seconds=0.01)],
        "accel_x": [0.547363],
        "accel_y": [-0.0073242],
        "accel_z": [0.0117187],
        "gyro_x": [-0.062500],
        "gyro_y": [0.125],
        "gyro_z": [0.0],
        "quat_w": [0.782693],
        "quat_x": [-0.028025],
        "quat_y": [-0.620550],
        "quat_z": [-0.0390345],
        "mag_x": [4.411164],
        "mag_y": [-40.876351],
        "mag_z": [28.270708],
        "pressure": [98405],  # With a single data row (no NaNs), this will be an int
        "temperature": [22.431],
        "total_accel": [0.547538],
        "total_accel_rolling": [0.547538],
    }
).set_index("time")


def test_log_loader_sens_override(tmp_log: Path) -> None:
    df, _ = load_log(tmp_log, sensitivity_override=SENS_OVERRIDE)
    pd.testing.assert_frame_equal(df, TRUTH_DF_SENS_OVERRIDE, check_exact=False)


TRUTH_DF_MULTILINE = pd.DataFrame(
    {
        "time": [dt.timedelta(seconds=0.1), dt.timedelta(seconds=0.2), dt.timedelta(seconds=0.3)],
        "accel_x": [1, 2, 3],
        "pressure": [98405.0, math.nan, 98406.0],
        "temperature": [22, 23, 24],
    }
).set_index("time")

TRUTH_MPU_SPLIT = pd.DataFrame(
    {
        "time": [dt.timedelta(seconds=0.1), dt.timedelta(seconds=0.2), dt.timedelta(seconds=0.3)],
        "accel_x": [1, 2, 3],
    }
).set_index("time")

TRUTH_PRESS_TEMP_SPLIT = pd.DataFrame(
    {
        "time": [dt.timedelta(seconds=0.1), dt.timedelta(seconds=0.3)],
        "pressure": [98405.0, 98406.0],
        "temperature": [22, 24],
    }
).set_index("time")


def test_split_press_temp() -> None:
    press_temp, mpu = _split_press_temp(TRUTH_DF_MULTILINE)
    pd.testing.assert_frame_equal(press_temp, TRUTH_PRESS_TEMP_SPLIT, check_exact=False)
    pd.testing.assert_frame_equal(mpu, TRUTH_MPU_SPLIT, check_exact=False)
