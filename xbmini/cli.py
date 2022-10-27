from pathlib import Path

import click
import typer
from sco1_misc import prompts

from xbmini import log_parser

xbmini_cli = typer.Typer(add_completion=False, no_args_is_help=True)


@xbmini_cli.command()
def batch_combine(
    top_dir: Path = typer.Option(None, exists=True, file_okay=False),
    log_pattern: str = typer.Option("*.CSV"),
    dry_run: bool = typer.Option(False),
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
        except ValueError:
            raise click.ClickException("No directory selected, aborting.")

    log_parser.batch_combine(
        top_dir=top_dir,
        pattern=log_pattern,
        dry_run=dry_run,
        skip_strs=skip_strs,
    )


# Until more commands are added, add a callback to keep batch from running on a bare CLI invocation
@xbmini_cli.callback()
def callback() -> None:  # noqa: D103
    pass


if __name__ == "__main__":  # pragma: no cover
    xbmini_cli()
