import asyncio
import random
import os
import json
import time
import re
from functools import lru_cache
from threading import Lock

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
from database import (
    init_db,
    db_save_user, db_load_users, db_get_user_lang, db_set_user_lang, db_find_user,
    db_load_admins, db_add_admin, db_remove_admin,
    db_add_premium, db_remove_premium, db_is_premium, db_get_premium_time_left,
    db_load_premium_users, db_clear_premium,
    db_add_premium_plus, db_remove_premium_plus, db_is_premium_plus,
    db_clear_premium_plus, db_load_premium_plus_users,
    db_save_global_test, db_load_global_test, db_load_global_tests,
    db_delete_global_test, db_update_test_field,
    db_save_user_test_id, db_load_user_test_ids, db_delete_user_test_id,
    db_load_ready_tests, db_add_to_ready_tests, db_remove_from_ready_tests,
    db_log_admin_action, db_get_admin_logs, db_clear_admin_logs,
    db_save_test_result, db_get_leaderboard,
)

LANG_FILE = "lang.json"



SUPER_ADMIN_ID = 7760002425


# ====================== КЭШ ======================
# Все кэши хранятся в памяти, сбрасываются при изменении данных

_cache: dict = {}
_cache_lock = Lock()

def _get_cache(key: str):
    return _cache.get(key)

def _set_cache(key: str, value):
    _cache[key] = value

def _del_cache(*keys):
    for k in keys:
        _cache.pop(k, None)

# ====================== JSON УТИЛИТЫ ======================



# ====================== ЯЗЫК ======================

def load_lang():
    with open(LANG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

LANG = load_lang()
def t(user_id: int, key: str, **kwargs) -> str:
    """Получить перевод по ключу"""
    lang = get_user_lang(user_id)
    # Если языка нет — fallback на русский
    texts = LANG.get(lang, LANG.get("ru", {}))
    text = texts.get(key, f"[{key}]")   # если ключа нет — покажет [ключ]
    if kwargs:
        try:
            text = text.format(**kwargs)
        except:
            pass
    return text

def save_user(user):
    """Сохранить пользователя в БД"""
    db_save_user(user)


def find_user(query):
    """Найти пользователя по имени/username/ID"""
    user_id, user_dict = db_find_user(query)
    if user_id:
        return user_id, user_dict
    return None, None


def get_user_lang(user_id: int) -> str:
    """Получить язык пользователя"""
    return db_get_user_lang(user_id)


def is_admin(user_id: int) -> bool:
    """Проверить админ ли пользователь"""
    if user_id == SUPER_ADMIN_ID:
        return True
    return user_id in db_load_admins()


def add_admin(user_id: int):
    """Сделать админом"""
    db_add_admin(user_id)


def remove_admin(user_id: int):
    """Убрать админа"""
    if user_id != SUPER_ADMIN_ID:
        db_remove_admin(user_id)


def add_premium(user_id, days: int):
    """Выдать премиум"""
    db_add_premium(user_id, days)


def remove_premium(user_id):
    """Удалить премиум"""
    db_remove_premium(user_id)


def is_premium(user_id) -> bool:
    """Проверить есть ли премиум"""
    return db_is_premium(user_id)


def get_premium_time_left(user_id) -> str | None:
    """Получить оставшееся время премиума"""
    return db_get_premium_time_left(user_id)


def load_premium_users() -> dict:
    """Загрузить всех премиум пользователей"""
    return db_load_premium_users()


def save_premium_users(data: dict):
    """Полностью заменить премиум пользователей"""
    db_clear_premium()
    for user_id, expire in data.items():
        db_add_premium(int(user_id), 0)


def add_premium_plus(user_id, days: int):
    """Выдать премиум+"""
    db_add_premium_plus(user_id, days)


def remove_premium_plus(user_id):
    """Удалить премиум+"""
    db_remove_premium_plus(user_id)


def is_premium_plus(user_id) -> bool:
    """Проверить премиум+"""
    return db_is_premium_plus(user_id)


def can_bypass_limits(user_id) -> bool:
    """Может ли админ обойти лимиты"""
    return is_admin(user_id)


def load_users() -> dict:
    """Загрузить всех пользователей"""
    users = db_load_users()
    return {str(uid): u for uid, u in users.items()}


def save_global_test(test_data: dict) -> str:
    """Сохранить новый тест"""
    return db_save_global_test(test_data, owner_id=None)


def load_global_test(test_id: str) -> dict | None:
    """Загрузить тест по ID"""
    return db_load_global_test(test_id)


def load_global_tests() -> dict:
    """Загрузить все тесты"""
    return db_load_global_tests()


def delete_global_test(test_id: str):
    """Удалить тест"""
    db_delete_global_test(test_id)


def save_user_test_id(user_id, test_id: str):
    """Сохранить тест юзеру"""
    db_save_user_test_id(user_id, test_id)


def load_user_test_ids(user_id) -> list:
    """Загрузить тесты юзера"""
    return db_load_user_test_ids(user_id)


def delete_user_test_id(user_id, test_id: str):
    """Удалить тест у юзера"""
    db_delete_user_test_id(user_id, test_id)


def load_ready_tests() -> dict:
    """Загрузить готовые тесты"""
    return db_load_ready_tests()


def add_to_ready_tests(test_id: str, admin_id: int) -> bool:
    """Добавить в готовые тесты"""
    return db_add_to_ready_tests(test_id, admin_id)


def remove_from_ready_tests(test_id: str) -> bool:
    """Убрать из готовых тестов"""
    return db_remove_from_ready_tests(test_id)


def log_admin_action(admin_id: int, action: str, target_user, details: str):
    """Логировать действие админа"""
    users = load_users()
    admin_name = users.get(str(admin_id), {}).get("name", f"ID{admin_id}")
    db_log_admin_action(admin_id, admin_name, action, target_user, details)


def get_admin_logs(limit=50) -> list:
    """Получить логи админов"""
    return db_get_admin_logs(limit)


def clear_admin_logs():
    """Очистить логи"""
    db_clear_admin_logs()


def save_test_result(test_id, group_key, user_id, score, total, time_spent):
    """Сохранить результат теста"""
    users = load_users()
    username = users.get(str(user_id), {}).get("username", f"ID{user_id}")
    db_save_test_result(test_id, group_key, user_id, username, score, total, time_spent)


def get_leaderboard(test_id, group_key, limit=10) -> list:
    """Получить лидерборд"""
    return db_get_leaderboard(test_id, group_key, limit)

def save_global_tests(tests: dict):
    """Сохранить изменения во всех глобальных тестах (используется при редактировании)"""
    for test_id, test_data in tests.items():
        db_update_test_field(test_id, "name", test_data.get("name"))
        db_update_test_field(test_id, "time", test_data.get("time"))
        db_update_test_field(test_id, "order_type", test_data.get("order", "normal"))
    _del_cache("global_tests")  # очищаем кэш


def load_premium_plus() -> dict:
    """Загрузить всех Premium+ пользователей"""
    return db_load_premium_plus_users()


def save_premium_plus(data: dict):
    """Полностью заменить Premium+ пользователей"""
    db_clear_premium_plus()
    for user_id, expire in data.items():
        db_add_premium_plus(int(user_id), 0)  # expire уже установлен в БД

# ====================== ВСПОМОГАТЕЛЬНЫЕ ======================

def read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def read_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)

