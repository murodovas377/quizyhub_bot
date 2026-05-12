import asyncio
import random
import os
import json
import time
import re

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, PollAnswer
)
from aiogram.filters import Command, StateFilter, Filter
from aiogram.types import BotCommand
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.base import StorageKey
from docx import Document
from config import BOT_TOKEN
from datetime import datetime


FILE = "premium.json"
USERS_FILE = "users.json"

if not os.path.exists(FILE):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=4)

ADMINS_FILE = "admins.json"
GLOBAL_TESTS_FILE = "global_tests.json"
RESULTS_FILE = "test_results.json"
ACTIONS_LOG_FILE = "admin_actions_log.json"
READY_TESTS_FILE = "ready_tests.json"

LANG_FILE = "lang.json"

def load_lang():
    with open(LANG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

LANG = load_lang()

SUPER_ADMIN_ID = 7760002425

# ====================== ХРАНЕНИЕ ======================
def save_global_test(test_data):
    if os.path.exists("global_tests.json"):
        with open("global_tests.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    test_id = str(random.randint(1000000, 9999999))
    while test_id in data:
        test_id = str(random.randint(1000000, 9999999))
    data[test_id] = test_data
    with open("global_tests.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return test_id


def log_admin_action(admin_id, action, target_user, details):
    """Логирует действия администратора"""
    logs = load_json(ACTIONS_LOG_FILE, {})

    if "actions" not in logs:
        logs["actions"] = []

    log_entry = {
        "admin_id": admin_id,
        "admin_name": load_users().get(str(admin_id), {}).get("name", f"ID{admin_id}"),
        "action": action,  # give_premium, remove_premium, give_admin, remove_admin, etc
        "target_user": target_user,  # ID пользователя или "all_users"
        "details": details,  # подробное описание
        "timestamp": datetime.now().isoformat()
    }

    logs["actions"].append(log_entry)
    save_json(ACTIONS_LOG_FILE, logs)


def get_admin_logs(limit=50):
    """Получает последние логи действий администраторов"""
    logs = load_json(ACTIONS_LOG_FILE, {})
    actions = logs.get("actions", [])
    # Сортируем по времени (новые в начале)
    actions = sorted(actions, key=lambda x: x.get("timestamp", ""), reverse=True)
    return actions[:limit]


def clear_admin_logs():
    """Очищает все логи (только для SUPER_ADMIN)"""
    save_json(ACTIONS_LOG_FILE, {"actions": []})

def load_global_test(test_id):
    if not os.path.exists("global_tests.json"):
        return None
    with open("global_tests.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(test_id)

def delete_global_test(test_id):
    if os.path.exists("global_tests.json"):
        with open("global_tests.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        data.pop(test_id, None)
        with open("global_tests.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

def save_user_test_id(user_id, test_id):
    if os.path.exists("user_data.json"):
        with open("user_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    user_id_str = str(user_id)
    if user_id_str not in data:
        data[user_id_str] = []
    if test_id not in data[user_id_str]:
        data[user_id_str].append(test_id)
    with open("user_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_user_test_ids(user_id):
    if not os.path.exists("user_data.json"):
        return []
    with open("user_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return [item for item in data.get(str(user_id), []) if isinstance(item, str)]

def delete_user_test_id(user_id, test_id):
    if os.path.exists("user_data.json"):
        with open("user_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        user_id_str = str(user_id)
        if user_id_str in data and test_id in data[user_id_str]:
            data[user_id_str].remove(test_id)
        with open("user_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

def load_json(filename, default=None):
    if not os.path.exists(filename):
        data = default or {}
        save_json(filename, data)
        return data
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ====================== АДМИНЫ ======================
def load_admins():
    return load_json(ADMINS_FILE, [SUPER_ADMIN_ID])

def save_admins(data):
    save_json(ADMINS_FILE, data)

def is_admin(user_id):
    return user_id == SUPER_ADMIN_ID or user_id in load_admins()

def add_admin(user_id):
    admins = load_admins()
    if user_id not in admins:
        admins.append(user_id)
        save_admins(admins)

def remove_admin(user_id):
    if user_id == SUPER_ADMIN_ID:
        return
    admins = load_admins()
    if user_id in admins:
        admins.remove(user_id)
        save_admins(admins)

# ====================== ПОЛЬЗОВАТЕЛИ ======================
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def find_user(query):
    users = load_users()
    query = str(query).lower()
    for user_id, u in users.items():
        username = (u.get("username") or "").lower()
        name = (u.get("name") or "").lower()
        uid = str(user_id)
        if query in username or query in name or query in uid:
            return user_id, u
    return None, None

def save_user(user):
    data = load_users()
    user_id = str(user.id)
    if user_id not in data:
        data[user_id] = {
            "id": user.id,
            "username": user.username,
            "name": user.full_name,
            "lang": "ru"
        }
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user_lang(user_id):
    users = load_users()
    user = users.get(str(user_id), {})
    return user.get("lang", "ru")

def t(user_id, key):
    lang = get_user_lang(user_id)
    return LANG.get(lang, LANG["ru"]).get(key, LANG["ru"].get(key, key))
def load_ready_tests():
    if not os.path.exists(READY_TESTS_FILE):
        return {}
    with open(READY_TESTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_ready_tests(data):
    with open(READY_TESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def add_to_ready_tests(test_id, admin_id):
    """Админ добавляет тест в Готовые тесты"""
    data = load_ready_tests()
    if test_id not in data:
        data[test_id] = {
            "test_id": test_id,
            "added_by": admin_id,
            "added_date": datetime.now().isoformat()
        }
        save_ready_tests(data)
        return True
    return False

def remove_from_ready_tests(test_id):
    data = load_ready_tests()
    if test_id in data:
        del data[test_id]
        save_ready_tests(data)
        return True
    return False

# ====================== ПРЕМИУМ ======================
def load_premium_users():
    if not os.path.exists(FILE):
        return {}
    with open(FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_premium_users(data):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def add_premium(user_id, days):
    data = load_premium_users()
    expire = int(time.time()) + days * 86400
    data[str(user_id)] = expire
    save_premium_users(data)

def remove_premium(user_id):
    data = load_premium_users()
    user_id = str(user_id)
    if user_id in data:
        del data[user_id]
        save_premium_users(data)

def is_premium(user_id):
    data = load_premium_users()
    expire = data.get(str(user_id))
    if not expire:
        return False
    if time.time() > expire:
        del data[str(user_id)]
        save_premium_users(data)
        return False
    return True

def is_premium_plus(user_id):
    """Проверяет наличие Премиум+"""
    plus_file = "premium_plus.json"
    if not os.path.exists(plus_file):
        return False
    with open(plus_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    expire = data.get(str(user_id))
    if not expire:
        return False
    if time.time() > expire:
        del data[str(user_id)]
        with open(plus_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return False
    return True

def add_premium_plus(user_id, days):
    """Выдать Премиум+"""
    plus_file = "premium_plus.json"
    if not os.path.exists(plus_file):
        data = {}
    else:
        with open(plus_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    expire = int(time.time()) + days * 86400
    data[str(user_id)] = expire
    with open(plus_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def remove_premium_plus(user_id):
    """Убрать Премиум+"""
    plus_file = "premium_plus.json"
    if not os.path.exists(plus_file):
        return
    with open(plus_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    user_id = str(user_id)
    if user_id in data:
        del data[user_id]
        with open(plus_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

def can_bypass_limits(user_id):
    return is_admin(user_id)

def get_premium_time_left(user_id):
    data = load_premium_users()
    expire = data.get(str(user_id))
    if not expire:
        return None
    left = expire - time.time()
    if left <= 0:
        return None
    days = int(left // 86400)
    hours = int((left % 86400) // 3600)
    return f"{days} дн. {hours} ч."

# ====================== РЕЗУЛЬТАТЫ ТЕСТОВ ======================
def save_test_result(test_id, group_key, user_id, score, total, time_spent):
    results = load_json(RESULTS_FILE)
    if test_id not in results:
        results[test_id] = {}
    if group_key not in results[test_id]:
        results[test_id][group_key] = []
    result = {
        "user_id": user_id,
        "username": load_users().get(str(user_id), {}).get("username", f"ID{user_id}"),
        "score": score,
        "total": total,
        "time_spent": round(time_spent, 1),
        "date": datetime.now().isoformat()
    }
    results[test_id][group_key].append(result)
    save_json(RESULTS_FILE, results)

def get_leaderboard(test_id, group_key, limit=10):
    results = load_json(RESULTS_FILE)
    data = results.get(test_id, {}).get(group_key, [])
    sorted_data = sorted(data, key=lambda x: (-x["score"], x["time_spent"]))
    return sorted_data[:limit]

# ====================== ВСПОМОГАТЕЛЬНЫЕ ======================
def read_txt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def read_docx(path):
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)

def safe_trim(text, limit=100):
    return text if len(text) <= limit else text[:limit - 3] + "..."

def parse_text(content: str, answer_mode: str):
    questions = []
    blocks = re.split(r"\n*\+{3,}\n*", content)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        parts = re.split(r"\n*={3,}\n*", block)
        if len(parts) < 2:
            continue
        q_text = parts[0].strip()
        # Убрать нумерацию в начале (1. 1) 1: и т.д.)
        q_text = re.sub(r"^\d+[\.\)\:\-]\s*", "", q_text).strip()

        if not q_text:
            continue
        raw_answers = [p.strip() for p in parts[1:] if p.strip()]
        answers = []
        correct_index = None
        for ans in raw_answers:
            clean = ans.strip()
            # Убрать нумерацию в ответах
            clean = re.sub(r"^\d+[\.\)\:\-]\s*", "", clean).strip()
            if answer_mode == "2":
                if clean.lstrip().startswith("#"):
                    clean = clean.lstrip()[1:].strip()
                    correct_index = len(answers)
            answers.append(clean)

        if answer_mode == "1" and answers:
            correct_index = 0
        if correct_index is None:
            continue
        if len(answers) < 2:
            continue
        questions.append({
            "question": q_text,
            "answers": answers,
            "correct": correct_index
        })
    return questions

def get_q_word(user_id: int, answered: int) -> str:
    """Возвращает правильную форму слова 'вопрос' для языка пользователя."""
    lang = get_user_lang(user_id)
    if lang == "ru":
        if answered % 10 == 1 and answered % 100 != 11:
            return t(user_id, "q_word_1")
        elif answered % 10 in (2, 3, 4) and answered % 100 not in (12, 13, 14):
            return t(user_id, "q_word_2")
        else:
            return t(user_id, "q_word_5")
    else:
        # EN и UZ — одна форма
        return t(user_id, "q_word_5")

def get_fsm_context(user_id: int):
    return FSMContext(storage=dp.storage, key=StorageKey(chat_id=user_id, user_id=user_id, bot_id=bot.id))

# ====================== БОТ ======================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
poll_owners = {}

class CreateTest(StatesGroup):
    name = State()
    answer_mode = State()
    file = State()
    time = State()
    split = State()

class AdminSearch(StatesGroup):
    query = State()

class EditTest(StatesGroup):
    name = State()
    time = State()
    order = State()

class SendToGroup(StatesGroup):
    group_id = State()

def get_menu(user_id):
    keyboard = [
        [KeyboardButton(text=t(user_id, "new_test"))],
        [KeyboardButton(text=t(user_id, "ready_tests"))],   # новая кнопка
        [KeyboardButton(text=t(user_id, "my_tests"))],
        [KeyboardButton(text=t(user_id, "premium"))]
    ]
    if is_admin(user_id):
        keyboard.append([KeyboardButton(text=t(user_id, "admin"))])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# ====================== ФИЛЬТР КНОПОК МЕНЮ ======================
class IsMenuButton(Filter):
    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        menu_keys = ["new_test", "premium", "my_tests", "admin",
                     "back", "users", "search", "premium_active",
                     "give_all_premium", "remove_premium_all",
                     "give_all_premium_plus", "remove_premium_plus_all"]
        return any(
            message.text == LANG[lang].get(key)
            for lang in LANG
            for key in menu_keys
        )

# ====================== ХЕНДЛЕРЫ ======================

@dp.message(Command("start"))
async def start_handler(message: Message):
    save_user(message.from_user)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz")]
    ])
    await message.answer("🌐 Выберите язык / Choose language / Tilni tanlang:", reply_markup=kb)

@dp.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(t(message.from_user.id, "help_client"))

@dp.message(Command("lang"))
async def lang_command(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz")]
    ])
    await message.answer("🌐 Выберите язык / Choose language / Tilni tanlang:", reply_markup=kb)

@dp.message(Command("stop"))
async def stop_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(t(message.from_user.id, "test_stopped"), reply_markup=get_menu(message.from_user.id))


@dp.message(Command("adminlog"))
async def adminlog_command(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return await message.answer(t(message.from_user.id, "no_access"))

    await show_admin_logs(message, message.from_user.id, 0)


async def show_admin_logs(message, admin_id: int, page: int = 0, edit: bool = False):
    """Показывает историю действий администраторов (пагинация 5 логов на странице)"""
    logs = get_admin_logs(limit=100)

    if not logs:
        await message.answer(t(admin_id, "no_admin_logs"), reply_markup=get_menu(admin_id))
        return

    items_per_page = 5
    total = len(logs)
    start = page * items_per_page
    current_logs = logs[start:start + items_per_page]

    text = "📋 История действий администраторов:\n\n"

    for log in current_logs:
        admin_name = log.get("admin_name", "Unknown")
        action = log.get("action", "unknown")
        target = log.get("target_user", "unknown")
        timestamp = log.get("timestamp", "")[:16]  # Сокращаем до даты+времени
        details = log.get("details", "")

        # Переводим действие на русский
        action_ru = {
            "give_premium": "📤 Выдал Premium",
            "remove_premium": "❌ Удалил Premium",
            "give_admin": "👮 Сделал админом",
            "remove_admin": "👮❌ Снял админа",
            "give_premium_all": "📤 Выдал Premium всем",
            "give_premium_plus_all": "📤 Выдал Premium+ всем",
            "remove_premium_all": "❌ Удалил Premium у всех",
        }.get(action, action)

        text += f"🔹 {action_ru}\n"
        text += f"   👤 Админ: {admin_name}\n"
        text += f"   🎯 Пользователь: {target}\n"
        text += f"   ⏰ {timestamp}\n"
        text += f"   📝 {details}\n\n"

    buttons = []

    # Навигация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"adminlog_page_{page - 1}"))
    if start + items_per_page < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"adminlog_page_{page + 1}"))
    if nav:
        buttons.append(nav)

    # Кнопка очистки логов (только SUPER_ADMIN)
    buttons.append([InlineKeyboardButton(text=t(admin_id, "clear_logs"), callback_data="clear_admin_logs")])
    buttons.append([InlineKeyboardButton(text=t(admin_id, "back"), callback_data="back_to_admin")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)

@dp.message(Command("newquiz"))
async def newquiz_command(message: Message, state: FSMContext):
    await new_test(message, state)

@dp.message(Command("test_premium"))
async def test_premium_cmd(message: Message):
    await message.answer(str(load_premium_users()))

@dp.message(Command("add_premium"))
async def give_premium(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return await message.answer(t(message.from_user.id, "no_access"))
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        days = int(parts[2]) if len(parts) > 2 else 30
        add_premium(user_id, days)
        await message.answer(f"✅ Пользователь {user_id} получил премиум на {days} дней")
    except:
        await message.answer("Используй: /add_premium USER_ID [DAYS]")

@dp.message(Command("remove_premium"))
async def remove_premium_cmd(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return await message.answer(t(message.from_user.id, "no_access"))
    try:
        user_id = int(message.text.split()[1])
        remove_premium(user_id)
        await message.answer(f"❌ Премиум у {user_id} удалён")
    except:
        await message.answer("Используй: /remove_premium USER_ID")
@dp.message(Command("addlist"))
async def addlist_command(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return await message.answer(t(message.from_user.id, "no_access"))
    try:
        test_id = message.text.split()[1]
        if add_to_ready_tests(test_id, message.from_user.id):
            await message.answer(f"✅ Тест {test_id} добавлен в Готовые тесты")
        else:
            await message.answer(f"⚠️ Тест уже в Готовых тестах")
    except:
        await message.answer("Используй: /addlist TEST_ID")

@dp.message(Command("removelist"))
async def removelist_command(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return await message.answer(t(message.from_user.id, "no_access"))
    try:
        test_id = message.text.split()[1]
        if remove_from_ready_tests(test_id):
            await message.answer(f"✅ Тест {test_id} удалён из Готовых тестов")
        else:
            await message.answer(f"⚠️ Тест не найден")
    except:
        await message.answer("Используй: /removelist TEST_ID")

# ====================== ПЕРЕХВАТ КНОПОК МЕНЮ В ЛЮБОМ СОСТОЯНИИ ======================

@dp.message(IsMenuButton(), ~StateFilter(None))
async def any_state_menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await main_text_handler(message, state)

# ====================== ГЛАВНЫЙ ТЕКСТОВЫЙ ХЕНДЛЕР ======================

@dp.message(F.text, StateFilter(None))
async def main_text_handler(message: Message, state: FSMContext):
    text = message.text
    user_id = message.from_user.id

    if text == t(user_id, "admin"):
        if not is_admin(user_id):
            return await message.answer(t(user_id, "no_access"))

        kb_buttons = [
            [KeyboardButton(text=t(user_id, "users")), KeyboardButton(text=t(user_id, "search"))],
            [KeyboardButton(text=t(user_id, "premium_active"))],
        ]

        # ТОЛЬКО для SUPER_ADMIN добавить кнопку истории
        if user_id == SUPER_ADMIN_ID:
            kb_buttons.append([KeyboardButton(text=t(user_id, "admin_history"))])

        kb_buttons.append([KeyboardButton(text=t(user_id, "back"))])

        kb = ReplyKeyboardMarkup(
            keyboard=kb_buttons,
            resize_keyboard=True
        )
        await message.answer("🛠 Админ панель:", reply_markup=kb)
        return

    if text == t(user_id, "new_test"):
        await new_test(message, state)
        return

    if text == t(user_id, "my_tests"):
        await show_my_tests(message, user_id)
        return

    if text == t(user_id, "premium"):
        # Определяем статус подписки
        if is_premium_plus(user_id):
            status = "💎+ Премиум+ активна"
        elif is_premium(user_id):
            status = "💎 Премиум активна"
        else:
            status = "❌ Подписка отсутствует"

        premium_time = get_premium_time_left(user_id)
        if premium_time:
            status += f"\n⏳ Осталось: {premium_time}"

        message_text = t(user_id, "buy_premium").format(status=status)
        await message.answer(message_text)
        return
    if text == t(user_id, "ready_tests"):
        await show_ready_tests(message, user_id)
        return

    if is_admin(user_id):
        if text == t(user_id, "users"):
            await show_users_for_admin_management(message, user_id, 0)
            return

        elif text == t(user_id, "search"):
            await message.answer(t(user_id, "enter_query"))
            await state.set_state(AdminSearch.query)
            return


        elif text == t(user_id, "premium_active"):

            data = load_premium_users()

            users_data = load_users()

            msg = "💎 Активные Premium подписки:\n\n"

            has_any = False

            for uid, expire in data.items():

                left = int(expire - time.time())

                if left > 0:
                    has_any = True

                    name = users_data.get(uid, {}).get("name", f"ID{uid}")

                    msg += f"• {name} ({uid}) — {left // 86400} дн.\n"

            if not has_any:
                msg = "Нет активных премиум пользователей"

            kb = ReplyKeyboardMarkup(keyboard=[

                [KeyboardButton(text=t(user_id, "give_all_premium")),
                 KeyboardButton(text=t(user_id, "remove_premium_all"))],

                [KeyboardButton(text=t(user_id, "give_all_premium_plus")),
                 KeyboardButton(text=t(user_id, "remove_premium_plus_all"))],

                [KeyboardButton(text=t(user_id, "back"))]

            ], resize_keyboard=True)

            await message.answer(msg, reply_markup=kb)

            return


        elif text == t(user_id, "give_all_premium"):

            if not is_admin(user_id):
                return

            users_all = load_users()

            for uid in users_all:
                add_premium(int(uid), 30)

            log_admin_action(user_id, "give_premium_all", "all_users",

                             f"Выдал Premium всем {len(users_all)} пользователям на 30 дней")

            await message.answer(t(user_id, "all_premium_given"))

            return


        elif text == t(user_id, "remove_premium_all"):

            if not is_admin(user_id):
                return

            pdata = load_premium_users()

            count = len(pdata)

            pdata.clear()

            save_premium_users(pdata)

            log_admin_action(user_id, "remove_premium_all", "all_users",

                             f"Удалил Premium у всех {count} пользователей")

            await message.answer("✅ Все Premium подписки удалены")

            return


        elif text == t(user_id, "give_all_premium_plus"):

            if not is_admin(user_id):
                return

            users_all = load_users()

            for uid in users_all:
                add_premium(int(uid), 30)

            log_admin_action(user_id, "give_premium_plus_all", "all_users",

                             "Выдал Премиум+ всем пользователям (30 дней)")

            await message.answer(t(user_id, "all_premium_plus_given"))

            return


        elif text == t(user_id, "remove_premium_plus_all"):

            if not is_admin(user_id):
                return

            pdata = load_premium_users()

            count = len(pdata)

            pdata.clear()

            save_premium_users(pdata)

            log_admin_action(user_id, "remove_premium_plus_all", "all_users",

                             f"Удалил Premium+ у всех {count} пользователей")

            await message.answer("✅ Все Premium+ подписки удалены")

            return

        elif text == t(user_id, "admin_history"):
            await show_admin_logs(message, user_id, 0)
            return

        elif text == t(user_id, "back"):
            await message.answer(t(user_id, "welcome"), reply_markup=get_menu(user_id))
            return

# ====================== ПОИСК ПОЛЬЗОВАТЕЛЯ ======================

@dp.message(AdminSearch.query)
async def admin_search_handler(message: Message, state: FSMContext):
    user_id_found, user_data = find_user(message.text)
    if not user_id_found:
        await message.answer(t(message.from_user.id, "user_not_found"))
        await state.clear()
        return

    u = user_data
    premium = is_premium(user_id_found)
    left = get_premium_time_left(user_id_found)
    status = "💎 Премиум" if premium else "❌ Нет премиума"
    if left:
        status += f"\n⏳ Осталось: {left}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 1 мес", callback_data=f"give_1_{user_id_found}")],
        [InlineKeyboardButton(text="⭐ 3 мес", callback_data=f"give_3_{user_id_found}")],
        [InlineKeyboardButton(text="⭐ 6 мес", callback_data=f"give_6_{user_id_found}")],
        [InlineKeyboardButton(text="❌ Убрать премиум", callback_data=f"remove_{user_id_found}")],
    ])

    name = u.get("name", "Без имени")
    username = u.get("username", "")
    username_str = f"@{username}" if username else ""

    await message.answer(
        f"👤 {name} {username_str}\nID: {user_id_found}\n\n{status}",
        reply_markup=kb
    )
    await state.clear()

# ====================== СОЗДАНИЕ ТЕСТА ======================

async def new_test(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_tests = load_user_test_ids(user_id)

    if not can_bypass_limits(user_id) and not is_premium(user_id) and len(user_tests) >= 2:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Перейти в Premium", callback_data="premium")]
        ])
        await message.answer(t(user_id, "premium_ended"), reply_markup=kb)
        return

    await message.answer(t(user_id, "enter_name"))
    await state.set_state(CreateTest.name)

@dp.message(CreateTest.name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    user_id = message.from_user.id
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(user_id, "mode_hash"), callback_data="answer_mode_2")],
        [InlineKeyboardButton(text=t(user_id, "mode_first"), callback_data="answer_mode_1")]
    ])
    await message.answer(t(user_id, "choose_mode"), reply_markup=kb)
    await state.set_state(CreateTest.answer_mode)

@dp.message(CreateTest.file, F.document)
async def get_file(message: Message, state: FSMContext):
    doc = message.document
    if not doc.file_name.endswith((".txt", ".docx")):
        await message.answer(t(message.from_user.id, "file_error"))
        return

    file = await bot.get_file(doc.file_id)
    user_folder = f"files/{message.from_user.id}"
    os.makedirs(user_folder, exist_ok=True)
    path = f"{user_folder}/{doc.file_name}"
    await bot.download_file(file.file_path, path)

    text = read_txt(path) if doc.file_name.endswith(".txt") else read_docx(path)
    data = await state.get_data()
    questions = parse_text(text, data.get("answer_mode"))

    if not questions:
        await message.answer(t(message.from_user.id, "parse_error"))
        return

    await state.update_data(questions=questions)
    await message.answer(t(message.from_user.id, "enter_time"))
    await state.set_state(CreateTest.time)

@dp.message(CreateTest.time)
async def set_time(message: Message, state: FSMContext):
    if not message.text.isdigit() or not (10 <= int(message.text) <= 300):
        await message.answer(t(message.from_user.id, "enter_time"))
        return
    await state.update_data(time=int(message.text))
    await message.answer(t(message.from_user.id, "enter_split"))
    await state.set_state(CreateTest.split)

@dp.message(CreateTest.split)
async def split_handler(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer(t(message.from_user.id, "enter_number"))
        return
    data = await state.get_data()
    test_data = {
        "name": data.get("name"),
        "questions": data.get("questions"),
        "split": int(message.text),
        "time": data.get("time", 60)
    }
    test_id = save_global_test(test_data)
    save_user_test_id(message.from_user.id, test_id)
    name = data.get("name", "")
    await message.answer(
        t(message.from_user.id, "test_created_full").format(name=name),
        reply_markup=get_menu(message.from_user.id)
    )
    await state.clear()

# ====================== МОИ ТЕСТЫ ======================

async def show_my_tests(message: Message, user_id: int):
    test_ids = load_user_test_ids(user_id)
    if not test_ids:
        await message.answer(t(user_id, "you_havent_test"), reply_markup=get_menu(user_id))
        return

    ready_tests = load_ready_tests()
    buttons = []

    for tid in test_ids:
        test_data = load_global_test(tid)
        if test_data:
            text = test_data['name']
            callback = f"start_test_{tid}"
            buttons.append([InlineKeyboardButton(text=text, callback_data=callback)])


    if not buttons:
        await message.answer(t(user_id, "you_havent_test"), reply_markup=get_menu(user_id))
        return

    await message.answer(t(user_id, "your_tests"), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

async def show_users_for_admin_management(message: Message, admin_id: int, page: int = 0):
    """Управление пользователями: админ права + премиум (inline, 5 на странице)"""
    users = load_users()
    if not users:
        await message.answer(t(admin_id, "no_users"), reply_markup=get_menu(admin_id))
        return

    items_per_page = 5
    user_list = list(users.items())
    total = len(user_list)
    start = page * items_per_page
    current_users = user_list[start:start + items_per_page]

    buttons = []
    for uid, u in current_users:
        is_admin_user = is_admin(int(uid)) and int(uid) != SUPER_ADMIN_ID
        premium_user = is_premium(int(uid))

        # Определяем статус (администратор может быть с премиумом)
        if is_admin_user:
            if premium_user:
                status = "👮💎"
            else:
                status = "👮"
        else:
            if premium_user:
                status = "💎"
            else:
                status = "👤"

        name = u.get("name", "Без имени")
        buttons.append([InlineKeyboardButton(
            text=f"{status} {safe_trim(name, 18)} (ID: {uid})",
            callback_data=f"manage_user_{uid}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"users_manage_page_{page - 1}"))
    if start + items_per_page < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"users_manage_page_{page + 1}"))
    if nav:
        buttons.append(nav)

        # НОВЫЕ КНОПКИ: выдать всем и убрать у всех
        buttons.append([
            InlineKeyboardButton(text=t(admin_id, "give_all_premium"), callback_data="give_premium_all"),
            InlineKeyboardButton(text=t(admin_id, "give_all_premium_plus"), callback_data="give_premium_plus_all")
        ])
        buttons.append([
            InlineKeyboardButton(text=t(admin_id, "remove_premium_all"), callback_data="remove_premium_all")
        ])

    buttons.append([InlineKeyboardButton(text=t(admin_id, "back"), callback_data="back_to_admin")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(t(admin_id, "users"), reply_markup=kb)

async def show_ready_tests(message: Message, user_id: int):
    """Показывает готовые тесты (требует Premium+)"""
    if not is_premium_plus(user_id) and user_id != SUPER_ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Перейти в Premium", callback_data="premium")]
        ])
        await message.answer(t(user_id, "premium_required_ready"), reply_markup=kb)
        return

    ready = load_ready_tests()
    if not ready:
        await message.answer(t(user_id, "no_ready_tests"), reply_markup=get_menu(user_id))
        return

    buttons = []
    for tid in ready:
        test_data = load_global_test(tid)
        if test_data:
            buttons.append([InlineKeyboardButton(
                text=f"{test_data['name']} ({len(test_data['questions'])} вопросов)",
                callback_data=f"start_ready_test_{tid}"
            )])

    if not buttons:
        await message.answer(t(user_id, "no_ready_tests"), reply_markup=get_menu(user_id))
        return

    await message.answer(t(user_id, "ready_tests_list"), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

async def show_test_groups(message: Message, test: dict, test_id: str, user_id: int, page: int = 0, is_ready_test: bool = False):
    questions = test.get("questions", [])
    split = test.get("split", 30)
    groups = list(range(0, len(questions), split))

    items_per_page = 5
    start_idx = page * items_per_page
    current_groups = groups[start_idx: start_idx + items_per_page]

    buttons = []
    for s in current_groups:
        e = min(s + split, len(questions))
        buttons.append([InlineKeyboardButton(
            text=f"{s + 1}-{e}",
            callback_data=f"group_{test_id}_{s}_{e}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"groups_page_{test_id}_{page - 1}"))
    if start_idx + items_per_page < len(groups):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"groups_page_{test_id}_{page + 1}"))
    if nav:
        buttons.append(nav)

    if not is_ready_test:
        bottom_buttons = [
            InlineKeyboardButton(text=t(user_id, "btn_send_group"), callback_data=f"send_group_{test_id}"),
            InlineKeyboardButton(text=t(user_id, "edit_test"), callback_data=f"edit_test_{test_id}")
        ]
        if user_id == SUPER_ADMIN_ID:
            ready_tests = load_ready_tests()
            if test_id in ready_tests:
                bottom_buttons.append(InlineKeyboardButton(
                    text=t(user_id, "remove_from_ready"),
                    callback_data=f"toggle_ready_{test_id}"
                ))
            else:
                bottom_buttons.append(InlineKeyboardButton(
                    text=t(user_id, "add_to_ready"),
                    callback_data=f"toggle_ready_{test_id}"
                ))
        buttons.append(bottom_buttons)
        buttons.append([
            InlineKeyboardButton(text=t(user_id, "btn_delete_test"), callback_data=f"delete_test_{test_id}"),
            InlineKeyboardButton(text=t(user_id, "btn_back"), callback_data="back_to_my_tests")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text=t(user_id, "btn_back"), callback_data="back_to_ready_tests")
        ])

    await message.edit_text(
        t(user_id, "choose_group").format(name=test.get("name", "Тест")),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

# ====================== ОБРАТНЫЙ ОТСЧЁТ ======================

async def start_countdown(chat_id: int, user_id: int):
    msg = await bot.send_message(chat_id, t(user_id, "countdown_3"))
    await asyncio.sleep(1)
    await msg.edit_text(t(user_id, "countdown_2"))
    await asyncio.sleep(1)
    await msg.edit_text(t(user_id, "countdown_1"))
    await asyncio.sleep(1)
    await msg.edit_text(t(user_id, "countdown_go"))
    await asyncio.sleep(0.8)
    await msg.delete()

# ====================== РЕЗУЛЬТАТ ======================

async def send_test_result(chat_id: int, data: dict, state: FSMContext):
    test = data.get("test")
    score = data.get("score", 0)
    wrong = data.get("wrong", 0)
    start = data.get("start", 0)
    end = data.get("end", 0)
    user_id = data.get("user_id")
    answered = score + wrong
    no_answer = end - start - answered
    test_name = test.get("name", "")
    time_spent = round(time.time() - data.get("start_time", time.time()), 1)

    q_word = get_q_word(user_id, answered)

    text = (
        t(user_id, "result_header").format(name=test_name) + "\n\n" +
        t(user_id, "result_answered").format(answered=answered, q_word=q_word) + "\n" +
        t(user_id, "result_correct").format(score=score) + "\n" +
        t(user_id, "result_wrong").format(wrong=wrong) + "\n" +
        t(user_id, "result_no_answer").format(no_answer=no_answer) + "\n" +
        t(user_id, "result_time").format(time_spent=time_spent)
    )

    test_id = data.get("test_id")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t(user_id, "btn_retry"),
            callback_data=f"retry_test_{test_id}_{start}_{end}"
        )],
        [InlineKeyboardButton(text=t(user_id, "btn_send_group"), callback_data=f"send_to_group_{test_id}")],
        [InlineKeyboardButton(text=t(user_id, "btn_share"), callback_data=f"share_{test_id}_{start}_{end}")]
    ])

    await bot.send_message(chat_id, text, reply_markup=kb)
    await state.clear()

# ====================== ОТПРАВКА ВОПРОСА ======================

async def send_question(state: FSMContext):
    data = await state.get_data()
    if data.get("paused"):
        return

    chat_id = data.get("chat_id")
    test = data.get("test")
    q_index = data.get("q_index", 0)
    start = data.get("start", 0)
    end = data.get("end", 0)

    if q_index >= end:
        await send_test_result(chat_id, data, state)
        return

    q = test["questions"][q_index]
    answers = [safe_trim(a.strip()) for a in q["answers"] if a.strip()]
    answers = answers[:10]

    correct_index = q["correct"]
    paired = list(enumerate(answers))
    random.shuffle(paired)
    shuffled = [ans for _, ans in paired]
    new_correct = next(i for i, (old, _) in enumerate(paired) if old == correct_index)

    local = q_index - start + 1
    total = end - start
    question_text = f"[{local}/{total}] {q['question']}"

    poll = await bot.send_poll(
        chat_id=chat_id,
        question=question_text,
        options=shuffled,
        type='quiz',
        correct_option_id=new_correct,
        is_anonymous=False,
        open_period=test.get("time", 20)
    )

    time_limit = test.get("time", 20)
    task = asyncio.create_task(check_inactive_timeout(state, poll.poll.id, time_limit))
    await state.update_data(timeout_task=task)

    poll_owners[poll.poll.id] = data.get("user_id")

    await state.update_data(
        current_poll_id=poll.poll.id,
        correct=new_correct,
        answered=None
    )

async def check_inactive_timeout(state: FSMContext, poll_id: str, time_limit: int):
    await asyncio.sleep(time_limit + 5)

    data = await state.get_data()

    if data.get("current_poll_id") != poll_id:
        return

    chat_id = data.get("chat_id")
    user_id = data.get("user_id")
    test = data.get("test")

    if time_limit <= 25:
        # Режим коротких вопросов: пауза после 2 пропущенных подряд
        inactive = data.get("inactive_count", 0) + 1
        await state.update_data(inactive_count=inactive)
        if inactive < 2:
            return
    else:
        # Режим длинных вопросов: ждём до суммарных 60 сек
        extra_wait = max(0, 60 - (time_limit + 5))
        if extra_wait > 0:
            await asyncio.sleep(extra_wait)
        data = await state.get_data()
        if data.get("current_poll_id") != poll_id:
            return
        await state.update_data(inactive_count=data.get("inactive_count", 0) + 1)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(user_id, "continue_test"), callback_data="resume_test")],
        [InlineKeyboardButton(text=t(user_id, "stop_tests"), callback_data="stop_test")]
    ])

    await bot.send_message(
        chat_id,
        t(user_id, "test_paused").format(name=test.get("name", "")),
        reply_markup=kb
    )

    await state.update_data(paused=True)

# ====================== CALLBACK ХЕНДЛЕРЫ ======================

@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    users = load_users()
    user_id = str(callback.from_user.id)
    if user_id in users:
        users[user_id]["lang"] = lang
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=4)
    await callback.answer("✅ Language updated")
    await callback.message.delete()
    await bot.send_message(
        callback.from_user.id,
        t(callback.from_user.id, "welcome"),
        reply_markup=get_menu(callback.from_user.id)
    )


@dp.callback_query(F.data == "back_to_ready_tests")
async def back_to_ready_tests(callback: CallbackQuery):
    await show_ready_tests(callback.message, callback.from_user.id)
    await callback.answer()


@dp.callback_query(F.data.startswith("adminlog_page_"))
async def adminlog_page_handler(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    await show_admin_logs(callback.message, callback.from_user.id, page, edit=True)
    await callback.answer()


@dp.callback_query(F.data == "clear_admin_logs")
async def clear_admin_logs_callback(callback: CallbackQuery):
    if callback.from_user.id != SUPER_ADMIN_ID:
        return await callback.answer(t(callback.from_user.id, "no_access"), show_alert=True)

    clear_admin_logs()

    # Логируем само очищение логов
    log_admin_action(
        admin_id=callback.from_user.id,
        action="clear_logs",
        target_user="system",
        details="Очистил историю действий администраторов"
    )

    await callback.answer(t(callback.from_user.id, "logs_cleared"), show_alert=True)
    await show_admin_logs(callback.message, callback.from_user.id, 0, edit=True)

@dp.callback_query(F.data.startswith("manage_user_"))
async def manage_user_menu(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    admin_id = callback.from_user.id

    is_admin_user = is_admin(user_id) and user_id != SUPER_ADMIN_ID
    premium_user = is_premium(user_id)
    premium_time = get_premium_time_left(user_id)

    users = load_users()
    u = users.get(str(user_id), {})
    name = u.get("name", "Без имени")

    status_text = ""
    if is_admin_user:
        status_text += "👮 Администратор\n"
    if premium_user:
        status_text += f"💎 Премиум\n⏳ Осталось: {premium_time}\n"
    if not is_admin_user and not premium_user:
        status_text = "👤 Обычный пользователь"

    # Показываем текущий статус подписки
    if premium_user:
        status_text += "(Активна 💎 Premium)\n"
    else:
        status_text += "(Подписка отсутствует)\n""Обычный пользователь"

    buttons = [
        [InlineKeyboardButton(text="💎 Premium 1м", callback_data=f"give_1_{user_id}")],
        [InlineKeyboardButton(text="💎 Premium 3м", callback_data=f"give_3_{user_id}")],
        [InlineKeyboardButton(text="💎 Premium 6м", callback_data=f"give_6_{user_id}")],
        [InlineKeyboardButton(text="💎+ Premium+ 1м", callback_data=f"give_plus_1_{user_id}")],
        [InlineKeyboardButton(text="💎+ Premium+ 3м", callback_data=f"give_plus_3_{user_id}")],
        [InlineKeyboardButton(text="💎+ Premium+ 6м", callback_data=f"give_plus_6_{user_id}")],
        [InlineKeyboardButton(text="❌ Убрать Premium", callback_data=f"remove_{user_id}")],
    ]

    # ТОЛЬКО для SUPER_ADMIN кнопка админа
    if admin_id == SUPER_ADMIN_ID:
        admin_btn = InlineKeyboardButton(
            text=t(admin_id, "unmake_admin" if is_admin_user else "make_admin"),
            callback_data=f"{'del_admin' if is_admin_user else 'mk_admin'}_{user_id}"
        )
        buttons.append([admin_btn])

    buttons.append([InlineKeyboardButton(text=t(admin_id, "btn_back"), callback_data="back_to_manage_users")])

    await callback.message.edit_text(
        f"👤 {name}\nID: {user_id}\n\n{status_text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("users_manage_page_"))
async def users_manage_page_handler(callback: CallbackQuery):
    page = int(callback.data.split("_")[3])
    await show_users_for_admin_management(callback.message, callback.from_user.id, page)
    await callback.answer()


@dp.callback_query(F.data == "back_to_manage_users")
async def back_to_manage_users(callback: CallbackQuery):
    await show_users_for_admin_management(callback.message, callback.from_user.id, 0)
    await callback.answer()


@dp.callback_query(F.data == "give_premium_all")
async def give_premium_all_callback(callback: CallbackQuery):
    if callback.from_user.id != SUPER_ADMIN_ID:
        return await callback.answer(t(callback.from_user.id, "no_access"), show_alert=True)

    users = load_users()
    for uid in users:
        add_premium(int(uid), 30)

    # Логируем выдачу премиума всем
    log_admin_action(
        admin_id=callback.from_user.id,
        action="give_premium_all",
        target_user="all_users",
        details=f"Выдал Premium всем {len(users)} пользователям на 30 дней"
    )

    await callback.answer(t(callback.from_user.id, "all_premium_given"), show_alert=True)


@dp.callback_query(F.data == "remove_premium_all")
async def remove_premium_all_callback(callback: CallbackQuery):
    if callback.from_user.id != SUPER_ADMIN_ID:
        return await callback.answer(t(callback.from_user.id, "no_access"), show_alert=True)

    data = load_premium_users()
    count = len(data)
    data.clear()
    save_premium_users(data)

    # Логируем удаление премиума у всех
    log_admin_action(
        admin_id=callback.from_user.id,
        action="remove_premium_all",
        target_user="all_users",
        details=f"Удалил Premium у всех {count} пользователей"
    )

    await callback.answer("✅ Все премиум подписки удалены", show_alert=True)


@dp.callback_query(F.data == "give_premium_plus_all")
async def give_premium_plus_all_callback(callback: CallbackQuery):
    if callback.from_user.id != SUPER_ADMIN_ID:
        return await callback.answer(t(callback.from_user.id, "no_access"), show_alert=True)

    users = load_users()
    for uid in users:
        add_premium(int(uid), 30)  # 30 дней как Премиум+

    # Логируем это действие
    log_admin_action(
        admin_id=callback.from_user.id,
        action="give_premium_plus_all",
        target_user="all_users",
        details="Выдал Премиум+ всем пользователям (30 дней)"
    )

    await callback.answer(t(callback.from_user.id, "all_premium_plus_given"), show_alert=True)
    await show_users_for_admin_management(callback.message, callback.from_user.id, 0)

@dp.callback_query(F.data.startswith("answer_mode_"))
async def answer_mode_callback(callback: CallbackQuery, state: FSMContext):
    mode = callback.data.split("_")[-1]
    await state.update_data(answer_mode=mode)
    await callback.message.answer(t(callback.from_user.id, "send_file"))
    await state.set_state(CreateTest.file)
    await callback.answer()

@dp.callback_query(F.data == "resume_test")
async def resume_test(callback: CallbackQuery, state: FSMContext):
    await state.update_data(paused=False, inactive_count=0)
    await callback.message.delete()
    await send_question(state)

@dp.callback_query(F.data == "stop_test")
async def stop_test_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        t(callback.from_user.id, "test_stopped"),
        reply_markup=get_menu(callback.from_user.id)
    )
    await state.clear()
    await callback.answer()


@dp.callback_query(F.data == "premium")
async def premium_info(callback: CallbackQuery):
    user_id = callback.from_user.id

    # Определяем статус подписки
    if is_premium_plus(user_id):
        status = "💎+ Премиум+ активна"
    elif is_premium(user_id):
        status = "💎 Премиум активна"
    else:
        status = "❌ Подписка отсутствует"

    premium_time = get_premium_time_left(user_id)
    if premium_time:
        status += f"\n⏳ Осталось: {premium_time}"

    message_text = f"📊 Ваш статус:\n{status}\n\n" + t(user_id, "buy_premium")

    await callback.message.answer(message_text)
    await callback.answer()


@dp.callback_query(F.data.regexp(r'^give_\d+_\d+$'))
async def give_premium_callback(callback: CallbackQuery):
    parts = callback.data.split("_")
    months = parts[1]
    user_id = int(parts[2])
    days = int(months) * 30
    add_premium(user_id, days)

    users = load_users()
    target_name = users.get(str(user_id), {}).get("name", f"ID{user_id}")

    # Логируем выдачу премиума
    log_admin_action(
        admin_id=callback.from_user.id,
        action="give_premium",
        target_user=f"{user_id}",
        details=f"Выдал Premium на {months} мес. ({days} дней) пользователю {target_name}"
    )

    await callback.answer(t(callback.from_user.id, "gived_premium"))

@dp.callback_query(F.data.startswith("give_plus_"))
async def give_premium_plus_callback(callback: CallbackQuery):
    """Выдать Премиум+ (доступ в Готовые тесты)"""
    parts = callback.data.split("_")
    months = parts[2]
    user_id = int(parts[3])
    days = int(months) * 30
    add_premium_plus(user_id, days)
    await callback.answer(t(callback.from_user.id, "gived_premium_plus"))


@dp.callback_query(F.data.startswith("remove_"))
async def remove_premium_callback(callback: CallbackQuery):
    user_id = callback.data.split("_")[1]
    data = load_premium_users()
    data.pop(user_id, None)
    save_premium_users(data)

    users = load_users()
    target_name = users.get(user_id, {}).get("name", f"ID{user_id}")

    # Логируем удаление премиума
    log_admin_action(
        admin_id=callback.from_user.id,
        action="remove_premium",
        target_user=user_id,
        details=f"Удалил Premium у пользователя {target_name}"
    )

    await callback.answer(t(callback.from_user.id, "premium_delete"))

@dp.callback_query(F.data.startswith("retry_test_"))
async def retry_test(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    test_id = parts[2]
    start = int(parts[3])
    end = int(parts[4])

    test = load_global_test(test_id)
    if not test:
        return await callback.answer(t(callback.from_user.id, "test_not_found"), show_alert=True)

    await state.update_data(
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id,
        test_id=test_id,
        test=test,
        q_index=start,
        start=start,
        end=end,
        score=0,
        wrong=0,
        start_time=time.time(),
        inactive_count=0,
        paused=False
    )
    await callback.answer()
    await start_countdown(callback.message.chat.id, callback.from_user.id)
    await send_question(state)

@dp.callback_query(F.data.startswith("start_ready_test_"))
async def select_ready_test(callback: CallbackQuery):
    test_id = callback.data.split("_")[-1]
    test = load_global_test(test_id)
    if not test:
        return await callback.answer(t(callback.from_user.id, "test_not_found"), show_alert=True)
    # Для готовых тестов БЕЗ КНОПОК РЕДАКТИРОВАНИЯ
    await show_test_groups(callback.message, test, test_id, callback.from_user.id, is_ready_test=True)

@dp.callback_query(F.data.startswith("start_test_"))
async def select_test(callback: CallbackQuery):
    test_id = callback.data.split("_")[-1]
    test = load_global_test(test_id)
    if not test:
        return await callback.answer(t(callback.from_user.id, "test_not_found"), show_alert=True)
    await show_test_groups(callback.message, test, test_id, callback.from_user.id, page=0, is_ready_test=False)
    await callback.answer()

@dp.callback_query(F.data.startswith("delete_test_"))
async def delete_test_callback(callback: CallbackQuery):
    test_id = callback.data.split("_")[-1]
    user_id = callback.from_user.id
    delete_global_test(test_id)
    delete_user_test_id(user_id, test_id)
    await callback.answer(t(user_id, "test_deleted_alert"), show_alert=True)
    await callback.message.edit_text(t(user_id, "test_deleted_text"))

@dp.callback_query(F.data.startswith("group_"))
async def show_group_info(callback: CallbackQuery):
    parts = callback.data.split("_")
    test_id = parts[1]
    start = int(parts[2])
    end = int(parts[3])
    user_id = callback.from_user.id
    test = load_global_test(test_id)
    if not test:
        return await callback.answer(t(user_id, "test_not_found"), show_alert=True)

    text = t(user_id, "group_info").format(
        start=start + 1,
        end=end,
        name=test["name"],
        count=end - start,
        time=test.get("time", 60)
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(user_id, "btn_start_test"), callback_data=f"begin_test_{test_id}_{start}_{end}")],
        [InlineKeyboardButton(text=t(user_id, "btn_share_short"), callback_data=f"share_{test_id}_{start}_{end}")],
        [InlineKeyboardButton(text=t(user_id, "btn_back"), callback_data=f"back_to_groups_{test_id}")]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("back_to_groups_"))
async def back_to_groups(callback: CallbackQuery):
    test_id = callback.data.split("_")[-1]
    test = load_global_test(test_id)
    if not test:
        await callback.answer(t(callback.from_user.id, "test_list_not_found"), show_alert=True)
        return
    ready_tests = load_ready_tests()
    is_ready = test_id in ready_tests
    await show_test_groups(callback.message, test, test_id, callback.from_user.id, page=0, is_ready_test=is_ready)
    await callback.answer()

@dp.callback_query(F.data == "back_to_my_tests")
async def back_to_my_tests(callback: CallbackQuery):
    await show_my_tests(callback.message, callback.from_user.id)
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_rights_"))
async def admin_rights_menu(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    is_admin_user = is_admin(user_id) and user_id != SUPER_ADMIN_ID

    users = load_users()
    u = users.get(str(user_id), {})
    name = u.get("name", "Без имени")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t(callback.from_user.id, "unmake_admin" if is_admin_user else "make_admin"),
            callback_data=f"{'del_admin' if is_admin_user else 'mk_admin'}_{user_id}"
        )],
        [InlineKeyboardButton(text=t(callback.from_user.id, "back"), callback_data="back_to_admin_rights")]
    ])

    await callback.message.edit_text(
        f"👤 {name}\nID: {user_id}\n\n{'👮 Статус: Админ' if is_admin_user else '👤 Статус: Пользователь'}",
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    await callback.message.delete()
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(callback.from_user.id, "users")),
             KeyboardButton(text=t(callback.from_user.id, "search"))],
            [KeyboardButton(text=t(callback.from_user.id, "back"))]
        ],
        resize_keyboard=True
    )
    await callback.message.answer("🛠 Админ панель:", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("user_"))
async def user_menu(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    premium = is_premium(user_id)
    left = get_premium_time_left(user_id)
    text_status = "💎 Премиум" if premium else "❌ Нет премиума"
    if left:
        text_status += f"\n⏳ Осталось: {left}"

    admin_status = is_admin(user_id) and user_id != SUPER_ADMIN_ID
    admin_btn = InlineKeyboardButton(
        text=t(callback.from_user.id, "unmake_admin" if admin_status else "make_admin"),
        callback_data=f"del_admin_{user_id}" if admin_status else f"mk_admin_{user_id}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 1 мес", callback_data=f"give_1_{user_id}")],
        [InlineKeyboardButton(text="⭐ 3 мес", callback_data=f"give_3_{user_id}")],
        [InlineKeyboardButton(text="⭐ 6 мес", callback_data=f"give_6_{user_id}")],
        [InlineKeyboardButton(text="❌ Убрать премиум", callback_data=f"remove_{user_id}")],
        [admin_btn],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_users")]
    ])

    await callback.message.edit_text(
        f"👤 Пользователь: {user_id}\n\n{text_status}",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("mk_admin_"))
async def make_admin_callback(callback: CallbackQuery):
    if callback.from_user.id != SUPER_ADMIN_ID:
        return await callback.answer(t(callback.from_user.id, "no_access"), show_alert=True)
    user_id = int(callback.data.split("_")[2])
    add_admin(user_id)

    users = load_users()
    target_name = users.get(str(user_id), {}).get("name", f"ID{user_id}")

    # Логируем выдачу админа
    log_admin_action(
        admin_id=callback.from_user.id,
        action="give_admin",
        target_user=str(user_id),
        details=f"Сделал администратором пользователя {target_name}"
    )

    await callback.answer(t(callback.from_user.id, "admin_added"), show_alert=True)


@dp.callback_query(F.data.startswith("del_admin_"))
async def del_admin_callback(callback: CallbackQuery):
    if callback.from_user.id != SUPER_ADMIN_ID:
        return await callback.answer(t(callback.from_user.id, "no_access"), show_alert=True)
    user_id = int(callback.data.split("_")[2])
    remove_admin(user_id)

    users = load_users()
    target_name = users.get(str(user_id), {}).get("name", f"ID{user_id}")

    # Логируем удаление админа
    log_admin_action(
        admin_id=callback.from_user.id,
        action="remove_admin",
        target_user=str(user_id),
        details=f"Снял права администратора у пользователя {target_name}"
    )

    await callback.answer(t(callback.from_user.id, "admin_removed"), show_alert=True)

@dp.callback_query(F.data == "back_to_users")
async def back_to_users(callback: CallbackQuery):
    await show_users_page(callback.message, callback.from_user.id, 0)
    await callback.answer()

async def show_users_page(target, user_id: int, page: int = 0):
    users = load_users()
    if not users:
        text = t(user_id, "no_users")
        # Всегда используем answer для Message, edit_text для CallbackQuery
        if hasattr(target, 'edit_text'):  # CallbackQuery
            await target.edit_text(text)
        else:  # Message
            await target.answer(text)
        return

    items_per_page = 10
    user_list = list(users.items())
    total = len(user_list)
    start = page * items_per_page
    current_users = user_list[start:start + items_per_page]

    buttons = []
    for uid, u in current_users:
        status = "💎" if is_premium(uid) else "❌"
        name = u.get("name", "Без имени")
        buttons.append([InlineKeyboardButton(
            text=f"{status} {name}",
            callback_data=f"user_{uid}"
        )])

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"users_page_{page - 1}"
            )
        )
    if start + items_per_page < total:
        nav.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"users_page_{page + 1}"
            )
        )
    if nav:
        buttons.append(nav)

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        if hasattr(target, 'edit_text'):  # CallbackQuery
            await target.edit_text(t(user_id, "users"), reply_markup=kb)
        else:  # Message
            await target.answer(t(user_id, "users"), reply_markup=kb)
    except:
        # Если нельзя отредактировать, отправим новое сообщение
        await target.answer(t(user_id, "users"), reply_markup=kb)

