from __future__ import annotations

import datetime as dt
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from xbmini.heading_parser import HeaderInfo, extract_header, parse_header

NUMERIC_T = int | float

CONVERSION_GROUPS = {
    "Accel": ("accel_x", "accel_y", "accel_z"),
    "Gyro": ("gyro_x", "gyro_y", "gyro_z"),
    "Mag": ("mag_x", "mag_y", "mag_z"),
}

PRESS_TEMP_COLS = ["pressure", "temperature"]  # Pandas needs as a list for indexing
QUATERNION_COLS = ["quat_x", "quat_y", "quat_z", "quat_w"]  # Pandas needs as a list for indexing


class HasSensitivity(t.Protocol):  # noqa: D101
    sensitivity: int


def load_log(
    log_filepath: Path,
    conversion_groups: t.Mapping[str, tuple[str, ...]] = CONVERSION_GROUPS,
    sensitivity_override: None | t.Mapping[str, HasSensitivity] = None,
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

    for sensor, column_group in conversion_groups.items():
        for column in column_group:
            full_data[column] = full_data[column] / sensor_info[sensor].sensitivity

    # Convert temperature from mill-degree C to C
    full_data["temperature"] = full_data["temperature"] / 1000

    # Convert quaternion data, incoming as 16bit values, then normalize with RMS
    full_data[QUATERNION_COLS] = full_data[QUATERNION_COLS] / 65536
    q_rms = full_data[QUATERNION_COLS].pow(2).sum(axis=1).pow(1 / 2)
    for col in QUATERNION_COLS:
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
        conversion_groups: t.Mapping[str, tuple[str, ...]] = CONVERSION_GROUPS,
        sensitivity_override: None | t.Mapping[str, HasSensitivity] = None,
    ) -> XBMLog:
        """
        Build a log instance from the provided log file.

        To work around known issues with some firmware where the sensor headers do not provide the
        correct counts/unit conversion constant, `sensitivity_override` may be optionally specified
        to manually provide these constants.
        """
        # Since we're cheating and using the multi-load method, we have to set the merged flag back
        # to False before returning
        log = cls.from_multi_log((log_filepath,), conversion_groups, sensitivity_override)
        log._is_merged = False

        return log

    @classmethod
    def from_multi_log(
        cls,
        log_filepaths: t.Sequence[Path],
        conversion_groups: t.Mapping[str, tuple[str, ...]] = CONVERSION_GROUPS,
        sensitivity_override: None | t.Mapping[str, HasSensitivity] = None,
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
                load_log(log_file, conversion_groups, sensitivity_override)[0]
                for log_file in log_filepaths
            ]
        )
        press_temp, mpu_data = _split_press_temp(full_data)

        return cls(mpu=mpu_data, press_temp=press_temp, header_info=header_info, _is_merged=True)
