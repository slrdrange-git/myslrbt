import os
import logging
import asyncio
import json
import uuid
import random
import string
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery, SuccessfulPayment,
    FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

# ============================================
# НАСТРОЙКИ
# ============================================
TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = 775020198  # ← ТВОЙ ID
PORT = int(os.environ.get('PORT', 8080))
RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL', 'https://your-bot.onrender.com')

# Логи
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# ГЛОБАЛЬНЫЙ ЦИКЛ ASYNCIO
# ============================================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# ============================================
# БАЗА ДАННЫХ
# ============================================
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_json(filename, data):
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# === Клиенты ===
def get_clients():
    return load_json('clients.json')

def save_clients(clients):
    save_json('clients.json', clients)

# === Заказы ===
def get_orders():
    return load_json('orders.json')

def save_orders(orders):
    save_json('orders.json', orders)

# === Отзывы ===
def get_reviews():
    return load_json('reviews.json')

def save_reviews(reviews):
    save_json('reviews.json', reviews)

# === Рефералы ===
def get_referrals():
    return load_json('referrals.json')

def save_referrals(referrals):
    save_json('referrals.json', referrals)

# === Демо-проект ===
DEMO_PROJECT = {
    "name": "🤖 Демо-бот для записи",
    "description": "Посмотри, как работает мой бот в реальном времени!",
    "link": "https://t.me/your_demo_bot",  # ← ССЫЛКА НА ТВОЙ ДЕМО-БОТ
    "features": [
        "✅ Запись на услуги",
        "✅ Календарь на месяц",
        "✅ Отзывы с фото",
        "✅ Админ-панель",
        "✅ Напоминания"
    ]
}

# === Программа лояльности ===
LOYALTY_THRESHOLD = 5  # Количество заказов для бонуса
LOYALTY_BONUS = 250     # Сумма бонуса в рублях

# ============================================
# ГЕНЕРАЦИЯ ПРОМОКОДА
# ============================================
def generate_promo_code(user_id, length=8):
    letters = string.ascii_uppercase + string.digits
    code = ''.join(random.choice(letters) for i in range(length))
    return f"LOYALTY{code}"

# ============================================
# РАСЧЁТ РЕЙТИНГА
# ============================================
def calculate_rating():
    reviews = get_reviews()
    approved = [r for r in reviews if r.get('approved', False)]
    
    if not approved:
        return 5.0  # По умолчанию 5 звёзд
    
    total = sum(r['rating'] for r in approved)
    avg = total / len(approved)
    return round(avg, 1)

# ============================================
# СОСТОЯНИЯ
# ============================================
class OrderStates(StatesGroup):
    choosing_product = State()
    entering_contact = State()
    entering_details = State()
    confirming = State()

class ReviewStates(StatesGroup):
    waiting_rating = State()
    waiting_text = State()
    waiting_contact = State()
    waiting_photo = State()
    confirming = State()

class AdminStates(StatesGroup):
    processing_order = State()
    broadcast_message = State()
    broadcast_confirm = State()

