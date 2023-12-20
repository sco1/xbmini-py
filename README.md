# xbmini-py
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/xbmini-py)](https://pypi.org/project/xbmini-pyxbmini-py/)
[![PyPI](https://img.shields.io/pypi/v/xbmini-py)](https://pypi.org/project/xbmini-py/)
[![PyPI - License](https://img.shields.io/pypi/l/xbmini-py?color=magenta)](https://github.com/sco1/xbmini-py/blob/master/LICENSE)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/sco1/xbmini-py/main.svg)](https://results.pre-commit.ci/latest/github/sco1/xbmini-py/main)
[![Code style: black](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)
[![Open in Visual Studio Code](https://img.shields.io/badge/Open%20in-VSCode.dev-blue)](https://vscode.dev/github.com/sco1/xbmini-py)

Python Toolkit for the [GCDC HAM](http://www.gcdataconcepts.com/ham.html)

## Known Firmware Compatibility
This package is currently tested against firmware versions `1379` and `2108`, compatibility with other firmware versions is not guaranteed.

## Installation
Install from PyPi with your favorite `pip` invocation:

```bash
$ pip install xbmini-py
```

You can confirm proper installation via the `xbmini` CLI:
<!-- [[[cog
import cog
from subprocess import PIPE, run
out = run(["xbmini", "--help"], stdout=PIPE, encoding="ascii")
cog.out(
    f"```\n$ xbmini --help\n{out.stdout.rstrip()}\n```"
)
]]] -->
```
$ xbmini --help
                                                                               
 Usage: xbmini [OPTIONS] COMMAND [ARGS]...                                     
                                                                               
+- Options -------------------------------------------------------------------+
| --help          Show this message and exit.                                 |
+-----------------------------------------------------------------------------+
+- Commands ------------------------------------------------------------------+
| batch-combine  Batch combine XBM files for each logger and dump a           |
|                serialized `XBMLog` instance to CSV.                         |
| dash           Dash UI launchers                                            |
+-----------------------------------------------------------------------------+
```
<!-- [[[end]]] -->

## Usage
### `xbmini batch-combine`
Batch combine XBM files for each logger and dump a serialized `XBMLog` instance to a CSV in its respective logger's directory.
#### Input Parameters
| Parameter       | Description                                            | Type         | Default                                |
|-----------------|--------------------------------------------------------|--------------|----------------------------------------|
| `--top-dir`     | Path to top-level log directory to search.<sup>1</sup> | `Path\|None` | GUI Prompt                             |
| `--log-pattern` | XBMini log file glob pattern.<sup>2</sup>              | `str`        | `"*.CSV"`                              |
| `--dry-run`     | Show processing pipeline without processing any files. | `bool`       | `False`                                |
| `--skip-strs`   | Skip files containing any of the provided substrings.  | `list[str]`  | `["processed", "trimmed", "combined"]` |

1. Log searching will be executed recursively starting from the top directory
2. Case sensitivity is deferred to the host OS

### `xbmini dash`
A series of helper UIs are provided by [Dash](https://dash.plotly.com/). Running the CLI commands will start a local server for the user to interact with.

**WARNING:** These apps are intended for use on a development server only. Do not use them in a production environment.

A list of available UIs can be accessed via the command line:
<!-- [[[cog
import cog
from subprocess import PIPE, run
out = run(["xbmini", "dash", "--help"], stdout=PIPE, encoding="ascii")
cog.out(
    f"```\n$ xbmini dash --help\n{out.stdout.rstrip()}\n```"
)
]]] -->
```
$ xbmini dash --help
                                                                               
 Usage: xbmini dash [OPTIONS] COMMAND [ARGS]...                                
                                                                               
 Dash UI launchers                                                             
                                                                               
+- Options -------------------------------------------------------------------+
| --help          Show this message and exit.                                 |
+-----------------------------------------------------------------------------+
+- Commands ------------------------------------------------------------------+
| trim     Helper UI for trimming serialized XBMLog CSVs.                     |
+-----------------------------------------------------------------------------+
```
<!-- [[[end]]] -->
