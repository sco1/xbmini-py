import typing as t
from pathlib import Path

import pandas as pd

from xbmini.heading_parser import extract_header, parse_header

CONVERSION_GROUPS = {
    "Accel": ("accel_x", "accel_y", "accel_z"),
    "Gyro": ("gyro_x", "gyro_y", "gyro_z"),
    "Mag": ("mag_x", "mag_y", "mag_z"),
}


class HasSensitivity(t.Protocol):  # noqa: D101
    sensitivity: int


def load_log(
    log_filepath: Path,
    conversion_groups: t.Mapping[str, tuple[str, ...]] = CONVERSION_GROUPS,
    sensitivity_override: None | t.Mapping[str, HasSensitivity] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load the provided XBM log into two `DataFrame`s: one for MPU data and one for press/temp.

    To work around known issues with some firmware where the sensor headers do not provide the
    correct counts/unit conversion factor, `sensitivity_override` may be optionally specified to
    manually provide these factors. It is expected to be a dictionary of the form
    `<sensor name>: <sensor_info>` where `sensor name` maps to the sensor type (e.g. `"Accel"`,
    `"Gyro"`, or `"Mag"`) and `sensor_info` is an object with a `sensivity` attribute specifying the
    counts/unit conversion factor.
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

    # Split off temperature & pressure since they sample at a lower rate
    press_temp = ["pressure", "temperature"]
    press_temp_df = full_data[press_temp].dropna(axis=0)
    full_data = full_data.drop(press_temp, axis=1, errors="ignore")

    # Convert measurements from raw counts to measured values
    if sensitivity_override:
        sensor_info = sensitivity_override
    else:
        sensor_info = header_info.sensors

    for sensor, column_group in conversion_groups.items():
        for column in column_group:
            full_data[column] = full_data[column] / sensor_info[sensor].sensitivity

    return full_data, press_temp_df