# ============================================
# ПРОВЕРКА НА АДМИНА
# ============================================
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# ============================================
# ТОВАРЫ (БОТЫ)
# ============================================
PRODUCTS = [
    {
        "id": "tattoo_bot",
        "name": "🤖 Бот для тату-мастера",
        "price": 25000,
        "description": "✅ Опыт — бот, которым можно гордиться\n✅ Качество — код не сыпется, работает 24/7\n✅ Поддержка — не бросаю после продажи\n✅ Результат — бот реально приносит деньги",
        "features": [
            "💰 ДЕНЬГИ: Работает 24/7, принимает заявки, пока вы спите",
            "⚡️ Окупаемость: 1-2 клиента — и бот ваш окупился",
            "⏰ ВРЕМЯ: Вы не отвечаете на тупые вопросы",
            "📈 РОСТ: Отзывы + промокоды = новые клиенты"
        ],
        "client_features": [
            "✅ Услуги с ценами — без 'прайс в личку'",
            "✅ Запись за 30 секунд",
            "✅ История записей и отмена",
            "✅ Отзывы с фото + промокоды",
            "✅ Напоминание за 24 часа",
            "✅ Инфо с контактами"
        ],
        "admin_features": [
            "✅ Управление услугами",
            "✅ Все записи с фильтрацией",
            "✅ Подтверждение/отмена в 1 клик",
            "✅ Модерация отзывов",
            "✅ Статистика по выручке",
            "✅ Рассылка клиентам",
            "✅ Уведомления о каждой записи"
        ]
    },
    {
        "id": "manicure_bot",
        "name": "💅 Бот для маникюра",
        "price": 20000,
        "description": "✅ Опыт — бот, которым можно гордиться\n✅ Качество — код не сыпется, работает 24/7\n✅ Поддержка — не бросаю после продажи\n✅ Результат — бот реально приносит деньги",
        "features": [
            "💰 ДЕНЬГИ: Работает 24/7, принимает заявки, пока вы спите",
            "⚡️ Окупаемость: 1-2 клиента — и бот ваш окупился",
            "⏰ ВРЕМЯ: Вы не отвечаете на тупые вопросы",
            "📈 РОСТ: Отзывы + промокоды = новые клиенты"
        ],
        "client_features": [
            "✅ Услуги с ценами",
            "✅ Запись за 30 секунд",
            "✅ История записей",
            "✅ Отзывы с фото",
            "✅ Напоминание за 24 часа"
        ],
        "admin_features": [
            "✅ Управление услугами",
            "✅ Все записи",
            "✅ Подтверждение/отмена",
            "✅ Модерация отзывов",
            "✅ Статистика",
            "✅ Рассылка",
            "✅ Уведомления"
        ]
    },
    {
        "id": "barber_bot",
        "name": "✂️ Бот для барбера",
        "price": 20000,
        "description": "✅ Опыт — бот, которым можно гордиться\n✅ Качество — код не сыпется, работает 24/7\n✅ Поддержка — не бросаю после продажи\n✅ Результат — бот реально приносит деньги",
        "features": [
            "💰 ДЕНЬГИ: Работает 24/7, принимает заявки",
            "⚡️ Окупаемость: 1-2 клиента — окупился",
            "⏰ ВРЕМЯ: Вы не отвечаете на тупые вопросы",
            "📈 РОСТ: Отзывы + промокоды"
        ],
        "client_features": [
            "✅ Услуги с ценами",
            "✅ Запись за 30 секунд",
            "✅ История записей",
            "✅ Отзывы с фото",
            "✅ Напоминание за 24 часа"
        ],
        "admin_features": [
            "✅ Управление услугами",
            "✅ Все записи",
            "✅ Подтверждение/отмена",
            "✅ Модерация отзывов",
            "✅ Статистика",
            "✅ Уведомления"
        ]
    },
    {
        "id": "custom_bot",
        "name": "⚡️ Индивидуальный бот",
        "price": 35000,
        "description": "✅ Опыт — бот, которым можно гордиться\n✅ Качество — код не сыпется, работает 24/7\n✅ Поддержка — не бросаю после продажи\n✅ Результат — бот реально приносит деньги",
        "features": [
            "💰 ДЕНЬГИ: Работает 24/7, принимает заявки",
            "⚡️ Окупаемость: 1-2 клиента — окупился",
            "⏰ ВРЕМЯ: Вы не отвечаете на тупые вопросы",
            "📈 РОСТ: Отзывы + промокоды"
        ],
        "client_features": [
            "✅ Любой функционал под ваш бизнес",
            "✅ Индивидуальный дизайн",
            "✅ Интеграции с CRM",
            "✅ Поддержка 2 месяца"
        ],
        "admin_features": [
            "✅ Полное администрирование",
            "✅ Статистика",
            "✅ Рассылка",
            "✅ Уведомления"
        ]
    }
]

# ============================================
# ИНИЦИАЛИЗАЦИЯ БОТА
# ============================================
storage = MemoryStorage()
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=storage)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================
async def notify_admin(message: str):
    """Отправляет уведомление админу"""
    try:
        await bot.send_message(ADMIN_ID, f"👑 <b>Админ:</b>\n{message}")
    except Exception as e:
        logger.error(f"Ошибка уведомления админа: {e}")

async def notify_user(user_id: int, message: str):
    """Отправляет уведомление пользователю"""
    try:
        await bot.send_message(user_id, f"📢 <b>Уведомление:</b>\n{message}")
    except Exception as e:
        logger.error(f"Ошибка уведомления пользователя {user_id}: {e}")

def generate_order_id():
    return str(uuid.uuid4())[:8].upper()

def check_loyalty(user_id):
    """Проверяет количество заказов и начисляет бонус"""
    orders = get_orders()
    completed = [o for o in orders if o['user_id'] == user_id and o['status'] == 'completed']
    
    if len(completed) >= LOYALTY_THRESHOLD:
        referrals = get_referrals()
        # Проверяем, получал ли уже бонус
        existing = [r for r in referrals if r['user_id'] == user_id and r['type'] == 'loyalty']
        if not existing:
            return True
    return False

