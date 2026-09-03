from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime
import html
import logging
import os
import random
from typing import Any
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.formatting import Bold, Text, as_key_value, as_line, as_list
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

from affix_data import (
    AFFIX_GROUPS,
    ALL_PRESET_EXCEPTION_WORDS,
    GROUP_BY_ID,
    PRESET_BY_ID,
    QUIZ_PRESETS,
    SELECTABLE_AFFIX_GROUPS,
    AffixGroup,
    groups_by_kind,
)
from wiktionary import load_words as load_wiktionary_words

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
REMINDER_TIMEZONE = ZoneInfo("Europe/Minsk")


@dataclass
class ReminderSettings:
    enabled: bool = False
    interval_minutes: int = 180
    times_per_day: int = 2
    disabled_weekdays: set[int] = field(default_factory=set)
    sent_on: date | None = None
    sent_today: int = 0
    last_sent_at: datetime | None = None
    quiet_start_hour: int = 22
    quiet_end_hour: int = 9
    notification_message_id: int | None = None


@dataclass
class QuizQuestion:
    group_id: str
    english: str
    russian: str
    source_word: str | None = None


@dataclass
class UserState:
    enabled_group_ids: set[str] = field(default_factory=set)
    enabled_preset_ids: set[str] = field(default_factory=set)
    include_all_exceptions: bool = False
    quiz_enabled: bool = False
    current_question: QuizQuestion | None = None
    main_message_id: int | None = None
    question_message_id: int | None = None
    word_source: str = "static"
    reminders: ReminderSettings = field(default_factory=ReminderSettings)


router = Router()
states: dict[int, UserState] = {}
dictionary_examples: dict[str, list[tuple[str, str]]] = {}
dictionary_base_words: dict[str, str] = {}


def user_state(user_id: int) -> UserState:
    return states.setdefault(user_id, UserState())


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Таблица", callback_data="table:menu", style="primary")],
        [InlineKeyboardButton(text="Опрос", callback_data="quiz:menu", style="success")],
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
        [InlineKeyboardButton(
            text=enabled,
            callback_data="quiz:toggle",
            style="danger" if state.quiz_enabled else "success",
        )],
        [InlineKeyboardButton(text="Настроить группы", callback_data="quiz:groups:0")],
        [InlineKeyboardButton(
            text=f"Режим: {'статичный' if state.word_source == 'static' else 'динамичный'}",
            callback_data="quiz:source",
            style="primary",
        )],
        [InlineKeyboardButton(text="Назад", callback_data="main")],
    ])


def quiz_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подсказка", callback_data="quiz:hint")],
        [InlineKeyboardButton(text="Следующий вопрос", callback_data="quiz:next")],
        [InlineKeyboardButton(text="Остановить", callback_data="quiz:stop", style="danger")],
    ])


