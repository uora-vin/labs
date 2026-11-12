"""Лабораторная работа № 2.

Вариант 25: проверка и поиск синтаксически корректных паспортных данных.
"""

import re
from urllib.parse import urlparse

import requests

# Серия — четыре цифры, номер — шесть цифр.
# Цифры серии можно записать слитно или через пробел/дефис.
# Между серией и номером также допускается пробел или дефис.
_PASSPORT_BODY = r"\d{2}[ -]?\d{2}[ -]?\d{6}"
_PASSPORT_FULL = re.compile(_PASSPORT_BODY)
# При поиске не вырезаем паспорт из более длинной последовательности цифр.
_PASSPORT_SEARCH = re.compile(rf"(?<!\d){_PASSPORT_BODY}(?!\d)")

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


def validate_passport(text: str) -> bool:
    """Проверить, что вся строка является паспортными данными."""
    if not isinstance(text, str):
        return False
    return _PASSPORT_FULL.fullmatch(text) is not None


def find_passports(text: str) -> list[str]:
    """Найти все паспортные данные в тексте в порядке появления."""
    if not isinstance(text, str):
        return []
    return [match.group(0) for match in _PASSPORT_SEARCH.finditer(text)]


def read_from_file(filename: str) -> str:
    """Прочитать текст из файла в кодировке UTF-8."""
    try:
        with open(filename, encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Файл не найден: {filename}") from error
    except UnicodeError as error:
        raise UnicodeError(
            f"Файл не является корректным UTF-8: {filename}"
        ) from error
    except OSError as error:
        raise OSError(
            f"Не удалось прочитать файл {filename}: {error}"
        ) from error


def read_from_url(url: str) -> str:
    """Загрузить страницу по URL и вернуть её текст."""
    if not isinstance(url, str):
        raise ValueError("URL должен быть строкой.")
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise ValueError(
            "Введите полный URL, начинающийся с http:// или https://."
        )

    try:
        response = requests.get(
            url,
            headers={"User-Agent": _USER_AGENT},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(
            f"Не удалось загрузить страницу: {error}"
        ) from error
    return response.text


def show_results(text: str) -> None:
    """Вывести найденные паспортные данные."""
    passports = find_passports(text)
    if not passports:
        print("Паспортные данные не найдены.")
        return
    print(f"Найдено: {len(passports)}")
    for number, passport in enumerate(passports, start=1):
        print(f"{number}. {passport}")


def main() -> None:
    """Запустить консольное меню."""
    print("Проверка и поиск паспортных данных")
    while True:
        print("\n1 — проверить паспорт")
        print("2 — найти в файле")
        print("3 — найти на веб-странице")
        print("0 — выход")
        try:
            choice = input("Выберите действие: ").strip()
            if choice == "0":
                print("Работа завершена.")
                return
            elif choice == "1":
                value = input("Введите паспорт: ").strip()
                if validate_passport(value):
                    print("Паспорт корректный.")
                else:
                    print("Паспорт некорректный.")
            elif choice == "2":
                filename = input("Файл [sample.txt]: ").strip()
                if not filename:
                    filename = "sample.txt"
                show_results(read_from_file(filename))
            elif choice == "3":
                url = input("Введите URL: ").strip()
                show_results(read_from_url(url))
            else:
                print("Такого пункта нет. Выберите 0, 1, 2 или 3.")
        except (EOFError, KeyboardInterrupt):
            print("\nРабота завершена.")
            return
        except (ValueError, OSError, RuntimeError) as error:
            print(f"Ошибка: {error}")


if __name__ == "__main__":
    main()