def safe_trim(text: str, limit=100) -> str:
    return text if len(text) <= limit else text[:limit - 3] + "..."

def parse_text(content: str, answer_mode: str) -> list:
    questions = []
    for block in re.split(r"\n*\+{3,}\n*", content):
        block = block.strip()
        if not block:
            continue
        parts = re.split(r"\n*={3,}\n*", block)
        if len(parts) < 2:
            continue
        q_text = re.sub(r"^\d+[\.\)\:\-]\s*", "", parts[0].strip()).strip()
        if not q_text:
            continue
        answers = []
        correct_index = None
        for ans in parts[1:]:
            clean = re.sub(r"^\d+[\.\)\:\-]\s*", "", ans.strip()).strip()
            if not clean:
                continue
            if answer_mode == "2" and clean.lstrip().startswith("#"):
                clean = clean.lstrip()[1:].strip()
                correct_index = len(answers)
            answers.append(clean)
        if answer_mode == "1" and answers:
            correct_index = 0
        if correct_index is None or len(answers) < 2:
            continue
        questions.append({"question": q_text, "answers": answers, "correct": correct_index})
    return questions

def get_q_word(user_id: int, answered: int) -> str:
    lang = get_user_lang(user_id)
    if lang == "ru":
        if answered % 10 == 1 and answered % 100 != 11:
            return t(user_id, "q_word_1")
        elif answered % 10 in (2, 3, 4) and answered % 100 not in (12, 13, 14):
            return t(user_id, "q_word_2")
        else:
            return t(user_id, "q_word_5")
    return t(user_id, "q_word_5")

def get_fsm_context(user_id: int):
    return FSMContext(storage=dp.storage, key=StorageKey(chat_id=user_id, user_id=user_id, bot_id=bot.id))

# ====================== БОТ ======================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
poll_owners: dict = {}

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

class BroadcastMessage(StatesGroup):
    message = State()
    confirm = State()

