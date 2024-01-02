from __future__ import annotations

import json
import re
from collections import abc
from dataclasses import asdict, dataclass, field, fields
from enum import Enum
from pathlib import Path

HEADER_MAP = {
    "Time": "time",
    "Ax": "accel_x",
    "Ay": "accel_y",
    "Az": "accel_z",
    "Gx": "gyro_x",
    "Gy": "gyro_y",
    "Gz": "gyro_z",
    "Qw": "quat_w",
    "Qx": "quat_x",
    "Qy": "quat_y",
    "Qz": "quat_z",
    "Mx": "mag_x",
    "My": "mag_y",
    "Mz": "mag_z",
    "P": "pressure",
    "T": "temperature",
}

VER_SN_RE = re.compile(r"Version,\s+(\d+)[\w\s,]+SN:(\w+)")


class ParserError(RuntimeError):  # noqa: D101
    ...


class LoggerType(Enum):  # noqa: D101
    HAM_IMU_ALT = "HAM-IMU+alt"
    IMU_GPS = "GPS"


@dataclass
class SensorInfo:  # noqa: D101
    name: str
    sample_rate: int
    sensitivity: int
    full_scale: int
    units: str

    def to_dict(self) -> dict[str, int | str]:
        """Dump the instance into a dictionary."""
        # Because our fields are all serializable, we can just serialize natively
        return asdict(self)

    def to_json(self) -> str:
        """Dump the instance into a JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, in_json: str) -> SensorInfo:
        """Rebuild a `SensorInfo` instance from the provided JSON string."""
        # Because our fields are all serializable, we can just use the constructor natively
        return cls(**json.loads(in_json))


@dataclass
class HeaderInfo:  # noqa: D101
    n_header_lines: int
    logger_type: LoggerType
    firmware_version: int
    serial: str
    header_spec: list[str]
    sensors: dict[str, SensorInfo] = field(default_factory=dict)

    _custom_serialize: frozenset[str] = frozenset(("logger_type", "sensors", "_custom_serialize"))

    def to_dict(self) -> dict[str, str | dict[str, dict[str, int | str]] | list[str]]:
        """Dump the instance into a serializable dictionary."""
        # Rather than some complicated instance matching logic, just dump what's serializable first
        # and add in things that need custom handling
        out_dict = {
            field.name: getattr(self, field.name)
            for field in fields(self)
            if field.name not in self._custom_serialize
        }

        # Serialize the remainder. _custom_serialize is ignored
        out_dict["logger_type"] = self.logger_type.value
        out_dict["sensors"] = {
            sensor_name: sensor_obj.to_dict() for sensor_name, sensor_obj in self.sensors.items()
        }

        return out_dict

    def to_json(self) -> str:
        """Dump the instance into a JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_raw_dict(cls, tmp_dict: dict) -> HeaderInfo:
        """
        Rebuild a `HeaderInfo` instance from the provided dictionary.

        NOTE: It is assumed that the `"logger_type"` and `"sensors"` fields contain serialized
        versions of their respective object types that require deserialization into instances.
        """
        tmp_dict["logger_type"] = LoggerType(tmp_dict["logger_type"])
        tmp_dict["sensors"] = {
            sensor_name: SensorInfo(**sensor_dict)
            for sensor_name, sensor_dict in tmp_dict["sensors"].items()
        }

        return cls(**tmp_dict)

    @classmethod
    def from_json(cls, in_json: str) -> HeaderInfo:
        """Rebuild a `HeaderInfo` instance from the provided JSON string."""
        return cls.from_raw_dict(json.loads(in_json))


def _map_headers(
    header_line: str,
    header_map: dict[str, str] = HEADER_MAP,
    verbose: bool = True,
) -> list[str]:
    """
    Map comma-separated header shortnames to human-readable values.

    If a value cannot be mapped it will be left as-is. A warning can be optionally printed by
    setting the `verbose` flag.
    """
    header_spec = []
    for shortname in header_line.split(","):
        shortname = shortname.strip()
        mapped_name = header_map.get(shortname, None)
        if mapped_name is None:
            if verbose:
                print(f"Could not map column header '{shortname}' to human-readable value.")

            header_spec.append(shortname)
        else:
            header_spec.append(mapped_name)

    return header_spec


def extract_header(log_filepath: Path, header_prefix: str = ";") -> list[str]:
    """Extract header lines from the provided log file."""
    header_lines = []
    with log_filepath.open("r") as f:
        for line in f:  # pragma: no branch
            if line.startswith(header_prefix):
                header_lines.append(line.lstrip(header_prefix).strip())
            else:
                break

    # Check for a sensor fault
    # During self-test a fault may be detected, which prints e.g. "MPU Fault" as a non-comment line,
    # which aborts our heading extraction early
    if "Fault" in line:
        raise ParserError(f"Sensor fault encountered: '{line.strip()}'")

    if not header_lines:
        raise ValueError("No header lines found. Is this a valid log file?")

    return header_lines


def parse_header(header_lines: abc.Sequence[str]) -> HeaderInfo:
    """Parse log file information from the provided header lines."""
    firmware_version = -1
    for line in header_lines:
        if line.startswith("Title"):
            # Expected like "Title, http://www.gcdataconcepts.com, HAM-IMU+alt, MPU9250 BMP280"
            split_line = [chunk.strip() for chunk in line.split(",")]
            logger_type = LoggerType(split_line[2])
            continue

        if line.startswith("Version"):
            try_match = VER_SN_RE.match(line)
            if try_match:
                firmware_version = int(try_match.group(1))
                device_serial = try_match.group(2)
            else:
                raise ParserError("Unexpected formatting of 'Version' header line encountered.")

            continue

    # Column headers should be the last line, convert these to more readable names
    header_spec = _map_headers(header_lines[-1])

    try:
        header_info = HeaderInfo(
            n_header_lines=len(header_lines),
            logger_type=logger_type,
            firmware_version=firmware_version,
            serial=device_serial,
            header_spec=header_spec,
        )
    except NameError as e:
        missing_varname = re.findall(r"'(\w+)'", str(e))[0]
        raise ParserError(
            f"Unable to locate necessary header information. Missing: '{missing_varname}'"
        )

    return header_info


def parse_from_file(log_filepath: Path, header_prefix: str = ";") -> HeaderInfo:  # pragma: no cover
    """Helper pipeline to receive `HeaderInfo` directly from the provided log file."""
    return parse_header(extract_header(log_filepath, header_prefix))
