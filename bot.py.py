import asyncio
import os
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from dotenv import load_dotenv


# =========================================================
# НАСТРОЙКИ
# =========================================================

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip()
]

DB_NAME = "catalog.db"


# =========================================================
# ТОВАРЫ
# =========================================================

PRODUCTS = [
    {
        "brand": "ANNIMA LOVE",
        "flavor": "Кислая вишня",
        "price": 400,
        "quantity": 10,
        "description": "Яркий вкус кислой вишни.",
        "photo": "",
    },
    {
        "brand": "ANNIMA LOVE",
        "flavor": "Манго",
        "price": 400,
        "quantity": 5,
        "description": "Сочный вкус манго.",
        "photo": "",
    },
    {
        "brand": "ANNIMA LOVE",
        "flavor": "Клубника",
        "price": 400,
        "quantity": 7,
        "description": "Сладкий вкус клубники.",
        "photo": "",
    },
]


# False = остатки сохраняются после перезапуска
# True = остатки из PRODUCTS заново записываются в БД
SYNC_QUANTITY = False


# =========================================================
# БАЗА ДАННЫХ
# =========================================================

def get_db():
    return sqlite3.connect(DB_NAME)


def init_db():
    db = get_db()
    cursor = db.cursor()

    # Таблица товаров
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            flavor TEXT NOT NULL,
            price INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            description TEXT,
            photo TEXT
        )
    """)

    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT
        )
    """)

    db.commit()
    db.close()


def save_user(user):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name
        """,
        (
            user.id,
            user.username,
            user.first_name,
        )
    )

    db.commit()
    db.close()


def get_users():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT user_id
        FROM users
    """)

    users = [row[0] for row in cursor.fetchall()]

    db.close()

    return users


def sync_products():
    db = get_db()
    cursor = db.cursor()

    for product in PRODUCTS:
        cursor.execute(
            """
            SELECT id FROM products
            WHERE brand = ? AND flavor = ?
            """,
            (
                product["brand"],
                product["flavor"],
            )
        )

        existing = cursor.fetchone()

        if existing:
            if SYNC_QUANTITY:
                cursor.execute(
                    """
                    UPDATE products
                    SET price = ?,
                        quantity = ?,
                        description = ?,
                        photo = ?
                    WHERE id = ?
                    """,
                    (
                        product["price"],
                        product["quantity"],
                        product["description"],
                        product["photo"],
                        existing[0],
                    )
                )

        else:
            cursor.execute(
                """
                INSERT INTO products
                (brand, flavor, price, quantity, description, photo)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    product["brand"],
                    product["flavor"],
                    product["price"],
                    product["quantity"],
                    product["description"],
                    product["photo"],
                )
            )

    db.commit()
    db.close()


def get_categories():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT DISTINCT brand
        FROM products
        WHERE quantity > 0
        ORDER BY brand
    """)

    categories = [
        row[0]
        for row in cursor.fetchall()
    ]

    db.close()

    return categories


def get_products_by_category(brand):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT id, brand, flavor, price, quantity, description, photo
        FROM products
        WHERE brand = ? AND quantity > 0
        ORDER BY id
        """,
        (brand,)
    )

    products = cursor.fetchall()

    db.close()

    return products


def get_product(product_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT id, brand, flavor, price, quantity, description, photo
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    )

    product = cursor.fetchone()

    db.close()

    return product


def get_all_products():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT id, brand, flavor, price, quantity, description, photo
        FROM products
        ORDER BY id
    """)

    products = cursor.fetchall()

    db.close()

    return products


def decrease_product(product_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE products
        SET quantity = quantity - 1
        WHERE id = ? AND quantity > 0
        """,
        (product_id,)
    )

    success = cursor.rowcount > 0

    db.commit()
    db.close()

    return success


def delete_product(product_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        DELETE FROM products
        WHERE id = ?
        """,
        (product_id,)
    )

    deleted = cursor.rowcount > 0

    db.commit()
    db.close()

    return deleted


# =========================================================
# КЛАВИАТУРЫ
# =========================================================

def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Каталог",
                    callback_data="catalog"
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ О нас",
                    callback_data="about"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📞 Контакты",
                    callback_data="contact"
                )
            ]
        ]
    )