@dp.callback_query(F.data.startswith("users_page_"))
async def users_page_handler(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    await show_users_page(callback.message, callback.from_user.id, page)
    await callback.answer()

@dp.callback_query(F.data.startswith("share_"))
async def share_test(callback: CallbackQuery):
    parts = callback.data.split("_")
    test_id = parts[1]
    start = parts[2]
    end = parts[3]
    link = f"https://t.me/{(await bot.get_me()).username}?start={test_id}_{start}_{end}"
    await callback.message.answer(
        t(callback.from_user.id, "share_link").format(link=link)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("begin_test_"))
async def begin_test(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    test_id = parts[2]
    start = int(parts[3])
    end = int(parts[4])
    test = load_global_test(test_id)

    all_questions = test.get("questions", [])
    # ВАЖНО! Берём только вопросы в диапазоне start-end
    group_questions = all_questions[start:end]
    order = test.get("order", "normal")

    if order == "shuffle":
        group_questions = group_questions.copy()
        random.shuffle(group_questions)
    elif order == "questions":
        group_questions = group_questions.copy()
        random.shuffle(group_questions)
    elif order == "answers":
        group_questions = [
            {**q, "answers": (lambda a, c: (
                (lambda p: (
                    [ans for _, ans in p],
                    next(i for i, (old, _) in enumerate(p) if old == c)
                ))(list(enumerate(a)))
            ))(q["answers"], q["correct"])[0]}
            for q in group_questions
        ]

    test = {**test, "questions": group_questions}

    end = start + (end - start)  # оставляем диапазон тем же
    if not test:
        return await callback.answer(t(callback.from_user.id, "test_not_found"), show_alert=True)

    await state.update_data(
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id,
        test_id=test_id,
        test=test,
        q_index=start,
        start=start,
        end=end,
        score=0,
        wrong=0,
        start_time=time.time(),
        inactive_count=0,
        paused=False
    )

    await callback.answer()
    await start_countdown(callback.message.chat.id, callback.from_user.id)
    await send_question(state)

# ====================== НОВЫЕ CALLBACK ХЕНДЛЕРЫ (2.8) ======================

@dp.callback_query(F.data.startswith("groups_page_"))
async def groups_page_handler(callback: CallbackQuery):
    parts = callback.data.split("_")
    test_id = parts[2]
    page = int(parts[3])
    test = load_global_test(test_id)
    if not test:
        return await callback.answer(t(callback.from_user.id, "test_not_found"), show_alert=True)

    # Определяем, готовый ли это тест
    ready_tests = load_ready_tests()
    is_ready = test_id in ready_tests

    await show_test_groups(callback.message, test, test_id, callback.from_user.id, page, is_ready_test=is_ready)
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_test_"))
async def edit_test_menu(callback: CallbackQuery):
    test_id = callback.data.split("_")[2]
    test = load_global_test(test_id)
    if not test:
        return await callback.answer(t(callback.from_user.id, "test_not_found"), show_alert=True)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(callback.from_user.id, "change_name"), callback_data=f"edit_name_{test_id}")],
        [InlineKeyboardButton(text=t(callback.from_user.id, "change_timer"), callback_data=f"edit_time_{test_id}")],
        [InlineKeyboardButton(text=t(callback.from_user.id, "change_order"), callback_data=f"edit_order_{test_id}")],
        [InlineKeyboardButton(text=t(callback.from_user.id, "btn_back"), callback_data=f"back_to_groups_{test_id}")]
    ])
    await callback.message.edit_text(f"✏️ Редактирование теста:\n{test.get('name', 'Без названия')}", reply_markup=kb)

