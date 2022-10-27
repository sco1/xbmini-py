from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, fields
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
KNOWN_LEGACY_HEADER_FIRMWARE = {1379}
EXPECTED_SENSOR_NAMES = {"Accel", "Gyro", "Mag"}


class ParserError(RuntimeError):  # noqa: D101
    ...


class SensorParseError(ParserError):  # noqa: D101
    ...


class LoggerType(Enum):  # noqa: D101
    HAM_IMU_ALT = "HAM-IMU+alt"


@dataclass
class SensorInfo:  # noqa: D101
    name: str
    sample_rate: int
    sensitivity: int
    full_scale: int
    units: str

    @classmethod
    def from_header_line(cls, header_line: str) -> SensorInfo:
        """
        Parse sensor configuration from the provided header line.

        Sensor headers are assumed to be of the form:
            <name, sample rate, counts per unit, full scale value, units>

        e.g. `"Accel, 225, 1000, 16, g"`
        """
        split_line = [chunk.strip() for chunk in header_line.split(",")]
        name = split_line[0]
        sample_rate = int(split_line[1])
        sensitivity = int(split_line[2])
        full_scale = int(split_line[3])
        units = split_line[4]

        return cls(
            name=name,
            sample_rate=sample_rate,
            sensitivity=sensitivity,
            full_scale=full_scale,
            units=units,
        )

    @classmethod
    def from_legacy_header(cls, header_line: str) -> dict[str, SensorInfo]:
        """
        Parse sensor configuration from the provided legacy sensor header line format.

        Expected like: `MPU SR, 200,Hz,  Accel sens, 2048,counts/g, Gyro sens, 16,counts/dps,\
        Mag SR, 10,Hz,  Mag sens, 1666,counts/mT`
        """
        # In the legacy header, Accel and Gyro share a single sample rate declaration and separate
        # sensitivities
        sensor_info = {}
        raw_mpu_sample_rate = re.search(r"MPU SR,\s+(\d+)", header_line)
        if not raw_mpu_sample_rate:
            raise SensorParseError("Could not locate MPU sample rate.")

        mpu_sample_rate = int(raw_mpu_sample_rate.group(1))

        for sensor in ("Accel", "Gyro"):
            check_match = re.search(rf"{sensor} sens,\s+(\d+),([\w/]+)", header_line)
            if not check_match:
                raise SensorParseError(f"Could not locate '{sensor}' sensitivity and/or units.")

            raw_counts, raw_units = check_match.groups()
            sensitivity = int(raw_counts)
            units = raw_units.split("/")[-1]

            sensor_info[sensor] = cls(
                name=sensor,
                sample_rate=mpu_sample_rate,
                sensitivity=sensitivity,
                full_scale=-1,  # This needs to be mapped from the sensitivity, check the docs
                units=units,
            )

        # Magnetometer comes in the final chunk
        check_mag = re.search(r"Mag SR,\s+(\d+),Hz,\s+Mag sens,\s+(\d+),([\w/]+)", header_line)
        if not check_mag:
            raise SensorParseError("Could not locate magnetometer sensor specification.")

        raw_mag_sample_rate, raw_counts, raw_units = check_mag.groups()
        mag_sample_rate = int(raw_mag_sample_rate)
        sensitivity = int(raw_counts)
        units = raw_units.split("/")[-1]

        sensor_info["Mag"] = cls(
            name="Mag",
            sample_rate=mag_sample_rate,
            sensitivity=sensitivity,
            full_scale=-1,  # This needs to be mapped from the sensitivity, check the docs
            units=units,
        )

        return sensor_info

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
    sensors: dict[str, SensorInfo]
    header_spec: list[str]

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


def _parse_sensor_info(sensor_lines: list[str], firmware_ver: int) -> dict[str, SensorInfo]:
    sensor_info = {}
    if firmware_ver in KNOWN_LEGACY_HEADER_FIRMWARE:
        # All sensor information for this firmware version(s) is in one header line
        sensor_info.update(SensorInfo.from_legacy_header(sensor_lines[0]))
    else:
        # Sensor header line isn't useful in newer firmware versions
        for line in sensor_lines[1:]:
            spec = SensorInfo.from_header_line(line)
            sensor_info[spec.name] = spec

    return sensor_info


def parse_header(header_lines: list[str]) -> HeaderInfo:
    """Parse log file information from the provided header lines."""
    firmware_version = -1
    sensor_lines = []
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

        # Sensor information presentation differs by firmware version, so we'll pull them out and
        # parse after they're all gathered
        # This will include the "MPU" line, which is useful for legacy and useless otherwise
        if line.startswith("MPU"):
            sensor_lines.append(line)

        if any(line.startswith(sensor_name) for sensor_name in EXPECTED_SENSOR_NAMES):
            sensor_lines.append(line)
            continue

    # If we didn't find all of the expected sensors then we should abort here to prevent issues
    # issues downstream
    sensor_info = _parse_sensor_info(sensor_lines, firmware_version)
    if not sensor_info:
        raise SensorParseError("Unable to locate any sensor configuration header lines.")

    key_diff = EXPECTED_SENSOR_NAMES - sensor_info.keys()
    if key_diff:
        raise SensorParseError(
            f"Unable to locate all expected sensor names. Missing: {', '.join(key_diff)}"
        )

    # Column headers should be the last line, convert these to more readable names
    header_spec = _map_headers(header_lines[-1])

    try:
        header_info = HeaderInfo(
            n_header_lines=len(header_lines),
            logger_type=logger_type,
            firmware_version=firmware_version,
            serial=device_serial,
            sensors=sensor_info,
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