def get_menu(user_id: int) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=t(user_id, "new_test"))],
        [KeyboardButton(text=t(user_id, "ready_tests"))],
        [KeyboardButton(text=t(user_id, "my_tests"))],
        [KeyboardButton(text=t(user_id, "premium"))]
    ]
    if is_admin(user_id):
        keyboard.append([KeyboardButton(text=t(user_id, "admin"))])
    if user_id == SUPER_ADMIN_ID:
        keyboard.append([KeyboardButton(text="📢 Рассылка")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# ====================== ФИЛЬТР КНОПОК МЕНЮ ======================

class IsMenuButton(Filter):
    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        if message.text == "📢 Рассылка":
            return True
        menu_keys = [
            "new_test", "premium", "my_tests", "admin", "back", "users",
            "search", "premium_active", "give_all_premium", "remove_premium_all",
            "give_all_premium_plus", "remove_premium_plus_all"
        ]
        txt = message.text
        return any(txt == LANG[lang].get(key) for lang in LANG for key in menu_keys)

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

@dp.message(Command("newquiz"))
async def newquiz_command(message: Message, state: FSMContext):
    await new_test(message, state)

@dp.message(Command("add_premium"))
async def give_premium_cmd(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return await message.answer(t(message.from_user.id, "no_access"))
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        days = int(parts[2]) if len(parts) > 2 else 30
        add_premium(user_id, days)
        await message.answer(f"✅ Пользователь {user_id} получил премиум на {days} дней")
    except Exception:
        await message.answer("Используй: /add_premium USER_ID [DAYS]")

@dp.message(Command("remove_premium"))
async def remove_premium_cmd(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return await message.answer(t(message.from_user.id, "no_access"))
    try:
        remove_premium(int(message.text.split()[1]))
        await message.answer("❌ Премиум удалён")
    except Exception:
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
            await message.answer("⚠️ Тест уже в Готовых тестах")
    except Exception:
        await message.answer("Используй: /addlist TEST_ID")

@dp.message(Command("removelist"))
async def removelist_command(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return await message.answer(t(message.from_user.id, "no_access"))
    try:
        test_id = message.text.split()[1]
        msg = "✅ Удалён" if remove_from_ready_tests(test_id) else "⚠️ Не найден"
        await message.answer(msg)
    except Exception:
        await message.answer("Используй: /removelist TEST_ID")

# ====================== ПЕРЕХВАТ МЕНЮ В ЛЮБОМ СОСТОЯНИИ ======================

@dp.message(IsMenuButton(), ~StateFilter(None))
async def any_state_menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await main_text_handler(message, state)

# ====================== ГЛАВНЫЙ ТЕКСТОВЫЙ ХЕНДЛЕР ======================

@dp.message(F.text, StateFilter(None))
async def main_text_handler(message: Message, state: FSMContext):
    text = message.text
    user_id = message.from_user.id

    if text == "📢 Рассылка" and user_id == SUPER_ADMIN_ID:
        await message.answer(
            "📢 Введите сообщение для рассылки.\n\nПоддерживается текст, фото, видео, документ.\nДля отмены: /stop",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="❌ Отмена")]],
                resize_keyboard=True
            )
        )
        await state.set_state(BroadcastMessage.message)
        return

    if text == t(user_id, "new_test"):
        await new_test(message, state)
        return

    if text == t(user_id, "my_tests"):
        await show_my_tests(message, user_id)
        return

    if text == t(user_id, "ready_tests"):
        await show_ready_tests(message, user_id)
        return

    if text == t(user_id, "premium"):
        if is_premium_plus(user_id):
            status = "💎+ Премиум+ активна"
        elif is_premium(user_id):
            status = "💎 Премиум активна"
        else:
            status = "❌ Подписка отсутствует"
        left = get_premium_time_left(user_id)
        if left:
            status += f"\n⏳ Осталось: {left}"
        await message.answer(t(user_id, "buy_premium").format(status=status))
        return

    if text == t(user_id, "admin"):
        if not is_admin(user_id):
            return await message.answer(t(user_id, "no_access"))
        kb_buttons = [
            [KeyboardButton(text=t(user_id, "users")), KeyboardButton(text=t(user_id, "search"))],
            [KeyboardButton(text=t(user_id, "premium_active"))],
        ]
        if user_id == SUPER_ADMIN_ID:
            kb_buttons.append([KeyboardButton(text=t(user_id, "admin_history"))])
        kb_buttons.append([KeyboardButton(text=t(user_id, "back"))])
        await message.answer("🛠 Админ панель:", reply_markup=ReplyKeyboardMarkup(keyboard=kb_buttons, resize_keyboard=True))
        return

    if not is_admin(user_id):
        return

    # --- Админ-кнопки ---
    if text == t(user_id, "users"):
        await show_users_for_admin_management(message, user_id, 0)

    elif text == t(user_id, "search"):
        await message.answer(t(user_id, "enter_query"))
        await state.set_state(AdminSearch.query)

    elif text == t(user_id, "premium_active"):
        data = load_premium_users()
        users_data = load_users()
        lines = []
        now = time.time()
        for uid, expire in data.items():
            left = int(expire - now)
            if left > 0:
                name = users_data.get(uid, {}).get("name", f"ID{uid}")
                lines.append(f"• {name} ({uid}) — {left // 86400} дн.")
        msg = "💎 Активные Premium подписки:\n\n" + "\n".join(lines) if lines else "Нет активных премиум пользователей"
        kb = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text=t(user_id, "give_all_premium")), KeyboardButton(text=t(user_id, "remove_premium_all"))],
            [KeyboardButton(text=t(user_id, "give_all_premium_plus")), KeyboardButton(text=t(user_id, "remove_premium_plus_all"))],
            [KeyboardButton(text=t(user_id, "back"))]
        ], resize_keyboard=True)
        await message.answer(msg, reply_markup=kb)

    elif text == t(user_id, "give_all_premium"):
        users_all = load_users()
        for uid in users_all:
            add_premium(int(uid), 30)
        log_admin_action(user_id, "give_premium_all", "all_users", f"Выдал Premium всем {len(users_all)} на 30 дней")
        await message.answer(t(user_id, "all_premium_given"))

    elif text == t(user_id, "remove_premium_all"):
        pdata = load_premium_users()
        count = len(pdata)
        pdata.clear()
        save_premium_users(pdata)
        log_admin_action(user_id, "remove_premium_all", "all_users", f"Удалил Premium у {count} пользователей")
        await message.answer("✅ Все Premium подписки удалены")

    elif text == t(user_id, "give_all_premium_plus"):
        users_all = load_users()
        for uid in users_all:
            add_premium_plus(int(uid), 30)
        log_admin_action(user_id, "give_premium_plus_all", "all_users", "Выдал Premium+ всем (30 дней)")
        await message.answer(t(user_id, "all_premium_plus_given"))


    elif text == t(user_id, "remove_premium_plus_all"):

        pdata = load_premium_plus()

        count = len(pdata)

        save_premium_plus({})  # очищаем через нашу новую функцию

        log_admin_action(user_id, "remove_premium_plus_all", "all_users", f"Удалил Premium+ у {count} пользователей")

        await message.answer("✅ Все Premium+ подписки удалены")

    elif text == t(user_id, "admin_history"):
        await show_admin_logs(message, user_id, 0)

    elif text == t(user_id, "back"):
        await message.answer(t(user_id, "welcome"), reply_markup=get_menu(user_id))

# ====================== ПОИСК ======================

@dp.message(AdminSearch.query)
async def admin_search_handler(message: Message, state: FSMContext):
    user_id_found, user_data = find_user(message.text)
    await state.clear()
    if not user_id_found:
        return await message.answer(t(message.from_user.id, "user_not_found"))
    premium = is_premium(user_id_found)
    left = get_premium_time_left(user_id_found)
    status = "💎 Премиум" if premium else "❌ Нет премиума"
    if left:
        status += f"\n⏳ Осталось: {left}"
    name = user_data.get("name", "Без имени")
    username = user_data.get("username", "")
    username_str = f"@{username}" if username else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 1 мес", callback_data=f"give_1_{user_id_found}")],
        [InlineKeyboardButton(text="⭐ 3 мес", callback_data=f"give_3_{user_id_found}")],
        [InlineKeyboardButton(text="⭐ 6 мес", callback_data=f"give_6_{user_id_found}")],
        [InlineKeyboardButton(text="❌ Убрать премиум", callback_data=f"remove_{user_id_found}")],
    ])
    await message.answer(f"👤 {name} {username_str}\nID: {user_id_found}\n\n{status}", reply_markup=kb)

# ====================== СОЗДАНИЕ ТЕСТА ======================