@dp.callback_query(F.data.startswith("edit_name_"))
async def edit_name_handler(callback: CallbackQuery, state: FSMContext):
    test_id = callback.data.split("_")[2]
    await state.update_data(test_id=test_id)
    await callback.message.answer(t(callback.from_user.id, "enter_new_name"))
    await state.set_state(EditTest.name)
    await callback.answer()


@dp.message(EditTest.name)
async def process_new_name(message: Message, state: FSMContext):
    data = await state.get_data()
    test_id = data.get("test_id")

    if os.path.exists("global_tests.json"):
        with open("global_tests.json", "r", encoding="utf-8") as f:
            all_tests = json.load(f)

        if test_id in all_tests:
            all_tests[test_id]["name"] = message.text
            with open("global_tests.json", "w", encoding="utf-8") as f:
                json.dump(all_tests, f, ensure_ascii=False, indent=4)
            await message.answer("✅ Название теста успешно изменено!")
        else:
            await message.answer(t(message.from_user.id, "test_not_found"))
    else:
        await message.answer(t(message.from_user.id, "test_not_found"))

    await state.clear()

@dp.callback_query(F.data.startswith("edit_time_"))
async def edit_time_handler(callback: CallbackQuery, state: FSMContext):
    test_id = callback.data.split("_")[2]
    await state.update_data(test_id=test_id)
    await callback.message.answer(t(callback.from_user.id, "enter_time"))
    await state.set_state(EditTest.time)
    await callback.answer()


