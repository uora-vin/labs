"""Консольное меню программы «Ресторан» (лаба 1).

Тут только ввод/вывод и меню. Классы, CRUD и файлы — в main.py.

Запуск: python cli.py
        python cli.py --demo
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

from main import (
    Customer,
    MenuItem,
    Order,
    OrderItem,
    Reservation,
    Restaurant,
    RestaurantError,
    create_demo_restaurant,
    print_summary,
)

MENU = (
    "1. Показать меню ресторана",
    "2. Показать заказы",
    "3. Показать брони",
    "4. Добавить блюдо",
    "5. Добавить гостя",
    "6. Создать заказ",
    "7. Добавить блюдо в заказ",
    "8. Оплатить заказ",
    "9. Забронировать столик",
    "10. Удалить блюдо",
    "11. Сохранить в JSON",
    "12. Загрузить из JSON",
    "13. Сохранить в XML",
    "14. Загрузить из XML",
    "0. Выход",
)

DATA_FILE_JSON = "restaurant.json"
DATA_FILE_XML = "restaurant.xml"


# --- ввод данных ------------------------------------------------------------

def _ask(prompt: str, default: str = "") -> str:
    # если пользователь ничего не ввёл, берём значение по умолчанию
    value = input(prompt).strip()
    return value or default


def _ask_int(prompt: str) -> int:
    raw = input(prompt).strip()
    try:
        return int(raw)
    except ValueError as exc:
        # переводим свою ошибку в нашу, чтобы в меню было понятное сообщение
        raise RestaurantError(f"«{raw}» — это не целое число.") from exc


def _ask_float(prompt: str) -> float:
    # разрешаем вводить 12,5 вместо 12.5
    raw = input(prompt).strip().replace(",", ".")
    try:
        return float(raw)
    except ValueError as exc:
        raise RestaurantError(f"«{raw}» — это не число.") from exc


def _next_id(items: list[Any]) -> int:
    # следующий номер = максимальный + 1
    return max((item.id for item in items), default=0) + 1


def _choose(items: list[Any], title: str) -> Any:
    # показываем список с номерами и возвращаем выбранный элемент
    if not items:
        raise RestaurantError(f"{title}: список пуст, добавлять нечего.")
    print(f"\n{title}:")
    for number, item in enumerate(items, 1):
        print(f"  {number}. {item.describe()}")
    number = _ask_int("Номер: ")
    if not 1 <= number <= len(items):
        raise RestaurantError(f"Номер должен быть от 1 до {len(items)}.")
    return items[number - 1]


# --- пункты меню ------------------------------------------------------------

def show_menu(restaurant: Restaurant) -> None:
    if not restaurant.menu_items:
        print("Меню пока пустое.")
        return
    print(f"\nМеню: {restaurant.name}")
    # выводим блюда по категориям
    for category in restaurant.categories:
        dishes = [
            item for item in restaurant.menu_items
            if item.category_id == category.id
        ]
        if not dishes:
            continue
        print(f"  {category.name}:")
        for item in dishes:
            print(f"    {item.describe()}")


def show_orders(restaurant: Restaurant) -> None:
    if not restaurant.orders:
        print("Заказов пока нет.")
        return
    print("\nЗаказы:")
    for order in restaurant.orders:
        customer = restaurant.find_customer(order.customer_id)
        employee = restaurant.find_employee(order.employee_id)
        total = restaurant.order_total(order.id)
        print(
            f"  {order.describe()} — {customer.full_name}, "
            f"официант {employee.full_name}, {total:.2f} руб."
        )
    print(f"Выручка по оплаченным заказам: {restaurant.paid_total():.2f} руб.")


def show_reservations(restaurant: Restaurant) -> None:
    if not restaurant.reservations:
        print("Броней пока нет.")
        return
    print("\nБрони:")
    for item in restaurant.reservations:
        customer = restaurant.find_customer(item.customer_id)
        print(f"  {item.describe()} — {customer.full_name}, гостей {item.guests}")


def add_menu_item(restaurant: Restaurant) -> None:
    category = _choose(restaurant.categories, "Категории")
    name = _ask("Название блюда: ")
    description = _ask("Описание: ")
    price = _ask_float("Цена, руб.: ")
    weight = _ask_float("Вес или объём: ")
    item = MenuItem(
        _next_id(restaurant.menu_items), name, category.id, price, weight,
        description,
    )
    restaurant.add_menu_item(item)
    print(f"Блюдо «{item.name}» добавлено (ID {item.id}).")


def add_customer(restaurant: Restaurant) -> None:
    full_name = _ask("ФИО гостя: ")
    phone = _ask("Телефон: ")
    discount = _ask_float("Скидка, % (0 — без скидки): ")
    balance = _ask_float("Баланс, руб.: ")
    customer = Customer(
        _next_id(restaurant.customers), full_name, phone, discount, balance
    )
    restaurant.add_customer(customer)
    print(f"Гость «{customer.full_name}» добавлен (ID {customer.id}).")


def _add_items(restaurant: Restaurant, order: Order) -> None:
    # добавляем блюда в заказ, пока не введут 0
    if not restaurant.menu_items:
        raise RestaurantError("Сначала добавьте блюда в меню (пункт 4).")
    while True:
        print("\nМеню:")
        for number, item in enumerate(restaurant.menu_items, 1):
            print(f"  {number}. {item.describe()}")
        number = _ask_int("Номер блюда (0 — закончить): ")
        if number == 0:
            return
        if not 1 <= number <= len(restaurant.menu_items):
            print(f"Номер должен быть от 0 до {len(restaurant.menu_items)}.")
            continue
        quantity = _ask_int("Количество: ")
        dish = restaurant.menu_items[number - 1]
        # создаём новую позицию заказа
        line = OrderItem(
            _next_id(restaurant.order_items), order.id, dish.id, quantity
        )
        restaurant.add_order_item(line)
        print(f"Добавлено: {dish.name} × {quantity}")


def create_order(restaurant: Restaurant) -> None:
    customer = _choose(restaurant.customers, "Гости")
    employee = _choose(restaurant.employees, "Сотрудники")

    table = None
    if restaurant.tables:
        print("\nСтолики:")
        for item in restaurant.tables:
            state = "свободен" if restaurant.table_is_free(item.id) else "занят"
            print(f"  {item.describe()} — {state}")
        number = _ask_int("Номер столика (0 — без столика): ")
        if number != 0:
            table = restaurant.find_table(number)
            # за занятый столик не сажаем
            if not restaurant.table_is_free(number):
                raise RestaurantError(
                    f"Столик №{number} занят: есть активная бронь или заказ."
                )

    order = Order(
        _next_id(restaurant.orders),
        customer.id,
        employee.id,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        table.id if table else None,
    )
    restaurant.add_order(order)
    print(f"Заказ №{order.id} создан.")
    _add_items(restaurant, order)
    print(f"Сумма заказа: {restaurant.order_total(order.id):.2f} руб.")


def add_items_to_order(restaurant: Restaurant) -> None:
    # ищем только неоплаченные заказы
    open_orders = [
        item for item in restaurant.orders if item.status == "Новый"
    ]
    order = _choose(open_orders, "Неоплаченные заказы")
    print(f"Сумма заказа: {restaurant.order_total(order.id):.2f} руб.")
    _add_items(restaurant, order)
    print(f"Сумма заказа: {restaurant.order_total(order.id):.2f} руб.")


def pay_order(restaurant: Restaurant) -> None:
    open_orders = [
        item for item in restaurant.orders if item.status == "Новый"
    ]
    order = _choose(open_orders, "Неоплаченные заказы")
    # вся проверка (пустой заказ, не хватает денег) идёт в main.py
    total = restaurant.pay_order(order.id)
    customer = restaurant.find_customer(order.customer_id)
    print(
        f"Заказ №{order.id} оплачен, сумма {total:.2f} руб. "
        f"Остаток на балансе: {customer.balance:.2f} руб."
    )


def book_table(restaurant: Restaurant) -> None:
    customer = _choose(restaurant.customers, "Гости")
    free_tables = [
        item for item in restaurant.tables if restaurant.table_is_free(item.id)
    ]
    table = _choose(free_tables, "Свободные столики")
    reserved_at = _ask("Дата и время (ГГГГ-ММ-ДД ЧЧ:ММ): ")
    guests = _ask_int("Гостей: ")
    reservation = Reservation(
        _next_id(restaurant.reservations), table.id, customer.id, reserved_at,
        guests,
    )
    restaurant.add_reservation(reservation)
    print(f"Столик №{table.id} забронирован на {reservation.reserved_at}.")


def delete_menu_item(restaurant: Restaurant) -> None:
    item = _choose(restaurant.menu_items, "Меню")
    restaurant.delete_menu_item(item.id)
    print(f"Блюдо «{item.name}» удалено.")


def save_json(restaurant: Restaurant, data_dir: Path) -> None:
    default = str(data_dir / DATA_FILE_JSON)
    path = _ask(f"Файл [{default}]: ", default)
    restaurant.save_json(path)
    print(f"Данные сохранены в {path}.")


def load_json(data_dir: Path) -> Restaurant:
    default = str(data_dir / DATA_FILE_JSON)
    path = _ask(f"Файл [{default}]: ", default)
    loaded = Restaurant.load_json(path)
    print(f"Загружены данные: {loaded.name}. Заказов: {len(loaded.orders)}.")
    return loaded


def save_xml(restaurant: Restaurant, data_dir: Path) -> None:
    default = str(data_dir / DATA_FILE_XML)
    path = _ask(f"Файл [{default}]: ", default)
    restaurant.save_xml(path)
    print(f"Данные сохранены в {path}.")


def load_xml(data_dir: Path) -> Restaurant:
    default = str(data_dir / DATA_FILE_XML)
    path = _ask(f"Файл [{default}]: ", default)
    loaded = Restaurant.load_xml(path)
    print(f"Загружены данные: {loaded.name}. Заказов: {len(loaded.orders)}.")
    return loaded


# --- запуск -----------------------------------------------------------------

def run_menu(data_dir: Path) -> int:
    json_path = data_dir / DATA_FILE_JSON
    if json_path.exists():
        # если файл есть, начинаем с него
        try:
            restaurant = Restaurant.load_json(json_path)
            print(f"Данные загружены из {json_path}.")
        except RestaurantError as exc:
            print(f"Не удалось прочитать {json_path}: {exc}")
            print("Используются демонстрационные данные.")
            restaurant = create_demo_restaurant()
    else:
        restaurant = create_demo_restaurant()
        print("Файл данных не найден, используются демонстрационные данные.")

    while True:
        print()
        for line in MENU:
            print(line)
        try:
            choice = input("Выбор: ").strip()
            if choice == "0":
                print("До свидания!")
                return 0
            elif choice == "1":
                show_menu(restaurant)
            elif choice == "2":
                show_orders(restaurant)
            elif choice == "3":
                show_reservations(restaurant)
            elif choice == "4":
                add_menu_item(restaurant)
            elif choice == "5":
                add_customer(restaurant)
            elif choice == "6":
                create_order(restaurant)
            elif choice == "7":
                add_items_to_order(restaurant)
            elif choice == "8":
                pay_order(restaurant)
            elif choice == "9":
                book_table(restaurant)
            elif choice == "10":
                delete_menu_item(restaurant)
            elif choice == "11":
                save_json(restaurant, data_dir)
            elif choice == "12":
                restaurant = load_json(data_dir)
            elif choice == "13":
                save_xml(restaurant, data_dir)
            elif choice == "14":
                restaurant = load_xml(data_dir)
            else:
                print("Такого пункта нет. Введите число от 0 до 14.")
        except RestaurantError as exc:
            print(f"Ошибка: {exc}")
        except (ValueError, TypeError) as exc:
            print(f"Ошибка входных данных: {exc}")
        except (OSError, ET.ParseError) as exc:
            print(f"Ошибка при работе с файлом: {exc}")
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            return 0
        except Exception as exc:  # чтобы программа не падала совсем
            print(f"Непредвиденная ошибка: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Учёт ресторана (ЛР1)")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="создать демонстрационные данные и сохранить JSON/XML",
    )
    parser.add_argument(
        "--data",
        default="data",
        help="каталог с файлами данных (по умолчанию data)",
    )
    args = parser.parse_args()
    data_dir = Path(args.data)

    try:
        if args.demo:
            restaurant = create_demo_restaurant()
            restaurant.save_json(data_dir / DATA_FILE_JSON)
            restaurant.save_xml(data_dir / DATA_FILE_XML)
            print("Демо-данные созданы и сохранены в JSON и XML.")
            print_summary(restaurant)
            return 0
        return run_menu(data_dir)
    except RestaurantError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1
    except (ValueError, TypeError) as exc:
        print(f"Ошибка входных данных: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nРабота прервана.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