def categories_menu():
    buttons = []

    categories = get_categories()

    for brand in categories:
        buttons.append([
            InlineKeyboardButton(
                text=f"📦 {brand}",
                callback_data=f"category:{brand}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="🏠 Главное меню",
            callback_data="back"
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def products_menu(brand):
    buttons = []

    products = get_products_by_category(brand)

    for product in products:
        product_id = product[0]
        flavor = product[2]
        price = product[3]
        quantity = product[4]

        buttons.append([
            InlineKeyboardButton(
                text=f"{flavor} — {price} ₽ ({quantity} шт.)",
                callback_data=f"product:{product_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="catalog"
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def product_menu(product_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Выбрать",
                    callback_data=f"select:{product_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="catalog"
                )
            ]
        ]
    )


def selected_product_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Вернуться в каталог",
                    callback_data="catalog"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="back"
                )
            ]
        ]
    )


def admin_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить товар",
                    callback_data="admin_add"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Все товары",
                    callback_data="admin_products"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить товар",
                    callback_data="admin_delete"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔔 Рассылка",
                    callback_data="admin_broadcast"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="back"
                )
            ]
        ]
    )


def broadcast_cancel_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="broadcast_cancel"
                )
            ]
        ]
    )


# =========================================================
# FSM ДОБАВЛЕНИЯ ТОВАРА
# =========================================================

class AddProduct(StatesGroup):
    brand = State()
    flavor = State()
    price = State()
    quantity = State()
    description = State()
    photo = State()


# =========================================================
# FSM РАССЫЛКИ
# =========================================================

class BroadcastState(StatesGroup):
    waiting_message = State()


# =========================================================
# BOT / DISPATCHER
# =========================================================

bot = Bot(TOKEN)
dp = Dispatcher()


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message):
    # Запоминаем пользователя
    save_user(message.from_user)

    await message.answer(
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Выберите нужный раздел:",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# =========================================================
# ID
# =========================================================

@dp.message(Command("id"))
async def get_id(message: Message):
    await message.answer(
        f"🆔 Ваш Telegram ID:\n\n"
        f"<code>{message.from_user.id}</code>",
        parse_mode="HTML"
    )


# =========================================================
# КАТАЛОГ
# =========================================================

@dp.callback_query(F.data == "catalog")
async def catalog(callback: CallbackQuery):
    await callback.message.edit_text(
        "📦 <b>Каталог</b>\n\n"
        "Выберите бренд:",
        parse_mode="HTML",
        reply_markup=categories_menu()
    )

    await callback.answer()


# =========================================================
# КАТЕГОРИЯ
# =========================================================

@dp.callback_query(F.data.startswith("category:"))
async def category(callback: CallbackQuery):
    brand = callback.data.split(":", 1)[1]

    products = get_products_by_category(brand)

    if not products:
        await callback.message.edit_text(
            "❌ В этой категории сейчас нет товаров.",
            reply_markup=categories_menu()
        )

        await callback.answer()
        return

    await callback.message.edit_text(
        f"📦 <b>{brand}</b>\n\n"
        "Выберите вкус:",
        parse_mode="HTML",
        reply_markup=products_menu(brand)
    )

    await callback.answer()


# =========================================================
# КАРТОЧКА ТОВАРА
# =========================================================

@dp.callback_query(F.data.startswith("product:"))
async def product(callback: CallbackQuery):
    product_id = int(
        callback.data.split(":", 1)[1]
    )

    item = get_product(product_id)

    if not item:
        await callback.answer(
            "Товар не найден.",
            show_alert=True
        )
        return

    (
        product_id,
        brand,
        flavor,
        price,
        quantity,
        description,
        photo
    ) = item

    if quantity <= 0:
        await callback.answer(
            "❌ Товар закончился.",
            show_alert=True
        )
        return

    text = (
        f"📦 <b>{brand}</b>\n\n"
        f"🍓 <b>Вкус:</b> {flavor}\n"
        f"💰 <b>Цена:</b> {price} ₽\n"
        f"📊 <b>Остаток:</b> {quantity} шт.\n\n"
        f"📝 <b>Описание:</b>\n"
        f"{description or 'Нет описания'}"
    )

    if photo:
        await callback.message.answer_photo(
            photo=photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=product_menu(product_id)
        )
    else:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=product_menu(product_id)
        )

    await callback.answer()


