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
PAYMENT_TOKEN = os.environ.get('PAYMENT_TOKEN')
ADMIN_ID = 775020198
PORT = int(os.environ.get('PORT', 8080))
RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL')

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

# === Товары ===
def get_products():
    products = load_json('products.json')
    if not products:
        products = [
            {
                "id": "tattoo_bot",
                "name": "🤖 Бот для тату-мастера",
                "price": 1999,
                "type": "base",
                "description": "✅ Опыт — бот, которым можно гордиться\n✅ Качество — код не сыпется, работает 24/7\n✅ Поддержка — не бросаю после продажи\n✅ Результат — бот реально приносит деньги",
                "features": [
                    "💰 ДЕНЬГИ: Работает 24/7, принимает заявки, пока вы спите",
                    "⚡️ Окупаемость: 1-2 клиента — окупился",
                    "⏰ ВРЕМЯ: Вы не отвечаете на одинаковые вопросы",
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
                    "✅ Уведомления о каждой записи",
                    "✅ Поддержка 2 месяца + вечная поддержка серверов"
                ]
            },
            {
                "id": "manicure_bot",
                "name": "💅 Бот для маникюра",
                "price": 1999,
                "type": "base",
                "description": "✅ Опыт — бот, которым можно гордиться\n✅ Качество — код не сыпется, работает 24/7\n✅ Поддержка — не бросаю после продажи\n✅ Результат — бот реально приносит деньги",
                "features": [
                    "💰 ДЕНЬГИ: Работает 24/7, принимает заявки, пока вы спите",
                    "⚡️ Окупаемость: 1-2 клиента — окупился",
                    "⏰ ВРЕМЯ: Вы не отвечаете на одинаковые вопросы",
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
                    "✅ Уведомления",
                    "✅ Поддержка 2 месяца + вечная поддержка серверов"
                ]
            },
            {
                "id": "barber_bot",
                "name": "✂️ Бот для барбера",
                "price": 1999,
                "type": "base",
                "description": "✅ Опыт — бот, которым можно гордиться\n✅ Качество — код не сыпется, работает 24/7\n✅ Поддержка — не бросаю после продажи\n✅ Результат — бот реально приносит деньги",
                "features": [
                    "💰 ДЕНЬГИ: Работает 24/7, принимает заявки",
                    "⚡️ Окупаемость: 1-2 клиента — окупился",
                    "⏰ ВРЕМЯ: Вы не отвечаете на одинаковые вопросы",
                    "📈 РОСТ: Отзывы + промокоды"
                ],
                "client_features": [
                    "✅ Услуги с ценами",
                    "✅ Запись за 30 секунд",
                    "✅ История записей",
                    "✅ Отзывы с фото",
                    "✅ Напоминание за 24 часа",
                ],
                "admin_features": [
                    "✅ Управление услугами",
                    "✅ Все записи",
                    "✅ Подтверждение/отмена",
                    "✅ Модерация отзывов",
                    "✅ Статистика",
                    "✅ Уведомления",
                    "✅ Поддержка 2 месяца + вечная поддержка серверов"
                ]
            },
            {
                "id": "custom_bot",
                "name": "⚡️ Индивидуальный бот",
                "price": 1999,
                "type": "base",
                "description": "✅ Опыт — бот, которым можно гордиться\n✅ Качество — код не сыпется, работает 24/7\n✅ Поддержка — не бросаю после продажи\n✅ Результат — бот реально приносит деньги",
                "features": [
                    "💰 ДЕНЬГИ: Работает 24/7, принимает заявки",
                    "⚡️ Окупаемость: 1-2 клиента — окупился",
                    "⏰ ВРЕМЯ: Вы не отвечаете на одинаковые вопросы",
                    "📈 РОСТ: Отзывы + промокоды"
                ],
                "client_features": [
                    "✅ Любой функционал под ваш бизнес",
                    "✅ Индивидуальный дизайн",
                    "✅ Интеграции с CRM"
                ],
                "admin_features": [
                    "✅ Полное администрирование",
                    "✅ Статистика",
                    "✅ Рассылка",
                    "✅ Уведомления"
                    "✅ Поддержка 3 месяца + вечная поддержка серверов"
                ]
            },
            {
                "id": "complex_bot",
                "name": "🚀 Проект повышенной сложности",
                "price": 2249,
                "type": "custom",
                "description": "✅ Опыт — бот, которым можно гордиться\n✅ Качество — код не сыпется, работает 24/7\n✅ Поддержка — не бросаю после продажи\n✅ Результат — бот реально приносит деньги",
                "features": [
                    "💰 ДЕНЬГИ: Работает 24/7, принимает заявки",
                    "⚡️ Окупаемость: 1-2 клиента — окупился",
                    "⏰ ВРЕМЯ: Вы не отвечаете на одинаковые вопросы",
                    "📈 РОСТ: Отзывы + промокоды"
                ],
                "client_features": [
                    "✅ Сложная логика",
                    "✅ Множество интеграций",
                    "✅ Кастомные решения"
                ],
                "admin_features": [
                    "✅ Полное администрирование",
                    "✅ Расширенная статистика",
                    "✅ Приоритетная поддержка",
                    "✅ Поддержка 3 месяца + вечная поддержка серверов"
                ]
            }
        ]
        save_json('products.json', products)
    return products

