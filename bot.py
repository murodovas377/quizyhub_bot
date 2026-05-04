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


FILE = "premium.json"
USERS_FILE = "users.json"

if not os.path.exists(FILE):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=4)

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

def is_admin(user_id):
    return user_id == SUPER_ADMIN_ID

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
        if not q_text:
            continue
        raw_answers = [p.strip() for p in parts[1:] if p.strip()]
        answers = []
        correct_index = None
        for ans in raw_answers:
            clean = ans.strip()
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

def get_menu(user_id):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(user_id, "new_test"))],
            [KeyboardButton(text=t(user_id, "premium"))],
            [KeyboardButton(text=t(user_id, "my_tests"))],
            [KeyboardButton(text=t(user_id, "admin"))]
        ],
        resize_keyboard=True
    )

# ====================== ФИЛЬТР КНОПОК МЕНЮ ======================
class IsMenuButton(Filter):
    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        menu_keys = ["new_test", "premium", "my_tests", "admin",
                     "back", "users", "search", "premium_active"]
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
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=t(user_id, "users")), KeyboardButton(text=t(user_id, "search"))],
                [KeyboardButton(text=t(user_id, "premium_active"))],
                [KeyboardButton(text=t(user_id, "back"))]
            ],
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
        await message.answer(t(user_id, "premium_info"))
        return

    if is_admin(user_id):
        if text == t(user_id, "users"):
            users = load_users()
            if not users:
                return await message.answer(t(user_id, "no_users"))
            buttons = []
            for uid, u in list(users.items())[:50]:
                status = "💎" if is_premium(uid) else "❌"
                buttons.append([InlineKeyboardButton(
                    text=f"{status} {u.get('name', 'Без имени')}",
                    callback_data=f"user_{uid}"
                )])
            await message.answer(t(user_id, "users"), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
            return

        elif text == t(user_id, "search"):
            await message.answer(t(user_id, "enter_query"))
            await state.set_state(AdminSearch.query)
            return

        elif text == t(user_id, "premium_active"):
            data = load_premium_users()
            msg = "💎 Premium:\n\n"
            for uid, expire in data.items():
                left = int(expire - time.time())
                if left > 0:
                    msg += f"• {uid} — {left // 86400} дн.\n"
            await message.answer(msg if msg != "💎 Premium:\n\n" else "Нет активных премиум пользователей")
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

    buttons = [
        [InlineKeyboardButton(
            text=f"{test_data['name']} ({len(test_data['questions'])} вопросов)",
            callback_data=f"start_test_{tid}"
        )]
        for tid in test_ids
        if (test_data := load_global_test(tid))
    ]

    if not buttons:
        await message.answer(t(user_id, "you_havent_test"), reply_markup=get_menu(user_id))
        return

    await message.answer(t(user_id, "your_tests"), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

async def show_test_groups(message: Message, test: dict, test_id: str, user_id: int):
    questions = test.get("questions", [])
    split = test.get("split", len(questions) or 10)
    buttons = [
        [InlineKeyboardButton(
            text=f"{start + 1}-{min(start + split, len(questions))}",
            callback_data=f"group_{test_id}_{start}_{min(start + split, len(questions))}"
        )]
        for start in range(0, len(questions), split)
    ]
    buttons.append([
        InlineKeyboardButton(text=t(user_id, "btn_delete_test"), callback_data=f"delete_test_{test_id}"),
        InlineKeyboardButton(text=t(user_id, "btn_back"), callback_data="back_to_my_tests")
    ])
    await message.edit_text(
        t(user_id, "choose_group").format(name=test["name"]),
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
    await callback.message.answer(t(callback.from_user.id, "buy_premium"))
    await callback.answer()

@dp.callback_query(F.data.startswith("give_"))
async def give_premium_callback(callback: CallbackQuery):
    parts = callback.data.split("_")
    months = parts[1]
    user_id = int(parts[2])
    days = int(months) * 30
    add_premium(user_id, days)
    await callback.answer(t(callback.from_user.id, "gived_premium"))

@dp.callback_query(F.data.startswith("remove_"))
async def remove_premium_callback(callback: CallbackQuery):
    user_id = callback.data.split("_")[1]
    data = load_premium_users()
    data.pop(user_id, None)
    save_premium_users(data)
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

@dp.callback_query(F.data.startswith("start_test_"))
async def select_test(callback: CallbackQuery):
    test_id = callback.data.split("_")[-1]
    test = load_global_test(test_id)
    if not test:
        return await callback.answer(t(callback.from_user.id, "test_not_found"), show_alert=True)
    await show_test_groups(callback.message, test, test_id, callback.from_user.id)

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
    await show_test_groups(callback.message, test, test_id, callback.from_user.id)
    await callback.answer()

@dp.callback_query(F.data == "back_to_my_tests")
async def back_to_my_tests(callback: CallbackQuery):
    await show_my_tests(callback.message, callback.from_user.id)
    await callback.answer()

@dp.callback_query(F.data.startswith("user_"))
async def user_menu(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    premium = is_premium(user_id)
    left = get_premium_time_left(user_id)
    text_status = "💎 Премиум" if premium else "❌ Нет премиума"
    if left:
        text_status += f"\n⏳ Осталось: {left}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 1 мес", callback_data=f"give_1_{user_id}")],
        [InlineKeyboardButton(text="⭐ 3 мес", callback_data=f"give_3_{user_id}")],
        [InlineKeyboardButton(text="⭐ 6 мес", callback_data=f"give_6_{user_id}")],
        [InlineKeyboardButton(text="❌ Убрать премиум", callback_data=f"remove_{user_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_users")]
    ])

    await callback.message.edit_text(
        f"👤 Пользователь: {user_id}\n\n{text_status}",
        reply_markup=kb
    )

@dp.callback_query(F.data == "back_to_users")
async def back_to_users(callback: CallbackQuery):
    users = load_users()
    buttons = []
    for user_id, u in list(users.items())[:50]:
        name = u.get("name") or "Без имени"
        username = f"@{u.get('username')}" if u.get("username") else ""
        status = "💎" if is_premium(user_id) else "❌"
        text = f"{status} {name} {username}".strip()
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"user_{user_id}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(t(callback.from_user.id, "choose_client"), reply_markup=kb)
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

@dp.callback_query(F.data.startswith("send_to_group_"))
async def send_to_group(callback: CallbackQuery):
    await callback.answer(t(callback.from_user.id, "function_not_realised"), show_alert=True)

@dp.callback_query(F.data.startswith("begin_test_"))
async def begin_test(callback: CallbackQuery, state: FSMContext):
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