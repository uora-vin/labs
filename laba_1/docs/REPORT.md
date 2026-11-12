# Отчёт по лабораторной работе № 1

**Тема:** ООП в Python. Обработка исключительных ситуаций. Форматы XML и JSON.
**Вариант:** 25 — предметная область «Ресторан».
**Выполнил:** ФИО, группа ____________
**Проверил:** ____________

## 1. Цель работы

Спроектировать диаграмму классов предметной области «Ресторан», реализовать
её на Python в объектно-ориентированном стиле, обработать встроенные и
собственные исключения, а также реализовать чтение и запись данных
в форматах JSON и XML.

## 2. Постановка задачи

1. Построить UML-диаграмму классов для предметной области «Ресторан».
2. Написать по диаграмме код на Python (классы, инкапсуляция, наследование,
   полиморфизм, аннотации типов, комментарии, PEP 8).
3. Реализовать базовые операции CRUD для хранимых данных и оплату заказа
   с баланса гостя.
4. Обработать встроенные и собственные исключения так, чтобы ошибка ввода
   не завершала программу.
5. Спроектировать структуру хранения данных и реализовать чтение/запись
   в JSON и XML.
6. Подготовить отчёт.

## 3. Предметная область

Ресторан ведёт меню (категории, блюда, ингредиенты и рецепты), штат
сотрудников, гостей, столики, бронирования и заказы с позициями.
Сумма заказа считается по ценам меню с учётом скидки гостя, оплата
списывается с баланса гостя.

| Сущность | Назначение | Ключевые поля |
|---|---|---|
| `Person` | общие данные человека | `id`, `full_name`, `phone` |
| `Employee` | сотрудник ресторана | `position`, `salary` |
| `Customer` | гость ресторана | `discount_percent`, `balance`, `pay()` |
| `Category` | категория меню | `name`, `description` |
| `Ingredient` | ингредиент | `name`, `unit` |
| `MenuItem` | позиция меню | `category_id`, `price`, `weight` |
| `RecipeLine` | строка рецепта | `menu_item_id`, `ingredient_id`, `amount` |
| `Table` | столик | `seats`, `zone` |
| `Reservation` | бронь столика | `table_id`, `customer_id`, `reserved_at`, `guests`, `status` |
| `Order` | заказ | `customer_id`, `employee_id`, `table_id`, `created_at`, `status`, `pay()` |
| `OrderItem` | позиция заказа | `order_id`, `menu_item_id`, `quantity` |
| `Restaurant` | хранилище и операции | списки всех сущностей, CRUD, JSON/XML |
| `RestaurantError` | базовое исключение | — |
| `InsufficientFundsError` | не хватает денег | — |
| `EmptyOrderError` | пустой заказ | — |

Всего 13 классов модели и 3 класса исключений (требование «более 10
классов» выполнено).

## 4. Диаграмма классов

Диаграмма находится в папке `uml`:

- `restaurant_uml.puml` — исходник (PlantUML, импортируется в draw.io);
- `restaurant_uml.png` — изображение для отчёта;
- `restaurant_uml.svg` — векторная версия.

Основные отношения:

- **наследование:** `Person` ← `Employee`, `Customer`;
  `RestaurantError` ← `InsufficientFundsError`, `EmptyOrderError`;
- **полиморфизм:** метод `describe()` по-разному реализован в `Person`,
  `Employee`, `Customer`, `MenuItem`, `Table`, `Reservation`, `Order`;
- **композиция:** `Restaurant` хранит справочники и документы
  (`Category`, `MenuItem`, `Order` и др.), `Order` состоит из `OrderItem`;
- **ассоциации по внешним ключам:** `MenuItem → Category`,
  `RecipeLine → MenuItem, Ingredient`, `Order → Customer, Employee, Table`,
  `Reservation → Table, Customer`, `OrderItem → MenuItem`.

## 5. Реализация классов

