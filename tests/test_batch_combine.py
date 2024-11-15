from pathlib import Path

import pytest

from xbmini.heading_parser import ParserError
from xbmini.log_parser import batch_combine, bin_logging_sessions


# Sub components of the batch combine helper are already tested elsewhere, so for now can do some
# basic checks
def test_batch_combine_no_session_bin(tmp_multi_log: list[Path]) -> None:
    log_dir = tmp_multi_log[0].parent
    batch_combine(log_dir, bin_sessions=False)

    processed = list(log_dir.glob("*_processed.CSV"))
    assert len(processed) == 1


def test_batch_combine_dry_run_no_session_bin(tmp_multi_log: list[Path]) -> None:
    log_dir = tmp_multi_log[0].parent
    batch_combine(log_dir, dry_run=True, bin_sessions=False)

    processed = list(log_dir.glob("*_processed.CSV"))
    assert len(processed) == 0


# Log file selection is done prior to session binning conditional so no need to check both branches
def test_batch_combine_skip_processed(
    capsys: pytest.CaptureFixture, tmp_multi_log: list[Path]
) -> None:
    log_dir = tmp_multi_log[0].parent
    batch_combine(log_dir, bin_sessions=False)
    processed = list(log_dir.glob("*_processed.CSV"))
    assert len(processed) == 1

    _ = capsys.readouterr()  # Clear capsys to isolate parsing of the next string
    batch_combine(log_dir, bin_sessions=False)
    assert "2 log(s)" in capsys.readouterr().out


def test_batch_combine_bad_logger_skipped_no_session_bin(tmp_multi_log: list[Path]) -> None:
    log_dir = tmp_multi_log[0].parent
    bad_data = log_dir / "bad.CSV"
    bad_data.write_text("")
    batch_combine(log_dir, bin_sessions=False)

    processed = list(log_dir.glob("*_processed.CSV"))
    assert len(processed) == 0


def _session_paths_to_names(sessions: list[list[Path]]) -> list[list[str]]:
    """Helper function to make session comparisons easier."""
    simplified_sessions = []
    for s in sessions:
        simplified_sessions.append([f.name for f in s])

    return simplified_sessions


def test_session_bin_ensure_sorted(tmp_multi_session: list[Path]) -> None:
    # Fixture starts with a log with no end comment, then has 2 with shutdown comments, so if we
    # reverse and let the first one dangle then we would end up with 3 sessions if left unsorted
    log_files = reversed(tmp_multi_session)
    log_sessions = bin_logging_sessions(log_files)

    truth_sessions = [["log_1.CSV", "log_2.CSV"], ["log_3.CSV"]]
    assert _session_paths_to_names(log_sessions) == truth_sessions


def test_session_bin_unsorted(tmp_multi_session: list[Path]) -> None:
    # Fixture starts with a log with no end comment, then has 2 with shutdown comments, so if we
    # reverse and let the first one dangle then we should end up with 3 sessions if left unsorted
    log_files = reversed(tmp_multi_session)
    log_sessions = bin_logging_sessions(log_files, ensure_sorted=False)

    truth_sessions = [["log_3.CSV"], ["log_2.CSV"], ["log_1.CSV"]]
    assert _session_paths_to_names(log_sessions) == truth_sessions


def test_session_bin_empty_file_raises(tmp_path: Path) -> None:
    bad_data = tmp_path / "log_1.CSV"
    bad_data.write_text("")

    with pytest.raises(ParserError, match="No log data"):
        bin_logging_sessions([bad_data])


def test_batch_combine_session_bin(tmp_multi_session: list[Path]) -> None:
    log_dir = tmp_multi_session[0].parent
    batch_combine(log_dir, bin_sessions=True)

    processed = list(log_dir.glob("*_processed.CSV"))
    assert len(processed) == 2


def test_batch_combine_dry_run_session_bin(tmp_multi_session: list[Path]) -> None:
    log_dir = tmp_multi_session[0].parent
    batch_combine(log_dir, dry_run=True, bin_sessions=True)

    processed = list(log_dir.glob("*_processed.CSV"))
    assert len(processed) == 0


def test_batch_combine_bad_logger_skipped_session_bin(tmp_multi_session: list[Path]) -> None:
    log_dir = tmp_multi_session[0].parent
    bad_data = log_dir / "log_4.CSV"
    bad_data.write_text("\n")  # Add one line to skip the ParserError when trying to bin sessions
    batch_combine(log_dir, bin_sessions=True)

    processed = list(log_dir.glob("*_processed.CSV"))

    # Fixture passes 2 logging sessions
    assert len(processed) == 2