# ============================================
# КЛАВИАТУРЫ
# ============================================
def main_menu():
    kb = [
        [InlineKeyboardButton(text="🛍 Каталог ботов", callback_data="catalog")],
        [InlineKeyboardButton(text="🎮 Демо-проект", callback_data="demo")],
        [InlineKeyboardButton(text="⭐️ Отзывы", callback_data="reviews")],
        [InlineKeyboardButton(text="👨‍💻 О разработчике", callback_data="about")],
        [InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders")],
        [InlineKeyboardButton(text="🎁 Программа лояльности", callback_data="loyalty")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def products_keyboard():
    kb = []
    for p in PRODUCTS:
        kb.append([InlineKeyboardButton(
            text=f"{p['name']} - {p['price']}₽",
            callback_data=f"prod_{p['id']}"
        )])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def product_detail_keyboard(product_id):
    kb = [
        [InlineKeyboardButton(text="✅ Заказать", callback_data=f"order_{product_id}")],
        [InlineKeyboardButton(text="🔙 В каталог", callback_data="catalog")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def demo_keyboard():
    kb = [
        [InlineKeyboardButton(text="🎮 Посмотреть демо", url=DEMO_PROJECT['link'])],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def reviews_keyboard():
    kb = [
        [InlineKeyboardButton(text="👀 Все отзывы", callback_data="show_reviews")],
        [InlineKeyboardButton(text="✏️ Оставить отзыв", callback_data="leave_review")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def rating_keyboard():
    kb = []
    for i in range(1, 6):
        kb.append([InlineKeyboardButton(
            text="⭐️" * i,
            callback_data=f"rating_{i}"
        )])
    kb.append([InlineKeyboardButton(text="🔙 Отмена", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def photo_options_keyboard():
    kb = [
        [
            InlineKeyboardButton(text="📸 Добавить фото", callback_data="add_photo"),
            InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_photo")
        ],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def admin_menu():
    kb = [
        [InlineKeyboardButton(text="📋 Заказы", callback_data="admin_orders")],
        [InlineKeyboardButton(text="⭐️ Модерация отзывов", callback_data="admin_reviews")],
        [InlineKeyboardButton(text="👥 Клиенты", callback_data="admin_clients")],
        [InlineKeyboardButton(text="💰 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🎁 Бонусы лояльности", callback_data="admin_loyalty")],
        [InlineKeyboardButton(text="🔙 Выход", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def back_keyboard():
    kb = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def cancel_keyboard():
    kb = [[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ============================================
# Flask
# ============================================
app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Бот-продавец работает! 🤖"

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    try:
        update_data = request.json
        asyncio.run_coroutine_threadsafe(process_update(update_data), loop)
        return 'ok', 200
    except Exception as e:
        logger.error(f"Ошибка вебхука: {e}")
        return 'error', 500

async def process_update(update_data):
    try:
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"Ошибка обработки апдейта: {e}")

@app.route('/webhook_info', methods=['GET'])
def webhook_info():
    try:
        future = asyncio.run_coroutine_threadsafe(get_webhook_info(), loop)
        result = future.result(timeout=5)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

async def get_webhook_info():
    bot_info = await bot.get_me()
    webhook_info = await bot.get_webhook_info()
    return {
        "bot": {"id": bot_info.id, "username": bot_info.username},
        "webhook": {"url": webhook_info.url}
    }

@app.route('/set_webhook', methods=['GET'])
def set_webhook_route():
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook/{TOKEN}"
    asyncio.run_coroutine_threadsafe(bot.set_webhook(webhook_url), loop)
    return f"✅ Webhook установлен на {webhook_url}"

# ============================================
# ОБРАБОТЧИКИ БОТА
# ============================================

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    logger.info(f"Пользователь {user.full_name} запустил бота")
    
    # Сохраняем клиента
    clients = get_clients()
    if not any(c['user_id'] == user.id for c in clients):
        clients.append({
            "user_id": user.id,
            "username": user.username or user.full_name,
            "first_seen": datetime.now().isoformat(),
            "orders": [],
            "reviews": []
        })
        save_clients(clients)
    
    rating = calculate_rating()
    
    welcome_text = (
        f"🔥 <b>Привет, {user.first_name}!</b>\n\n"
        f"👨‍💻 <b>Разработчик:</b> @x40vef4yX\n"
        f"⭐️ <b>Рейтинг:</b> {rating}/5.0 (на основе отзывов)\n\n"
        f"Я создаю <b>Telegram-ботов</b>, которые реально приносят деньги!\n\n"
        f"👇 <b>Выбери действие:</b>"
    )
    
    await message.answer(welcome_text, reply_markup=main_menu())

@dp.callback_query(F.data == "back")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    rating = calculate_rating()
    await callback.message.edit_text(
        f"🔥 <b>Главное меню</b>\n\n⭐️ Рейтинг: {rating}/5.0",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "cancel")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "catalog")
async def catalog(callback: types.CallbackQuery):
    text = "🛍 <b>Каталог ботов</b>\n\nВыбери готовое решение:"
    await callback.message.edit_text(text, reply_markup=products_keyboard())

@dp.callback_query(F.data.startswith("prod_"))
async def show_product(callback: types.CallbackQuery, state: FSMContext):
    prod_id = callback.data.replace("prod_", "")
    product = next((p for p in PRODUCTS if p['id'] == prod_id), None)
    
    if not product:
        await callback.answer("❌ Товар не найден")
        return
    
    await state.update_data(selected_product=product)
    
    text = (
        f"{product['name']}\n\n"
        f"{product['description']}\n\n"
        f"🎯 <b>ЧТО ДАЁТ БИЗНЕСУ:</b>\n" + "\n".join([f"  {f}" for f in product['features']]) + "\n\n"
        f"🛠 <b>ДЛЯ КЛИЕНТОВ:</b>\n" + "\n".join([f"  {f}" for f in product['client_features']]) + "\n\n"
        f"👑 <b>ДЛЯ ВАС:</b>\n" + "\n".join([f"  {f}" for f in product['admin_features']]) + "\n\n"
        f"💰 <b>Цена:</b> {product['price']}₽"
    )
    
    await callback.message.edit_text(text, reply_markup=product_detail_keyboard(prod_id))

@dp.callback_query(F.data == "demo")
async def demo(callback: types.CallbackQuery):
    text = (
        f"🎮 <b>{DEMO_PROJECT['name']}</b>\n\n"
        f"{DEMO_PROJECT['description']}\n\n"
        f"⚡️ <b>Возможности:</b>\n" + "\n".join([f"  {f}" for f in DEMO_PROJECT['features']]) + "\n\n"
        f"👇 Нажми кнопку ниже, чтобы протестировать!"
    )
    await callback.message.edit_text(text, reply_markup=demo_keyboard())

@dp.callback_query(F.data == "about")
async def about(callback: types.CallbackQuery):
    rating = calculate_rating()
    reviews = get_reviews()
    approved = [r for r in reviews if r.get('approved', False)]
    orders = get_orders()
    completed = [o for o in orders if o['status'] == 'completed']
    
    text = (
        f"👨‍💻 <b>О разработчике</b>\n\n"
        f"⭐️ <b>Рейтинг:</b> {rating}/5.0 (на основе {len(approved)} отзывов)\n"
        f"📦 <b>Проектов:</b> {len(completed)}+\n"
        f"✅ <b>Гарантия:</b> 1 месяц поддержки\n\n"
        f"🔥 <b>Почему я:</b>\n"
        f"✅ Опыт — бот, которым можно гордиться\n"
        f"✅ Качество — код не сыпется, работает 24/7\n"
        f"✅ Поддержка — не бросаю после продажи\n"
        f"✅ Результат — бот реально приносит деньги"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard())

@dp.callback_query(F.data == "loyalty")
async def loyalty(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    orders = get_orders()
    completed = [o for o in orders if o['user_id'] == user_id and o['status'] == 'completed']
    
    text = (
        f"🎁 <b>Программа лояльности</b>\n\n"
        f"🔥 <b>Условия:</b>\n"
        f"• За {LOYALTY_THRESHOLD} выполненных заказов — бонус {LOYALTY_BONUS}₽ на карту\n"
        f"• Бонус начисляется автоматически после {LOYALTY_THRESHOLD}-го заказа\n\n"
        f"📊 <b>Ваш прогресс:</b>\n"
        f"✅ Выполнено заказов: {len(completed)}\n"
        f"🎯 Осталось до бонуса: {max(0, LOYALTY_THRESHOLD - len(completed))}"
    )
    
    await callback.message.edit_text(text, reply_markup=back_keyboard())

@dp.callback_query(F.data == "reviews")
async def reviews_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⭐️ <b>Отзывы</b>\n\nВыбери действие:",
        reply_markup=reviews_keyboard()
    )

@dp.callback_query(F.data == "show_reviews")
async def show_reviews(callback: types.CallbackQuery):
    reviews = get_reviews()
    approved = [r for r in reviews if r.get('approved', False)]
    
    if not approved:
        await callback.message.edit_text(
            "😕 Пока нет отзывов. Будь первым!",
            reply_markup=reviews_keyboard()
        )
        return
    
    text = "⭐️ <b>Отзывы клиентов:</b>\n\n"
    for r in approved[-10:]:
        stars = "⭐️" * r['rating']
        text += f"👤 {r['username']} {stars}\n"
        text += f"📝 {r['text']}\n"
        if r.get('contact'):
            text += f"📞 {r['contact']}\n"
        text += f"🕐 {r['created_at'][:10]}\n\n"
    
    await callback.message.edit_text(text, reply_markup=reviews_keyboard())

@dp.callback_query(F.data == "leave_review")
async def leave_review(callback: types.CallbackQuery, state: FSMContext):
    # Проверяем, есть ли выполненные заказы
    orders = get_orders()
    user_orders = [o for o in orders if o['user_id'] == callback.from_user.id and o['status'] == 'completed']
    
    if not user_orders:
        await callback.answer(
            "❌ Оставлять отзывы могут только клиенты с выполненными заказами!",
            show_alert=True
        )
        return
    
    await state.set_state(ReviewStates.waiting_rating)
    await callback.message.edit_text(
        "⭐️ Оцените мою работу от 1 до 5:",
        reply_markup=rating_keyboard()
    )

@dp.callback_query(ReviewStates.waiting_rating, F.data.startswith("rating_"))
async def process_rating(callback: types.CallbackQuery, state: FSMContext):
    rating = int(callback.data.replace("rating_", ""))
    await state.update_data(rating=rating)
    await state.set_state(ReviewStates.waiting_text)
    await callback.message.edit_text(
        "📝 Напишите ваш отзыв (текст):",
        reply_markup=cancel_keyboard()
    )

@dp.message(ReviewStates.waiting_text)
async def process_text(message: types.Message, state: FSMContext):
    if len(message.text) > 1000:
        await message.answer("❌ Слишком длинный отзыв. Максимум 1000 символов.")
        return
    
    await state.update_data(review_text=message.text)
    await state.set_state(ReviewStates.waiting_contact)
    await message.answer(
        "📞 Оставьте ваш контакт для проверки (телефон или @username):",
        reply_markup=cancel_keyboard()
    )

@dp.message(ReviewStates.waiting_contact)
async def process_contact(message: types.Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await state.set_state(ReviewStates.waiting_photo)
    await message.answer(
        "📸 Добавьте фото к отзыву (или пропустите):",
        reply_markup=photo_options_keyboard()
    )

@dp.callback_query(ReviewStates.waiting_photo, F.data == "add_photo")
async def add_photo_prompt(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📸 Отправьте фото:",
        reply_markup=cancel_keyboard()
    )

@dp.message(ReviewStates.waiting_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    reviews = get_reviews()
    new_review = {
        "id": len(reviews) + 1,
        "user_id": message.from_user.id,
        "username": message.from_user.username or message.from_user.full_name,
        "rating": data['rating'],
        "text": data['review_text'],
        "contact": data.get('contact', ''),
        "has_photo": True,
        "approved": False,
        "created_at": datetime.now().isoformat()
    }
    reviews.append(new_review)
    save_reviews(reviews)
    
    await notify_admin(
        f"⭐️ <b>Новый отзыв на модерацию!</b>\n\n"
        f"👤 Пользователь: @{message.from_user.username or message.from_user.full_name}\n"
        f"⭐️ Оценка: {data['rating']}\n"
        f"📝 Текст: {data['review_text']}\n"
        f"📞 Контакт: {data.get('contact', 'не указан')}\n"
        f"📸 С фото"
    )
    
    await message.answer(
        "✅ Спасибо за отзыв! Он появится после проверки модератором.",
        reply_markup=main_menu()
    )
    await state.clear()

@dp.callback_query(ReviewStates.waiting_photo, F.data == "skip_photo")
async def skip_photo(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    reviews = get_reviews()
    new_review = {
        "id": len(reviews) + 1,
        "user_id": callback.from_user.id,
        "username": callback.from_user.username or callback.from_user.full_name,
        "rating": data['rating'],
        "text": data['review_text'],
        "contact": data.get('contact', ''),
        "has_photo": False,
        "approved": False,
        "created_at": datetime.now().isoformat()
    }
    reviews.append(new_review)
    save_reviews(reviews)
    
    await notify_admin(
        f"⭐️ <b>Новый отзыв на модерацию!</b>\n\n"
        f"👤 Пользователь: @{callback.from_user.username or callback.from_user.full_name}\n"
        f"⭐️ Оценка: {data['rating']}\n"
        f"📝 Текст: {data['review_text']}\n"
        f"📞 Контакт: {data.get('contact', 'не указан')}\n"
        f"📸 Без фото"
    )
    
    await callback.message.edit_text(
        "✅ Спасибо за отзыв! Он появится после проверки модератором.",
        reply_markup=main_menu()
    )
    await state.clear()

@dp.callback_query(F.data == "my_orders")
async def my_orders(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    orders = get_orders()
    user_orders = [o for o in orders if o['user_id'] == user_id]
    
    if not user_orders:
        await callback.message.edit_text(
            "📋 <b>У вас пока нет заказов</b>\n\nХотите заказать бота? Перейдите в каталог!",
            reply_markup=back_keyboard()
        )
        return
    
    text = "📋 <b>Мои заказы</b>\n\n"
    for o in user_orders[-5:]:
        status_emoji = {
            'new': '🆕',
            'paid': '💳',
            'in_progress': '⚙️',
            'completed': '✅'
        }.get(o['status'], '❓')
        text += f"{status_emoji} <b>Заказ #{o['id']}</b>\n"
        text += f"   💎 {o['product_name']}\n"
        text += f"   📊 Статус: {o['status']}\n"
        text += f"   💰 {o['price']}₽\n\n"
    
    await callback.message.edit_text(text, reply_markup=back_keyboard())

# ---------- ОФОРМЛЕНИЕ ЗАКАЗА ----------
@dp.callback_query(F.data.startswith("order_"))
async def start_order(callback: types.CallbackQuery, state: FSMContext):
    prod_id = callback.data.replace("order_", "")
    product = next((p for p in PRODUCTS if p['id'] == prod_id), None)
    
    if not product:
        await callback.answer("❌ Товар не найден")
        return
    
    await state.update_data(
        product_id=prod_id,
        product_name=product['name'],
        product_price=product['price']
    )
    
    await state.set_state(OrderStates.entering_contact)
    await callback.message.edit_text(
        "📝 <b>Оформление заказа</b>\n\n"
        "Шаг 1 из 3\n\n"
        "Как с вами связаться? (телефон или @username)",
        reply_markup=cancel_keyboard()
    )

@dp.message(OrderStates.entering_contact)
async def process_contact(message: types.Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await state.set_state(OrderStates.entering_details)
    await message.answer(
        "Шаг 2 из 3\n\n"
        "Опишите подробнее, что нужно сделать?\n"
        "(какой функционал, дизайн, сроки)",
        reply_markup=cancel_keyboard()
    )

@dp.message(OrderStates.entering_details)
async def process_details(message: types.Message, state: FSMContext):
    await state.update_data(details=message.text)
    data = await state.get_data()
    
    # Создаём заказ
    orders = get_orders()
    order_id = generate_order_id()
    new_order = {
        "id": order_id,
        "user_id": message.from_user.id,
        "username": message.from_user.username or message.from_user.full_name,
        "product_id": data['product_id'],
        "product_name": data['product_name'],
        "price": data['product_price'],
        "contact": data['contact'],
        "details": data['details'],
        "status": "new",
        "created_at": datetime.now().isoformat()
    }
    orders.append(new_order)
    save_orders(orders)
    
    # Уведомление админу
    await notify_admin(
        f"🆕 <b>НОВЫЙ ЗАКАЗ #{order_id}</b>\n\n"
        f"👤 Клиент: @{message.from_user.username or message.from_user.full_name}\n"
        f"💎 Товар: {data['product_name']}\n"
        f"💰 Цена: {data['product_price']}₽\n"
        f"📞 Контакт: {data['contact']}\n"
        f"📝 Детали: {data['details']}"
    )
    
    await message.answer(
        f"✅ <b>Заказ #{order_id} создан!</b>\n\n"
        f"💎 Товар: {data['product_name']}\n"
        f"💰 Сумма: {data['product_price']}₽\n\n"
        f"Я свяжусь с вами в ближайшее время для уточнения деталей.\n\n"
        f"Спасибо за доверие! 🙌",
        reply_markup=main_menu()
    )
    await state.clear()

# ---------- АДМИНКА ----------
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещен")
        return
    await message.answer("👑 <b>Админ-панель</b>", reply_markup=admin_menu())

@dp.callback_query(F.data == "admin_orders")
async def admin_orders(callback: types.CallbackQuery):
    orders = get_orders()
    if not orders:
        await callback.message.edit_text("📋 Нет заказов", reply_markup=back_keyboard())
        return
    
    text = "📋 <b>Все заказы</b>\n\n"
    for o in orders[-10:]:
        status_emoji = {
            'new': '🆕',
            'paid': '💳',
            'in_progress': '⚙️',
            'completed': '✅'
        }.get(o['status'], '❓')
        text += f"{status_emoji} <b>#{o['id']}</b>\n"
        text += f"   👤 @{o['username']}\n"
        text += f"   💎 {o['product_name']}\n"
        text += f"   💰 {o['price']}₽\n"
        text += f"   📞 {o['contact']}\n"
        text += f"   📊 {o['status']}\n"
        text += f"   [Подтвердить](confirm_{o['id']}) | [Выполнено](complete_{o['id']})\n\n"
    
    # Добавляем кнопки действий
    kb = []
    for o in orders[-5:]:
        if o['status'] == 'new':
            kb.append([InlineKeyboardButton(
                text=f"✅ Подтвердить #{o['id']}",
                callback_data=f"confirm_{o['id']}"
            )])
        elif o['status'] == 'in_progress':
            kb.append([InlineKeyboardButton(
                text=f"✔️ Выполнено #{o['id']}",
                callback_data=f"complete_{o['id']}"
            )])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_order(callback: types.CallbackQuery):
    order_id = callback.data.replace("confirm_", "")
    orders = get_orders()
    
    for o in orders:
        if o['id'] == order_id:
            o['status'] = 'in_progress'
            break
    
    save_orders(orders)
    
    # Уведомляем клиента
    await notify_user(
        o['user_id'],
        f"✅ <b>Заказ #{order_id} подтверждён!</b>\n\n"
        f"Я приступил к работе над вашим ботом.\n"
        f"О результате сообщу дополнительно."
    )
    
    await callback.answer("✅ Заказ подтверждён")
    await admin_orders(callback)

@dp.callback_query(F.data.startswith("complete_"))
async def complete_order(callback: types.CallbackQuery):
    order_id = callback.data.replace("complete_", "")
    orders = get_orders()
    
    order = None
    for o in orders:
        if o['id'] == order_id:
            o['status'] = 'completed'
            order = o
            break
    
    save_orders(orders)
    
    # Уведомляем клиента
    await notify_user(
        o['user_id'],
        f"✅ <b>Заказ #{order_id} выполнен!</b>\n\n"
        f"Ваш бот готов! 🚀\n\n"
        f"⭐️ Пожалуйста, оставьте отзыв о работе — это очень важно для меня!\n"
        f"👉 Нажмите «⭐️ Отзывы» в главном меню, чтобы поделиться впечатлениями.\n\n"
        f"Спасибо, что выбрали меня! 🙌"
    )
    
    # Проверяем лояльность
    if check_loyalty(o['user_id']):
        referrals = get_referrals()
        referrals.append({
            "user_id": o['user_id'],
            "type": "loyalty",
            "bonus": LOYALTY_BONUS,
            "created_at": datetime.now().isoformat()
        })
        save_referrals(referrals)
        
        await notify_user(
            o['user_id'],
            f"🎁 <b>Бонус лояльности!</b>\n\n"
            f"Поздравляем! Это ваш {LOYALTY_THRESHOLD}-й заказ.\n"
            f"Вам начислен бонус {LOYALTY_BONUS}₽.\n\n"
            f"Для получения напишите @x40vef4yX"
        )
        
        await notify_admin(
            f"🎁 <b>Бонус лояльности</b>\n\n"
            f"Клиент @{o['username']} выполнил {LOYALTY_THRESHOLD} заказов!\n"
            f"Бонус {LOYALTY_BONUS}₽ ожидает выплаты."
        )
    
    await callback.answer("✅ Заказ отмечен как выполненный")
    await admin_orders(callback)

@dp.callback_query(F.data == "admin_reviews")
async def admin_reviews(callback: types.CallbackQuery):
    reviews = get_reviews()
    pending = [r for r in reviews if not r.get('approved', False)]
    
    if not pending:
        await callback.message.edit_text(
            "⭐️ Нет отзывов на модерации",
            reply_markup=back_keyboard()
        )
        return
    
    text = "⭐️ <b>Отзывы на модерации</b>\n\n"
    for r in pending[:5]:
        text += f"👤 {r['username']} (⭐️{'⭐️' * r['rating']})\n"
        text += f"📝 {r['text'][:100]}...\n"
        text += f"📞 {r.get('contact', 'нет')}\n"
        text += f"📸 {'✅' if r.get('has_photo') else '❌'}\n"
        text += f"🆔 {r['id']}\n\n"
    
    kb = []
    for r in pending[:5]:
        kb.append([
            InlineKeyboardButton(text=f"✅ Одобрить #{r['id']}", callback_data=f"approve_review_{r['id']}"),
            InlineKeyboardButton(text=f"❌ Отклонить #{r['id']}", callback_data=f"reject_review_{r['id']}")
        ])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("approve_review_"))
async def approve_review(callback: types.CallbackQuery):
    review_id = int(callback.data.replace("approve_review_", ""))
    reviews = get_reviews()
    
    for r in reviews:
        if r['id'] == review_id:
            r['approved'] = True
            break
    
    save_reviews(reviews)
    
    await callback.answer("✅ Отзыв одобрен")
    await admin_reviews(callback)

@dp.callback_query(F.data.startswith("reject_review_"))
async def reject_review(callback: types.CallbackQuery):
    review_id = int(callback.data.replace("reject_review_", ""))
    reviews = get_reviews()
    reviews = [r for r in reviews if r['id'] != review_id]
    save_reviews(reviews)
    
    await callback.answer("❌ Отзыв отклонён и удалён")
    await admin_reviews(callback)

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    orders = get_orders()
    clients = get_clients()
    reviews = get_reviews()
    referrals = get_referrals()
    
    total_orders = len(orders)
    completed_orders = len([o for o in orders if o['status'] == 'completed'])
    total_revenue = sum(o['price'] for o in orders if o['status'] == 'completed')
    total_clients = len(clients)
    total_reviews = len(reviews)
    approved_reviews = len([r for r in reviews if r.get('approved', False)])
    rating = calculate_rating()
    total_bonuses = len([r for r in referrals if r['type'] == 'loyalty'])
    
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"📦 Всего заказов: {total_orders}\n"
        f"✅ Выполнено: {completed_orders}\n"
        f"💰 Выручка: {total_revenue}₽\n"
        f"👥 Клиентов: {total_clients}\n"
        f"⭐️ Отзывов: {approved_reviews}/{total_reviews}\n"
        f"📊 Рейтинг: {rating}/5.0\n"
        f"🎁 Бонусов выдано: {total_bonuses}"
    )
    
    await callback.message.edit_text(text, reply_markup=back_keyboard())

@dp.callback_query(F.data == "admin_clients")
async def admin_clients(callback: types.CallbackQuery):
    clients = get_clients()
    
    if not clients:
        await callback.message.edit_text("👥 Нет клиентов", reply_markup=back_keyboard())
        return
    
    text = "👥 <b>Клиенты</b>\n\n"
    for c in clients[-10:]:
        orders = get_orders()
        user_orders = [o for o in orders if o['user_id'] == c['user_id']]
        completed = len([o for o in user_orders if o['status'] == 'completed'])
        text += f"👤 @{c['username']}\n"
        text += f"   🆔 {c['user_id']}\n"
        text += f"   📦 Заказов: {len(user_orders)} (✅{completed})\n"
        text += f"   🕐 {c['first_seen'][:10]}\n\n"
    
    await callback.message.edit_text(text, reply_markup=back_keyboard())

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.broadcast_message)
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\n"
        "Отправь сообщение для рассылки (текст, фото или видео):",
        reply_markup=cancel_keyboard()
    )

@dp.message(AdminStates.broadcast_message)
async def broadcast_get_message(message: types.Message, state: FSMContext):
    broadcast_data = {
        'type': message.content_type,
        'text': message.text or message.caption,
    }
    
    if message.photo:
        broadcast_data['photo'] = message.photo[-1].file_id
    if message.video:
        broadcast_data['video'] = message.video.file_id
    
    await state.update_data(broadcast=broadcast_data)
    await state.set_state(AdminStates.broadcast_confirm)
    
    clients = get_clients()
    
    preview = f"📢 <b>Предпросмотр рассылки:</b>\n\n{message.text or message.caption}\n\n"
    preview += f"Будет отправлено <b>{len(clients)}</b> клиентам.\n\nПодтвердить?"
    
    if message.photo:
        await message.answer_photo(
            photo=message.photo[-1].file_id,
            caption=preview,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin")]
            ])
        )
    else:
        await message.answer(
            preview,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin")]
            ])
        )

@dp.callback_query(AdminStates.broadcast_confirm, F.data == "broadcast_confirm")
async def broadcast_confirm(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    broadcast = data['broadcast']
    clients = get_clients()
    
    await callback.message.edit_text(f"📢 Начинаю рассылку {len(clients)} клиентам...")
    
    success = 0
    for client in clients:
        try:
            if broadcast['type'] == 'text':
                await bot.send_message(client['user_id'], broadcast['text'])
            elif broadcast['type'] == 'photo':
                await bot.send_photo(client['user_id'], broadcast['photo'], caption=broadcast['text'])
            elif broadcast['type'] == 'video':
                await bot.send_video(client['user_id'], broadcast['video'], caption=broadcast['text'])
            success += 1
            await asyncio.sleep(0.1)
        except:
            pass
    
    await callback.message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\nОтправлено: {success}",
        reply_markup=admin_menu()
    )
    await state.clear()

@dp.callback_query(F.data == "admin_loyalty")
async def admin_loyalty(callback: types.CallbackQuery):
    referrals = get_referrals()
    loyalty = [r for r in referrals if r['type'] == 'loyalty']
    
    text = "🎁 <b>Бонусы лояльности</b>\n\n"
    if not loyalty:
        text += "Пока нет начисленных бонусов."
    else:
        for r in loyalty[-10:]:
            text += f"👤 ID: {r['user_id']}\n"
            text += f"💰 Сумма: {r['bonus']}₽\n"
            text += f"🕐 {r['created_at'][:10]}\n\n"
    
    await callback.message.edit_text(text, reply_markup=back_keyboard())

# ============================================
# ЗАПУСК
# ============================================
async def on_startup():
    logger.info("🚀 Бот-магазин запускается...")
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook/{TOKEN}"
    await bot.set_webhook(webhook_url)
    logger.info(f"✅ Вебхук установлен на {webhook_url}")

def run_bot():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(on_startup())
    loop.run_forever()

if __name__ == "__main__":
    import threading
    threading.Thread(target=run_bot, daemon=True).start()
    logger.info("🚀 Flask запускается...")
    app.run(host="0.0.0.0", port=PORT)