@dp.message(EditTest.time)
async def process_new_time(message: Message, state: FSMContext):
    if not message.text.isdigit() or not (10 <= int(message.text) <= 300):
        return await message.answer(t(message.from_user.id, "enter_time"))

    data = await state.get_data()
    test_id = data.get("test_id")

    if os.path.exists("global_tests.json"):
        with open("global_tests.json", "r", encoding="utf-8") as f:
            all_tests = json.load(f)

        if test_id in all_tests:
            all_tests[test_id]["time"] = int(message.text)
            with open("global_tests.json", "w", encoding="utf-8") as f:
                json.dump(all_tests, f, ensure_ascii=False, indent=4)
            await message.answer("✅ Таймер успешно изменён!")
        else:
            await message.answer(t(message.from_user.id, "test_not_found"))
    else:
        await message.answer(t(message.from_user.id, "test_not_found"))

    await state.clear()

@dp.callback_query(F.data.startswith("edit_order_"))
async def edit_order_handler(callback: CallbackQuery):
    test_id = callback.data.split("_")[2]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(callback.from_user.id, "shuffle_all"), callback_data=f"order_shuffle_{test_id}")],
        [InlineKeyboardButton(text=t(callback.from_user.id, "by_order"), callback_data=f"order_normal_{test_id}")],
        [InlineKeyboardButton(text=t(callback.from_user.id, "only_questions"), callback_data=f"order_questions_{test_id}")],
        [InlineKeyboardButton(text=t(callback.from_user.id, "only_answers"), callback_data=f"order_answers_{test_id}")],
        [InlineKeyboardButton(text=t(callback.from_user.id, "btn_back"), callback_data=f"edit_test_{test_id}")]
    ])
    await callback.message.edit_text("Выберите новый порядок вопросов:", reply_markup=kb)

