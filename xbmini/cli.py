from pathlib import Path

import click
import typer
from sco1_misc import prompts

from xbmini import log_parser
from xbmini.trim import windowtrim_log_file

xbmini_cli = typer.Typer(add_completion=False, no_args_is_help=True)

trim_cli = typer.Typer(add_completion=False)
xbmini_cli.add_typer(trim_cli, name="trim", help="XBMini log trimming.")


@xbmini_cli.command(name="merge", short_help="Combine multiple log sessions.")
def batch_combine(
    top_dir: Path = typer.Option(None, exists=True, file_okay=False),
    log_pattern: str = "*.CSV",
    bin_sessions: bool = True,
    dry_run: bool = False,
    # Typer can't handle sets or arbitrary length tuples so we'll just hint as a list
    skip_strs: list[str] = log_parser.SKIP_STRINGS,  # type: ignore[assignment]
) -> None:
    """
    Batch combine XBM files for each logger and dump a serialized `XBMLog` instance to CSV.

    If a filename contains any of the substrings contained in `skip_strs` it will not be included in
    the files to be combined.

    If `dry_run` is specified, a listing of logger directories is printed and no CSV files will be
    generated.

    NOTE: All CSV files in a specific logger's directory are assumed to be from the same session &
    are combined into a single file.

    NOTE: Any pre-existing combined file in a given logger directory will be overwritten.
    """
    if top_dir is None:
        try:
            top_dir = prompts.prompt_for_dir(title="Select Top Level Log Directory")
        except ValueError as e:
            raise click.ClickException("No directory selected, aborting.") from e

    log_parser.batch_combine(
        top_dir=top_dir,
        pattern=log_pattern,
        dry_run=dry_run,
        skip_strs=skip_strs,
        bin_sessions=bin_sessions,
    )


@trim_cli.command(name="single")
def trim_log(
    log_path: Path = typer.Option(None, exists=True, file_okay=True, dir_okay=False),
) -> None:
    """
    Plot the provided log file's pressure altitude vs. elapsed time for interactive windowing.

    A trimmed CSV with a `"_trimmed"` suffix is written to the same directory as the input log data.

    NOTE: Any existing trimmed file with the same name will be overwritten.
    """
    if log_path is None:
        try:
            log_path = prompts.prompt_for_file(title="Select HAM Log For Trimming.")
        except ValueError as e:
            raise click.ClickException("No file selected, aborting.") from e

    windowtrim_log_file(log_path, write_csv=True)


@trim_cli.command(name="batch")
def batch_trim_log(
    top_dir: Path = typer.Option(None, exists=True, file_okay=False),
    log_pattern: str = typer.Option("*.CSV"),
) -> None:
    """
    Plot all matching log files' pressure altitude vs. elapsed time for interactive windowing.

    For each matching log file, a trimmed CSV with a `"_trimmed"` suffix is written to the same
    directory as the input log data.

    NOTE: Any existing trimmed file with the same name will be overwritten.

    NOTE: When globbing the log directory for log files to trim, case sensitivity of the provided
    `log_pattern` is deferred to the host OS.
    """
    if top_dir is None:
        try:
            top_dir = prompts.prompt_for_dir(title="Select Top Level Log Directory")
        except ValueError as e:
            raise click.ClickException("No directory selected, aborting.") from e

    for f in top_dir.glob(log_pattern):
        windowtrim_log_file(f, write_csv=True)


if __name__ == "__main__":  # pragma: no cover
    xbmini_cli()
