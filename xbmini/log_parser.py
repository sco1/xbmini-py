from __future__ import annotations

import datetime as dt
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from xbmini.heading_parser import HeaderInfo, extract_header, parse_header

NUMERIC_T = int | float

SENSOR_GROUPS = {
    "Accel": ["accel_x", "accel_y", "accel_z"],
    "Gyro": ["gyro_x", "gyro_y", "gyro_z"],
    "Mag": ["mag_x", "mag_y", "mag_z"],
    "Quat": ["quat_x", "quat_y", "quat_z", "quat_w"],
}
IMU_SENSORS = ("Accel", "Gyro", "Mag")

PRESS_TEMP_COLS = ["pressure", "temperature"]  # Pandas needs as a list for indexing

ROLLING_WINDOW_WIDTH = 200


class HasSensitivity(t.Protocol):  # noqa: D101
    sensitivity: int


def load_log(
    log_filepath: Path,
    sensor_groups: dict[str, list[str]] = SENSOR_GROUPS,
    sensitivity_override: None | t.Mapping[str, HasSensitivity] = None,
    rolling_window_width: int = ROLLING_WINDOW_WIDTH,
) -> tuple[pd.DataFrame, HeaderInfo]:
    """
    Load data from the provided XBM log file.

    To work around known issues with some firmware where the sensor headers do not provide the
    correct counts/unit conversion constant, `sensitivity_override` may be optionally specified to
    manually provide these constants.
    """
    header_info = parse_header(extract_header(log_filepath))

    full_data = pd.read_csv(
        log_filepath,
        skiprows=header_info.n_header_lines,
        header=None,
        names=header_info.header_spec,
        index_col="time",
        comment=";",
    )

    # Convert measurements from raw counts to measured values
    if sensitivity_override:
        sensor_info = sensitivity_override
    else:
        sensor_info = header_info.sensors

    for sensor in IMU_SENSORS:
        for column in sensor_groups[sensor]:
            full_data[column] = full_data[column] / sensor_info[sensor].sensitivity

    # Calculate total acceleration & a rolling average
    full_data["total_accel"] = full_data[sensor_groups["Accel"]].pow(2).sum(axis=1).pow(1 / 2)
    full_data["total_accel_rolling"] = (
        full_data["total_accel"].rolling(rolling_window_width, center=True).mean()
    )

    # Convert temperature from mill-degree C to C
    full_data["temperature"] = full_data["temperature"] / 1000

    # Convert quaternion data, incoming as 16bit values, then normalize with RMS
    quat_cols = sensor_groups["Quat"]
    full_data[quat_cols] = full_data[quat_cols] / 65536
    q_rms = full_data[quat_cols].pow(2).sum(axis=1).pow(1 / 2)
    for col in quat_cols:
        # Not sure what the magic pandas invocation is do do this without a loop
        full_data[col] = full_data[col] / q_rms

    return full_data, header_info


def _split_press_temp(
    log_df: pd.DataFrame, columns: t.List[str] = PRESS_TEMP_COLS
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split off temperature & pressure columns since they sample at a lower rate.

    The columns are dropped from the incoming `DataFrame`, and the modified dataframe is returned.
    """
    press_temp_df = log_df[columns].dropna(axis=0)
    log_df = log_df.drop(columns, axis=1, errors="ignore")

    return press_temp_df, log_df


@dataclass(slots=True)
class XBMLog:  # noqa: D101
    mpu: pd.DataFrame
    press_temp: pd.DataFrame
    header_info: HeaderInfo
    drop_date: dt.date | None = None
    drop_location: str | None = None
    drop_id: str | None = None
    _is_merged: bool = False
    _is_trimmed: bool = False

    analysis_dt: dt.datetime = field(default_factory=dt.datetime.now)
    _ground_pressure: NUMERIC_T = 101_325  # Pascals
    total_rigged_weight: None | NUMERIC_T = None

    def __post_init__(self) -> None:
        # Calculate pressure altitude using the specified ground level pressure
        self._calculate_pressure_altitude()

    def _calculate_pressure_altitude(self) -> None:
        self.press_temp["press_alt_m"] = 44_330 * (
            1 - (self.press_temp["pressure"] / self.ground_pressure).pow(1 / 5.225)
        )
        self.press_temp["press_alt_ft"] = self.press_temp["press_alt_m"] * 3.2808

    @property
    def logger_id(self) -> str:  # noqa: D102
        return self.header_info.serial

    @property
    def ground_pressure(self) -> NUMERIC_T:  # noqa: D102
        return self._ground_pressure

    @ground_pressure.setter
    def ground_pressure(self, pressure: NUMERIC_T) -> None:
        """Recalculate pressure altitudes if the ground pressure changes."""
        self._ground_pressure = pressure
        self._calculate_pressure_altitude()

    @classmethod
    def from_log_file(
        cls,
        log_filepath: Path,
        sensor_groups: dict[str, list[str]] = SENSOR_GROUPS,
        sensitivity_override: None | t.Mapping[str, HasSensitivity] = None,
        rolling_window_width: int = ROLLING_WINDOW_WIDTH,
    ) -> XBMLog:
        """
        Build a log instance from the provided log file.

        To work around known issues with some firmware where the sensor headers do not provide the
        correct counts/unit conversion constant, `sensitivity_override` may be optionally specified
        to manually provide these constants.
        """
        # Since we're cheating and using the multi-load method, we have to set the merged flag back
        # to False before returning
        log = cls.from_multi_log(
            log_filepaths=(log_filepath,),
            sensor_groups=sensor_groups,
            sensitivity_override=sensitivity_override,
            rolling_window_width=rolling_window_width,
        )
        log._is_merged = False

        return log

    @classmethod
    def from_multi_log(
        cls,
        log_filepaths: t.Sequence[Path],
        sensor_groups: dict[str, list[str]] = SENSOR_GROUPS,
        sensitivity_override: None | t.Mapping[str, HasSensitivity] = None,
        rolling_window_width: int = ROLLING_WINDOW_WIDTH,
    ) -> XBMLog:
        """
        Build a log instance by joining the provided log files.

        It is assumed that all of the provided log files are from the same logging session, so they
        share the same header information and timeseries.

        To work around known issues with some firmware where the sensor headers do not provide the
        correct counts/unit conversion constant, `sensitivity_override` may be optionally specified
        to manually provide these constants.
        """
        header_info = parse_header(extract_header(log_filepaths[0]))
        full_data = pd.concat(
            [
                load_log(log_file, sensor_groups, sensitivity_override, rolling_window_width)[0]
                for log_file in log_filepaths
            ]
        )
        press_temp, mpu_data = _split_press_temp(full_data)

        return cls(
            mpu=mpu_data,
            press_temp=press_temp,
            header_info=header_info,
            _is_merged=True,
        )