def save_products(products):
    save_json('products.json', products)

# === Демо-проект ===
DEMO_BOT_LINK = "https://t.me/x404x_test_bot"
DEMO_PROJECT = {
    "name": "🤖 Демо-бот для записи",
    "description": "Посмотри, как работает мой бот в реальном времени!",
    "link": DEMO_BOT_LINK,
    "features": [
        "✅ Запись на услуги",
        "✅ Календарь на месяц",
        "✅ Отзывы с фото",
        "✅ Админ-панель",
        "✅ Напоминания"
    ]
}

# === Программа лояльности ===
LOYALTY_THRESHOLD = 5
LOYALTY_BONUS = 250

# ============================================
# ГЕНЕРАЦИЯ РЕФЕРАЛЬНОЙ ССЫЛКИ
# ============================================
def generate_referral_code(user_id):
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"ref_{user_id}_{code}"

async def get_referral_link(user_id):
    code = generate_referral_code(user_id)
    bot_info = await bot.get_me()
    return f"https://t.me/{bot_info.username}?start={code}"

# ============================================
# РАСЧЁТ РЕЙТИНГА
# ============================================
def calculate_rating():
    reviews = get_reviews()
    approved = [r for r in reviews if r.get('approved', False)]
    
    if not approved:
        return 5.0
    
    total = sum(r['rating'] for r in approved)
    avg = total / len(approved)
    return round(avg, 1)

# ============================================
# ПОДСЧЁТ ПРИГЛАШЁННЫХ ДРУЗЕЙ
# ============================================
def count_referrals(user_id):
    referrals = get_referrals()
    return len([r for r in referrals if r['referrer_id'] == user_id and r.get('order_completed', False)])

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
    waiting_photo = State()

class AdminStates(StatesGroup):
    processing_order = State()
    broadcast_message = State()
    broadcast_confirm = State()
    adding_product_name = State()
    adding_product_price = State()
    adding_product_type = State()
    adding_product_features = State()

# ============================================
# ПРОВЕРКА НА АДМИНА
# ============================================
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

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
    try:
        await bot.send_message(ADMIN_ID, f"👑 <b>Админ:</b>\n{message}")
    except Exception as e:
        logger.error(f"Ошибка уведомления админа: {e}")

async def notify_user(user_id: int, message: str):
    try:
        await bot.send_message(user_id, f"📢 <b>Уведомление:</b>\n{message}")
    except Exception as e:
        logger.error(f"Ошибка уведомления пользователя {user_id}: {e}")