Классы предметной области описаны через `@dataclass`: конструктор и методы
сравнения создаются автоматически, а проверка данных выполняется
в `__post_init__`. Например:

```python
@dataclass
class MenuItem:
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
```

Проверки вынесены во вспомогательные функции `_required`, `_positive_int`,
`_number`, `_moment`, чтобы не дублировать код в каждом классе.

Оплата реализована двумя методами: `Customer.pay()` списывает деньги
с баланса и выбрасывает `InsufficientFundsError`, а `Order.pay()` проверяет
статус, наличие позиций (`EmptyOrderError`) и вызывает `Customer.pay()`:

```python
def pay(self, customer: Customer, *, total: float, items_count: int) -> None:
    if self.status != "Новый":
        raise RestaurantError(
            f"Заказ №{self.id} нельзя оплатить: статус «{self.status}»."
        )
    if items_count == 0:
        raise EmptyOrderError("Нельзя оплатить пустой заказ: сначала добавьте блюда.")
    customer.pay(total)
    self.status = "Оплачен"
```

Сумма и количество позиций передаются из `Restaurant`, потому что позиции
заказа хранятся в отдельном списке `order_items` (как в примере с
поликлиникой, где приём ссылается на пациента и врача по ID).

## 6. CRUD

Все операции собраны в классе `Restaurant`. Перед добавлением записи
проверяется существование связанных записей, перед удалением — отсутствие
ссылок на удаляемую запись.

| Операция | Методы |
|---|---|
| Create | `add_category`, `add_ingredient`, `add_menu_item`, `add_recipe_line`, `add_employee`, `add_customer`, `add_table`, `add_reservation`, `add_order`, `add_order_item` |
| Read | `find_category`, `find_menu_item`, `find_employee`, `find_customer`, `find_table`, `find_reservation`, `find_order`, `order_items_of` |
| Update | `update_customer`, `update_menu_item`, `update_order_status`, `update_reservation_status` |
| Delete | `delete_menu_item`, `delete_customer`, `delete_order`, `delete_reservation` |
| Расчёты и оплата | `order_total`, `paid_total`, `table_is_free`, `pay_order` |

Пример защиты от «висячих» ссылок:

```python
def delete_menu_item(self, menu_item_id: int) -> None:
    item = self.find_menu_item(menu_item_id)
    if any(line.menu_item_id == menu_item_id for line in self.order_items):
        raise RestaurantError("Нельзя удалить блюдо, которое есть в заказах.")
    self.menu_items.remove(item)
```

## 7. Обработка исключений

Собственных исключений три: базовое `RestaurantError` и два частных случая,
которые пользователь должен видеть отдельно, — `InsufficientFundsError`
и `EmptyOrderError`. Оба частных исключения наследуются от базового,
поэтому обрабатывать их можно одним блоком `except RestaurantError`.

| Ситуация | Исключение | Обработка |
|---|---|---|
| пустое обязательное поле | `RestaurantError` | сообщение пользователю, возврат в меню |
| отрицательная цена, нулевой вес, отрицательный баланс | `RestaurantError` | сообщение пользователю |
| неверный формат даты | `RestaurantError` | сообщение пользователю |
| несуществующий ID | `RestaurantError` | сообщение пользователю |
| удаление записи со ссылками | `RestaurantError` | сообщение пользователю |
| повторная оплата заказа | `RestaurantError` | сообщение пользователю |
| на балансе мало денег | `InsufficientFundsError` | «Не хватает денег: нужно …, на балансе …» |
| оплата заказа без блюд | `EmptyOrderError` | «Нельзя оплатить пустой заказ…» |
| введено не число | `ValueError` → `RestaurantError` | «… — это не число» |
| файл не найден | `FileNotFoundError` → `RestaurantError` | сообщение пользователю |
| ошибка синтаксиса JSON | `json.JSONDecodeError` → `RestaurantError` | номер строки и описание |
| ошибка синтаксиса XML | `ET.ParseError` → `RestaurantError` | сообщение пользователю |
| ошибка записи файла | `OSError` → `RestaurantError` | сообщение пользователю |
| Ctrl+C, конец ввода | `KeyboardInterrupt`, `EOFError` | корректный выход из программы |