@dp.callback_query(F.data.startswith("order_shuffle_") | F.data.startswith("order_normal_") |
                   F.data.startswith("order_questions_") | F.data.startswith("order_answers_"))
async def apply_order_handler(callback: CallbackQuery):
    parts = callback.data.split("_")
    order_type = parts[1]   # shuffle / normal / questions / answers
    test_id = parts[2]

    if os.path.exists("global_tests.json"):
        with open("global_tests.json", "r", encoding="utf-8") as f:
            all_tests = json.load(f)

        if test_id in all_tests:
            all_tests[test_id]["order"] = order_type
            with open("global_tests.json", "w", encoding="utf-8") as f:
                json.dump(all_tests, f, ensure_ascii=False, indent=4)
            await callback.answer("✅ Порядок изменён!", show_alert=True)
        else:
            await callback.answer(t(callback.from_user.id, "test_not_found"), show_alert=True)
    else:
        await callback.answer(t(callback.from_user.id, "test_not_found"), show_alert=True)


@dp.callback_query(F.data.startswith("toggle_ready_"))
async def toggle_ready_callback(callback: CallbackQuery):
    if callback.from_user.id != SUPER_ADMIN_ID:
        return await callback.answer(t(callback.from_user.id, "no_access"), show_alert=True)

    test_id = callback.data.split("_")[2]
    ready_tests = load_ready_tests()

    if test_id in ready_tests:
        remove_from_ready_tests(test_id)
        await callback.answer(t(callback.from_user.id, "test_removed_from_ready"), show_alert=True)
    else:
        add_to_ready_tests(test_id, callback.from_user.id)
        await callback.answer(t(callback.from_user.id, "test_added_to_ready"), show_alert=True)

    test = load_global_test(test_id)
    if test:
        await show_test_groups(callback.message, test, test_id, callback.from_user.id, page=0, is_ready_test=False)


