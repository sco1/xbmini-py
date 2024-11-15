# Changelog
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (`<major>`.`<minor>`.`<patch>`)

## [v0.5.0]
### Changed
* #37 Swap from pandas to polars dataframes for all parsed data outputs

### Added
* #35 Add support for GPS normalization when parsing raw log data

## [v0.4.0]
### Changed
* Bump minimum Python version to 3.11
* (Internal) Migrate to uv from poetry
* #34 `xbmini.log_parser.batch_combine` now defaults to attempting to separate logging sessions before combining

### Added
* Add `matplotlib`-based log trimming helper

### Removed
* #26, #29 Remove Plotly Dash-based trim application

## [v0.3.0]
### Changed
* #21 Normalize handling of sensor overrides for HAM-IMU devices

## [v0.2.0]
### Added
* Add an `XBMLog` object to represent a parsed log session
* Add vizualization API to assist with plot generation
* Add CLI with initial helper pipeline commands (`xbmini batch-combine`)
* Add Dash UI for trimming serialized `XBMLog` CSVs (`xbmini dash trim`)

### Changed
* #2 More gracefully handle sensor faults during log file header parsing
* (Internal) Add Python 3.11 to GHA

## [v0.1.0]
Initial release
