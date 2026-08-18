from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime
import html
import os
import random
from typing import Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.formatting import Bold, Text, as_key_value, as_line, as_list
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

from affix_data import AFFIX_GROUPS, GROUP_BY_ID, AffixGroup, groups_by_kind

try:
    from aiogram.types import InputRichMessage
except ImportError:
    InputRichMessage = None

try:
    from aiogram.types import InputRichBlockTable, RichBlockTableCell
except ImportError:
    InputRichBlockTable = None
    RichBlockTableCell = None


WEEKDAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
PAGE_SIZE = 6


@dataclass
class ReminderSettings:
    enabled: bool = False
    interval_minutes: int = 180
    times_per_day: int = 2
    disabled_weekdays: set[int] = field(default_factory=set)
    sent_on: date | None = None
    sent_today: int = 0
    last_sent_at: datetime | None = None


@dataclass
class QuizQuestion:
    group_id: str
    english: str
    russian: str


@dataclass
class UserState:
    enabled_group_ids: set[str] = field(default_factory=lambda: {group.id for group in AFFIX_GROUPS})
    quiz_enabled: bool = False
    current_question: QuizQuestion | None = None
    main_message_id: int | None = None
    question_message_id: int | None = None
    reminders: ReminderSettings = field(default_factory=ReminderSettings)


router = Router()
states: dict[int, UserState] = {}


def user_state(user_id: int) -> UserState:
    return states.setdefault(user_id, UserState())


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Таблица", callback_data="table:menu")],
        [InlineKeyboardButton(text="Опрос", callback_data="quiz:menu")],
        [InlineKeyboardButton(text="Напоминания", callback_data="rem:menu")],
    ])


def table_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Префиксы", callback_data="table:Префикс:0")],
        [InlineKeyboardButton(text="Суффиксы", callback_data="table:Суффикс:0")],
        [InlineKeyboardButton(text="Назад", callback_data="main")],
    ])


def table_keyboard(kind: str, page: int, max_page: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="Назад", callback_data=f"table:{kind}:{page - 1}"))
    if page < max_page:
        nav.append(InlineKeyboardButton(text="Дальше", callback_data=f"table:{kind}:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="К выбору", callback_data="table:menu")])
    rows.append([InlineKeyboardButton(text="Главное меню", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def quiz_menu_keyboard(state: UserState) -> InlineKeyboardMarkup:
    enabled = "Остановить опрос" if state.quiz_enabled else "Начать опрос"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=enabled, callback_data="quiz:toggle")],
        [InlineKeyboardButton(text="Настроить группы", callback_data="quiz:groups:0")],
        [InlineKeyboardButton(text="Назад", callback_data="main")],
    ])


def quiz_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подсказка", callback_data="quiz:hint")],
        [InlineKeyboardButton(text="Следующий вопрос", callback_data="quiz:next")],
        [InlineKeyboardButton(text="Остановить", callback_data="quiz:stop")],
    ])