async def new_test(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not can_bypass_limits(user_id) and not is_premium(user_id) and len(load_user_test_ids(user_id)) >= 2:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Перейти в Premium", callback_data="premium")]
        ])
        return await message.answer(t(user_id, "premium_ended"), reply_markup=kb)
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
        return await message.answer(t(message.from_user.id, "file_error"))
    file = await bot.get_file(doc.file_id)
    user_folder = f"files/{message.from_user.id}"
    os.makedirs(user_folder, exist_ok=True)
    path = f"{user_folder}/{doc.file_name}"
    await bot.download_file(file.file_path, path)
    text = read_txt(path) if doc.file_name.endswith(".txt") else read_docx(path)
    data = await state.get_data()
    questions = parse_text(text, data.get("answer_mode"))
    if not questions:
        return await message.answer(t(message.from_user.id, "parse_error"))
    await state.update_data(questions=questions)
    await message.answer(t(message.from_user.id, "enter_time"))
    await state.set_state(CreateTest.time)

@dp.message(CreateTest.time)
async def set_time(message: Message, state: FSMContext):
    if not message.text.isdigit() or not (10 <= int(message.text) <= 300):
        return await message.answer(t(message.from_user.id, "enter_time"))
    await state.update_data(time=int(message.text))
    await message.answer(t(message.from_user.id, "enter_split"))
    await state.set_state(CreateTest.split)