def group_settings_keyboard(state: UserState, page: int) -> InlineKeyboardMarkup:
    groups = list(SELECTABLE_AFFIX_GROUPS)
    max_page = max(0, (len(groups) - 1) // PAGE_SIZE)
    visible = groups[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    rows = []
    for group in visible:
        mark = "✓" if group.id in state.enabled_group_ids else "✕"
        label = f"{mark} {group.affixes} | {group.group}"
        rows.append([InlineKeyboardButton(
            text=f"{label[:61]}..." if len(label) > 64 else label,
            callback_data=f"quiz:g_toggle:{group.id}:{page}",
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="Назад", callback_data=f"quiz:groups:{page - 1}"))
    if page < max_page:
        nav.append(InlineKeyboardButton(text="Дальше", callback_data=f"quiz:groups:{page + 1}"))
    if nav:
        rows.append(nav)
    all_enabled = (
        all(group.id in state.enabled_group_ids for group in groups)
        and all(preset.id in state.enabled_preset_ids for preset in QUIZ_PRESETS)
        and state.include_all_exceptions
    )
    rows.append([InlineKeyboardButton(
        text="Выключить все" if all_enabled else "Включить все",
        callback_data=f"quiz:g_all:{page}",
        style="danger" if all_enabled else "success",
    )])
    exception_mark = "✓" if state.include_all_exceptions else "✕"
    rows.append([InlineKeyboardButton(
        text=f"{exception_mark} Все исключения",
        callback_data=f"quiz:all_exceptions:{page}",
        style="primary" if state.include_all_exceptions else None,
    )])
    for preset in QUIZ_PRESETS:
        mark = "✓" if preset.id in state.enabled_preset_ids else "✕"
        rows.append([InlineKeyboardButton(
            text=f"{mark} {preset.title}",
            callback_data=f"quiz:preset:{preset.id}:{page}",
            style="primary" if preset.id in state.enabled_preset_ids else None,
        )])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="quiz:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reminder_keyboard(state: UserState) -> InlineKeyboardMarkup:
    reminder = state.reminders
    enabled = "Выключить" if reminder.enabled else "Включить"
    rows = [
        [InlineKeyboardButton(
            text=enabled,
            callback_data="rem:toggle",
            style="danger" if reminder.enabled else "success",
        )],
        [
            InlineKeyboardButton(text="-30 мин", callback_data="rem:interval:-30"),
            InlineKeyboardButton(text="+30 мин", callback_data="rem:interval:30"),
        ],
        [
            InlineKeyboardButton(text="-1 раз", callback_data="rem:times:-1"),
            InlineKeyboardButton(text="+1 раз", callback_data="rem:times:1"),
        ],
        [
            InlineKeyboardButton(text="Тишина с -1 ч", callback_data="rem:quiet_start:-1"),
            InlineKeyboardButton(text="Тишина с +1 ч", callback_data="rem:quiet_start:1"),
        ],
        [
            InlineKeyboardButton(text="Тишина до -1 ч", callback_data="rem:quiet_end:-1"),
            InlineKeyboardButton(text="Тишина до +1 ч", callback_data="rem:quiet_end:1"),
        ],
    ]
    rows.extend(
        [InlineKeyboardButton(
            text=f"{'✕' if i in reminder.disabled_weekdays else '✓'} {name}",
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
        as_key_value("Обычных групп", Bold(f"{len(state.enabled_group_ids)}/{len(SELECTABLE_AFFIX_GROUPS)}")),
        as_key_value("Пресетов", Bold(f"{len(state.enabled_preset_ids)}/{len(QUIZ_PRESETS)}")),
        as_key_value("Источник слов", Bold("примеры из таблиц" if state.word_source == "static" else "Wiktionary")),
        "Вопросы идут с русского на английский. После ответа бот показывает правильный вариант.",
    )


def group_settings_content(state: UserState) -> Text:
    return as_list(
        Bold("Группы для опроса"),
        "Выбирай отдельные аффиксы или готовый пресет. Пресет всегда включает свои слова и связанные с ним исключения.",
        "Кнопка «Все исключения» добавляет исключения из всех пресетов.",
        f"Сейчас выбрано: {len(state.enabled_preset_ids)} пресетов, {len(state.enabled_group_ids)} обычных групп; все исключения: {'включены' if state.include_all_exceptions else 'выключены'}.",
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
        as_key_value("Тишина", Bold(f"{r.quiet_start_hour:02d}:00-{r.quiet_end_hour:02d}:00")),
        "Открытое уведомление заменяется следующим. Его можно закрыть отдельной кнопкой.",
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


def active_examples(state: UserState) -> list[tuple[AffixGroup, str, str, str | None]]:
    items: list[tuple[AffixGroup, str, str, str | None]] = []
    for group in SELECTABLE_AFFIX_GROUPS:
        if group.id in state.enabled_group_ids:
            if state.word_source == "static":
                items.extend((group, english, russian, None) for english, russian in group.examples)
            else:
                items.extend((group, english, russian, None) for english, russian in dictionary_examples.get(group.id, ()))

    for preset_id in state.enabled_preset_ids:
        preset = PRESET_BY_ID[preset_id]
        for group_id in preset.group_ids:
            group = GROUP_BY_ID[group_id]
            if state.word_source == "static":
                items.extend((group, english, russian, None) for english, russian in group.examples)
            else:
                items.extend((group, english, russian, None) for english, russian in dictionary_examples.get(group_id, ()))
        if state.word_source == "static":
            items.extend(
                (GROUP_BY_ID[word.group_id], word.english, word.russian, word.base_word)
                for word in preset.study_words
            )
        items.extend(
            (GROUP_BY_ID[word.group_id], word.english, word.russian, word.base_word)
            for word in preset.exception_words
        )

    if state.include_all_exceptions:
        items.extend(
            (GROUP_BY_ID[word.group_id], word.english, word.russian, word.base_word)
            for word in ALL_PRESET_EXCEPTION_WORDS
        )

    unique_items = {
        (group.id, english.casefold(), russian.casefold(), source_word.casefold() if source_word else None):
        (group, english, russian, source_word)
        for group, english, russian, source_word in items
    }
    return list(unique_items.values())


def parsed_dictionary_words() -> list[tuple[str, str]]:
    words = {
        (english.casefold(), russian.casefold()): (english, russian)
        for examples in dictionary_examples.values()
        for english, russian in examples
    }
    return sorted(words.values(), key=lambda item: (item[0].casefold(), item[1].casefold()))


def split_message_lines(lines: list[str], limit: int = 3500) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for line in lines:
        added_length = len(line) + (1 if current else 0)
        if current and current_length + added_length > limit:
            chunks.append("\n".join(current))
            current = []
            current_length = 0
        current.append(line)
        current_length += len(line) + (1 if len(current) > 1 else 0)
    if current:
        chunks.append("\n".join(current))
    return chunks


def make_question(state: UserState) -> QuizQuestion | None:
    examples = active_examples(state)
    if not examples:
        return None
    group, english, russian, source_word = random.choice(examples)
    state.current_question = QuizQuestion(
        group_id=group.id,
        english=english,
        russian=russian,
        source_word=source_word,
    )
    return state.current_question


def normalize_answer(value: str) -> str:
    value = value.lower().strip()
    if value.startswith("to "):
        value = value[3:]
    return " ".join(value.replace("‑", "-").split())


BASE_WORD_OVERRIDES = {
    "biography": "life",
    "biology": "life",
    "centimetre": "metre",
    "centigrade": "grade",
    "happiness": "happy",
    "darkness": "dark",
    "growth": "grow",
    "difference": "differ",
    "freedom": "free",
    "creativity": "create",
    "responsibility": "responsible",
    "pleasure": "please",
    "chinese": "China",
    "japanese": "Japan",
    "mexican": "Mexico",
    "russian": "Russia",
    "dictionary": "dictate",
    "directorate": "director",
    "scholarly": "scholar",
    "quickly": "quick",
    "happily": "happy",
    "yearly": "year",
    "awkward": "awkward",
}


def base_word(question: QuizQuestion) -> str:
    """Return the English stem to show alongside the affix meaning."""
    if question.source_word:
        return question.source_word
    word = question.english.removeprefix("to ").lower()
    if word in dictionary_base_words:
        return dictionary_base_words[word]
    if word in BASE_WORD_OVERRIDES:
        return BASE_WORD_OVERRIDES[word]

    group = GROUP_BY_ID[question.group_id]
    if group.kind == "Префикс":
        prefixes = (
            "contra", "extra", "super", "ultra", "under", "inter", "multi", "trans",
            "centi", "semi", "over", "poly", "tele", "sub", "pre", "mis", "non",
            "dis", "out", "bio", "co", "re", "de", "un", "in", "il", "ir", "im",
            "en", "em", "ex", "by", "up",
        )
        for prefix in prefixes:
            if word.startswith(f"{prefix}-"):
                return word[len(prefix) + 1:]
            if word.startswith(prefix) and len(word) > len(prefix) + 1:
                return word[len(prefix):]
        return word

    suffix_rules = (
        ("ization", "ize"), ("ation", "ate"), ("ition", "ite"), ("sion", "de"),
        ("tion", "te"), ("ment", ""), ("ness", ""), ("hood", ""), ("ship", ""),
        ("dom", ""), ("ity", "e"), ("ance", ""), ("ence", ""), ("able", ""),
        ("ible", "e"), ("ive", ""), ("ful", ""), ("less", ""), ("ous", ""),
        ("ery", ""), ("ism", ""), ("ist", ""), ("eer", ""), ("ee", ""),
        ("er", ""), ("or", ""), ("ly", ""), ("ward", ""), ("ize", ""),
        ("en", ""), ("al", ""), ("ic", ""), ("y", ""),
    )
    for suffix, replacement in suffix_rules:
        if word.endswith(suffix) and len(word) > len(suffix):
            return f"{word[:-len(suffix)]}{replacement}"
    return word


@router.message(CommandStart())
async def start(message: Message) -> None:
    state = user_state(message.from_user.id)
    sent = await message.answer(**main_content().as_kwargs(), reply_markup=main_keyboard())
    state.main_message_id = sent.message_id


@router.message(Command("list"))
async def list_parsed_words(message: Message) -> None:
    words = parsed_dictionary_words()
    if not words:
        await message.answer(
            "Слова Wiktionary ещё загружаются. Подожди немного и повтори /list."
        )
        return

    await message.answer(**as_list(Bold("Слова Wiktionary"), f"Загружено: {len(words)}.").as_kwargs())
    lines = [f"{html.escape(english)} - {html.escape(russian)}" for english, russian in words]
    for chunk in split_message_lines(lines):
        await message.answer(chunk)


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
            message = (
                "В динамичном режиме пока нет слов Wiktionary. Подожди завершения загрузки и проверь выбранные группы."
                if state.word_source == "dynamic"
                else "Сначала выбери пресет или включи хотя бы одну обычную группу."
            )
            await callback.answer(message, show_alert=True)
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
    previous_question = state.current_question
    if previous_question is None:
        await callback.answer("Сейчас нет вопроса.", show_alert=True)
        return
    state.quiz_enabled = True
    question = make_question(state)
    if question is None:
        state.quiz_enabled = False
        await callback.answer("Нет включенных групп.", show_alert=True)
        return
    result = Text("Правильный ответ: ", Bold(previous_question.english), ".")
    await edit_question(bot, callback.message.chat.id, state, prefix=result)
    await callback.answer()


@router.callback_query(F.data == "quiz:hint")
async def quiz_hint(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    question = state.current_question
    if question is None:
        await callback.answer("Сейчас нет вопроса.", show_alert=True)
        return
    group = GROUP_BY_ID[question.group_id]
    await callback.answer(
        f"Подсказка: {group.group}\nБазовое слово: {base_word(question)}",
        show_alert=True,
    )


@router.callback_query(F.data == "quiz:source")
async def quiz_source(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    state.word_source = "dynamic" if state.word_source == "static" else "static"
    await safe_edit_content(callback.message, quiz_menu_content(state), quiz_menu_keyboard(state))
    await callback.answer()


@router.callback_query(F.data.startswith("quiz:groups:"))
async def quiz_groups(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    state.main_message_id = callback.message.message_id
    page = int(callback.data.rsplit(":", 1)[1])
    await safe_edit_content(callback.message, group_settings_content(state), group_settings_keyboard(state, page))
    await callback.answer()


@router.callback_query(F.data.startswith("quiz:preset:"))
async def quiz_preset_toggle(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    _, _, preset_id, page_raw = callback.data.split(":")
    if preset_id in state.enabled_preset_ids:
        state.enabled_preset_ids.remove(preset_id)
    else:
        state.enabled_preset_ids.add(preset_id)
    page = int(page_raw)
    await safe_edit_content(callback.message, group_settings_content(state), group_settings_keyboard(state, page))
    await callback.answer()


@router.callback_query(F.data.startswith("quiz:all_exceptions:"))
async def quiz_all_exceptions_toggle(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    state.include_all_exceptions = not state.include_all_exceptions
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
    all_group_ids = {group.id for group in SELECTABLE_AFFIX_GROUPS}
    all_preset_ids = {preset.id for preset in QUIZ_PRESETS}
    if (
        all_group_ids.issubset(state.enabled_group_ids)
        and all_preset_ids.issubset(state.enabled_preset_ids)
        and state.include_all_exceptions
    ):
        state.enabled_group_ids.clear()
        state.enabled_preset_ids.clear()
        state.include_all_exceptions = False
    else:
        state.enabled_group_ids = all_group_ids
        state.enabled_preset_ids = all_preset_ids
        state.include_all_exceptions = True
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
async def reminders_toggle(callback: CallbackQuery, bot: Bot) -> None:
    state = user_state(callback.from_user.id)
    state.main_message_id = callback.message.message_id
    reminder = state.reminders
    reminder.enabled = not reminder.enabled
    if not reminder.enabled:
        await delete_reminder_notification(bot, callback.from_user.id, reminder)
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


@router.callback_query(F.data.startswith("rem:quiet_start:"))
async def reminder_quiet_start(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    state.main_message_id = callback.message.message_id
    delta = int(callback.data.rsplit(":", 1)[1])
    state.reminders.quiet_start_hour = (state.reminders.quiet_start_hour + delta) % 24
    await safe_edit_content(callback.message, reminders_content(state), reminder_keyboard(state))
    await callback.answer()


@router.callback_query(F.data.startswith("rem:quiet_end:"))
async def reminder_quiet_end(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    state.main_message_id = callback.message.message_id
    delta = int(callback.data.rsplit(":", 1)[1])
    state.reminders.quiet_end_hour = (state.reminders.quiet_end_hour + delta) % 24
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


@router.callback_query(F.data == "rem:close")
async def close_reminder(callback: CallbackQuery) -> None:
    state = user_state(callback.from_user.id)
    reminder = state.reminders
    if callback.message.message_id != reminder.notification_message_id:
        await callback.answer("Это уведомление уже закрыто.")
        return
    reminder.notification_message_id = None
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message()
async def answer_quiz(message: Message, bot: Bot) -> None:
    state = user_state(message.from_user.id)
    question = state.current_question
    if not state.quiz_enabled or question is None:
        await message.answer("Открой /start и выбери действие через кнопки.")
        return
    correct = normalize_answer(message.text or "") == normalize_answer(question.english)
    result = Text(
        "Верно. Правильный ответ: " if correct else "Неверно. Правильный ответ: ",
        Bold(question.english),
        ".",
    )
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    next_question = make_question(state)
    if next_question is None:
        return
    await edit_question(bot, message.chat.id, state, prefix=result)


def is_quiet_time(now: datetime, reminder: ReminderSettings) -> bool:
    start = reminder.quiet_start_hour
    end = reminder.quiet_end_hour
    if start == end:
        return False
    if start < end:
        return start <= now.hour < end
    return now.hour >= start or now.hour < end


def reset_daily_counter(reminder: ReminderSettings, now: datetime) -> None:
    if reminder.sent_on == now.date():
        return
    reminder.sent_on = now.date()
    reminder.sent_today = 0
    reminder.last_sent_at = None


async def delete_reminder_notification(bot: Bot, user_id: int, reminder: ReminderSettings) -> None:
    message_id = reminder.notification_message_id
    reminder.notification_message_id = None
    if message_id is None:
        return
    try:
        await bot.delete_message(user_id, message_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        pass


async def send_reminder_notification(bot: Bot, user_id: int, reminder: ReminderSettings) -> bool:
    await delete_reminder_notification(bot, user_id, reminder)
    try:
        sent = await bot.send_message(
            user_id,
            "Пора повторить частички.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="Закрыть уведомление",
                    callback_data="rem:close",
                    style="danger",
                )],
            ]),
        )
    except (TelegramBadRequest, TelegramForbiddenError):
        return False
    reminder.notification_message_id = sent.message_id
    return True


async def reminder_loop(bot: Bot) -> None:
    while True:
        now = datetime.now(REMINDER_TIMEZONE)
        for user_id, state in list(states.items()):
            reminder = state.reminders
            reset_daily_counter(reminder, now)
            if not reminder.enabled:
                continue
            if now.weekday() in reminder.disabled_weekdays or is_quiet_time(now, reminder):
                continue
            if reminder.sent_today >= reminder.times_per_day:
                continue
            if reminder.last_sent_at is not None:
                elapsed = (now - reminder.last_sent_at).total_seconds() / 60
                if elapsed < reminder.interval_minutes:
                    continue
            if await send_reminder_notification(bot, user_id, reminder):
                reminder.sent_today += 1
                reminder.last_sent_at = now
        await asyncio.sleep(30)


async def load_wiktionary_quiz_words() -> None:
    examples, bases = await load_wiktionary_words()
    dictionary_examples.update(examples)
    dictionary_base_words.update(bases)
    loaded_count = sum(len(words) for words in examples.values())
    logging.getLogger(__name__).info("Loaded %s Wiktionary quiz words", loaded_count)


async def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set. Create .env from .env.example and put your Telegram bot token there.")
    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(router)
    asyncio.create_task(reminder_loop(bot))
    asyncio.create_task(load_wiktionary_quiz_words())
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
