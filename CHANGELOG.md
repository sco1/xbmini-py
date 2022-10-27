# Changelog
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (`<major>`.`<minor>`.`<patch>`)

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