@dp.message(CreateTest.split)
async def split_handler(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer(t(message.from_user.id, "enter_number"))
    data = await state.get_data()
    test_id = save_global_test({
        "name": data.get("name"),
        "questions": data.get("questions"),
        "split": int(message.text),
        "time": data.get("time", 60)
    })
    save_user_test_id(message.from_user.id, test_id)
    await message.answer(
        t(message.from_user.id, "test_created_full").format(name=data.get("name", "")),
        reply_markup=get_menu(message.from_user.id)
    )
    await state.clear()

# ====================== МОИ ТЕСТЫ ======================

async def show_my_tests(message: Message, user_id: int):
    test_ids = load_user_test_ids(user_id)
    if not test_ids:
        return await message.answer(t(user_id, "you_havent_test"), reply_markup=get_menu(user_id))
    buttons = []
    for tid in test_ids:
        test_data = load_global_test(tid)
        if test_data:
            buttons.append([InlineKeyboardButton(text=test_data['name'], callback_data=f"start_test_{tid}")])
    if not buttons:
        return await message.answer(t(user_id, "you_havent_test"), reply_markup=get_menu(user_id))
    await message.answer(t(user_id, "your_tests"), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

async def show_ready_tests(message: Message, user_id: int):
    if not is_premium_plus(user_id) and user_id != SUPER_ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Перейти в Premium", callback_data="premium")]
        ])
        return await message.answer(t(user_id, "premium_required_ready"), reply_markup=kb)
    ready = load_ready_tests()
    if not ready:
        return await message.answer(t(user_id, "no_ready_tests"), reply_markup=get_menu(user_id))
    buttons = []
    for tid in ready:
        test_data = load_global_test(tid)
        if test_data:
            buttons.append([InlineKeyboardButton(
                text=f"{test_data['name']} ({len(test_data['questions'])} вопросов)",
                callback_data=f"start_ready_test_{tid}"
            )])
    if not buttons:
        return await message.answer(t(user_id, "no_ready_tests"), reply_markup=get_menu(user_id))
    await message.answer(t(user_id, "ready_tests_list"), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


async def show_users_for_admin_management(message: Message, admin_id: int, page: int = 0):
    users = load_users()
    if not users:
        return await message.answer(t(admin_id, "no_users"), reply_markup=get_menu(admin_id))

    items_per_page = 10  # ← ИЗМЕНЕНО НА 10
    user_list = list(users.items())
    total = len(user_list)
    start = page * items_per_page
    current_users = user_list[start:start + items_per_page]

    buttons = []
    for uid, u in current_users:
        is_adm = is_admin(int(uid)) and int(uid) != SUPER_ADMIN_ID
        has_prem = is_premium(int(uid))
        if is_adm:
            status = "👮💎" if has_prem else "👮"
        else:
            status = "💎" if has_prem else "👤"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {safe_trim(u.get('name', 'Без имени'), 18)} (ID: {uid})",
            callback_data=f"manage_user_{uid}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"users_manage_page_{page - 1}"))
    if start + items_per_page < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"users_manage_page_{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text=t(admin_id, "back"), callback_data="back_to_admin")])

    await message.answer(
        f"👥 Пользователи ({start + 1}-{min(start + items_per_page, total)} из {total})",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

async def show_test_groups(message: Message, test: dict, test_id: str, user_id: int, page: int = 0, is_ready_test: bool = False):
    questions = test.get("questions", [])
    split = test.get("split", 30)
    groups = list(range(0, len(questions), split))
    items_per_page = 5
    start_idx = page * items_per_page
    current_groups = groups[start_idx:start_idx + items_per_page]
    buttons = []
    for s in current_groups:
        e = min(s + split, len(questions))
        buttons.append([InlineKeyboardButton(text=f"{s + 1}-{e}", callback_data=f"group_{test_id}_{s}_{e}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"groups_page_{test_id}_{page - 1}"))
    if start_idx + items_per_page < len(groups):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"groups_page_{test_id}_{page + 1}"))
    if nav:
        buttons.append(nav)
    if not is_ready_test:
        bottom = [
            InlineKeyboardButton(text=t(user_id, "btn_send_group"), callback_data=f"send_group_{test_id}"),
            InlineKeyboardButton(text=t(user_id, "edit_test"), callback_data=f"edit_test_{test_id}")
        ]
        if user_id == SUPER_ADMIN_ID:
            ready_tests = load_ready_tests()
            if test_id in ready_tests:
                bottom.append(InlineKeyboardButton(text=t(user_id, "remove_from_ready"), callback_data=f"toggle_ready_{test_id}"))
            else:
                bottom.append(InlineKeyboardButton(text=t(user_id, "add_to_ready"), callback_data=f"toggle_ready_{test_id}"))
        buttons.append(bottom)
        buttons.append([
            InlineKeyboardButton(text=t(user_id, "btn_delete_test"), callback_data=f"delete_test_{test_id}"),
            InlineKeyboardButton(text=t(user_id, "btn_back"), callback_data="back_to_my_tests")
        ])
    else:
        buttons.append([InlineKeyboardButton(text=t(user_id, "btn_back"), callback_data="back_to_ready_tests")])
    await message.edit_text(
        t(user_id, "choose_group").format(name=test.get("name", "Тест")),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

async def show_admin_logs(message, admin_id: int, page: int = 0, edit: bool = False):
    logs = get_admin_logs(limit=100)
    if not logs:
        return await message.answer(t(admin_id, "no_admin_logs"), reply_markup=get_menu(admin_id))
    items_per_page = 5
    total = len(logs)
    start = page * items_per_page
    current_logs = logs[start:start + items_per_page]
    action_names = {
        "give_premium": "📤 Выдал Premium",
        "remove_premium": "❌ Удалил Premium",
        "give_admin": "👮 Сделал админом",
        "remove_admin": "👮❌ Снял админа",
        "give_premium_all": "📤 Выдал Premium всем",
        "give_premium_plus_all": "📤 Выдал Premium+ всем",
        "remove_premium_all": "❌ Удалил Premium у всех",
        "broadcast": "📢 Рассылка",
        "clear_logs": "🗑 Очистил логи",
    }
    text = "📋 История действий администраторов:\n\n"
    for log in current_logs:
        action_ru = action_names.get(log.get("action", ""), log.get("action", ""))
        text += (
            f"🔹 {action_ru}\n"
            f"   👤 Админ: {log.get('admin_name', 'Unknown')}\n"
            f"   🎯 Пользователь: {log.get('target_user', '')}\n"
            f"   ⏰ {log.get('timestamp', '')[:16]}\n"
            f"   📝 {log.get('details', '')}\n\n"
        )
    buttons = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"adminlog_page_{page - 1}"))
    if start + items_per_page < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"adminlog_page_{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text=t(admin_id, "clear_logs"), callback_data="clear_admin_logs")])
    buttons.append([InlineKeyboardButton(text=t(admin_id, "back"), callback_data="back_to_admin")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)

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
    orig_start = data.get("orig_start", start)   # ← оригинальный старт для retry
    orig_end = data.get("orig_end", end)
    user_id = data.get("user_id")
    answered = score + wrong
    no_answer = end - start - answered
    time_spent = round(time.time() - data.get("start_time", time.time()), 1)
    test_id = data.get("test_id")
    q_word = get_q_word(user_id, answered)
    text = (
        t(user_id, "result_header").format(name=test.get("name", "")) + "\n\n" +
        t(user_id, "result_answered").format(answered=answered, q_word=q_word) + "\n" +
        t(user_id, "result_correct").format(score=score) + "\n" +
        t(user_id, "result_wrong").format(wrong=wrong) + "\n" +
        t(user_id, "result_no_answer").format(no_answer=no_answer) + "\n" +
        t(user_id, "result_time").format(time_spent=time_spent)
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(user_id, "btn_retry"),
                              callback_data=f"retry_test_{test_id}_{orig_start}_{orig_end}")],
        [InlineKeyboardButton(text=t(user_id, "btn_send_group"), callback_data=f"send_to_group_{test_id}")],
        [InlineKeyboardButton(text=t(user_id, "btn_share"), callback_data=f"share_{test_id}_{orig_start}_{orig_end}")]
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
    answers = [safe_trim(a.strip()) for a in q["answers"] if a.strip()][:10]
    correct_index = q["correct"]
    paired = list(enumerate(answers))
    random.shuffle(paired)
    shuffled = [ans for _, ans in paired]
    new_correct = next(i for i, (old, _) in enumerate(paired) if old == correct_index)

    question_text = f"[{q_index - start + 1}/{end - start}] {q['question']}"
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

    # Отменяем старый таймаут
    old_task = data.get("timeout_task")
    if old_task and not old_task.done():
        old_task.cancel()

    task = asyncio.create_task(check_inactive_timeout(state, poll.poll.id, time_limit))
    poll_owners[poll.poll.id] = data.get("user_id")
    await state.update_data(current_poll_id=poll.poll.id, correct=new_correct, answered=None, timeout_task=task)

async def check_inactive_timeout(state: FSMContext, poll_id: str, time_limit: int):
    await asyncio.sleep(time_limit + 5)
    data = await state.get_data()
    if data.get("current_poll_id") != poll_id:
        return
    chat_id = data.get("chat_id")
    user_id = data.get("user_id")
    test = data.get("test")
    if time_limit <= 25:
        inactive = data.get("inactive_count", 0) + 1
        await state.update_data(inactive_count=inactive)
        if inactive < 2:
            return
    else:
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
    await bot.send_message(chat_id, t(user_id, "test_paused").format(name=test.get("name", "")), reply_markup=kb)
    await state.update_data(paused=True)

# ====================== CALLBACK ХЕНДЛЕРЫ ======================

@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    db_set_user_lang(callback.from_user.id, lang)
    await callback.answer("✅ Язык обновлён")
    await callback.message.delete()
    await bot.send_message(
        callback.from_user.id,
        t(callback.from_user.id, "welcome"),
        reply_markup=get_menu(callback.from_user.id)
    )

@dp.callback_query(F.data == "back_to_ready_tests")
async def back_to_ready_tests_cb(callback: CallbackQuery):
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
    log_admin_action(callback.from_user.id, "clear_logs", "system", "Очистил историю")
    await callback.answer(t(callback.from_user.id, "logs_cleared"), show_alert=True)
    await show_admin_logs(callback.message, callback.from_user.id, 0, edit=True)

@dp.callback_query(F.data.startswith("manage_user_"))
async def manage_user_menu(callback: CallbackQuery):
    uid = int(callback.data.split("_")[2])
    admin_id = callback.from_user.id
    is_adm = is_admin(uid) and uid != SUPER_ADMIN_ID
    has_prem = is_premium(uid)
    left = get_premium_time_left(uid)
    users = load_users()
    name = users.get(str(uid), {}).get("name", "Без имени")
    status_text = ""
    if is_adm:
        status_text += "👮 Администратор\n"
    if has_prem:
        status_text += f"💎 Премиум — осталось: {left}\n"
    if not is_adm and not has_prem:
        status_text = "👤 Обычный пользователь"
    buttons = [
        [InlineKeyboardButton(text="💎 Premium 1м", callback_data=f"give_1_{uid}")],
        [InlineKeyboardButton(text="💎 Premium 3м", callback_data=f"give_3_{uid}")],
        [InlineKeyboardButton(text="💎 Premium 6м", callback_data=f"give_6_{uid}")],
        [InlineKeyboardButton(text="💎+ Premium+ 1м", callback_data=f"give_plus_1_{uid}")],
        [InlineKeyboardButton(text="💎+ Premium+ 3м", callback_data=f"give_plus_3_{uid}")],
        [InlineKeyboardButton(text="💎+ Premium+ 6м", callback_data=f"give_plus_6_{uid}")],
        [InlineKeyboardButton(text="❌ Убрать Premium", callback_data=f"remove_{uid}")],
    ]
    if admin_id == SUPER_ADMIN_ID:
        buttons.append([InlineKeyboardButton(
            text=t(admin_id, "unmake_admin" if is_adm else "make_admin"),
            callback_data=f"{'del_admin' if is_adm else 'mk_admin'}_{uid}"
        )])
    buttons.append([InlineKeyboardButton(text=t(admin_id, "btn_back"), callback_data="back_to_manage_users")])
    await callback.message.edit_text(
        f"👤 {name}\nID: {uid}\n\n{status_text}",
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
    log_admin_action(callback.from_user.id, "give_premium_all", "all_users", f"Выдал Premium всем {len(users)} на 30 дней")
    await callback.answer(t(callback.from_user.id, "all_premium_given"), show_alert=True)

@dp.callback_query(F.data == "remove_premium_all")
async def remove_premium_all_callback(callback: CallbackQuery):
    if callback.from_user.id != SUPER_ADMIN_ID:
        return await callback.answer(t(callback.from_user.id, "no_access"), show_alert=True)
    data = load_premium_users()
    count = len(data)
    data.clear()
    save_premium_users(data)
    log_admin_action(callback.from_user.id, "remove_premium_all", "all_users", f"Удалил Premium у {count}")
    await callback.answer("✅ Все премиум подписки удалены", show_alert=True)

@dp.callback_query(F.data == "give_premium_plus_all")
async def give_premium_plus_all_callback(callback: CallbackQuery):
    if callback.from_user.id != SUPER_ADMIN_ID:
        return await callback.answer(t(callback.from_user.id, "no_access"), show_alert=True)
    users = load_users()
    for uid in users:
        add_premium_plus(int(uid), 30)
    log_admin_action(callback.from_user.id, "give_premium_plus_all", "all_users", "Выдал Premium+ всем (30 дней)")
    await callback.answer(t(callback.from_user.id, "all_premium_plus_given"), show_alert=True)

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
    await callback.message.answer(t(callback.from_user.id, "test_stopped"), reply_markup=get_menu(callback.from_user.id))
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "premium")
async def premium_info(callback: CallbackQuery):
    user_id = callback.from_user.id
    if is_premium_plus(user_id):
        status = "💎+ Премиум+ активна"
    elif is_premium(user_id):
        status = "💎 Премиум активна"
    else:
        status = "❌ Подписка отсутствует"
    left = get_premium_time_left(user_id)
    if left:
        status += f"\n⏳ Осталось: {left}"
    await callback.message.answer(f"📊 Ваш статус:\n{status}\n\n" + t(user_id, "buy_premium").format(status=status))
    await callback.answer()

@dp.callback_query(F.data.regexp(r'^give_\d+_\d+$'))
async def give_premium_callback(callback: CallbackQuery):
    parts = callback.data.split("_")
    months, user_id = parts[1], int(parts[2])
    days = int(months) * 30
    add_premium(user_id, days)
    users = load_users()
    target_name = users.get(str(user_id), {}).get("name", f"ID{user_id}")
    log_admin_action(callback.from_user.id, "give_premium", str(user_id), f"Выдал Premium {months} мес. ({days} дн.) — {target_name}")
    await callback.answer(t(callback.from_user.id, "gived_premium"))

@dp.callback_query(F.data.startswith("give_plus_"))
async def give_premium_plus_callback(callback: CallbackQuery):
    parts = callback.data.split("_")
    months, user_id = parts[2], int(parts[3])
    add_premium_plus(user_id, int(months) * 30)
    await callback.answer(t(callback.from_user.id, "gived_premium_plus"))

@dp.callback_query(F.data.startswith("remove_"))
async def remove_premium_callback(callback: CallbackQuery):
    uid = callback.data.split("_")[1]
    data = load_premium_users()
    data.pop(uid, None)
    save_premium_users(data)
    users = load_users()
    target_name = users.get(uid, {}).get("name", f"ID{uid}")
    log_admin_action(callback.from_user.id, "remove_premium", uid, f"Удалил Premium — {target_name}")
    await callback.answer(t(callback.from_user.id, "premium_delete"))

@dp.callback_query(F.data.startswith("retry_test_"))
async def retry_test(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    test_id, start, end = parts[2], int(parts[3]), int(parts[4])
    test = load_global_test(test_id)
    if not test:
        return await callback.answer(t(callback.from_user.id, "test_not_found"), show_alert=True)
    group_questions = test.get("questions", [])[start:end]
    local_test = {**test, "questions": group_questions}
    await state.update_data(
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id,
        test_id=test_id, test=local_test,
        q_index=0, start=0, end=len(group_questions),
        orig_start=start, orig_end=end,  # ← тоже сохраняем
        score=0, wrong=0, start_time=time.time(), inactive_count=0, paused=False
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
    test_id, start, end = parts[1], int(parts[2]), int(parts[3])
    user_id = callback.from_user.id
    test = load_global_test(test_id)
    if not test:
        return await callback.answer(t(user_id, "test_not_found"), show_alert=True)
    text = t(user_id, "group_info").format(
        start=start + 1, end=end, name=test["name"],
        count=end - start, time=test.get("time", 60)
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
        return await callback.answer(t(callback.from_user.id, "test_list_not_found"), show_alert=True)
    is_ready = test_id in load_ready_tests()
    await show_test_groups(callback.message, test, test_id, callback.from_user.id, page=0, is_ready_test=is_ready)
    await callback.answer()

@dp.callback_query(F.data == "back_to_my_tests")
async def back_to_my_tests(callback: CallbackQuery):
    await show_my_tests(callback.message, callback.from_user.id)
    await callback.answer()

@dp.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    await callback.message.delete()
    uid = callback.from_user.id
    kb_buttons = [
        [KeyboardButton(text=t(uid, "users")), KeyboardButton(text=t(uid, "search"))],
        [KeyboardButton(text=t(uid, "premium_active"))],
    ]
    if uid == SUPER_ADMIN_ID:
        kb_buttons.append([KeyboardButton(text=t(uid, "admin_history"))])
    kb_buttons.append([KeyboardButton(text=t(uid, "back"))])
    await bot.send_message(uid, "🛠 Админ панель:", reply_markup=ReplyKeyboardMarkup(keyboard=kb_buttons, resize_keyboard=True))
    await callback.answer()

@dp.callback_query(F.data.startswith("mk_admin_"))
async def make_admin_callback(callback: CallbackQuery):
    if callback.from_user.id != SUPER_ADMIN_ID:
        return await callback.answer(t(callback.from_user.id, "no_access"), show_alert=True)
    uid = int(callback.data.split("_")[2])
    add_admin(uid)
    users = load_users()
    log_admin_action(callback.from_user.id, "give_admin", str(uid), f"Сделал админом: {users.get(str(uid), {}).get('name', uid)}")
    await callback.answer(t(callback.from_user.id, "admin_added"), show_alert=True)

@dp.callback_query(F.data.startswith("del_admin_"))
async def del_admin_callback(callback: CallbackQuery):
    if callback.from_user.id != SUPER_ADMIN_ID:
        return await callback.answer(t(callback.from_user.id, "no_access"), show_alert=True)
    uid = int(callback.data.split("_")[2])
    remove_admin(uid)
    users = load_users()
    log_admin_action(callback.from_user.id, "remove_admin", str(uid), f"Снял админа: {users.get(str(uid), {}).get('name', uid)}")
    await callback.answer(t(callback.from_user.id, "admin_removed"), show_alert=True)

@dp.callback_query(F.data.startswith("share_"))
async def share_test(callback: CallbackQuery):
    parts = callback.data.split("_")
    test_id, start, end = parts[1], parts[2], parts[3]
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={test_id}_{start}_{end}"
    await callback.message.answer(t(callback.from_user.id, "share_link").format(link=link))
    await callback.answer()

@dp.callback_query(F.data.startswith("begin_test_"))
async def begin_test(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    test_id, start, end = parts[2], int(parts[3]), int(parts[4])
    test = load_global_test(test_id)
    if not test:
        return await callback.answer(t(callback.from_user.id, "test_not_found"), show_alert=True)

    all_questions = test.get("questions", [])
    group_questions = all_questions[start:end]
    order = test.get("order", "normal")

    if order in ("shuffle", "questions"):
        group_questions = group_questions.copy()
        random.shuffle(group_questions)
    elif order == "answers":
        new_group = []
        for q in group_questions:
            paired = list(enumerate(q["answers"]))
            random.shuffle(paired)
            new_answers = [ans for _, ans in paired]
            new_correct = next(i for i, (old, _) in enumerate(paired) if old == q["correct"])
            new_group.append({**q, "answers": new_answers, "correct": new_correct})
        group_questions = new_group

    local_test = {**test, "questions": group_questions}
    await state.update_data(
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id,
        test_id=test_id, test=local_test,
        q_index=0, start=0, end=len(group_questions),
        orig_start=start, orig_end=end,  # ← сохраняем оригинальные индексы
        score=0, wrong=0, start_time=time.time(), inactive_count=0, paused=False
    )
    await callback.answer()
    await start_countdown(callback.message.chat.id, callback.from_user.id)
    await send_question(state)

@dp.callback_query(F.data.startswith("groups_page_"))
async def groups_page_handler(callback: CallbackQuery):
    parts = callback.data.split("_")
    test_id, page = parts[2], int(parts[3])
    test = load_global_test(test_id)
    if not test:
        return await callback.answer(t(callback.from_user.id, "test_not_found"), show_alert=True)
    is_ready = test_id in load_ready_tests()
    await show_test_groups(callback.message, test, test_id, callback.from_user.id, page, is_ready_test=is_ready)
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_test_"))
async def edit_test_menu(callback: CallbackQuery):
    test_id = callback.data.split("_")[2]
    test = load_global_test(test_id)
    if not test:
        return await callback.answer(t(callback.from_user.id, "test_not_found"), show_alert=True)
    uid = callback.from_user.id
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(uid, "change_name"), callback_data=f"edit_name_{test_id}")],
        [InlineKeyboardButton(text=t(uid, "change_timer"), callback_data=f"edit_time_{test_id}")],
        [InlineKeyboardButton(text=t(uid, "change_order"), callback_data=f"edit_order_{test_id}")],
        [InlineKeyboardButton(text=t(uid, "btn_back"), callback_data=f"back_to_groups_{test_id}")]
    ])
    await callback.message.edit_text(f"✏️ Редактирование теста:\n{test.get('name', '')}", reply_markup=kb)

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
    if not test_id:
        await message.answer(t(message.from_user.id, "test_not_found"))
        await state.clear()
        return

    tests = load_global_tests()
    if test_id in tests:
        tests[test_id]["name"] = message.text
        save_global_tests(tests)
        await message.answer("✅ Название изменено!")
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
    if not test_id:
        await message.answer(t(message.from_user.id, "test_not_found"))
        await state.clear()
        return

    tests = load_global_tests()
    if test_id in tests:
        tests[test_id]["time"] = int(message.text)
        save_global_tests(tests)
        await message.answer("✅ Таймер изменён!")
    else:
        await message.answer(t(message.from_user.id, "test_not_found"))
    await state.clear()

@dp.callback_query(F.data.startswith("edit_order_"))
async def edit_order_handler(callback: CallbackQuery):
    test_id = callback.data.split("_")[2]
    uid = callback.from_user.id
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(uid, "shuffle_all"), callback_data=f"order_shuffle_{test_id}")],
        [InlineKeyboardButton(text=t(uid, "by_order"), callback_data=f"order_normal_{test_id}")],
        [InlineKeyboardButton(text=t(uid, "only_questions"), callback_data=f"order_questions_{test_id}")],
        [InlineKeyboardButton(text=t(uid, "only_answers"), callback_data=f"order_answers_{test_id}")],
        [InlineKeyboardButton(text=t(uid, "btn_back"), callback_data=f"edit_test_{test_id}")]
    ])
    await callback.message.edit_text("Выберите порядок вопросов:", reply_markup=kb)

