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

PRESS_TEMP_COLS = ["pressure", "temperature"]  # Pandas needs this as a list for indexing


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
    mpu_data: pd.DataFrame
    press_temp_data: pd.DataFrame
    header_info: HeaderInfo
    _is_merged: bool = False
    _is_trimmed: bool = False

    analysis_dt: dt.datetime = field(default_factory=dt.datetime.now)
    ground_pressure: NUMERIC_T = 101_325
    total_rigged_weight: None | NUMERIC_T = None

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

        return cls(
            mpu_data=mpu_data, press_temp_data=press_temp, header_info=header_info, _is_merged=True
        )
