import os
import logging
import asyncio
import json
import uuid
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
PAYMENT_TOKEN = os.environ.get('PAYMENT_TOKEN')  # Для Telegram Stars
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

# === Товары (боты) ===
def get_products():
    return [
        {
            "id": "tattoo_bot",
            "name": "🤖 Бот для тату-мастера",
            "category": "beauty",
            "description": "Полноценный бот для записи в тату-салон",
            "long_desc": "✅ Календарь записи на месяц\n✅ Портфолио работ\n✅ Отзывы с фото\n✅ Промокоды\n✅ Напоминания\n✅ Админ-панель\n✅ Статистика",
            "price": 25000,
            "prepayment": 10000,
            "images": ["https://example.com/tattoo_1.jpg"],
            "features": ["Запись", "Портфолио", "Отзывы", "Промокоды"],
            "popular": True
        },
        {
            "id": "manicure_bot",
            "name": "💅 Бот для маникюра",
            "category": "beauty",
            "description": "Бот для салона красоты и мастеров маникюра",
            "long_desc": "✅ Онлайн-запись\n✅ Каталог услуг\n✅ Акции\n✅ Напоминания\n✅ Админка",
            "price": 20000,
            "prepayment": 8000,
            "images": ["https://example.com/manicure_1.jpg"],
            "features": ["Запись", "Каталог", "Акции"],
            "popular": True
        },
        {
            "id": "barber_bot",
            "name": "✂️ Бот для барбера",
            "category": "beauty",
            "description": "Бот для барбершопа с выбором мастера",
            "price": 20000,
            "prepayment": 8000,
            "images": ["https://example.com/barber_1.jpg"],
            "features": ["Запись", "Выбор мастера", "Прайс"],
            "popular": False
        },
        {
            "id": "custom_bot",
            "name": "⚡️ Индивидуальный бот",
            "category": "custom",
            "description": "Бот под ключ с любым функционалом",
            "long_desc": "✅ Любой функционал\n✅ Индивидуальный дизайн\n✅ Интеграции\n✅ Поддержка",
            "price": 35000,
            "prepayment": 15000,
            "images": ["https://example.com/custom_1.jpg"],
            "features": ["Индивидуально", "Интеграции", "Поддержка"],
            "popular": False
        }
    ]

def get_categories():
    return [
        {"id": "all", "name": "📋 Все боты"},
        {"id": "beauty", "name": "💅 Красота"},
        {"id": "custom", "name": "⚡️ Индивидуальные"},
        {"id": "popular", "name": "🔥 Популярные"}
    ]

# === Заказы ===
def get_orders():
    return load_json('orders.json')

def save_orders(orders):
    save_json('orders.json', orders)

# === Клиенты ===
def get_clients():
    return load_json('clients.json')

def save_clients(clients):
    save_json('clients.json', clients)

# === Отзывы ===
def get_reviews():
    return [
        {
            "id": 1,
            "user": "Алексей",
            "text": "Заказал бота для тату-салона. Сделали за 3 дня, всё работает идеально!",
            "rating": 5,
            "product": "tattoo_bot",
            "date": "2026-03-01"
        },
        {
            "id": 2,
            "user": "Марина",
            "text": "Бот для маникюра — просто бомба! Клиенты сами записываются.",
            "rating": 5,
            "product": "manicure_bot",
            "date": "2026-03-05"
        }
    ]

def generate_order_id():
    return str(uuid.uuid4())[:8].upper()

# ============================================
# СОСТОЯНИЯ
# ============================================
class OrderStates(StatesGroup):
    choosing_product = State()
    choosing_category = State()
    entering_contact = State()
    entering_details = State()
    confirming = State()
    waiting_payment = State()

class AdminStates(StatesGroup):
    adding_product_name = State()
    adding_product_price = State()
    adding_product_desc = State()
    broadcast_message = State()
    broadcast_confirm = State()

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