@dp.callback_query(F.data.startswith("send_to_group_") | F.data.startswith("send_group_"))
async def send_to_group_callback(callback: CallbackQuery, state: FSMContext):
    if callback.data.startswith("send_to_group_"):
        test_id = callback.data.split("_")[3]
    else:
        test_id = callback.data.split("_")[2]

    test = load_global_test(test_id)
    if not test:
        return await callback.answer(t(callback.from_user.id, "test_not_found"), show_alert=True)

    await state.update_data(send_test_id=test_id)
    await callback.message.answer(t(callback.from_user.id, "enter_group_id"))
    await state.set_state(SendToGroup.group_id)
    await callback.answer()


@dp.message(SendToGroup.group_id)
async def process_group_id(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    test_id = data.get("send_test_id")
    test = load_global_test(test_id)

    if not test:
        await message.answer(t(user_id, "test_not_found"))
        await state.clear()
        return

    group_input = message.text.strip()
    questions = test.get("questions", [])
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={test_id}_0_{len(questions)}"

    try:
        await bot.send_message(
            chat_id=group_input,
            text=f"📚 <b>{test['name']}</b>\n\n"
                 f"✏️ {len(questions)} вопросов\n"
                 f"⏱️ {test.get('time', 60)} сек на вопрос\n\n"
                 f"🔗 Начать тест: {link}",
            parse_mode="HTML"
        )
        await message.answer(t(user_id, "sent_to_group"), reply_markup=get_menu(user_id))
    except Exception:
        await message.answer(t(user_id, "group_error"), reply_markup=get_menu(user_id))

    await state.clear()
# ====================== ОБРАБОТЧИК ОТВЕТОВ ======================

@dp.poll_answer()
async def poll_answer_handler(poll_answer: PollAnswer):
    poll_id = poll_answer.poll_id
    user_id = poll_answer.user.id

    if poll_id not in poll_owners:
        return

    owner_id = poll_owners[poll_id]
    if user_id != owner_id:
        return

    state = get_fsm_context(owner_id)
    data = await state.get_data()

    task = data.get("timeout_task")
    if task:
        task.cancel()

    if data.get("current_poll_id") != poll_id:
        return

    chosen = poll_answer.option_ids[0] if poll_answer.option_ids else None
    correct = data.get("correct")

    score = data.get("score", 0)
    wrong = data.get("wrong", 0)
    q_index = data.get("q_index", 0)

    if chosen is not None and chosen == correct:
        score += 1
    else:
        wrong += 1

    await state.update_data(
        score=score,
        wrong=wrong,
        q_index=q_index + 1,
        inactive_count=0
    )

    poll_owners.pop(poll_id, None)
    await asyncio.sleep(0.5)
    await send_question(state)

# ====================== ОЧИСТКА ФАЙЛОВ ======================

async def clean_files():
    while True:
        await asyncio.sleep(604800)
        if not os.path.exists("files"):
            continue
        for user_folder in os.listdir("files"):
            folder_path = os.path.join("files", user_folder)
            if os.path.isdir(folder_path):
                for file in os.listdir(folder_path):
                    try:
                        os.remove(os.path.join(folder_path, file))
                    except:
                        pass

# ====================== КОМАНДЫ БОТА ======================

async def set_commands():
    commands = [
        BotCommand(command="start", description="🏠 Main menu / Главное меню / Asosiy menyu"),
        BotCommand(command="newquiz", description="create a new quiz"),
        BotCommand(command="quizzes", description="show your quizzes"),
        BotCommand(command="lang", description="change language"),
        BotCommand(command="stop", description="stop the active quiz"),
        BotCommand(command="help", description="about this bot"),
    ]
    await bot.set_my_commands(commands)

# ====================== ЗАПУСК ======================

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands()
    asyncio.create_task(clean_files())
    await dp.start_polling(bot)

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен...")
    asyncio.run(main())