@dp.callback_query(F.data.startswith("order_shuffle_") | F.data.startswith("order_normal_") |
                   F.data.startswith("order_questions_") | F.data.startswith("order_answers_"))
async def apply_order_handler(callback: CallbackQuery):
    parts = callback.data.split("_")
    order_type, test_id = parts[1], parts[2]
    tests = load_global_tests()
    if test_id in tests:
        tests[test_id]["order"] = order_type
        save_global_tests(tests)
        await callback.answer("✅ Порядок изменён!", show_alert=True)
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
    test_id = callback.data.split("_")[3] if callback.data.startswith("send_to_group_") else callback.data.split("_")[2]
    if not load_global_test(test_id):
        return await callback.answer(t(callback.from_user.id, "test_not_found"), show_alert=True)
    await state.update_data(send_test_id=test_id)
    await callback.message.answer(t(callback.from_user.id, "enter_group_id"))
    await state.set_state(SendToGroup.group_id)
    await callback.answer()

@dp.message(SendToGroup.group_id)
async def process_group_id(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    test = load_global_test(data.get("send_test_id"))
    if not test:
        await message.answer(t(user_id, "test_not_found"))
        await state.clear()
        return
    questions = test.get("questions", [])
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={data['send_test_id']}_0_{len(questions)}"
    try:
        await bot.send_message(
            chat_id=message.text.strip(),
            text=f"📚 <b>{test['name']}</b>\n\n✏️ {len(questions)} вопросов\n⏱️ {test.get('time', 60)} сек\n\n🔗 {link}",
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
    if poll_id not in poll_owners or poll_owners[poll_id] != user_id:
        return

    state = get_fsm_context(user_id)
    data = await state.get_data()

    # Отменяем таймаут
    task = data.get("timeout_task")
    if task and not task.done():
        task.cancel()

    if data.get("current_poll_id") != poll_id:
        return

    chosen = poll_answer.option_ids[0] if poll_answer.option_ids else None
    correct = data.get("correct")
    score = data.get("score", 0)
    wrong = data.get("wrong", 0)

    if chosen is not None and chosen == correct:
        score += 1
    else:
        wrong += 1

    await state.update_data(
        score=score, wrong=wrong,
        q_index=data.get("q_index", 0) + 1,
        inactive_count=0, timeout_task=None
    )
    poll_owners.pop(poll_id, None)
    await send_question(state)

# ====================== РАССЫЛКА ======================

@dp.message(BroadcastMessage.message)
async def broadcast_get_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text == "❌ Отмена":
        await state.clear()
        return await message.answer("❌ Рассылка отменена", reply_markup=get_menu(user_id))
    await state.update_data(broadcast_chat_id=message.chat.id, broadcast_message_id=message.message_id)
    count = len(load_users())
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"✅ Отправить ({count} польз.)", callback_data="broadcast_confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")
    ]])
    await message.answer(f"📢 Предпросмотр выше.\n\n👥 Получателей: {count}\n\nПодтвердите рассылку:", reply_markup=kb)
    await state.set_state(BroadcastMessage.confirm)

