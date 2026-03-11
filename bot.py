import os
import logging
import asyncio
import json
from datetime import datetime
from flask import Flask, request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

# ============================================
# НАСТРОЙКИ
# ============================================
TOKEN = os.environ.get('PRIVATE_BOT_TOKEN')  # Токен для личного бота
ADMIN_ID = 775020198  # ← ТВОЙ ID
PORT = int(os.environ.get('PORT', 8080))
RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL', 'https://privatebot.onrender.com')

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

def get_clients():
    return load_json('clients.json')

def save_clients(clients):
    save_json('clients.json', clients)

def get_projects():
    return load_json('projects.json')

def save_projects(projects):
    save_json('projects.json', projects)

# ============================================
# ПРОВЕРКА НА АДМИНА
# ============================================
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# ============================================
# СОСТОЯНИЯ
# ============================================
class ProjectStates(StatesGroup):
    waiting_client_name = State()
    waiting_project_type = State()
    waiting_project_details = State()
    waiting_price = State()
    waiting_deadline = State()

# ============================================
# ИНИЦИАЛИЗАЦИЯ БОТА
# ============================================
storage = MemoryStorage()
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=storage)

# ============================================
# Flask
# ============================================
app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Личный бот работает! 🤖"

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    try:
        update_data = request.json
        asyncio.run_coroutine_threadsafe(
            process_update(update_data),
            loop
        )
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

@app.route('/set_webhook', methods=['GET'])
def set_webhook_route():
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook/{TOKEN}"
    asyncio.run_coroutine_threadsafe(
        bot.set_webhook(webhook_url, allowed_updates=['message', 'callback_query']),
        loop
    )
    return f"✅ Webhook установлен на {webhook_url}"

