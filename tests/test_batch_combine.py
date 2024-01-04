from pathlib import Path

import pytest

from xbmini.log_parser import batch_combine


# Sub components of the batch combine helper are already tested elsewhere, so for now can do some
# basic checks
def test_batch_combine(tmp_multi_log: list[Path]) -> None:
    log_dir = tmp_multi_log[0].parent
    batch_combine(log_dir)

    processed = list(log_dir.glob("*_processed.CSV"))
    assert len(processed) == 1


def test_batch_combine_dry_run(tmp_multi_log: list[Path]) -> None:
    log_dir = tmp_multi_log[0].parent
    batch_combine(log_dir, dry_run=True)

    processed = list(log_dir.glob("*_processed.CSV"))
    assert len(processed) == 0


def test_batch_combine_skip_processed(
    capsys: pytest.CaptureFixture, tmp_multi_log: list[Path]
) -> None:
    log_dir = tmp_multi_log[0].parent
    batch_combine(log_dir)
    processed = list(log_dir.glob("*_processed.CSV"))
    assert len(processed) == 1

    _ = capsys.readouterr()  # Clear capsys to isolate parsing of the next string
    batch_combine(log_dir)
    assert "2 log(s)" in capsys.readouterr().out


def test_batch_combine_bad_logger_skipped(tmp_multi_log: list[Path]) -> None:
    log_dir = tmp_multi_log[0].parent
    bad_data = log_dir / "bad.CSV"
    bad_data.write_text("")
    batch_combine(log_dir)

    processed = list(log_dir.glob("*_processed.CSV"))
    assert len(processed) == 0