@dp.callback_query(F.data == "broadcast_confirm")
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id != SUPER_ADMIN_ID:
        return await callback.answer("Нет доступа", show_alert=True)

    data = await state.get_data()
    src_chat_id = data.get("broadcast_chat_id")
    src_message_id = data.get("broadcast_message_id")
    users = load_users()
    user_ids = list(users.keys())

    await callback.message.edit_text(f"📤 Рассылка началась...\n👥 Получателей: {len(user_ids)}")
    await state.clear()
    await callback.answer()

    success = 0
    failed = 0
    # Батчи по 25 — обновляем прогресс каждые 25 отправок
    batch_size = 25

    for i, uid in enumerate(user_ids):
        try:
            await bot.copy_message(chat_id=int(uid), from_chat_id=src_chat_id, message_id=src_message_id)
            success += 1
        except Exception:
            failed += 1
        # Пауза защита от flood: 25 сообщений/сек лимит Telegram
        if (i + 1) % batch_size == 0:
            await asyncio.sleep(1)

    await bot.send_message(
        user_id,
        f"✅ Рассылка завершена!\n\n📨 Отправлено: {success}\n❌ Не доставлено: {failed}",
        reply_markup=get_menu(user_id)
    )
    log_admin_action(user_id, "broadcast", "all_users", f"Рассылка: доставлено {success}, ошибок {failed}")

@dp.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Рассылка отменена")
    await bot.send_message(callback.from_user.id, "Главное меню:", reply_markup=get_menu(callback.from_user.id))
    await callback.answer()

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
                    except Exception:
                        pass

# ====================== КОМАНДЫ ======================

async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="🏠 Main menu / Главное меню / Asosiy menyu"),
        BotCommand(command="newquiz", description="Create a new quiz"),
        BotCommand(command="lang", description="Change language"),
        BotCommand(command="stop", description="Stop the active quiz"),
        BotCommand(command="help", description="About this bot"),
    ])

# ====================== ЗАПУСК ======================

async def main():
    init_db()                               # ← инициализация БД
    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands()
    asyncio.create_task(clean_files())
    await dp.start_polling(bot)

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен...")
    asyncio.run(main())