# =========================================================
# ВЫБОР ТОВАРА
# =========================================================

@dp.callback_query(F.data.startswith("select:"))
async def select_product(callback: CallbackQuery):
    product_id = int(
        callback.data.split(":", 1)[1]
    )

    item = get_product(product_id)

    if not item:
        await callback.answer(
            "❌ Товар не найден.",
            show_alert=True
        )
        return

    (
        product_id,
        brand,
        flavor,
        price,
        quantity,
        description,
        photo
    ) = item

    if quantity <= 0:
        await callback.answer(
            "❌ Товар уже закончился.",
            show_alert=True
        )
        return

    # Уменьшаем остаток
    success = decrease_product(product_id)

    if not success:
        await callback.answer(
            "❌ Товар уже закончился.",
            show_alert=True
        )
        return

    user = callback.from_user

    username = (
        f"@{user.username}"
        if user.username
        else "нет username"
    )

    # =====================================================
    # УВЕДОМЛЕНИЕ АДМИНИСТРАТОРАМ
    # =====================================================

    admin_text = (
        "🔔 <b>Новый выбор товара</b>\n\n"
        f"🏷 <b>Бренд:</b> {brand}\n"
        f"🍓 <b>Вкус:</b> {flavor}\n"
        f"💰 <b>Цена:</b> {price} ₽\n"
        f"📦 <b>Количество:</b> 1 шт.\n"
        f"📊 <b>Осталось:</b> {quantity - 1} шт.\n\n"
        f"👤 <b>Пользователь:</b> {username}\n"
        f"🆔 <b>Telegram ID:</b> "
        f"<code>{user.id}</code>"
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                admin_text,
                parse_mode="HTML"
            )

        except Exception as e:
            print(
                f"Не удалось отправить уведомление "
                f"администратору {admin_id}: {e}"
            )

    # =====================================================
    # СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЮ
    # =====================================================

    await callback.message.answer(
        "✅ <b>Товар выбран.</b>\n\n"
        "Информация отправлена администратору.",
        parse_mode="HTML",
        reply_markup=selected_product_menu()
    )

    await callback.answer()


# =========================================================
# О НАС
# =========================================================

@dp.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ <b>О нас</b>\n\n"
        "Добро пожаловать в наш каталог!",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

    await callback.answer()


# =========================================================
# КОНТАКТЫ
# =========================================================

@dp.callback_query(F.data == "contact")
async def contact(callback: CallbackQuery):
    await callback.message.edit_text(
        "📞 <b>Контакты</b>\n\n"
        "По всем вопросам обращайтесь к администратору.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

    await callback.answer()


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите нужный раздел:",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

    await callback.answer()


# =========================================================
# АДМИНКА
# =========================================================

@dp.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer(
            "❌ У вас нет доступа к админ-панели."
        )
        return

    await message.answer(
        "🔐 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )


# =========================================================
# ДОБАВЛЕНИЕ ТОВАРА
# =========================================================

@dp.callback_query(F.data == "admin_add")
async def admin_add(
    callback: CallbackQuery,
    state: FSMContext
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    await state.set_state(
        AddProduct.brand
    )

    await callback.message.answer(
        "➕ <b>Добавление товара</b>\n\n"
        "Введите бренд:",
        parse_mode="HTML"
    )

    await callback.answer()


@dp.message(AddProduct.brand)
async def add_brand(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        brand=message.text.strip()
    )

    await state.set_state(
        AddProduct.flavor
    )

    await message.answer(
        "Введите вкус:"
    )


@dp.message(AddProduct.flavor)
async def add_flavor(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        flavor=message.text.strip()
    )

    await state.set_state(
        AddProduct.price
    )

    await message.answer(
        "Введите цену числом:\n"
        "Например: 400"
    )


@dp.message(AddProduct.price)
async def add_price(
    message: Message,
    state: FSMContext
):
    try:
        price = int(
            message.text.strip()
        )

        if price < 0:
            raise ValueError

    except ValueError:
        await message.answer(
            "❌ Цена должна быть целым числом.\n"
            "Например: 400"
        )
        return

    await state.update_data(
        price=price
    )

    await state.set_state(
        AddProduct.quantity
    )

    await message.answer(
        "Введите количество товара:\n"
        "Например: 10"
    )


@dp.message(AddProduct.quantity)
async def add_quantity(
    message: Message,
    state: FSMContext
):
    try:
        quantity = int(
            message.text.strip()
        )

        if quantity < 0:
            raise ValueError

    except ValueError:
        await message.answer(
            "❌ Количество должно быть целым числом.\n"
            "Например: 10"
        )
        return

    await state.update_data(
        quantity=quantity
    )

    await state.set_state(
        AddProduct.description
    )

    await message.answer(
        "Введите описание товара:"
    )


@dp.message(AddProduct.description)
async def add_description(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        description=message.text.strip()
    )

    await state.set_state(
        AddProduct.photo
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Пропустить фото",
                    callback_data="add_no_photo"
                )
            ]
        ]
    )

    await message.answer(
        "📸 Отправьте фотографию товара.\n\n"
        "Если фото нет — нажмите "
        "«Пропустить фото».",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "add_no_photo")