# ============================================
# КЛАВИАТУРЫ
# ============================================
def main_menu():
    kb = [
        [InlineKeyboardButton(text="🛍 Каталог ботов", callback_data="catalog")],
        [InlineKeyboardButton(text="💰 Цены и тарифы", callback_data="prices")],
        [InlineKeyboardButton(text="⭐️ Отзывы", callback_data="reviews")],
        [InlineKeyboardButton(text="📞 Связаться", callback_data="contact")],
        [InlineKeyboardButton(text="ℹ️ О разработчике", callback_data="about")],
        [InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def categories_keyboard():
    categories = get_categories()
    kb = []
    for cat in categories:
        kb.append([InlineKeyboardButton(text=cat['name'], callback_data=f"cat_{cat['id']}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def products_keyboard(category_id):
    products = get_products()
    if category_id == "popular":
        filtered = [p for p in products if p.get('popular')]
    elif category_id == "all":
        filtered = products
    else:
        filtered = [p for p in products if p.get('category') == category_id]
    
    kb = []
    for p in filtered:
        kb.append([InlineKeyboardButton(
            text=f"{p['name']} - {p['price']}₽",
            callback_data=f"prod_{p['id']}"
        )])
    kb.append([InlineKeyboardButton(text="🔙 К категориям", callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def product_detail_keyboard(product_id):
    kb = [
        [InlineKeyboardButton(text="✅ Заказать", callback_data=f"order_{product_id}")],
        [InlineKeyboardButton(text="💳 Купить сразу", callback_data=f"buy_{product_id}")],
        [InlineKeyboardButton(text="🔙 В каталог", callback_data="catalog")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def confirm_order_keyboard(order_id):
    kb = [
        [InlineKeyboardButton(text="💳 Оплатить", callback_data=f"pay_{order_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def admin_menu():
    kb = [
        [InlineKeyboardButton(text="📦 Товары", callback_data="admin_products")],
        [InlineKeyboardButton(text="📋 Заказы", callback_data="admin_orders")],
        [InlineKeyboardButton(text="👥 Клиенты", callback_data="admin_clients")],
        [InlineKeyboardButton(text="💰 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
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
            "orders": []
        })
        save_clients(clients)
    
    welcome_text = (
        f"🔥 <b>Привет, {user.first_name}!</b>\n\n"
        f"Я — твой помощник в создании Telegram-ботов!\n\n"
        f"✅ <b>Что я делаю:</b>\n"
        f"• Боты для записи (тату, маникюр, барберы)\n"
        f"• Интернет-магазины\n"
        f"• Админ-панели и CRM\n"
        f"• Любые кастомные решения\n\n"
        f"👇 <b>Выбери действие:</b>"
    )
    
    await message.answer(welcome_text, reply_markup=main_menu())

@dp.callback_query(F.data == "back")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🔥 <b>Главное меню</b>",
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
    text = (
        "🛍 <b>Каталог ботов</b>\n\n"
        "Выбери категорию:"
    )
    await callback.message.edit_text(text, reply_markup=categories_keyboard())

@dp.callback_query(F.data.startswith("cat_"))
async def show_category(callback: types.CallbackQuery):
    cat_id = callback.data.replace("cat_", "")
    text = f"📋 <b>Товары в категории</b>\n\nВыбери бота:"
    await callback.message.edit_text(text, reply_markup=products_keyboard(cat_id))

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
        f"📝 {product['description']}\n\n"
        f"⚡️ <b>Возможности:</b>\n{product.get('long_desc', 'Уточняйте')}\n\n"
        f"💰 <b>Цена:</b> {product['price']}₽\n"
        f"💳 <b>Предоплата:</b> {product['prepayment']}₽\n\n"
        f"👇 Выбери действие:"
    )
    
    await callback.message.edit_text(text, reply_markup=product_detail_keyboard(prod_id))

@dp.callback_query(F.data == "prices")
async def show_prices(callback: types.CallbackQuery):
    products = get_products()
    text = "💰 <b>Цены и тарифы</b>\n\n"
    for p in products:
        text += f"• {p['name']}: {p['price']}₽\n"
    text += "\n💳 Предоплата 30-50%"
    await callback.message.edit_text(text, reply_markup=back_keyboard())

@dp.callback_query(F.data == "reviews")
async def show_reviews(callback: types.CallbackQuery):
    reviews = get_reviews()
    text = "⭐️ <b>Отзывы клиентов</b>\n\n"
    for r in reviews[-5:]:
        text += f"👤 {r['user']} {'⭐️' * r['rating']}\n"
        text += f"📝 {r['text']}\n\n"
    await callback.message.edit_text(text, reply_markup=back_keyboard())

@dp.callback_query(F.data == "contact")
async def contact(callback: types.CallbackQuery):
    text = (
        "📞 <b>Связаться с разработчиком</b>\n\n"
        "По всем вопросам пиши в личку:\n"
        "👉 @x40vef4yX\n\n"
        "Отвечаю быстро, обычно в течение часа!"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard())

@dp.callback_query(F.data == "about")
async def about(callback: types.CallbackQuery):
    text = (
        "ℹ️ <b>О разработчике</b>\n\n"
        "👨‍💻 Разработчик: @x40vef4yX\n"
        "📅 Опыт: 3+ года\n"
        "🚀 Проектов: 50+\n"
        "⭐️ Рейтинг: 5.0\n\n"
        "✅ Гарантия качества\n"
        "✅ Поддержка после сдачи\n"
        "✅ Быстрая разработка"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard())

@dp.callback_query(F.data == "my_orders")
async def my_orders(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    orders = get_orders()
    user_orders = [o for o in orders if o['user_id'] == user_id]
    
    if not user_orders:
        await callback.message.edit_text(
            "📋 <b>У тебя пока нет заказов</b>",
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
        text += f"{status_emoji} <b>{o['product_name']}</b>\n"
        text += f"   Статус: {o['status']}\n"
        text += f"   Цена: {o['price']}₽\n\n"
    
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
        product_price=product['price'],
        prepayment=product['prepayment']
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
        "(какие функции, дизайн, сроки)",
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
        "prepayment": data['prepayment'],
        "contact": data['contact'],
        "details": data['details'],
        "status": "new",
        "created_at": datetime.now().isoformat()
    }
    orders.append(new_order)
    save_orders(orders)
    
    await state.update_data(order_id=order_id)
    
    # Уведомление админу
    await notify_admin(
        f"🆕 <b>Новый заказ #{order_id}</b>\n\n"
        f"👤 Клиент: @{message.from_user.username or message.from_user.full_name}\n"
        f"💎 Товар: {data['product_name']}\n"
        f"💰 Цена: {data['product_price']}₽\n"
        f"📞 Контакт: {data['contact']}\n"
        f"📝 Детали: {data['details']}"
    )
    
    text = (
        f"✅ <b>Заказ #{order_id} создан!</b>\n\n"
        f"💎 Товар: {data['product_name']}\n"
        f"💰 Сумма: {data['product_price']}₽\n"
        f"💳 Предоплата: {data['prepayment']}₽\n\n"
        f"👇 Для начала работы внеси предоплату:"
    )
    
    await message.answer(text, reply_markup=confirm_order_keyboard(order_id))
    await state.set_state(OrderStates.waiting_payment)

@dp.callback_query(OrderStates.waiting_payment, F.data.startswith("pay_"))
async def process_payment(callback: types.CallbackQuery, state: FSMContext):
    order_id = callback.data.replace("pay_", "")
    data = await state.get_data()
    
    # Здесь должна быть интеграция с платёжной системой
    # Для примера просто отмечаем оплату
    orders = get_orders()
    for o in orders:
        if o['id'] == order_id:
            o['status'] = 'paid'
            break
    save_orders(orders)
    
    await notify_admin(f"💳 <b>Оплата по заказу #{order_id}</b>\n\nСумма: {data['prepayment']}₽")
    
    await callback.message.edit_text(
        f"✅ <b>Предоплата получена!</b>\n\n"
        f"Заказ #{order_id} передан в работу.\n"
        f"Я свяжусь с тобой в ближайшее время.\n\n"
        f"Спасибо за доверие! 🙌"
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
        text += f"   👤 {o['username']}\n"
        text += f"   💎 {o['product_name']}\n"
        text += f"   💰 {o['price']}₽\n\n"
    
    await callback.message.edit_text(text, reply_markup=back_keyboard())

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    orders = get_orders()
    clients = get_clients()
    
    total_orders = len(orders)
    total_revenue = sum(o['price'] for o in orders if o['status'] == 'paid')
    total_clients = len(clients)
    new_orders = len([o for o in orders if o['status'] == 'new'])
    
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"📦 Всего заказов: {total_orders}\n"
        f"🆕 Новых: {new_orders}\n"
        f"💰 Выручка: {total_revenue}₽\n"
        f"👥 Клиентов: {total_clients}\n"
    )
    
    await callback.message.edit_text(text, reply_markup=back_keyboard())

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.broadcast_message)
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\n"
        "Отправь сообщение для рассылки:",
        reply_markup=cancel_keyboard()
    )

@dp.message(AdminStates.broadcast_message)
async def broadcast_get_message(message: types.Message, state: FSMContext):
    await state.update_data(broadcast_text=message.text)
    await state.set_state(AdminStates.broadcast_confirm)
    
    clients = get_clients()
    await message.answer(
        f"📢 <b>Предпросмотр:</b>\n\n{message.text}\n\n"
        f"Будет отправлено {len(clients)} клиентам.\n\nПодтвердить?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin")]
        ])
    )

@dp.callback_query(AdminStates.broadcast_confirm, F.data == "broadcast_confirm")
async def broadcast_confirm(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    clients = get_clients()
    
    success = 0
    for client in clients:
        try:
            await bot.send_message(client['user_id'], data['broadcast_text'])
            success += 1
        except:
            pass
    
    await callback.message.answer(f"✅ Рассылка завершена!\nОтправлено: {success}")
    await state.clear()

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