def generate_order_id():
    return str(uuid.uuid4())[:8].upper()

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
        [InlineKeyboardButton(text="🎁 Пригласить друзей", callback_data="referral")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def products_keyboard():
    products = get_products()
    kb = []
    for p in products:
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
        [InlineKeyboardButton(text="🎮 Посмотреть демо", url=DEMO_BOT_LINK)],
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
        [InlineKeyboardButton(text="📦 Управление товарами", callback_data="admin_products_menu")],
        [InlineKeyboardButton(text="📋 Заказы", callback_data="admin_orders")],
        [InlineKeyboardButton(text="⭐️ Модерация отзывов", callback_data="admin_reviews")],
        [InlineKeyboardButton(text="👥 Клиенты", callback_data="admin_clients")],
        [InlineKeyboardButton(text="💰 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🎁 Бонусы лояльности", callback_data="admin_loyalty")],
        [InlineKeyboardButton(text="🔙 Выход", callback_data="exit_admin")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def admin_products_management_keyboard():
    kb = [
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product")],
        [InlineKeyboardButton(text="📋 Список товаров", callback_data="admin_products_list")],
        [InlineKeyboardButton(text="🔙 В админку", callback_data="admin")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def admin_products_list_keyboard():
    products = get_products()
    kb = []
    for p in products:
        kb.append([InlineKeyboardButton(
            text=f"{p['name']} - {p['price']}₽",
            callback_data=f"admin_edit_product_{p['id']}"
        )])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_products_menu")])
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
    return "Бот-магазин работает! 🤖"

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
        "webhook": {
            "url": webhook_info.url,
            "allowed_updates": webhook_info.allowed_updates
        }
    }

@app.route('/set_webhook', methods=['GET'])
def set_webhook_route():
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook/{TOKEN}"
    asyncio.run_coroutine_threadsafe(
        bot.set_webhook(
            url=webhook_url,
            allowed_updates=['message', 'callback_query', 'pre_checkout_query']
        ), 
        loop
    )
    return f"✅ Webhook установлен на {webhook_url}"

# ============================================
# ОБРАБОТЧИКИ БОТА
# ============================================

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    logger.info(f"Пользователь {user.full_name} (@{user.username}) запустил бота")
    
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith('ref_'):
        try:
            referrer_id = int(args[1].split('_')[1])
        except:
            pass
    
    clients = get_clients()
    client = next((c for c in clients if c['user_id'] == user.id), None)
    
    if not client:
        clients.append({
            "user_id": user.id,
            "full_name": user.full_name,
            "username": user.username,
            "first_seen": datetime.now().isoformat(),
            "orders": [],
            "reviews": [],
            "referred_by": referrer_id,
            "referrals": []
        })
        save_clients(clients)
        
        if referrer_id:
            referrals = get_referrals()
            referrals.append({
                "referrer_id": referrer_id,
                "referred_id": user.id,
                "date": datetime.now().isoformat(),
                "order_completed": False
            })
            save_referrals(referrals)
    
    rating = calculate_rating()
    reviews = get_reviews()
    approved_reviews = len([r for r in reviews if r.get('approved', False)])
    
    welcome_text = (
        f"🔥 <b>Привет, {user.first_name}!</b>\n\n"
        f"👨‍💻 <b>Разработчик:</b> @x40vef4yX\n"
        f"⭐️ <b>Рейтинг:</b> {rating}/5.0 (на основе {approved_reviews} отзывов)\n\n"
        f"Я создаю <b>Telegram-ботов</b>, которые реально приносят деньги!\n\n"
        f"👇 <b>Выбери действие:</b>"
    )
    
    await message.answer(welcome_text, reply_markup=main_menu())

@dp.callback_query(F.data == "back")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    rating = calculate_rating()
    reviews = get_reviews()
    approved_reviews = len([r for r in reviews if r.get('approved', False)])
    await callback.message.edit_text(
        f"🔥 <b>Главное меню</b>\n\n⭐️ Рейтинг: {rating}/5.0 (на основе {approved_reviews} отзывов)",
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
    products = get_products()
    base_count = len([p for p in products if p['type'] == 'base'])
    custom_count = len([p for p in products if p['type'] == 'custom'])
    
    text = (
        "🛍 <b>Каталог ботов</b>\n\n"
        f"💰 Всего товаров: {len(products)}\n"
        f"• Базовые проекты: {base_count} шт. (1999₽)\n"
        f"• Индивидуальные и сложные: {custom_count} шт. (2249₽)\n\n"
        "Выбери готовое решение:"
    )
    await callback.message.edit_text(text, reply_markup=products_keyboard())

@dp.callback_query(F.data.startswith("prod_"))
async def show_product(callback: types.CallbackQuery, state: FSMContext):
    prod_id = callback.data.replace("prod_", "")
    products = get_products()
    product = next((p for p in products if p['id'] == prod_id), None)
    
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
        f"📦 <b>Проектов:</b> 50+ (Через бота куплено {len(orders)})\n"
        f"✅ <b>Гарантия:</b> 1 месяц полной поддержки + обслуживание бота, далее техобслуживание серверов и бота\n\n"
        f"🔥 <b>Почему я:</b>\n"
        f"✅ Опыт — боты, которыми можно гордиться\n"
        f"✅ Качество — код не сыпется, работает 24/7\n"
        f"✅ Поддержка — не бросаю после продажи\n"
        f"✅ Надежность — сервера будут работать вечность\n"
        f"✅ Результат — бот реально приносит деньги\n"
        f"ℹ️ Мои контакты - @x40vef4yX"      
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard())

@dp.callback_query(F.data == "referral")
async def referral(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    code = generate_referral_code(user_id)
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={code}"
    
    invited = count_referrals(user_id)
    remaining = max(0, LOYALTY_THRESHOLD - invited)
    
    text = (
        f"🎁 <b>Приглашай друзей и получай бонусы!</b>\n\n"
        f"🔥 <b>Условия:</b>\n"
        f"• Пригласи {LOYALTY_THRESHOLD} друзей, и они должны купить бота\n"
        f"• После выполнения 5 заказов от приглашённых — бонус {LOYALTY_BONUS}₽ на карту\n"
        f"• Бонус начисляется автоматически, напиши админу для получения\n\n"
        f"📊 <b>Твой прогресс:</b>\n"
        f"✅ Приглашено друзей, сделавших заказ: {invited}\n"
        f"🎯 Осталось до бонуса: {remaining}\n\n"
        f"🔗 <b>Твоя реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👇 Отправь эту ссылку друзьям!"
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
        # Теперь имя берется автоматически из данных
        text += f"👤 {r['full_name']} {stars}\n"
        text += f"📝 {r['text']}\n"
        if r.get('username'):
            text += f"📞 @{r['username']}\n"
        text += f"🕐 {r['created_at'][:10]}\n\n"
    
    await callback.message.edit_text(text, reply_markup=reviews_keyboard())

@dp.callback_query(F.data == "leave_review")
async def leave_review(callback: types.CallbackQuery, state: FSMContext):
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
        "⭐️ Оцени мою работу от 1 до 5:",
        reply_markup=rating_keyboard()
    )

@dp.callback_query(ReviewStates.waiting_rating, F.data.startswith("rating_"))
async def process_rating(callback: types.CallbackQuery, state: FSMContext):
    rating = int(callback.data.replace("rating_", ""))
    await state.update_data(rating=rating)
    await state.set_state(ReviewStates.waiting_text)
    await callback.message.edit_text(
        "📝 Напиши свой отзыв:",
        reply_markup=cancel_keyboard()
    )

@dp.message(ReviewStates.waiting_text)
async def process_text(message: types.Message, state: FSMContext):
    if len(message.text) > 1000:
        await message.answer("❌ Слишком длинный отзыв. Максимум 1000 символов.")
        return
    
    await state.update_data(review_text=message.text)
    await state.set_state(ReviewStates.waiting_photo)
    await message.answer(
        "📸 Добавь фото к отзыву (или пропусти):",
        reply_markup=photo_options_keyboard()
    )

@dp.callback_query(ReviewStates.waiting_photo, F.data == "add_photo")
async def add_photo_prompt(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📸 Отправь фото:",
        reply_markup=cancel_keyboard()
    )

@dp.message(ReviewStates.waiting_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    reviews = get_reviews()
    new_review = {
        "id": len(reviews) + 1,
        "user_id": message.from_user.id,
        "full_name": message.from_user.full_name,  # Сохраняем полное имя
        "username": message.from_user.username,     # Сохраняем юзернейм
        "rating": data['rating'],
        "text": data['review_text'],
        "has_photo": True,
        "approved": False,
        "created_at": datetime.now().isoformat()
    }
    reviews.append(new_review)
    save_reviews(reviews)
    
    await notify_admin(
        f"⭐️ <b>Новый отзыв на модерацию!</b>\n\n"
        f"👤 Имя: {message.from_user.full_name}\n"
        f"📞 @{message.from_user.username or 'нет'}\n"
        f"⭐️ Оценка: {data['rating']}\n"
        f"📝 Текст: {data['review_text']}\n"
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
        "full_name": callback.from_user.full_name,
        "username": callback.from_user.username,
        "rating": data['rating'],
        "text": data['review_text'],
        "has_photo": False,
        "approved": False,
        "created_at": datetime.now().isoformat()
    }
    reviews.append(new_review)
    save_reviews(reviews)
    
    await notify_admin(
        f"⭐️ <b>Новый отзыв на модерацию!</b>\n\n"
        f"👤 Имя: {callback.from_user.full_name}\n"
        f"📞 @{callback.from_user.username or 'нет'}\n"
        f"⭐️ Оценка: {data['rating']}\n"
        f"📝 Текст: {data['review_text']}\n"
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
            "📋 <b>У тебя пока нет заказов</b>\n\nХочешь заказать бота? Переходи в каталог!",
            reply_markup=back_keyboard()
        )
        return
    
    text = "📋 <b>Мои заказы</b>\n\n"
    for o in user_orders[-5:]:
        status_emoji = {
            'new': '🆕',
            'payment': '💳',
            'in_progress': '⚙️',
            'completed': '✅',
            'cancelled': '❌'
        }.get(o['status'], '❓')
        status_text = {
            'new': 'Новый, ожидает подтверждения',
            'payment': 'Ожидает оплаты',
            'in_progress': 'Выполняется',
            'completed': 'Выполнен',
            'cancelled': 'Отменён'
        }.get(o['status'], o['status'])
        
        text += f"{status_emoji} <b>Заказ #{o['id']}</b>\n"
        text += f"   💎 {o['product_name']}\n"
        text += f"   📊 Статус: {status_text}\n"
        text += f"   💰 {o['price']}₽\n\n"
    
    await callback.message.edit_text(text, reply_markup=back_keyboard())

# ---------- ОФОРМЛЕНИЕ ЗАКАЗА ----------
@dp.callback_query(F.data.startswith("order_"))
async def start_order(callback: types.CallbackQuery, state: FSMContext):
    prod_id = callback.data.replace("order_", "")
    products = get_products()
    product = next((p for p in products if p['id'] == prod_id), None)
    
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
        "Как с тобой связаться? (телефон или @username)",
        reply_markup=cancel_keyboard()
    )

@dp.message(OrderStates.entering_contact)
async def process_contact(message: types.Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await state.set_state(OrderStates.entering_details)
    await message.answer(
        "Шаг 2 из 3\n\n"
        "Опиши подробнее, что нужно сделать?\n"
        "(какой функционал, дизайн, сроки)",
        reply_markup=cancel_keyboard()
    )

@dp.message(OrderStates.entering_details)
async def process_details(message: types.Message, state: FSMContext):
    await state.update_data(details=message.text)
    data = await state.get_data()
    
    orders = get_orders()
    order_id = generate_order_id()
    new_order = {
        "id": order_id,
        "user_id": message.from_user.id,
        "username": message.from_user.username or message.from_user.full_name,
        "full_name": message.from_user.full_name,
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
    
    await notify_admin(
        f"🆕 <b>НОВЫЙ ЗАКАЗ #{order_id}</b>\n\n"
        f"👤 Клиент: {message.from_user.full_name}\n"
        f"📞 @{message.from_user.username or 'нет'}\n"
        f"💎 Товар: {data['product_name']}\n"
        f"💰 Цена: {data['product_price']}₽\n"
        f"📞 Контакт: {data['contact']}\n"
        f"📝 Детали: {data['details']}"
    )
    
    await message.answer(
        f"✅ <b>Заказ #{order_id} создан!</b>\n\n"
        f"💎 Товар: {data['product_name']}\n"
        f"💰 Сумма: {data['product_price']}₽\n\n"
        f"Ожидай подтверждения от администратора.\n"
        f"После подтверждения придёт счёт на оплату.\n\n"
        f"Спасибо за доверие! 🙌",
        reply_markup=main_menu()
    )
    await state.clear()

# ---------- ОПЛАТА ЧЕРЕЗ PAYMASTER ----------
@dp.callback_query(F.data.startswith("accept_"))
async def accept_order(callback: types.CallbackQuery):
    order_id = callback.data.replace("accept_", "")
    orders = get_orders()
    
    order = None
    for o in orders:
        if o['id'] == order_id:
            o['status'] = 'payment'
            order = o
            break
    
    save_orders(orders)
    
    prices = [LabeledPrice(label=order['product_name'], amount=order['price'] * 100)]
    
    await bot.send_invoice(
        chat_id=order['user_id'],
        title=f"Оплата заказа #{order_id}",
        description=f"Товар: {order['product_name']}\n\nДетали: {order['details']}",
        payload=order_id,
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=prices,
        start_parameter="create_order",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", pay=True)]
        ])
    )
    
    await callback.answer("✅ Счёт отправлен клиенту")
    await admin_orders(callback)

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    try:
        logger.info(f"💰 Получен pre_checkout_query: {pre_checkout_query.id}")
        await pre_checkout_query.answer(ok=True)
        logger.info(f"✅ Ответ на pre_checkout_query отправлен: {pre_checkout_query.id}")
    except Exception as e:
        logger.error(f"❌ Ошибка в pre_checkout_handler: {e}")
        try:
            await pre_checkout_query.answer(ok=False, error_message="Техническая ошибка, попробуйте позже")
        except:
            pass

@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    payment_info = message.successful_payment
    order_id = payment_info.invoice_payload
    
    logger.info(f"💰 Получен successful_payment для заказа {order_id}")
    
    orders = get_orders()
    for order in orders:
        if order['id'] == order_id:
            # Меняем статус на "в работе", а не "выполнен"
            order['status'] = 'in_progress'
            order['paid_at'] = datetime.now().isoformat()
            order['payment_id'] = payment_info.telegram_payment_charge_id
            save_orders(orders)
            
            await message.answer(
                f"✅ <b>Заказ #{order_id} оплачен!</b>\n\n"
                f"Спасибо за оплату! Я приступаю к работе над твоим ботом.\n\n"
                f"⚙️ <b>Статус:</b> Заказ в работе\n\n"
                f"Когда бот будет готов, я свяжусь с тобой для передачи."
            )
            
            await notify_admin(
                f"💰 <b>Поступила оплата!</b>\n\n"
                f"Заказ #{order_id}\n"
                f"Сумма: {payment_info.total_amount / 100}₽\n"
                f"Клиент: {message.from_user.full_name}\n"
                f"📞 @{message.from_user.username or 'нет'}\n\n"
                f"⚙️ Статус изменён на 'в работе'"
            )
            break

# ---------- АДМИНКА ----------
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещен")
        return
    await message.answer("👑 <b>Админ-панель</b>", reply_markup=admin_menu())

@dp.callback_query(F.data == "admin")
async def admin_panel_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещен")
        return
    await callback.message.edit_text("👑 <b>Админ-панель</b>", reply_markup=admin_menu())

@dp.callback_query(F.data == "exit_admin")
async def exit_admin(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    rating = calculate_rating()
    reviews = get_reviews()
    approved_reviews = len([r for r in reviews if r.get('approved', False)])
    await callback.message.edit_text(
        f"🔥 <b>Главное меню</b>\n\n⭐️ Рейтинг: {rating}/5.0 (на основе {approved_reviews} отзывов)",
        reply_markup=main_menu()
    )

# ---------- УПРАВЛЕНИЕ ТОВАРАМИ ----------
@dp.callback_query(F.data == "admin_products_menu")
async def admin_products_menu(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "📦 <b>Управление товарами</b>\n\nВыберите действие:",
        reply_markup=admin_products_management_keyboard()
    )

@dp.callback_query(F.data == "admin_products_list")
async def admin_products_list(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    products = get_products()
    text = "📋 <b>Список товаров</b>\n\n"
    for p in products:
        text += f"• <b>{p['name']}</b>\n"
        text += f"  💰 {p['price']}₽\n"
        text += f"  🏷 Тип: {p['type']}\n"
        text += f"  🆔 {p['id']}\n\n"
    await callback.message.edit_text(text, reply_markup=admin_products_list_keyboard())

@dp.callback_query(F.data == "admin_add_product")
async def admin_add_product_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.adding_product_name)
    await callback.message.edit_text(
        "➕ <b>Добавление нового товара</b>\n\n"
        "Шаг 1 из 5\n\n"
        "Введи название товара:",
        reply_markup=cancel_keyboard()
    )

@dp.message(AdminStates.adding_product_name)
async def admin_add_product_name(message: types.Message, state: FSMContext):
    await state.update_data(product_name=message.text)
    await state.set_state(AdminStates.adding_product_price)
    await message.answer(
        "Шаг 2 из 5\n\n"
        "Введи цену товара в рублях (только число):",
        reply_markup=cancel_keyboard()
    )

@dp.message(AdminStates.adding_product_price)
async def admin_add_product_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
        await state.update_data(product_price=price)
        await state.set_state(AdminStates.adding_product_type)
        await message.answer(
            "Шаг 3 из 5\n\n"
            "Введи тип товара (base - базовый, custom - индивидуальный):",
            reply_markup=cancel_keyboard()
        )
    except ValueError:
        await message.answer("❌ Введи корректное число!")

@dp.message(AdminStates.adding_product_type)
async def admin_add_product_type(message: types.Message, state: FSMContext):
    if message.text.lower() not in ['base', 'custom']:
        await message.answer("❌ Тип должен быть base или custom")
        return
    await state.update_data(product_type=message.text.lower())
    await state.set_state(AdminStates.adding_product_features)
    await message.answer(
        "Шаг 4 из 5\n\n"
        "Введи особенности товара (каждое с новой строки):\n"
        "Например:\n"
        "✅ Качество 24/7\n"
        "✅ Поддержка\n"
        "✅ Интеграции",
        reply_markup=cancel_keyboard()
    )

@dp.message(AdminStates.adding_product_features)
async def admin_add_product_features(message: types.Message, state: FSMContext):
    features = message.text.split('\n')
    await state.update_data(product_features=features)
    data = await state.get_data()
    
    product_id = data['product_name'].lower().replace(' ', '_').replace('✅', '').strip()
    
    new_product = {
        "id": product_id,
        "name": data['product_name'],
        "price": data['product_price'],
        "type": data['product_type'],
        "description": "✅ Опыт — бот, которым можно гордиться\n✅ Качество — код не сыпется, работает 24/7",
        "features": [
            "💰 ДЕНЬГИ: Работает 24/7",
            "⚡️ Окупаемость: 1-2 клиента"
        ],
        "client_features": data['product_features'],
        "admin_features": [
            "✅ Управление услугами",
            "✅ Статистика"
        ]
    }
    
    products = get_products()
    products.append(new_product)
    save_products(products)
    
    await message.answer(
        f"✅ <b>Товар успешно добавлен!</b>\n\n"
        f"Название: {data['product_name']}\n"
        f"Цена: {data['product_price']}₽\n"
        f"Тип: {data['product_type']}\n"
        f"ID: {product_id}",
        reply_markup=admin_menu()
    )
    await state.clear()

@dp.callback_query(F.data.startswith("admin_edit_product_"))
async def admin_edit_product(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    product_id = callback.data.replace("admin_edit_product_", "")
    products = get_products()
    product = next((p for p in products if p['id'] == product_id), None)
    
    if not product:
        await callback.answer("❌ Товар не найден")
        return
    
    text = (
        f"✏️ <b>Редактирование товара</b>\n\n"
        f"ID: {product['id']}\n"
        f"Название: {product['name']}\n"
        f"Цена: {product['price']}₽\n"
        f"Тип: {product['type']}\n\n"
        f"<b>Особенности:</b>\n" + "\n".join([f"  {f}" for f in product.get('client_features', [])])
    )
    
    kb = [
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_delete_product_{product['id']}")],
        [InlineKeyboardButton(text="🔙 К списку", callback_data="admin_products_list")]
    ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("admin_delete_product_"))
async def admin_delete_product(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    product_id = callback.data.replace("admin_delete_product_", "")
    products = get_products()
    products = [p for p in products if p['id'] != product_id]
    save_products(products)
    
    await callback.answer("✅ Товар удалён")
    await admin_products_list(callback)

# ---------- УПРАВЛЕНИЕ ЗАКАЗАМИ ----------
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
            'payment': '💳',
            'in_progress': '⚙️',
            'completed': '✅',
            'cancelled': '❌'
        }.get(o['status'], '❓')
        status_text = {
            'new': 'Новый',
            'payment': 'Ожидает оплаты',
            'in_progress': 'В работе',
            'completed': 'Выполнен',
            'cancelled': 'Отменён'
        }.get(o['status'], o['status'])
        
        text += f"{status_emoji} <b>#{o['id']}</b>\n"
        text += f"   👤 {o['full_name']}\n"
        text += f"   📞 @{o['username'] or 'нет'}\n"
        text += f"   💎 {o['product_name']}\n"
        text += f"   💰 {o['price']}₽\n"
        text += f"   📞 {o['contact']}\n"
        text += f"   📊 {status_text}\n\n"
    
    kb = []
    for o in orders[-10:]:
        if o['status'] == 'new':
            kb.append([InlineKeyboardButton(
                text=f"✅ Принять #{o['id']}",
                callback_data=f"accept_{o['id']}"
            )])
        if o['status'] == 'in_progress':
            kb.append([InlineKeyboardButton(
                text=f"✅ Выполнено #{o['id']}",
                callback_data=f"complete_{o['id']}"
            )])
        if o['status'] in ['new', 'payment', 'in_progress']:
            kb.append([InlineKeyboardButton(
                text=f"❌ Отменить #{o['id']}",
                callback_data=f"cancel_order_{o['id']}"
            )])
    kb.append([InlineKeyboardButton(text="🔙 В админку", callback_data="admin")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

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
    
    await notify_user(
        order['user_id'],
        f"✅ <b>Заказ #{order_id} выполнен!</b>\n\n"
        f"Твой бот готов! 🚀\n\n"
        f"⭐️ <b>Пожалуйста, оставь отзыв о работе</b> — это очень важно для меня!\n"
        f"👉 Нажми «⭐️ Отзывы» в главном меню и поделись впечатлениями.\n\n"
        f"Спасибо, что выбрал меня! 🙌"
    )
    
    await callback.answer("✅ Заказ отмечен как выполненный")
    await admin_orders(callback)

@dp.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order_admin(callback: types.CallbackQuery):
    order_id = callback.data.replace("cancel_order_", "")
    orders = get_orders()
    
    order = None
    for o in orders:
        if o['id'] == order_id:
            o['status'] = 'cancelled'
            order = o
            break
    
    save_orders(orders)
    
    await notify_user(
        order['user_id'],
        f"❌ <b>Заказ #{order_id} отменён</b>\n\n"
        f"💎 Товар: {order['product_name']}\n"
        f"💰 Сумма: {order['price']}₽\n\n"
        f"К сожалению, заказ был отменён администратором.\n"
        f"По всем вопросам пиши @x40vef4yX"
    )
    
    await callback.answer("❌ Заказ отменён")
    await admin_orders(callback)

# ---------- МОДЕРАЦИЯ ОТЗЫВОВ ----------
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
        text += f"👤 {r['full_name']} (⭐️{'⭐️' * r['rating']})\n"
        text += f"📝 {r['text'][:100]}...\n"
        text += f"📞 @{r['username'] or 'нет'}\n"
        text += f"📸 {'✅' if r.get('has_photo') else '❌'}\n"
        text += f"🆔 {r['id']}\n\n"
    
    kb = []
    for r in pending[:5]:
        kb.append([
            InlineKeyboardButton(text=f"✅ Одобрить #{r['id']}", callback_data=f"approve_review_{r['id']}"),
            InlineKeyboardButton(text=f"❌ Отклонить #{r['id']}", callback_data=f"reject_review_{r['id']}")
        ])
    kb.append([InlineKeyboardButton(text="🔙 В админку", callback_data="admin")])
    
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
        invited = count_referrals(c['user_id'])
        
        text += f"👤 {c['full_name']}\n"
        text += f"   📞 @{c['username'] or 'нет'}\n"
        text += f"   🆔 {c['user_id']}\n"
        text += f"   📦 Заказов: {len(user_orders)} (✅{completed})\n"
        text += f"   👥 Приглашено друзей: {invited}\n"
        text += f"   🕐 {c['first_seen'][:10]}\n\n"
    
    await callback.message.edit_text(text, reply_markup=back_keyboard())

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    orders = get_orders()
    clients = get_clients()
    reviews = get_reviews()
    referrals = get_referrals()
    products = get_products()
    
    total_orders = len(orders)
    new_orders = len([o for o in orders if o['status'] == 'new'])
    payment_orders = len([o for o in orders if o['status'] == 'payment'])
    in_progress_orders = len([o for o in orders if o['status'] == 'in_progress'])
    completed_orders = len([o for o in orders if o['status'] == 'completed'])
    cancelled_orders = len([o for o in orders if o['status'] == 'cancelled'])
    total_revenue = sum(o['price'] for o in orders if o['status'] == 'completed')
    total_clients = len(clients)
    total_reviews = len(reviews)
    approved_reviews = len([r for r in reviews if r.get('approved', False)])
    rating = calculate_rating()
    total_referrals = len([r for r in referrals if r.get('order_completed', False)])
    
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"📦 Всего товаров: {len(products)}\n"
        f"📋 Всего заказов: {total_orders}\n"
        f"🆕 Новых: {new_orders}\n"
        f"💳 Ожидают оплаты: {payment_orders}\n"
        f"⚙️ В работе: {in_progress_orders}\n"
        f"✅ Выполнено: {completed_orders}\n"
        f"❌ Отменено: {cancelled_orders}\n"
        f"💰 Выручка: {total_revenue}₽\n"
        f"👥 Клиентов: {total_clients}\n"
        f"⭐️ Отзывов: {approved_reviews}/{total_reviews}\n"
        f"📊 Рейтинг: {rating}/5.0\n"
        f"👥 Приглашённых друзей: {total_referrals}"
    )
    
    await callback.message.edit_text(text, reply_markup=back_keyboard())

@dp.callback_query(F.data == "admin_loyalty")
async def admin_loyalty(callback: types.CallbackQuery):
    referrals = get_referrals()
    loyalty = [r for r in referrals if r.get('order_completed', False)]
    
    referrers = {}
    for r in loyalty:
        if r['referrer_id'] not in referrers:
            referrers[r['referrer_id']] = 0
        referrers[r['referrer_id']] += 1
    
    text = "🎁 <b>Бонусы лояльности</b>\n\n"
    if not referrers:
        text += "Пока нет начисленных бонусов."
    else:
        for referrer_id, count in referrers.items():
            if count >= LOYALTY_THRESHOLD:
                text += f"👤 ID: {referrer_id}\n"
                text += f"   👥 Пригласил: {count} друзей\n"
                text += f"   💰 Бонус: {LOYALTY_BONUS}₽ (доступен)\n\n"
    
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

# ============================================
# ЗАПУСК
# ============================================
async def on_startup():
    logger.info("🚀 Бот-магазин запускается...")
    
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook/{TOKEN}"
    await bot.set_webhook(
        url=webhook_url,
        allowed_updates=['message', 'callback_query', 'pre_checkout_query']
    )
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