Меню устроено так, что любая ошибка перехватывается и программа продолжает
работу (все проверки при этом лежат в `main.py`, меню их только ловит):

```python
try:
    choice = input("Выбор: ").strip()
    if choice == "1":
        show_menu(restaurant)
    elif choice == "8":
        pay_order(restaurant)          # внутри проверит баланс и пустой заказ
    elif choice == "12":
        restaurant = load_json(data_dir)   # вернёт новый объект
    ...
except RestaurantError as exc:
    print(f"Ошибка: {exc}")
except (ValueError, TypeError) as exc:
    print(f"Ошибка входных данных: {exc}")
except (OSError, ET.ParseError) as exc:
    print(f"Ошибка при работе с файлом: {exc}")
```

## 8. Форматы JSON и XML

### JSON

Корень — объект с названием ресторана и массивами сущностей. Один и тот же
набор данных читается и записывается методами `to_dict` / `from_dict`,
поэтому JSON и XML используют одну модель.

```json
{
  "restaurant": "Ресторан «Тёплый вечер»",
  "categories": [{"id": 1, "name": "Салаты", "description": "Холодные закуски"}],
  "customers": [{"id": 1, "full_name": "Алексей Петров",
                 "phone": "+7-900-444-55-66",
                 "discount_percent": 0.0, "balance": 5000.0}],
  "orders": [{"id": 1, "customer_id": 1, "employee_id": 1,
              "created_at": "2026-11-20 18:30", "table_id": 2, "status": "Новый"}]
}
```

### XML

Корень `restaurant` с атрибутом `name`, внутри — группы сущностей
(`categories`, `menu_items`, `orders`, …). Запись группы — элемент
в единственном числе, поля — вложенные элементы. Заказ «на вынос»
хранится с пустым `table_id`.

```xml
<?xml version='1.0' encoding='utf-8'?>
<restaurant name="Ресторан «Тёплый вечер»">
  <categories>
    <category>
      <id>1</id>
      <name>Салаты</name>
      <description>Холодные закуски</description>
    </category>
  </categories>
  <orders>
    <order>
      <id>3</id>
      <customer_id>1</customer_id>
      <employee_id>3</employee_id>
      <created_at>2026-11-21 12:15</created_at>
      <table_id></table_id>
      <status>Новый</status>
    </order>
  </orders>
</restaurant>
```

При загрузке XML числовые теги приводятся к `int` и `float`
(множества `int_fields`, `float_fields`), затем данные передаются
в общий `from_dict`.

### Сравнение форматов

| Критерий | JSON | XML |
|---|---|---|
| читаемость | высокая | средняя |
| объём | меньше | больше |
| типы данных | числа, строки, `null` изначально | всё строки, нужны преобразования |
| проверка структуры | нет встроенной | есть схема (XSD) |
| применение | веб-API, конфигурации | обмен документами, legacy-системы |

## 9. Тестирование

Проверено скриптом, результаты — в `docs/TEST_RESULTS.txt`
(53 проверки, все успешны):

1. `python cli.py --demo` — создаются `data/restaurant.json` и
   `data/restaurant.xml`, выводится сводка.
2. Загрузка JSON → сохранение → загрузка: данные совпадают, балансы гостей
   сохраняются.
3. Загрузка XML → сохранение → загрузка: данные совпадают, включая заказ
   без столика (`table_id` пустой).
4. Оплата заказа: сумма списывается с баланса, статус меняется на «Оплачен»,
   повторная оплата запрещена.
5. Оплата пустого заказа → `EmptyOrderError`.
6. Оплата заказа дороже баланса → `InsufficientFundsError`, баланс и статус
   не меняются.