async def add_no_photo(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.update_data(
        photo=""
    )

    await finish_add_product(
        callback.message,
        state
    )

    await callback.answer()


@dp.message(AddProduct.photo, F.photo)
async def add_photo(
    message: Message,
    state: FSMContext
):
    photo_id = message.photo[-1].file_id

    await state.update_data(
        photo=photo_id
    )

    await finish_add_product(
        message,
        state
    )


@dp.message(AddProduct.photo)
async def photo_required(message: Message):
    await message.answer(
        "📸 Отправьте фотографию товара "
        "или нажмите кнопку "
        "«Пропустить фото»."
    )


async def finish_add_product(
    message: Message,
    state: FSMContext
):
    data = await state.get_data()

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO products
        (brand, flavor, price, quantity, description, photo)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            data["brand"],
            data["flavor"],
            data["price"],
            data["quantity"],
            data["description"],
            data.get("photo", "")
        )
    )

    db.commit()
    db.close()

    await state.clear()

    await message.answer(
        "✅ <b>Товар успешно добавлен!</b>\n\n"
        f"🏷 Бренд: {data['brand']}\n"
        f"🍓 Вкус: {data['flavor']}\n"
        f"💰 Цена: {data['price']} ₽\n"
        f"📦 Количество: {data['quantity']} шт.",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )


# =========================================================
# ВСЕ ТОВАРЫ
# =========================================================