# ============================================
# КЛАВИАТУРЫ
# ============================================
def main_menu():
    kb = [
        [InlineKeyboardButton(text="📋 Мои проекты", callback_data="my_projects")],
        [InlineKeyboardButton(text="💬 Связаться с разработчиком", callback_data="contact_dev")],
        [InlineKeyboardButton(text="ℹ️ О проекте", callback_data="about")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def admin_menu():
    kb = [
        [InlineKeyboardButton(text="📋 Все проекты", callback_data="admin_projects")],
        [InlineKeyboardButton(text="➕ Новый проект", callback_data="admin_new_project")],
        [InlineKeyboardButton(text="👥 Клиенты", callback_data="admin_clients")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
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
# ОБРАБОТЧИКИ
# ============================================

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    
    # Если это админ - показываем админку
    if is_admin(user.id):
        await message.answer(
            "👑 <b>Личный кабинет разработчика</b>\n\n"
            "Управляй проектами, клиентами и задачами:",
            reply_markup=admin_menu()
        )
        return
    
    # Проверяем, есть ли клиент в базе
    clients = get_clients()
    client = next((c for c in clients if c['user_id'] == user.id), None)
    
    if not client:
        # Добавляем нового клиента
        clients.append({
            "user_id": user.id,
            "username": user.username or user.full_name,
            "joined_at": datetime.now().isoformat(),
            "projects": []
        })
        save_clients(clients)
    
    welcome_text = (
        f"🔥 <b>Привет, {user.first_name}!</b>\n\n"
        f"Добро пожаловать в личный кабинет клиента.\n"
        f"Здесь ты можешь отслеживать статус своих проектов и связываться с разработчиком."
    )
    
    await message.answer(welcome_text, reply_markup=main_menu())

@dp.callback_query(F.data == "back")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    
    if is_admin(callback.from_user.id):
        await callback.message.edit_text(
            "👑 <b>Личный кабинет разработчика</b>",
            reply_markup=admin_menu()
        )
    else:
        await callback.message.edit_text(
            "🔥 <b>Главное меню</b>",
            reply_markup=main_menu()
        )

@dp.callback_query(F.data == "cancel")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено",
        reply_markup=main_menu() if not is_admin(callback.from_user.id) else admin_menu()
    )

# ---------- КЛИЕНТСКАЯ ЧАСТЬ ----------
@dp.callback_query(F.data == "my_projects")
async def my_projects(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    projects = get_projects()
    user_projects = [p for p in projects if p['user_id'] == user_id]
    
    if not user_projects:
        await callback.message.edit_text(
            "📋 <b>У тебя пока нет проектов</b>\n\n"
            "Если ты оставлял заявку, разработчик скоро свяжется с тобой.",
            reply_markup=back_keyboard()
        )
        return
    
    text = "📋 <b>Твои проекты:</b>\n\n"
    for project in user_projects:
        status_emoji = {
            'new': '🆕',
            'in_progress': '⚙️',
            'review': '🔍',
            'completed': '✅'
        }.get(project['status'], '❓')
        
        text += f"{status_emoji} <b>{project['name']}</b>\n"
        text += f"   📝 {project['description'][:50]}...\n"
        text += f"   📊 Статус: {project['status']}\n"
        text += f"   📅 Дедлайн: {project.get('deadline', 'не указан')}\n\n"
    
    kb = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back")]]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "contact_dev")
async def contact_dev(callback: types.CallbackQuery):
    text = (
        "💬 <b>Связаться с разработчиком</b>\n\n"
        "По всем вопросам пиши в личку:\n"
        "👉 @x40vef4yX\n\n"
        "Отвечаю быстро, обычно в течение часа!"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard())

@dp.callback_query(F.data == "about")
async def about(callback: types.CallbackQuery):
    text = (
        "ℹ️ <b>О проекте</b>\n\n"
        "Этот бот создан для удобного ведения проектов.\n"
        "Здесь ты можешь:\n"
        "✅ Отслеживать статус заказа\n"
        "✅ Видеть дедлайны\n"
        "✅ Связываться с разработчиком\n\n"
        "Разработчик: @x40vef4yX"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard())

# ---------- АДМИНСКАЯ ЧАСТЬ ----------
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещен")
        return
    
    await message.answer(
        "👑 <b>Админ-панель</b>",
        reply_markup=admin_menu()
    )

@dp.callback_query(F.data == "admin_projects")
async def admin_projects(callback: types.CallbackQuery):
    projects = get_projects()
    
    if not projects:
        await callback.message.edit_text(
            "📋 Нет проектов",
            reply_markup=back_keyboard()
        )
        return
    
    text = "📋 <b>Все проекты:</b>\n\n"
    for project in projects[-10:]:
        status_emoji = {
            'new': '🆕',
            'in_progress': '⚙️',
            'review': '🔍',
            'completed': '✅'
        }.get(project['status'], '❓')
        
        text += f"{status_emoji} <b>{project['name']}</b>\n"
        text += f"   👤 Клиент ID: {project['user_id']}\n"
        text += f"   📊 Статус: {project['status']}\n"
        text += f"   💰 Цена: {project.get('price', 'не указана')}₽\n\n"
    
    kb = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back")]]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "admin_new_project")
async def admin_new_project(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ProjectStates.waiting_client_name)
    await callback.message.edit_text(
        "➕ <b>Новый проект</b>\n\n"
        "Введи ID клиента (можно узнать через @userinfobot):",
        reply_markup=cancel_keyboard()
    )

@dp.message(ProjectStates.waiting_client_name)
async def process_client_id(message: types.Message, state: FSMContext):
    try:
        client_id = int(message.text)
        await state.update_data(client_id=client_id)
        await state.set_state(ProjectStates.waiting_project_type)
        await message.answer(
            "Введи тип проекта (например: тату-бот, маникюр, индивидуальный):",
            reply_markup=cancel_keyboard()
        )
    except:
        await message.answer("❌ Введи корректный ID (число)")

@dp.message(ProjectStates.waiting_project_type)
async def process_project_type(message: types.Message, state: FSMContext):
    await state.update_data(project_type=message.text)
    await state.set_state(ProjectStates.waiting_project_details)
    await message.answer(
        "Опиши детали проекта (функции, особенности):",
        reply_markup=cancel_keyboard()
    )

@dp.message(ProjectStates.waiting_project_details)
async def process_project_details(message: types.Message, state: FSMContext):
    await state.update_data(project_details=message.text)
    await state.set_state(ProjectStates.waiting_price)
    await message.answer(
        "Введи цену проекта в рублях:",
        reply_markup=cancel_keyboard()
    )

@dp.message(ProjectStates.waiting_price)
async def process_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
        await state.update_data(price=price)
        await state.set_state(ProjectStates.waiting_deadline)
        await message.answer(
            "Введи дедлайн (например: 5 дней, 20.03.2026):",
            reply_markup=cancel_keyboard()
        )
    except:
        await message.answer("❌ Введи корректную цену (число)")

@dp.message(ProjectStates.waiting_deadline)
async def process_deadline(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    # Создаём проект
    projects = get_projects()
    new_project = {
        "id": len(projects) + 1,
        "user_id": data['client_id'],
        "name": data['project_type'],
        "description": data['project_details'],
        "price": data['price'],
        "deadline": message.text,
        "status": "new",
        "created_at": datetime.now().isoformat()
    }
    projects.append(new_project)
    save_projects(projects)
    
    # Уведомляем клиента
    try:
        await bot.send_message(
            data['client_id'],
            f"🎉 <b>Проект создан!</b>\n\n"
            f"📋 <b>Название:</b> {data['project_type']}\n"
            f"📝 <b>Описание:</b> {data['project_details']}\n"
            f"💰 <b>Цена:</b> {data['price']}₽\n"
            f"📅 <b>Дедлайн:</b> {message.text}\n\n"
            f"Скоро я приступлю к работе! Следи за статусом в разделе «Мои проекты»."
        )
    except:
        pass
    
    await message.answer(
        f"✅ <b>Проект создан!</b>\n\n"
        f"Клиент ID: {data['client_id']}\n"
        f"Тип: {data['project_type']}\n"
        f"Цена: {data['price']}₽\n"
        f"Дедлайн: {message.text}"
    )
    await state.clear()

# ============================================
# ЗАПУСК
# ============================================
async def on_startup():
    logger.info("🚀 Личный бот запускается...")
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook/{TOKEN}"
    await bot.set_webhook(webhook_url, allowed_updates=['message', 'callback_query'])
    logger.info(f"✅ Вебхук установлен на {webhook_url}")

def start_bot():
    loop.run_until_complete(on_startup())
    loop.run_forever()

if __name__ == "__main__":
    import threading
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    logger.info("🚀 Flask запускается...")
    app.run(host="0.0.0.0", port=PORT)