7. Ввод нечислового значения в меню — сообщение об ошибке, программа
   продолжает работу.
8. Попытка удалить блюдо, которое есть в заказе — сообщение
   «Нельзя удалить блюдо, которое есть в заказах».
9. Загрузка несуществующего и повреждённого файла — сообщение об ошибке,
   программа работает дальше.

## 10. Выводы

В ходе работы спроектирована и реализована объектно-ориентированная модель
ресторана из 13 классов, трёх классов исключений и двух модулей
(`main.py` — модель, `cli.py` — интерфейс). Освоены: описание классов через
`dataclass`, наследование и полиморфизм, инкапсуляция проверок
в `__post_init__`, операции CRUD с контролем ссылочной целостности,
собственные исключения и обработка встроенных исключений, сериализация
одной модели в два формата — JSON и XML.

## 11. Краткие ответы на вопросы к защите

1. **Прикладное программирование** — разработка программ для решения
   прикладных задач пользователя (учёт, документы, бизнес-процессы)
   в отличие от системного программирования.
2. **Особенности разработки ПО** — работа с требованиями, проектирование,
   тестирование, сопровождение, ограничения по срокам и качеству.
3. **Компилируемые и интерпретируемые языки** — C/C++ компилируются
   в машинный код заранее; Python выполняется интерпретатором построчно.
4. **Динамическая и статическая типизация** — в Python тип известен
   во время выполнения (`x = 1`), в C++/Java — при компиляции.
5. **Строгая и слабая типизация** — в Python `"1" + 1` даёт ошибку
   (строгая), в JS — `"11"` (слабая, приведение типов).
6. **Высокоуровневые и низкоуровневые языки** — Python скрывает управление
   памятью, ассемблер и C работают с регистрами и адресами.
7. **Изменяемые и неизменяемые типы** — `list`, `dict`, `set` изменяемы;
   `int`, `str`, `tuple` — нет (`s += "a"` создаёт новую строку).
8. **Операторы, ветвление, циклы, функции** — `+ - * / // % **`,
   `if/elif/else`, `for`/`while`, `def имя(параметры): ...`.
9. **ООП** — класс описывает данные и поведение, объект — экземпляр;
   инкапсуляция скрывает внутреннее состояние, наследование расширяет
   класс, полиморфизм позволяет вызывать один метод у разных классов.
10. **`*args` и `**kwargs`** — произвольное число позиционных и именованных
    аргументов: `def f(*args, **kwargs)`.
11. **Лямбда-функции** — анонимные функции: `key = lambda x: x.price`.
12. **Аннотации типов** — `def f(x: int) -> str:`; не влияют на выполнение,
    но документируют код и помогают IDE.
13. **PEP 8** — 4 пробела на отступ, `snake_case` для функций и переменных,
    `PascalCase` для классов, длина строки до 79–88 символов.
14. **Классификация ошибок** — синтаксические, логические, ошибки времени
    выполнения (исключения).
15. **Обработка ошибок** — `try/except/else/finally`, `raise`,
    собственные исключения.
16. **Базовые исключения** — `ValueError`, `TypeError`, `KeyError`,
    `IndexError`, `FileNotFoundError`, `ZeroDivisionError`.
17. **Собственное исключение** — `class MyError(Exception): pass`, затем
    `raise MyError("текст")`. В работе: `RestaurantError` и два его
    наследника — `InsufficientFundsError`, `EmptyOrderError`.
18. **XML** — древовидный текстовый формат; в Python: `xml.etree.ElementTree`
    (`ET.parse`, `ET.SubElement`, `tree.write`).
19. **JSON** — текстовый формат «объект/массив/значение»; в Python:
    `json.dump`/`json.load` и `json.dumps`/`json.loads`.
20. **Сравнение XML и JSON** — JSON компактнее и проще для данных,
    XML строже описывает структуру (схемы, пространства имён) и удобен
    для документов.