@dp.callback_query(F.data == "admin_products")
async def admin_products(
    callback: CallbackQuery
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    products = get_all_products()

    if not products:
        await callback.message.edit_text(
            "📦 <b>Товаров пока нет.</b>",
            parse_mode="HTML",
            reply_markup=admin_menu()
        )

        await callback.answer()
        return

    text = "📦 <b>Все товары:</b>\n\n"

    for product in products:
        (
            product_id,
            brand,
            flavor,
            price,
            quantity,
            description,
            photo
        ) = product

        text += (
            f"🆔 <b>{product_id}</b>\n"
            f"🏷 {brand}\n"
            f"🍓 {flavor}\n"
            f"💰 {price} ₽\n"
            f"📦 Остаток: {quantity} шт.\n"
            f"📸 Фото: "
            f"{'есть' if photo else 'нет'}\n"
            f"──────────────\n"
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="admin_back"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await callback.answer()


# =========================================================
# УДАЛЕНИЕ ТОВАРА
# =========================================================

@dp.callback_query(F.data == "admin_delete")
async def admin_delete(
    callback: CallbackQuery
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    products = get_all_products()

    if not products:
        await callback.message.edit_text(
            "❌ Товаров нет.",
            reply_markup=admin_menu()
        )

        await callback.answer()
        return

    buttons = []

    for product in products:
        product_id = product[0]
        brand = product[1]
        flavor = product[2]

        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {brand} — {flavor}",
                callback_data=f"delete:{product_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="admin_back"
        )
    ])

    await callback.message.edit_text(
        "🗑 <b>Удаление товара</b>\n\n"
        "Выберите товар:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("delete:"))
async def delete(
    callback: CallbackQuery
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    product_id = int(
        callback.data.split(":", 1)[1]
    )

    product = get_product(product_id)

    if not product:
        await callback.answer(
            "Товар уже удалён.",
            show_alert=True
        )
        return

    brand = product[1]
    flavor = product[2]

    delete_product(product_id)

    await callback.message.edit_text(
        "✅ <b>Товар удалён.</b>\n\n"
        f"🏷 {brand}\n"
        f"🍓 {flavor}",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )

    await callback.answer()


# =========================================================
# НАЗАД В АДМИНКУ
# =========================================================

@dp.callback_query(F.data == "admin_back")
async def admin_back(
    callback: CallbackQuery
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        "🔐 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )

    await callback.answer()


# =========================================================
# РАССЫЛКА
# =========================================================

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(
    callback: CallbackQuery,
    state: FSMContext
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    users = get_users()

    await state.set_state(
        BroadcastState.waiting_message
    )

    await callback.message.answer(
        "🔔 <b>Рассылка</b>\n\n"
        f"Получателей в базе: <b>{len(users)}</b>\n\n"
        "Отправьте сообщение, которое нужно "
        "разослать пользователям.\n\n"
        "Можно отправить:\n"
        "• текст\n"
        "• фото с подписью\n\n"
        "Для отмены нажмите кнопку ниже.",
        parse_mode="HTML",
        reply_markup=broadcast_cancel_menu()
    )

    await callback.answer()


# =========================================================
# ОТМЕНА РАССЫЛКИ
# =========================================================

@dp.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel(
    callback: CallbackQuery,
    state: FSMContext
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    await state.clear()

    await callback.message.answer(
        "❌ Рассылка отменена.",
        reply_markup=admin_menu()
    )

    await callback.answer()


# =========================================================
# ПОЛУЧЕНИЕ СООБЩЕНИЯ ДЛЯ РАССЫЛКИ
# =========================================================

@dp.message(BroadcastState.waiting_message)
async def process_broadcast(
    message: Message,
    state: FSMContext
):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    users = get_users()

    if not users:
        await state.clear()

        await message.answer(
            "❌ В базе пока нет пользователей.",
            reply_markup=admin_menu()
        )

        return

    # Сохраняем тип сообщения
    success_count = 0
    failed_count = 0

    # =====================================================
    # РАССЫЛКА ТЕКСТА
    # =====================================================

    if message.text:

        for user_id in users:
            try:
                await bot.send_message(
                    user_id,
                    message.text
                )

                success_count += 1

            except Exception as e:
                failed_count += 1

                print(
                    f"Ошибка отправки пользователю "
                    f"{user_id}: {e}"
                )

            # Небольшая пауза между отправками
            await asyncio.sleep(0.05)

    # =====================================================
    # РАССЫЛКА ФОТО
    # =====================================================

    elif message.photo:

        photo_id = message.photo[-1].file_id
        caption = message.caption or ""

        for user_id in users:
            try:
                await bot.send_photo(
                    user_id,
                    photo=photo_id,
                    caption=caption
                )

                success_count += 1

            except Exception as e:
                failed_count += 1

                print(
                    f"Ошибка отправки фото "
                    f"пользователю {user_id}: {e}"
                )

            await asyncio.sleep(0.05)

    # =====================================================
    # НЕПОДДЕРЖИВАЕМЫЙ ТИП
    # =====================================================

    else:
        await message.answer(
            "❌ Сейчас можно отправить только "
            "текст или фотографию с подписью."
        )
        return

    await state.clear()

    # =====================================================
    # РЕЗУЛЬТАТ
    # =====================================================

    await message.answer(
        "✅ <b>Рассылка завершена!</b>\n\n"
        f"📨 Успешно отправлено: "
        f"<b>{success_count}</b>\n"
        f"❌ Не доставлено: "
        f"<b>{failed_count}</b>",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )


# =========================================================
# ЗАПУСК
# =========================================================

async def main():
    if not TOKEN:
        print(
            "❌ BOT_TOKEN не найден в .env"
        )
        return

    if not ADMIN_IDS:
        print(
            "❌ ADMIN_IDS не найден в .env"
        )
        return

    init_db()
    sync_products()

    print("✅ Бот запущен!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())