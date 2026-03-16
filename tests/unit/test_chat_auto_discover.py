from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from infinitecontex.capture.chat_auto_discover import (
    _find_recent_file,
    auto_ingest_chat,
    discover_claude_logs,
    discover_copilot_logs,
    discover_cursor_sessions,
)


@pytest.fixture
def mock_home(tmp_path):
    with patch("pathlib.Path.home", return_value=tmp_path):
        yield tmp_path


def test_find_recent_file(tmp_path):
    assert _find_recent_file(tmp_path / "nonexistent", "*.json") is None

    d = tmp_path / "testdir"
    d.mkdir()
    assert _find_recent_file(d, "*.json") is None

    f1 = d / "1.json"
    f1.write_text("{}")

    import time

    time.sleep(0.01)
    f2 = d / "2.json"
    f2.write_text("{}")

    recent = _find_recent_file(d, "*.json")
    assert recent == f2


@patch("sys.platform", "darwin")
def test_discover_cursor_sessions_mac(mock_home):
    storage = mock_home / "Library/Application Support/Cursor/User/workspaceStorage/test"
    storage.mkdir(parents=True)
    db = storage / "state.vscdb"
    db.write_text("")

    res = discover_cursor_sessions()
    assert res == db


@patch("sys.platform", "win32")
def test_discover_cursor_sessions_win(mock_home):
    storage = mock_home / "AppData/Roaming/Cursor/User/workspaceStorage/test"
    storage.mkdir(parents=True)
    db = storage / "state.vscdb"
    db.write_text("")
    res = discover_cursor_sessions()
    assert res == db


@patch("sys.platform", "linux")
def test_discover_cursor_sessions_linux(mock_home):
    storage = mock_home / ".config/Cursor/User/workspaceStorage/test"
    storage.mkdir(parents=True)
    db = storage / "state.vscdb"
    db.write_text("")
    res = discover_cursor_sessions()
    assert res == db


def test_discover_cursor_local(monkeypatch, tmp_path):
    def mock_cwd():
        return tmp_path

    monkeypatch.setattr(Path, "cwd", mock_cwd)
    local_cursor = tmp_path / ".cursor"
    local_cursor.mkdir()
    f = local_cursor / "session.json"
    f.write_text("{}")

    with patch("infinitecontex.capture.chat_auto_discover.Path") as mock_path:
        # Mock Path(".cursor")
        mock_path.return_value = local_cursor
        mock_path.home.return_value = tmp_path
        res = discover_cursor_sessions()
        assert res == f


@patch("sys.platform", "darwin")
def test_discover_copilot_mac(mock_home):
    storage = mock_home / "Library/Application Support/Code/User/globalStorage/github.copilot-chat/test"
    storage.mkdir(parents=True)
    assert discover_copilot_logs() is None

    f = storage / "chat.json"
    f.write_text("{}")
    assert discover_copilot_logs() == f


@patch("sys.platform", "win32")
def test_discover_copilot_win(mock_home):
    storage = mock_home / "AppData/Roaming/Code/User/globalStorage/github.copilot-chat/test"
    storage.mkdir(parents=True)
    f = storage / "chat.json"
    f.write_text("{}")
    assert discover_copilot_logs() == f


@patch("sys.platform", "linux")
def test_discover_copilot_linux(mock_home):
    storage = mock_home / ".config/Code/User/globalStorage/github.copilot-chat/test"
    storage.mkdir(parents=True)
    f = storage / "chat.json"
    f.write_text("{}")
    assert discover_copilot_logs() == f


def test_discover_claude():
    with patch("infinitecontex.capture.chat_auto_discover.Path") as mock_path:
        m = MagicMock()
        m.exists.return_value = True
        m.is_file.return_value = True
        mock_path.return_value = m
        assert discover_claude_logs() == m

        m_none = MagicMock()
        m_none.exists.return_value = False
        mock_path.return_value = m_none
        assert discover_claude_logs() is None


@patch("infinitecontex.capture.chat_auto_discover.discover_claude_logs", return_value=None)
@patch("infinitecontex.capture.chat_auto_discover.discover_copilot_logs", return_value=None)
@patch("infinitecontex.capture.chat_auto_discover.discover_cursor_sessions", return_value=None)
def test_auto_ingest_chat_none(m1, m2, m3):
    res = auto_ingest_chat()
    assert res["developer_goal"] == ""
    assert res["decisions"] == []
    assert res["selected_source"] is None
    assert len(res["checked_sources"]) == 3


@patch("infinitecontex.capture.chat_auto_discover.discover_claude_logs")
@patch("infinitecontex.capture.chat_auto_discover.discover_copilot_logs")
@patch("infinitecontex.capture.chat_auto_discover.discover_cursor_sessions")
@patch("infinitecontex.capture.chat_auto_discover.ingest_chat_text")
def test_auto_ingest_chat_all_found(mock_extract, m_cursor, m_copilot, m_claude):
    m_claude.return_value = MagicMock()
    m_copilot.return_value = MagicMock()
    m_cursor.return_value = MagicMock()
    mock_extract.return_value = {"developer_goal": "ship it", "decisions": []}

    res = auto_ingest_chat()
    assert res["developer_goal"] == "ship it"
    assert res["selected_source"] == "claude"
    assert res["selected_path"] is not None
    assert len(res["checked_sources"]) == 3
    mock_extract.assert_called_once_with(m_claude.return_value)
