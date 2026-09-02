from __future__ import annotations

import asyncio
import re
from typing import Any

from affix_data import AFFIX_GROUPS, NOUNS_FROM_VERBS_STUDY_WORDS, AffixGroup, split_affixes


WIKTIONARY_API_URL = "https://en.wiktionary.org/w/api.php"
MAX_WORDS = 500
REQUEST_CONCURRENCY = 2
REQUEST_DELAY_SECONDS = 0.2
MAX_RETRIES = 3
USER_AGENT = "affix-aiogram-bot/1.0 (educational Telegram bot)"
ENGLISH_SECTION_RE = re.compile(
    r"^==English==\s*(.*?)(?=^==[^=].*?==|\Z)",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
RUSSIAN_TRANSLATION_RE = re.compile(
    r"\{\{(?:t|t\+|t-simple|tt)\|ru\|([^|}#]+)",
    re.IGNORECASE,
)


def normal_word(value: str) -> str:
    return value.removeprefix("to ").lower().replace("-", "")


def candidate_words() -> tuple[str, ...]:
    study_words = {normal_word(word) for group in AFFIX_GROUPS for word, _ in group.examples}
    study_words.update(normal_word(word.english) for word in NOUNS_FROM_VERBS_STUDY_WORDS)
    prefix_roots = (
        "agree", "appear", "approve", "build", "charge", "cook", "cover", "do", "fair",
        "fold", "friend", "happy", "heat", "kind", "like", "lock", "manage", "normal",
        "pack", "pay", "place", "possible", "read", "regular", "safe", "sign", "start",
        "trust", "usual", "visible", "work", "write",
    )
    prefixes = ("un", "re", "dis", "mis", "non", "over", "under", "pre", "sub", "inter", "trans")
    generated_words = {
        f"{prefix}{root}"
        for prefix in prefixes
        for root in prefix_roots
        if f"{prefix}{root}" not in study_words
    }
    remaining = max(0, MAX_WORDS - len(study_words))
    return tuple(sorted(study_words)) + tuple(sorted(generated_words))[:remaining]


def groups_for_word(word: str) -> tuple[AffixGroup, ...]:
    normalized = normal_word(word)
    matches: list[AffixGroup] = []
    for group in AFFIX_GROUPS:
        for affix in split_affixes(group.affixes):
            clean = re.sub(r"\([^)]*\)", "", affix).strip("- ").lower().replace("/", "")
            if not clean:
                continue
            if group.kind == "Префикс" and normalized.startswith(clean):
                matches.append(group)
            if group.kind == "Суффикс" and normalized.endswith(clean):
                matches.append(group)
    return tuple({group.id: group for group in matches}.values())


def find_russian_translation(wikitext: str) -> str | None:
    section = ENGLISH_SECTION_RE.search(wikitext)
    if section is None:
        return None
    for match in RUSSIAN_TRANSLATION_RE.finditer(section.group(1)):
        translation = match.group(1).strip().replace("_", " ")
        if translation:
            return translation
    return None


async def request_wikitext(session: Any, word: str) -> str | None:
    params = {
        "action": "parse",
        "page": word,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
    }
    for attempt in range(MAX_RETRIES):
        try:
            async with session.get(
                WIKTIONARY_API_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            ) as response:
                if response.status == 200:
                    payload = await response.json(content_type=None)
                    if isinstance(payload, dict):
                        parsed = payload.get("parse")
                        if isinstance(parsed, dict) and parsed.get("wikitext"):
                            return str(parsed["wikitext"])
                    return None
                if response.status not in {429, 502, 503, 504}:
                    return None
        except (asyncio.TimeoutError, OSError):
            pass
        await asyncio.sleep(1 + attempt)
    return None


async def load_words() -> tuple[dict[str, list[tuple[str, str]]], dict[str, str]]:
    from aiohttp import ClientSession

    semaphore = asyncio.Semaphore(REQUEST_CONCURRENCY)

    async with ClientSession() as session:
        async def load_one(word: str) -> tuple[str, str] | None:
            async with semaphore:
                wikitext = await request_wikitext(session, word)
                await asyncio.sleep(REQUEST_DELAY_SECONDS)
            if not wikitext:
                return None
            translation = find_russian_translation(wikitext)
            return (word, translation) if translation else None

        loaded = await asyncio.gather(*(load_one(word) for word in candidate_words()))

    examples: dict[str, list[tuple[str, str]]] = {}
    for item in loaded:
        if item is None:
            continue
        word, translation = item
        for group in groups_for_word(word):
            examples.setdefault(group.id, []).append((word, translation))
    return examples, {}
