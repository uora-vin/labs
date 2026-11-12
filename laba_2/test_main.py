"""Unit-тесты для проверки паспортных данных."""

from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

import main
from main import (
    find_passports,
    read_from_file,
    read_from_url,
    validate_passport,
)

SAMPLE_PATH = Path(__file__).with_name("sample.txt")

VALID_PASSPORTS = (
    "4509123456",
    "4509 123456",
    "4509-123456",
    "45 09 123456",
    "45-09-123456",
)

INVALID_PASSPORTS = (
    "",
    "4509 12345",
    "4509 1234567",
    "450912345",
    "45091234567",
    "450 9123456",
    "4509  123456",
    "4509--123456",
    "4509_123456",
    "4509.123456",
    "45O9 123456",
    "4509 12345A",
    " 4509 123456",
    "4509 123456 ",
)


@pytest.mark.parametrize("passport", VALID_PASSPORTS)
def test_validate_valid_passports(passport: str) -> None:
    assert validate_passport(passport) is True


@pytest.mark.parametrize("passport", INVALID_PASSPORTS)
def test_validate_invalid_passports(passport: str) -> None:
    assert validate_passport(passport) is False


@pytest.mark.parametrize("value", (None, 4509123456, ["4509 123456"]))
def test_validate_non_string_returns_false(value: object) -> None:
    assert validate_passport(value) is False  # type: ignore[arg-type]


def test_find_passports_in_text() -> None:
    text = (
        "Иванов — 4509 123456, Петров — 4510-654321, "
        "Сидоров — 4511123456, Смирнова — 46 07 987654."
    )
    assert find_passports(text) == [
        "4509 123456",
        "4510-654321",
        "4511123456",
        "46 07 987654",
    ]


def test_find_passports_returns_empty_list() -> None:
    assert find_passports("Здесь нет паспортных данных.") == []
    assert find_passports("") == []
    assert find_passports(None) == []  # type: ignore[arg-type]


def test_find_passports_does_not_match_longer_digit_sequence() -> None:
    text = "0045091234567 45091234567 1234 5678901"
    assert find_passports(text) == []


def test_find_passports_keeps_duplicates_and_order() -> None:
    text = "4509 123456 и ещё раз 4509 123456"
    assert find_passports(text) == ["4509 123456", "4509 123456"]


def test_sample_file_contains_expected_passports() -> None:
    text = read_from_file(str(SAMPLE_PATH))
    assert find_passports(text) == [
        "4509 123456",
        "4510-654321",
        "4511123456",
        "46 07 987654",
    ]


def test_read_from_file_returns_utf8_text(tmp_path: Path) -> None:
    path = tmp_path / "passports.txt"
    path.write_text("Паспорт: 4509 123456", encoding="utf-8")
    assert read_from_file(str(path)) == "Паспорт: 4509 123456"


def test_read_from_file_missing_file() -> None:
    with pytest.raises(FileNotFoundError, match="Файл не найден"):
        read_from_file("this_file_should_not_exist_12345.txt")


def test_read_from_file_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "invalid.txt"
    path.write_bytes(b"\xff\xfe\xfa")
    with pytest.raises(UnicodeError, match="UTF-8"):
        read_from_file(str(path))


def test_read_from_url_returns_page_text(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Mock()
    response.text = "Паспорт: 4509 123456"
    response.raise_for_status.return_value = None
    calls: dict[str, object] = {}

    def fake_get(
        url: str,
        headers: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> Mock:
        calls["url"] = url
        calls["headers"] = headers
        calls["timeout"] = timeout
        return response

    monkeypatch.setattr(main.requests, "get", fake_get)

    assert read_from_url("https://example.com") == "Паспорт: 4509 123456"
    assert calls["url"] == "https://example.com"
    headers = calls["headers"]
    assert isinstance(headers, dict)
    assert "User-Agent" in headers
    assert calls["timeout"] == 10


@pytest.mark.parametrize(
    "url",
    ("example.com", "ftp://example.com", "https://", ""),
)
def test_read_from_url_rejects_invalid_url(url: str) -> None:
    with pytest.raises(ValueError):
        read_from_url(url)


def test_read_from_url_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("404")
    monkeypatch.setattr(main.requests, "get", lambda *args, **kwargs: response)

    with pytest.raises(RuntimeError, match="Не удалось загрузить"):
        read_from_url("https://example.com/missing")


def test_read_from_url_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(*args: object, **kwargs: object) -> Mock:
        raise requests.Timeout("timeout")

    monkeypatch.setattr(main.requests, "get", fake_get)

    with pytest.raises(RuntimeError, match="Не удалось загрузить"):
        read_from_url("https://example.com")
