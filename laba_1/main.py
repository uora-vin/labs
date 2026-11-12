"""Лабораторная работа № 1. Предметная область «Ресторан».

Здесь только модель: классы, CRUD и сохранение в JSON/XML.

Запуск: python cli.py
"""

import json
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# --- 1. Исключения ----------------------------------------------------------

class RestaurantError(Exception):
    """Общая ошибка по ресторану."""


class InsufficientFundsError(RestaurantError):
    """Клиенту не хватает денег на оплату."""


class EmptyOrderError(RestaurantError):
    """В заказе нет блюд."""


# --- 2. Проверки полей ------------------------------------------------------

def _required(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise RestaurantError(f"Поле «{field_name}» должно быть строкой.")
    # убираем пробелы по краям и смотрим, что строка не пустая
    value = value.strip()
    if not value:
        raise RestaurantError(f"Поле «{field_name}» не может быть пустым.")
    return value


def _positive_int(value: int, field_name: str = "ID") -> int:
    # True и False тоже int, поэтому отдельно проверяем
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RestaurantError(
            f"{field_name} должен быть положительным целым числом."
        )
    return value


def _number(value: float, field_name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RestaurantError(f"Поле «{field_name}» должно быть числом.")
    if positive and value <= 0:
        raise RestaurantError(f"Поле «{field_name}» должно быть больше нуля.")
    if not positive and value < 0:
        raise RestaurantError(
            f"Поле «{field_name}» не может быть отрицательным."
        )
    return float(value)


def _moment(value: str, field_name: str) -> str:
    # проверяем дату через strptime, если формат не тот — будет ValueError
    try:
        datetime.strptime(value, "%Y-%m-%d %H:%M")
    except (TypeError, ValueError) as exc:
        raise RestaurantError(
            f"{field_name}: нужна дата и время в формате ГГГГ-ММ-ДД ЧЧ:ММ."
        ) from exc
    return value


# --- 3. Классы предметной области -------------------------------------------

@dataclass
class Person:
    """Человек: общее для сотрудника и гостя."""
    id: int
    full_name: str
    phone: str

    def __post_init__(self) -> None:
        _positive_int(self.id)
        self.full_name = _required(self.full_name, "ФИО")
        self.phone = _required(self.phone, "Телефон")

    def describe(self) -> str:
        return f"{self.full_name}, тел. {self.phone}"


@dataclass
class Employee(Person):
    """Сотрудник ресторана."""
    position: str
    salary: float = 0.0

    def __post_init__(self) -> None:
        super().__post_init__()
        self.position = _required(self.position, "Должность")
        self.salary = _number(self.salary, "Оклад")

    def describe(self) -> str:
        # переопределяем метод родителя
        return f"{self.full_name} — {self.position}"


@dataclass
class Customer(Person):
    """Гость. Скидка в процентах и баланс, с которого платит."""
    discount_percent: float = 0.0
    balance: float = 0.0

    def __post_init__(self) -> None:
        super().__post_init__()
        self.discount_percent = _number(self.discount_percent, "Скидка")
        if self.discount_percent > 100:
            raise RestaurantError("Скидка гостя не может быть больше 100 %.")
        self.balance = _number(self.balance, "Баланс")

    def describe(self) -> str:
        return (
            f"{self.full_name} (скидка {self.discount_percent:g} %, "
            f"баланс {self.balance:.2f} руб.)"
        )

    def pay(self, amount: float) -> None:
        # сумма не должна быть отрицательной
        amount = _number(amount, "Сумма оплаты")
        # если денег мало — своя ошибка, чтобы в меню было понятное сообщение
        if amount > self.balance:
            raise InsufficientFundsError(
                f"Не хватает денег: нужно {amount:.2f} руб., "
                f"на балансе {self.balance:.2f} руб."
            )
        self.balance = round(self.balance - amount, 2)


@dataclass
class Category:
    """Категория меню."""
    id: int
    name: str
    description: str = ""

    def __post_init__(self) -> None:
        _positive_int(self.id)
        self.name = _required(self.name, "Название категории")

    def describe(self) -> str:
        if self.description:
            return f"{self.name} — {self.description}"
        return self.name


@dataclass
class Ingredient:
    """Ингредиент для рецепта."""
    id: int
    name: str
    unit: str = "г"

    def __post_init__(self) -> None:
        _positive_int(self.id)
        self.name = _required(self.name, "Название ингредиента")
        self.unit = _required(self.unit, "Единица измерения")


@dataclass
class MenuItem:
    """Блюдо или напиток из меню."""
    id: int
    name: str
    category_id: int
    price: float
    weight: float
    description: str = ""

    def __post_init__(self) -> None:
        _positive_int(self.id)
        _positive_int(self.category_id, "ID категории")
        self.name = _required(self.name, "Название блюда")
        self.price = _number(self.price, "Цена")
        self.weight = _number(self.weight, "Вес или объём", positive=True)

    def describe(self) -> str:
        return f"{self.name} — {self.price:.2f} руб., {self.weight:g} г"


@dataclass
class RecipeLine:
    """Сколько ингредиента идёт на одну порцию блюда."""
    id: int
    menu_item_id: int
    ingredient_id: int
    amount: float

    def __post_init__(self) -> None:
        _positive_int(self.id)
        _positive_int(self.menu_item_id, "ID блюда")
        _positive_int(self.ingredient_id, "ID ингредиента")
        self.amount = _number(self.amount, "Количество", positive=True)


@dataclass
class Table:
    """Столик в зале."""
    id: int
    seats: int
    zone: str = "Основной зал"

    def __post_init__(self) -> None:
        _positive_int(self.id)
        _positive_int(self.seats, "Количество мест")
        self.zone = _required(self.zone, "Зона зала")

    def describe(self) -> str:
        return f"Столик №{self.id} ({self.seats} мест, {self.zone})"


@dataclass
class Reservation:
    """Бронь столика."""
    id: int
    table_id: int
    customer_id: int
    reserved_at: str
    guests: int
    status: str = "Активна"

    ALLOWED_STATUSES = ("Активна", "Отменена", "Завершена")

    def __post_init__(self) -> None:
        _positive_int(self.id)
        _positive_int(self.table_id, "ID столика")
        _positive_int(self.customer_id, "ID гостя")
        _positive_int(self.guests, "Количество гостей")
        self.reserved_at = _moment(self.reserved_at, "Время брони")
        if self.status not in self.ALLOWED_STATUSES:
            raise RestaurantError(
                "Статус брони должен быть: Активна, Отменена или Завершена."
            )

    def describe(self) -> str:
        return (
            f"№{self.id}: столик {self.table_id}, {self.reserved_at}, "
            f"{self.status}"
        )


@dataclass
class Order:
    """Заказ. Позиции лежат отдельно, в OrderItem."""
    id: int
    customer_id: int
    employee_id: int
    created_at: str
    table_id: int | None = None
    status: str = "Новый"

    ALLOWED_STATUSES = ("Новый", "Оплачен", "Отменён")

    def __post_init__(self) -> None:
        _positive_int(self.id)
        _positive_int(self.customer_id, "ID гостя")
        _positive_int(self.employee_id, "ID сотрудника")
        self.created_at = _moment(self.created_at, "Время заказа")
        # у заказа на вынос столика нет
        if self.table_id is not None:
            _positive_int(self.table_id, "ID столика")
        if self.status not in self.ALLOWED_STATUSES:
            raise RestaurantError(
                "Статус заказа должен быть: Новый, Оплачен или Отменён."
            )

    def describe(self) -> str:
        table = f"столик №{self.table_id}" if self.table_id else "без столика"
        return f"№{self.id}: {self.created_at}, {table}, {self.status}"

    def pay(self, customer: Customer, *, total: float, items_count: int) -> None:
        # сумма и число позиций приходят из Restaurant, потому что позиции
        # заказа хранятся в общем списке order_items, а не внутри заказа
        if self.status != "Новый":
            raise RestaurantError(
                f"Заказ №{self.id} нельзя оплатить: статус «{self.status}»."
            )
        # пустой заказ оплачивать нечего
        if items_count == 0:
            raise EmptyOrderError(
                "Нельзя оплатить пустой заказ: сначала добавьте блюда."
            )
        customer.pay(total)
        self.status = "Оплачен"


@dataclass
class OrderItem:
    """Позиция заказа: блюдо и сколько штук."""
    id: int
    order_id: int
    menu_item_id: int
    quantity: int

    def __post_init__(self) -> None:
        _positive_int(self.id)
        _positive_int(self.order_id, "ID заказа")
        _positive_int(self.menu_item_id, "ID блюда")
        _positive_int(self.quantity, "Количество")


# --- 4. Restaurant: хранение, CRUD, файлы -----------------------------------

@dataclass
class Restaurant:
    """Все данные ресторана и операции над ними."""
    name: str
    categories: list[Category] = field(default_factory=list)
    ingredients: list[Ingredient] = field(default_factory=list)
    menu_items: list[MenuItem] = field(default_factory=list)
    recipe_lines: list[RecipeLine] = field(default_factory=list)
    employees: list[Employee] = field(default_factory=list)
    customers: list[Customer] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    reservations: list[Reservation] = field(default_factory=list)
    orders: list[Order] = field(default_factory=list)
    order_items: list[OrderItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.name = _required(self.name, "Название ресторана")

    # маленькие помощники, чтобы не писать одно и то же в каждом add_/find_

    def _add(self, items: list[Any], entity: Any) -> None:
        # проверяем, что такого ID ещё нет
        for item in items:
            if item.id == entity.id:
                raise RestaurantError(f"Запись с ID {entity.id} уже существует.")
        items.append(entity)

    def _find(self, items: list[Any], entity_id: int, title: str) -> Any:
        # ищем запись по ID, если нет — ошибка
        _positive_int(entity_id)
        for item in items:
            if item.id == entity_id:
                return item
        raise RestaurantError(f"Объект «{title}» с ID {entity_id} не найден.")

    # --- добавление ---

    def add_category(self, item: Category) -> None:
        self._add(self.categories, item)

    def add_ingredient(self, item: Ingredient) -> None:
        self._add(self.ingredients, item)

    def add_menu_item(self, item: MenuItem) -> None:
        # блюдо не может ссылаться на несуществующую категорию
        self._find(self.categories, item.category_id, "Категория")
        self._add(self.menu_items, item)

    def add_recipe_line(self, item: RecipeLine) -> None:
        self._find(self.menu_items, item.menu_item_id, "Блюдо")
        self._find(self.ingredients, item.ingredient_id, "Ингредиент")
        self._add(self.recipe_lines, item)

    def add_employee(self, item: Employee) -> None:
        self._add(self.employees, item)

    def add_customer(self, item: Customer) -> None:
        self._add(self.customers, item)

    def add_table(self, item: Table) -> None:
        self._add(self.tables, item)

    def add_reservation(self, item: Reservation) -> None:
        self._find(self.tables, item.table_id, "Столик")
        self._find(self.customers, item.customer_id, "Гость")
        self._add(self.reservations, item)

    def add_order(self, item: Order) -> None:
        self._find(self.customers, item.customer_id, "Гость")
        self._find(self.employees, item.employee_id, "Сотрудник")
        if item.table_id is not None:
            self._find(self.tables, item.table_id, "Столик")
        self._add(self.orders, item)

    def add_order_item(self, item: OrderItem) -> None:
        self._find(self.orders, item.order_id, "Заказ")
        self._find(self.menu_items, item.menu_item_id, "Блюдо")
        self._add(self.order_items, item)

    # --- поиск ---

    def find_category(self, category_id: int) -> Category:
        return self._find(self.categories, category_id, "Категория")

    def find_menu_item(self, menu_item_id: int) -> MenuItem:
        return self._find(self.menu_items, menu_item_id, "Блюдо")

    def find_employee(self, employee_id: int) -> Employee:
        return self._find(self.employees, employee_id, "Сотрудник")

    def find_customer(self, customer_id: int) -> Customer:
        return self._find(self.customers, customer_id, "Гость")

    def find_table(self, table_id: int) -> Table:
        return self._find(self.tables, table_id, "Столик")

    def find_reservation(self, reservation_id: int) -> Reservation:
        return self._find(self.reservations, reservation_id, "Бронь")

    def find_order(self, order_id: int) -> Order:
        return self._find(self.orders, order_id, "Заказ")

    # --- изменение ---

    def update_customer(
        self,
        customer_id: int,
        *,
        full_name: str,
        phone: str,
        discount_percent: float = 0.0,
        balance: float | None = None,
    ) -> Customer:
        customer = self.find_customer(customer_id)
        # если баланс не передали, оставляем старый
        if balance is None:
            balance = customer.balance
        # сначала создаём новый объект, он проверит поля,
        # и только потом меняем старый
        updated = Customer(
            customer_id, full_name, phone, discount_percent, balance
        )
        customer.full_name = updated.full_name
        customer.phone = updated.phone
        customer.discount_percent = updated.discount_percent
        customer.balance = updated.balance
        return customer

    def update_menu_item(
        self,
        menu_item_id: int,
        *,
        name: str,
        category_id: int,
        price: float,
        weight: float,
        description: str = "",
    ) -> MenuItem:
        item = self.find_menu_item(menu_item_id)
        self.find_category(category_id)
        updated = MenuItem(
            menu_item_id, name, category_id, price, weight, description
        )
        item.name = updated.name
        item.category_id = updated.category_id
        item.price = updated.price
        item.weight = updated.weight
        item.description = updated.description
        return item

    def update_order_status(self, order_id: int, status: str) -> None:
        order = self.find_order(order_id)
        if status not in Order.ALLOWED_STATUSES:
            raise RestaurantError("Недопустимый статус заказа.")
        order.status = status

    def update_reservation_status(self, reservation_id: int, status: str) -> None:
        reservation = self.find_reservation(reservation_id)
        if status not in Reservation.ALLOWED_STATUSES:
            raise RestaurantError("Недопустимый статус брони.")
        reservation.status = status

    # --- удаление ---

    def delete_menu_item(self, menu_item_id: int) -> None:
        item = self.find_menu_item(menu_item_id)
        # нельзя удалить блюдо, если оно уже в чьём-то заказе
        for line in self.order_items:
            if line.menu_item_id == menu_item_id:
                raise RestaurantError(
                    "Нельзя удалить блюдо, которое есть в заказах."
                )
        for line in self.recipe_lines:
            if line.menu_item_id == menu_item_id:
                raise RestaurantError(
                    "Сначала удалите строки рецепта этого блюда."
                )
        self.menu_items.remove(item)

    def delete_customer(self, customer_id: int) -> None:
        customer = self.find_customer(customer_id)
        for order in self.orders:
            if order.customer_id == customer_id:
                raise RestaurantError(
                    "Нельзя удалить гостя, у которого есть заказы."
                )
        for item in self.reservations:
            if item.customer_id == customer_id:
                raise RestaurantError(
                    "Нельзя удалить гостя, у которого есть брони."
                )
        self.customers.remove(customer)

    def delete_order(self, order_id: int) -> None:
        # заказ и его позиции удаляем вместе
        order = self.find_order(order_id)
        self.order_items = [
            line for line in self.order_items if line.order_id != order_id
        ]
        self.orders.remove(order)

    def delete_reservation(self, reservation_id: int) -> None:
        reservation = self.find_reservation(reservation_id)
        self.reservations.remove(reservation)

    # --- расчёты и оплата ---

    def table_is_free(self, table_id: int) -> bool:
        self.find_table(table_id)
        # столик занят, если на него есть активная бронь
        for item in self.reservations:
            if item.table_id == table_id and item.status == "Активна":
                return False
        # или если за столиком есть неоплаченный заказ
        for order in self.orders:
            if order.table_id == table_id and order.status == "Новый":
                return False
        return True

    def order_items_of(self, order_id: int) -> list[OrderItem]:
        self.find_order(order_id)
        return [line for line in self.order_items if line.order_id == order_id]

    def order_total(self, order_id: int) -> float:
        order = self.find_order(order_id)
        customer = self.find_customer(order.customer_id)
        total = 0.0
        for line in self.order_items_of(order_id):
            dish = self.find_menu_item(line.menu_item_id)
            total += dish.price * line.quantity
        # скидка гостя, например 10 % => умножаем на 0.9
        discount = 1 - customer.discount_percent / 100
        return round(total * discount, 2)

    def pay_order(self, order_id: int) -> float:
        order = self.find_order(order_id)
        customer = self.find_customer(order.customer_id)
        total = self.order_total(order_id)
        items_count = len(self.order_items_of(order_id))
        order.pay(customer, total=total, items_count=items_count)
        return total

    def paid_total(self) -> float:
        total = 0.0
        for order in self.orders:
            if order.status == "Оплачен":
                total += self.order_total(order.id)
        return round(total, 2)

    # --- JSON и XML ---

    def to_dict(self) -> dict[str, Any]:
        # из объектов делаем обычный словарь, его удобно писать в файл
        return {
            "restaurant": self.name,
            "categories": [asdict(x) for x in self.categories],
            "ingredients": [asdict(x) for x in self.ingredients],
            "menu_items": [asdict(x) for x in self.menu_items],
            "recipe_lines": [asdict(x) for x in self.recipe_lines],
            "employees": [asdict(x) for x in self.employees],
            "customers": [asdict(x) for x in self.customers],
            "tables": [asdict(x) for x in self.tables],
            "reservations": [asdict(x) for x in self.reservations],
            "orders": [asdict(x) for x in self.orders],
            "order_items": [asdict(x) for x in self.order_items],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Restaurant":
        # порядок важен: сначала справочники, потом то, что на них ссылается
        try:
            restaurant = cls(data["restaurant"])
            parts = (
                ("categories", Category, restaurant.add_category),
                ("ingredients", Ingredient, restaurant.add_ingredient),
                ("menu_items", MenuItem, restaurant.add_menu_item),
                ("recipe_lines", RecipeLine, restaurant.add_recipe_line),
                ("employees", Employee, restaurant.add_employee),
                ("customers", Customer, restaurant.add_customer),
                ("tables", Table, restaurant.add_table),
                ("reservations", Reservation, restaurant.add_reservation),
                ("orders", Order, restaurant.add_order),
                ("order_items", OrderItem, restaurant.add_order_item),
            )
            for key, model, add_method in parts:
                for row in data[key]:
                    row = dict(row)
                    # пустой столик значит "заказ на вынос"
                    if "table_id" in row and row["table_id"] in ("", None):
                        row["table_id"] = None
                    add_method(model(**row))
            return restaurant
        except KeyError as exc:
            raise RestaurantError(
                f"В файле отсутствует обязательное поле: {exc}."
            ) from exc
        except TypeError as exc:
            raise RestaurantError(
                f"Структура данных не соответствует модели: {exc}."
            ) from exc

    def save_json(self, filename: str | Path) -> None:
        try:
            path = Path(filename)
            # если папки data ещё нет, создаём
            path.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
            path.write_text(text, encoding="utf-8")
        except (OSError, TypeError, ValueError) as exc:
            raise RestaurantError(f"Не удалось записать JSON-файл: {exc}") from exc

    @classmethod
    def load_json(cls, filename: str | Path) -> "Restaurant":
        try:
            data = json.loads(Path(filename).read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise RestaurantError("Корень JSON должен быть объектом.")
            return cls.from_dict(data)
        except FileNotFoundError as exc:
            raise RestaurantError(f"JSON-файл не найден: {filename}") from exc
        except json.JSONDecodeError as exc:
            raise RestaurantError(
                f"Ошибка синтаксиса JSON, строка {exc.lineno}: {exc.msg}"
            ) from exc
        except OSError as exc:
            raise RestaurantError(f"Не удалось прочитать JSON: {exc}") from exc

    def save_xml(self, filename: str | Path) -> None:
        try:
            root = ET.Element("restaurant", {"name": self.name})
            data = self.to_dict()
            # группа называется во множественном числе, а запись — в единственном
            tags = {
                "categories": "category",
                "ingredients": "ingredient",
                "menu_items": "menu_item",
                "recipe_lines": "recipe_line",
                "employees": "employee",
                "customers": "customer",
                "tables": "table",
                "reservations": "reservation",
                "orders": "order",
                "order_items": "order_item",
            }
            for key, tag in tags.items():
                group = ET.SubElement(root, key)
                for row in data[key]:
                    element = ET.SubElement(group, tag)
                    for field_name, value in row.items():
                        child = ET.SubElement(element, field_name)
                        # None пишем пустой строкой, иначе получится "None"
                        child.text = "" if value is None else str(value)

            ET.indent(root, space="  ")
            path = Path(filename)
            path.parent.mkdir(parents=True, exist_ok=True)
            ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
        except (OSError, TypeError, ValueError) as exc:
            raise RestaurantError(f"Не удалось записать XML-файл: {exc}") from exc

    @classmethod
    def load_xml(cls, filename: str | Path) -> "Restaurant":
        # в XML всё строки, поэтому числа приводим обратно к int/float
        int_fields = {
            "id", "category_id", "menu_item_id", "ingredient_id", "table_id",
            "customer_id", "employee_id", "order_id", "quantity", "guests",
            "seats",
        }
        float_fields = {
            "price", "weight", "salary", "amount", "discount_percent",
            "balance",
        }
        tags = {
            "categories": "category",
            "ingredients": "ingredient",
            "menu_items": "menu_item",
            "recipe_lines": "recipe_line",
            "employees": "employee",
            "customers": "customer",
            "tables": "table",
            "reservations": "reservation",
            "orders": "order",
            "order_items": "order_item",
        }
        try:
            root = ET.parse(filename).getroot()
            data: dict[str, Any] = {"restaurant": root.attrib["name"]}
            for key in tags:
                data[key] = []
                group = root.find(key)
                if group is None:
                    continue
                for element in list(group):
                    row: dict[str, Any] = {}
                    for child in list(element):
                        text = (child.text or "").strip()
                        if child.tag in int_fields:
                            row[child.tag] = int(text) if text else None
                        elif child.tag in float_fields:
                            row[child.tag] = float(text) if text else 0.0
                        else:
                            row[child.tag] = text
                    data[key].append(row)
            return cls.from_dict(data)
        except FileNotFoundError as exc:
            raise RestaurantError(f"XML-файл не найден: {filename}") from exc
        except ET.ParseError as exc:
            raise RestaurantError(f"Некорректный XML: {exc}") from exc
        except (KeyError, OSError, ValueError) as exc:
            raise RestaurantError(f"Не удалось прочитать XML: {exc}") from exc


# --- 5. Демо-данные и вывод -------------------------------------------------

def create_demo_restaurant() -> Restaurant:
    # на этих данных удобно проверять программу
    r = Restaurant("Ресторан «Тёплый вечер»")

    r.add_category(Category(1, "Салаты", "Холодные закуски"))
    r.add_category(Category(2, "Супы", "Горячие первые блюда"))
    r.add_category(Category(3, "Горячее", "Основные блюда"))
    r.add_category(Category(4, "Напитки", "Горячие и холодные"))
    r.add_category(Category(5, "Десерты", "Сладкое"))

    r.add_ingredient(Ingredient(1, "Куриное филе", "кг"))
    r.add_ingredient(Ingredient(2, "Помидоры", "кг"))
    r.add_ingredient(Ingredient(3, "Сыр пармезан", "кг"))
    r.add_ingredient(Ingredient(4, "Картофель", "кг"))
    r.add_ingredient(Ingredient(5, "Сливки", "л"))
    r.add_ingredient(Ingredient(6, "Кофе", "кг"))

    r.add_menu_item(
        MenuItem(1, "Салат «Цезарь»", 1, 520.0, 260.0, "С курицей и пармезаном")
    )
    r.add_menu_item(
        MenuItem(2, "Борщ с говядиной", 2, 340.0, 400.0, "Со сметаной")
    )
    r.add_menu_item(
        MenuItem(3, "Стейк из индейки", 3, 690.0, 320.0, "С овощами гриль")
    )
    r.add_menu_item(
        MenuItem(4, "Капучино", 4, 210.0, 250.0, "Двойное эспрессо")
    )
    r.add_menu_item(
        MenuItem(5, "Тирамису", 5, 390.0, 140.0, "Классический рецепт")
    )

    r.add_recipe_line(RecipeLine(1, 1, 1, 0.08))
    r.add_recipe_line(RecipeLine(2, 1, 2, 0.05))
    r.add_recipe_line(RecipeLine(3, 1, 3, 0.02))
    r.add_recipe_line(RecipeLine(4, 2, 4, 0.12))
    r.add_recipe_line(RecipeLine(5, 2, 5, 0.03))
    r.add_recipe_line(RecipeLine(6, 4, 6, 0.02))

    r.add_employee(
        Employee(1, "Анна Смирнова", "+7-900-111-22-33", "Официант", 55000.0)
    )
    r.add_employee(
        Employee(2, "Пётр Кузнецов", "+7-900-222-33-44", "Повар", 78000.0)
    )
    r.add_employee(
        Employee(3, "Ольга Иванова", "+7-900-333-44-55", "Администратор", 65000.0)
    )

    r.add_customer(
        Customer(1, "Алексей Петров", "+7-900-444-55-66", balance=5000.0)
    )
    r.add_customer(
        Customer(2, "Мария Соколова", "+7-900-555-66-77", 10.0, 3000.0)
    )

    r.add_table(Table(1, 2, "Основной зал"))
    r.add_table(Table(2, 4, "Основной зал"))
    r.add_table(Table(3, 6, "VIP-зал"))
    r.add_table(Table(4, 4, "Терраса"))

    r.add_reservation(Reservation(1, 3, 2, "2026-11-20 19:00", 5))
    r.add_reservation(Reservation(2, 1, 1, "2026-11-21 13:00", 2))

    r.add_order(Order(1, 1, 1, "2026-11-20 18:30", 2))
    r.add_order(Order(2, 2, 1, "2026-11-19 20:00", 4))
    r.add_order(Order(3, 1, 3, "2026-11-21 12:15"))  # на вынос, без столика

    r.add_order_item(OrderItem(1, 1, 1, 2))
    r.add_order_item(OrderItem(2, 1, 2, 1))
    r.add_order_item(OrderItem(3, 1, 4, 2))
    r.add_order_item(OrderItem(4, 2, 3, 2))
    r.add_order_item(OrderItem(5, 2, 5, 2))
    r.add_order_item(OrderItem(6, 3, 2, 1))
    r.add_order_item(OrderItem(7, 3, 4, 1))

    # второй заказ сразу оплачиваем, чтобы статус и баланс гостя совпадали
    r.pay_order(2)
    return r


def print_summary(restaurant: Restaurant) -> None:
    print(f"\n{restaurant.name}")
    print(
        f"Категорий: {len(restaurant.categories)} | "
        f"Позиций меню: {len(restaurant.menu_items)} | "
        f"Ингредиентов: {len(restaurant.ingredients)}"
    )
    print(
        f"Сотрудников: {len(restaurant.employees)} | "
        f"Гостей: {len(restaurant.customers)} | "
        f"Столиков: {len(restaurant.tables)}"
    )
    print(
        f"Броней: {len(restaurant.reservations)} | "
        f"Заказов: {len(restaurant.orders)} | "
        f"Позиций заказов: {len(restaurant.order_items)}"
    )
    for customer in restaurant.customers:
        print(f"  Гость: {customer.describe()}")
    for order in restaurant.orders:
        customer = restaurant.find_customer(order.customer_id)
        total = restaurant.order_total(order.id)
        print(
            f"  Заказ {order.describe()} — {customer.full_name}, "
            f"{total:.2f} руб."
        )
    print(f"Выручка по оплаченным заказам: {restaurant.paid_total():.2f} руб.")


if __name__ == "__main__":
    # это только модель, программа запускается через cli.py
    print("Здесь нет меню. Запустите: python cli.py")