def group_settings_keyboard(state: UserState, page: int) -> InlineKeyboardMarkup:
    groups = list(AFFIX_GROUPS)
    max_page = max(0, (len(groups) - 1) // PAGE_SIZE)
    visible = groups[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    rows = []
    for group in visible:
        mark = "✓" if group.id in state.enabled_group_ids else "×"
        rows.append([InlineKeyboardButton(
            text=f"{mark} {group.kind}: {group.group[:38]}",
            callback_data=f"quiz:g_toggle:{group.id}:{page}",
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="Назад", callback_data=f"quiz:groups:{page - 1}"))
    if page < max_page:
        nav.append(InlineKeyboardButton(text="Дальше", callback_data=f"quiz:groups:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="Включить все", callback_data=f"quiz:g_all:{page}")])
    rows.append([InlineKeyboardButton(text="К опросу", callback_data="quiz:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reminder_keyboard(state: UserState) -> InlineKeyboardMarkup:
    reminder = state.reminders
    enabled = "Выключить" if reminder.enabled else "Включить"
    rows = [
        [InlineKeyboardButton(text=enabled, callback_data="rem:toggle")],
        [
            InlineKeyboardButton(text="-30 мин", callback_data="rem:interval:-30"),
            InlineKeyboardButton(text="+30 мин", callback_data="rem:interval:30"),
        ],
        [
            InlineKeyboardButton(text="-1 раз", callback_data="rem:times:-1"),
            InlineKeyboardButton(text="+1 раз", callback_data="rem:times:1"),
        ],
    ]
    rows.extend(
        [InlineKeyboardButton(
            text=f"{'×' if i in reminder.disabled_weekdays else '✓'} {name}",
            callback_data=f"rem:day:{i}",
        )]
        for i, name in enumerate(WEEKDAYS)
    )
    rows.append([InlineKeyboardButton(text="Назад", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_content() -> Text:
    return as_list(
        Bold("Тренажер частичек"),
        "Выбирай таблицу, запускай опрос или настраивай напоминания. Идея тренировки: видеть значение аффикса и самому собирать слово.",
    )


def table_menu_content() -> Text:
    return as_list(
        Bold("Таблица"),
        "Префиксы и суффиксы вынесены отдельно. Внутри раздела они идут от меньшего количества частичек к большему.",
    )


def quiz_menu_content(state: UserState) -> Text:
    return as_list(
        Bold("Опрос"),
        as_key_value("Статус", Bold("идет" if state.quiz_enabled else "остановлен")),
        as_key_value("Включено групп", Bold(f"{len(state.enabled_group_ids)}/{len(AFFIX_GROUPS)}")),
        "Вопросы идут с русского на английский. Если ответ неправильный, бот показывает правильный вариант.",
    )


def group_settings_content(state: UserState) -> Text:
    return as_list(
        Bold("Группы для опроса"),
        f"Включай и выключай значения из 2-го столбца таблицы. Сейчас активно: {len(state.enabled_group_ids)}.",
    )


def reminders_content(state: UserState) -> Text:
    r = state.reminders
    disabled = ", ".join(WEEKDAYS[i] for i in sorted(r.disabled_weekdays)) or "нет"
    return as_list(
        Bold("Напоминания"),
        as_key_value("Статус", Bold("включены" if r.enabled else "выключены")),
        as_key_value("Таймер", Bold(f"{r.interval_minutes} мин")),
        as_key_value("Максимум в день", Bold(str(r.times_per_day))),
        as_key_value("Не присылать в дни", Bold(disabled)),
        "Уведомления приходят отдельными сообщениями, их можно удалить.",
    )


def question_content(question: QuizQuestion, prefix: Text | str | None = None) -> Text:
    body = as_list(
        Bold("Переведи на английский"),
        question.russian,
        "Ответ отправь обычным сообщением.",
    )
    if prefix:
        return as_list(prefix, body)
    return body


def format_examples(group: AffixGroup, limit: int | None = None) -> str:
    examples = group.examples if limit is None else group.examples[:limit]
    return "; ".join(f"{en} - {ru}" for en, ru in examples)


def render_table_plain(kind: str, page: int) -> tuple[str, int]:
    groups = groups_by_kind(kind)
    max_page = max(0, (len(groups) - 1) // PAGE_SIZE)
    page = min(max(page, 0), max_page)
    visible = groups[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    lines = [f"<b>{html.escape(kind)}ы</b>", f"Страница {page + 1}/{max_page + 1}\n"]
    for index, group in enumerate(visible, start=page * PAGE_SIZE + 1):
        analog = f"\nРусский аналог: {html.escape(group.ru_analog)}" if group.ru_analog else ""
        lines.append(
            f"<b>{index}. {html.escape(group.affixes)}</b> ({group.parts_count})\n"
            f"{html.escape(group.group)}{analog}\n"
            f"Примеры: {html.escape(format_examples(group, limit=3))}"
        )
    return "\n\n".join(lines), max_page


def rich_table_html(kind: str, page: int) -> tuple[str, int]:
    groups = groups_by_kind(kind)
    max_page = max(0, (len(groups) - 1) // PAGE_SIZE)
    page = min(max(page, 0), max_page)
    visible = groups[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    rows = [
        "<tr>"
        "<th>#</th><th>Аффиксы</th><th>Частей</th><th>Значение</th><th>Русский аналог</th><th>Примеры</th>"
        "</tr>"
    ]
    for index, group in enumerate(visible, start=page * PAGE_SIZE + 1):
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td><b>{html.escape(group.affixes)}</b></td>"
            f"<td>{group.parts_count}</td>"
            f"<td>{html.escape(group.group)}</td>"
            f"<td>{html.escape(group.ru_analog or '—')}</td>"
            f"<td>{html.escape(format_examples(group, limit=3))}</td>"
            "</tr>"
        )
    title = html.escape(f"{kind}ы, страница {page + 1}/{max_page + 1}")
    return (
        f"<h3>{title}</h3>"
        "<p>Отсортировано от меньшего количества частичек к большему.</p>"
        "<table border=\"1\">"
        f"{''.join(rows)}"
        "</table>",
        max_page,
    )


def make_rich_table_message(kind: str, page: int) -> tuple[Any | None, int]:
    if InputRichMessage is None:
        _, max_page = render_table_plain(kind, page)
        return None, max_page
    groups = groups_by_kind(kind)
    max_page = max(0, (len(groups) - 1) // PAGE_SIZE)
    page = min(max(page, 0), max_page)
    visible = groups[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    if InputRichBlockTable is not None and RichBlockTableCell is not None:
        cells = [[
            RichBlockTableCell(align="center", valign="middle", text="#", is_header=True),
            RichBlockTableCell(align="left", valign="middle", text="Аффиксы", is_header=True),
            RichBlockTableCell(align="center", valign="middle", text="Частей", is_header=True),
            RichBlockTableCell(align="left", valign="middle", text="Значение", is_header=True),
            RichBlockTableCell(align="left", valign="middle", text="Русский аналог", is_header=True),
            RichBlockTableCell(align="left", valign="middle", text="Примеры", is_header=True),
        ]]
        for index, group in enumerate(visible, start=page * PAGE_SIZE + 1):
            cells.append([
                RichBlockTableCell(align="center", valign="top", text=str(index)),
                RichBlockTableCell(align="left", valign="top", text=group.affixes),
                RichBlockTableCell(align="center", valign="top", text=str(group.parts_count)),
                RichBlockTableCell(align="left", valign="top", text=group.group),
                RichBlockTableCell(align="left", valign="top", text=group.ru_analog or "—"),
                RichBlockTableCell(align="left", valign="top", text=format_examples(group, limit=3)),
            ])
        return InputRichMessage(
            blocks=[InputRichBlockTable(
                cells=cells,
                is_bordered=True,
                is_striped=True,
                caption=f"{kind}ы, страница {page + 1}/{max_page + 1}",
            )],
            skip_entity_detection=True,
        ), max_page
    rich_html, _ = rich_table_html(kind, page)
    return InputRichMessage(html=rich_html, skip_entity_detection=True), max_page


async def safe_edit_content(message: Message, content: Text, keyboard: InlineKeyboardMarkup) -> None:
    try:
        await message.edit_text(**content.as_kwargs(), reply_markup=keyboard)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise


async def edit_main_quiz_menu(bot: Bot, chat_id: int, state: UserState) -> None:
    if state.main_message_id is None:
        return
    try:
        await bot.edit_message_text(
            **quiz_menu_content(state).as_kwargs(),
            chat_id=chat_id,
            message_id=state.main_message_id,
            reply_markup=quiz_menu_keyboard(state),
        )
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise


async def delete_question_message(bot: Bot, chat_id: int, state: UserState) -> None:
    question_message_id = state.question_message_id
    state.question_message_id = None
    if question_message_id is None:
        return
    try:
        await bot.delete_message(chat_id, question_message_id)
    except TelegramBadRequest:
        pass


async def send_question(bot: Bot, chat_id: int, state: UserState, prefix: Text | str | None = None) -> None:
    question = state.current_question
    if question is None:
        return
    sent = await bot.send_message(
        chat_id,
        **question_content(question, prefix=prefix).as_kwargs(),
        reply_markup=quiz_keyboard(),
    )
    state.question_message_id = sent.message_id


async def edit_question(
    bot: Bot,
    chat_id: int,
    state: UserState,
    prefix: Text | str | None = None,
) -> None:
    question = state.current_question
    if question is None:
        return
    if state.question_message_id is None:
        await send_question(bot, chat_id, state, prefix=prefix)
        return
    try:
        await bot.edit_message_text(
            **question_content(question, prefix=prefix).as_kwargs(),
            chat_id=chat_id,
            message_id=state.question_message_id,
            reply_markup=quiz_keyboard(),
        )
    except TelegramBadRequest as error:
        if "message is not modified" in str(error):
            return
        state.question_message_id = None
        await send_question(bot, chat_id, state, prefix=prefix)


async def edit_table_message(bot: Bot, message: Message, kind: str, page: int, keyboard: InlineKeyboardMarkup) -> None:
    rich_message, _ = make_rich_table_message(kind, page)
    if rich_message is not None:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.message_id,
                rich_message=rich_message,
                reply_markup=keyboard,
            )
            return
        except TelegramBadRequest:
            pass
    plain_text, _ = render_table_plain(kind, page)
    await message.edit_text(plain_text, reply_markup=keyboard)


def active_examples(state: UserState) -> list[tuple[AffixGroup, str, str]]:
    items: list[tuple[AffixGroup, str, str]] = []
    for group in AFFIX_GROUPS:
        if group.id in state.enabled_group_ids:
            items.extend((group, english, russian) for english, russian in group.examples)
    return items


def make_question(state: UserState) -> QuizQuestion | None:
    examples = active_examples(state)
    if not examples:
        return None
    group, english, russian = random.choice(examples)
    state.current_question = QuizQuestion(group_id=group.id, english=english, russian=russian)
    return state.current_question


def normalize_answer(value: str) -> str:
    value = value.lower().strip()
    if value.startswith("to "):
        value = value[3:]
    return " ".join(value.replace("‑", "-").split())


@router.message(CommandStart())
async def start(message: Message) -> None:
    state = user_state(message.from_user.id)
    sent = await message.answer(**main_content().as_kwargs(), reply_markup=main_keyboard())
    state.main_message_id = sent.message_id


@router.callback_query(F.data == "main")
async def main_menu(callback: CallbackQuery) -> None:
    user_state(callback.from_user.id).main_message_id = callback.message.message_id
    await safe_edit_content(callback.message, main_content(), main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "table:menu")
async def table_menu(callback: CallbackQuery) -> None:
    user_state(callback.from_user.id).main_message_id = callback.message.message_id
    await safe_edit_content(callback.message, table_menu_content(), table_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("table:"))
async def table_page(callback: CallbackQuery, bot: Bot) -> None:
    user_state(callback.from_user.id).main_message_id = callback.message.message_id
    _, kind, page_raw = callback.data.split(":")
    page = int(page_raw)
    _, max_page = make_rich_table_message(kind, page)
    await edit_table_message(bot, callback.message, kind, page, table_keyboard(kind, page, max_page))
    await callback.answer()


@router.callback_query(F.data == "quiz:menu")
async def quiz_menu(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    state.main_message_id = callback.message.message_id
    await safe_edit_content(callback.message, quiz_menu_content(state), quiz_menu_keyboard(state))
    await callback.answer()


@router.callback_query(F.data == "quiz:toggle")
async def quiz_toggle(callback: CallbackQuery, bot: Bot) -> None:
    state = user_state(callback.from_user.id)
    state.main_message_id = callback.message.message_id
    if state.quiz_enabled:
        state.quiz_enabled = False
        state.current_question = None
        await delete_question_message(bot, callback.message.chat.id, state)
        await safe_edit_content(callback.message, quiz_menu_content(state), quiz_menu_keyboard(state))
    else:
        state.quiz_enabled = True
        question = make_question(state)
        if question is None:
            state.quiz_enabled = False
            await callback.answer("Сначала включи хотя бы одну группу.", show_alert=True)
            return
        await safe_edit_content(callback.message, quiz_menu_content(state), quiz_menu_keyboard(state))
        await send_question(bot, callback.message.chat.id, state)
    await callback.answer()


@router.callback_query(F.data == "quiz:stop")
async def quiz_stop(callback: CallbackQuery, bot: Bot) -> None:
    state = user_state(callback.from_user.id)
    state.quiz_enabled = False
    state.current_question = None
    await delete_question_message(bot, callback.message.chat.id, state)
    await edit_main_quiz_menu(bot, callback.message.chat.id, state)
    await callback.answer()


@router.callback_query(F.data == "quiz:next")
async def quiz_next(callback: CallbackQuery, bot: Bot) -> None:
    state = user_state(callback.from_user.id)
    state.quiz_enabled = True
    question = make_question(state)
    if question is None:
        state.quiz_enabled = False
        await callback.answer("Нет включенных групп.", show_alert=True)
        return
    await edit_question(bot, callback.message.chat.id, state)
    await callback.answer()


@router.callback_query(F.data == "quiz:hint")
async def quiz_hint(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    question = state.current_question
    if question is None:
        await callback.answer("Сейчас нет вопроса.", show_alert=True)
        return
    group = GROUP_BY_ID[question.group_id]
    await callback.answer(f"Подсказка: {group.group}", show_alert=True)


@router.callback_query(F.data.startswith("quiz:groups:"))
async def quiz_groups(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    state.main_message_id = callback.message.message_id
    page = int(callback.data.rsplit(":", 1)[1])
    await safe_edit_content(callback.message, group_settings_content(state), group_settings_keyboard(state, page))
    await callback.answer()


@router.callback_query(F.data.startswith("quiz:g_toggle:"))
async def quiz_group_toggle(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    state.main_message_id = callback.message.message_id
    _, _, group_id, page_raw = callback.data.split(":")
    if group_id in state.enabled_group_ids:
        state.enabled_group_ids.remove(group_id)
    else:
        state.enabled_group_ids.add(group_id)
    page = int(page_raw)
    await safe_edit_content(callback.message, group_settings_content(state), group_settings_keyboard(state, page))
    await callback.answer()


@router.callback_query(F.data.startswith("quiz:g_all:"))
async def quiz_group_all(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    state.main_message_id = callback.message.message_id
    state.enabled_group_ids = {group.id for group in AFFIX_GROUPS}
    page = int(callback.data.rsplit(":", 1)[1])
    await safe_edit_content(callback.message, group_settings_content(state), group_settings_keyboard(state, page))
    await callback.answer()


@router.callback_query(F.data == "rem:menu")
async def reminders_menu(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    state.main_message_id = callback.message.message_id
    await safe_edit_content(callback.message, reminders_content(state), reminder_keyboard(state))
    await callback.answer()


@router.callback_query(F.data == "rem:toggle")
async def reminders_toggle(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    state.main_message_id = callback.message.message_id
    state.reminders.enabled = not state.reminders.enabled
    await safe_edit_content(callback.message, reminders_content(state), reminder_keyboard(state))
    await callback.answer()


@router.callback_query(F.data.startswith("rem:interval:"))
async def reminder_interval(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    state.main_message_id = callback.message.message_id
    delta = int(callback.data.rsplit(":", 1)[1])
    state.reminders.interval_minutes = min(1440, max(30, state.reminders.interval_minutes + delta))
    await safe_edit_content(callback.message, reminders_content(state), reminder_keyboard(state))
    await callback.answer()


@router.callback_query(F.data.startswith("rem:times:"))
async def reminder_times(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    state.main_message_id = callback.message.message_id
    delta = int(callback.data.rsplit(":", 1)[1])
    state.reminders.times_per_day = min(12, max(1, state.reminders.times_per_day + delta))
    await safe_edit_content(callback.message, reminders_content(state), reminder_keyboard(state))
    await callback.answer()


@router.callback_query(F.data.startswith("rem:day:"))
async def reminder_day(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    state.main_message_id = callback.message.message_id
    day = int(callback.data.rsplit(":", 1)[1])
    if day in state.reminders.disabled_weekdays:
        state.reminders.disabled_weekdays.remove(day)
    else:
        state.reminders.disabled_weekdays.add(day)
    await safe_edit_content(callback.message, reminders_content(state), reminder_keyboard(state))
    await callback.answer()


@router.message()
async def answer_quiz(message: Message, bot: Bot) -> None:
    state = user_state(message.from_user.id)
    question = state.current_question
    if not state.quiz_enabled or question is None:
        await message.answer("Открой /start и выбери действие через кнопки.")
        return
    correct = normalize_answer(message.text or "") == normalize_answer(question.english)
    result = Text("Верно.") if correct else Text("Неверно. Правильный ответ: ", Bold(question.english), ".")
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    next_question = make_question(state)
    if next_question is None:
        return
    await edit_question(bot, message.chat.id, state, prefix=result)


async def reminder_loop(bot: Bot) -> None:
    while True:
        now = datetime.now()
        for user_id, state in list(states.items()):
            reminder = state.reminders
            if not reminder.enabled or now.weekday() in reminder.disabled_weekdays:
                continue
            if reminder.sent_on != now.date():
                reminder.sent_on = now.date()
                reminder.sent_today = 0
                reminder.last_sent_at = None
            if reminder.sent_today >= reminder.times_per_day:
                continue
            if reminder.last_sent_at is not None:
                minutes_passed = (now - reminder.last_sent_at).total_seconds() / 60
                if minutes_passed < reminder.interval_minutes:
                    continue
            try:
                await bot.send_message(
                    user_id,
                    "Пора повторить частички. Открой опрос и собери пару слов по смыслу.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Открыть меню", callback_data="quiz:menu")]
                    ]),
                )
            except Exception:
                continue
            reminder.sent_today += 1
            reminder.last_sent_at = now
        await asyncio.sleep(60)


async def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set. Create .env from .env.example and put your Telegram bot token there.")
    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(router)
    asyncio.create_task(reminder_loop(bot))
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
