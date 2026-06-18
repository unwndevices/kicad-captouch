"""CLI behaviour, focused on the fab-rule guard wiring (warn / --strict)."""

from __future__ import annotations

import pytest

from captouch import __version__
from captouch.cli import main


def test_version_flag_prints_version_and_exits(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_gui_check_constructs_and_exits(capsys):
    pytest.importorskip("PySide6")
    rc = main(["gui", "--check"])
    assert rc == 0
    assert "gui ok" in capsys.readouterr().out


def test_slider_default_writes_files_and_exits_zero(tmp_path):
    rc = main(["slider", "--out", str(tmp_path), "--name", "S"])
    assert rc == 0
    assert (tmp_path / "S.kicad_mod").exists()
    assert (tmp_path / "S.kicad_sym").exists()


def test_list_fab_profiles_lists_and_exits_zero(capsys):
    rc = main(["trackpad", "--list-fab-profiles"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "default" in out and "jlcpcb" in out and "oshpark" in out


def test_trackpad_warns_but_still_generates_under_loose_profile(tmp_path, capsys):
    # The default trackpad's 0.15 mm annular ring is below OSH Park's floor, but
    # without --strict the files are still written and a warning is printed.
    rc = main(["trackpad", "--out", str(tmp_path), "--name", "T", "--fab-profile", "oshpark"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "warning:" in out
    assert "annular ring" in out
    assert (tmp_path / "T.kicad_mod").exists()


def test_strict_blocks_generation_and_writes_nothing(tmp_path, capsys):
    rc = main(["trackpad", "--out", str(tmp_path), "--name", "T",
               "--fab-profile", "oshpark", "--strict"])
    out = capsys.readouterr().out
    assert rc == 3
    assert "error:" in out and "refusing to generate" in out
    assert not (tmp_path / "T.kicad_mod").exists()
    assert not (tmp_path / "T.kicad_sym").exists()


def test_strict_passes_when_geometry_clears_the_profile(tmp_path):
    # Default profile: the stock trackpad clears every rule, so --strict succeeds.
    rc = main(["trackpad", "--out", str(tmp_path), "--name", "T", "--strict"])
    assert rc == 0
    assert (tmp_path / "T.kicad_mod").exists()
