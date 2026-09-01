from __future__ import annotations

import asyncio
import html
import re
from typing import Any

from affix_data import AFFIX_GROUPS, AffixGroup, split_affixes


API_BASE_URL = "https://dictionary.cambridge.org/api/v1"
MAX_WORDS = 500
TRANSLATION_RE = re.compile(r'<[^>]*class="[^"]*trans[^"]*"[^>]*>(.*?)</[^>]+>', re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


PREFIX_ROOTS = (
    "agree", "appear", "approve", "build", "charge", "cook", "cover", "do", "fair",
    "fold", "friend", "happy", "heat", "kind", "like", "lock", "manage", "normal",
    "pack", "pay", "place", "possible", "read", "regular", "safe", "sign", "start",
    "trust", "usual", "visible", "work", "write",
)

PREFIXES = (
    "un", "re", "dis", "mis", "non", "over", "under", "pre", "sub", "inter", "trans",
)


def normal_word(value: str) -> str:
    return value.removeprefix("to ").lower().replace("-", "")


def candidate_words() -> tuple[str, ...]:
    words = {normal_word(word) for group in AFFIX_GROUPS for word, _ in group.examples}
    words.update(f"{prefix}{root}" for prefix in PREFIXES for root in PREFIX_ROOTS)
    return tuple(sorted(words))[:MAX_WORDS]


def group_for_word(word: str) -> AffixGroup | None:
    normalized = normal_word(word)
    matches: list[tuple[int, AffixGroup]] = []
    for group in AFFIX_GROUPS:
        for affix in split_affixes(group.affixes):
            clean = re.sub(r"\([^)]*\)", "", affix).strip("- ").lower().replace("/", "")
            if not clean:
                continue
            if group.kind == "Префикс" and normalized.startswith(clean):
                matches.append((len(clean), group))
            if group.kind == "Суффикс" and normalized.endswith(clean):
                matches.append((len(clean), group))
    return max(matches, default=(0, None), key=lambda item: item[0])[1]


def find_russian_translation(entry_content: str) -> str | None:
    for match in TRANSLATION_RE.findall(entry_content):
        translation = html.unescape(TAG_RE.sub("", match)).strip()
        if translation and re.search(r"[А-Яа-яЁё]", translation):
            return " ".join(translation.split())
    return None


def find_base_word(entry_content: str) -> str | None:
    patterns = (
        r"(?:derived|formed)\s+from\s+<[^>]+>([^<]+)</",
        r"<[^>]*class=\"[^\"]*(?:deriv|base)[^\"]*\"[^>]*>([^<]+)</",
    )
    for pattern in patterns:
        match = re.search(pattern, entry_content, re.IGNORECASE)
        if match:
            return html.unescape(match.group(1)).strip()
    return None


def find_dictionary_code(payload: Any) -> str | None:
    stack: list[Any] = [payload]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            name = str(item.get("dictionaryName", "")).lower()
            code = item.get("dictionaryCode")
            if code and "english-russian" in name:
                return str(code)
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    return None


async def response_json(session: Any, url: str, access_key: str, **params: str) -> Any | None:
    try:
        async with session.get(
            url,
            params=params,
            headers={"Accept": "application/json", "accessKey": access_key},
            timeout=15,
        ) as response:
            if response.status != 200:
                return None
            return await response.json(content_type=None)
    except (asyncio.TimeoutError, OSError):
        return None


async def load_words(access_key: str, dictionary_code: str | None = None) -> tuple[dict[str, list[tuple[str, str]]], dict[str, str]]:
    from aiohttp import ClientSession

    async with ClientSession() as session:
        if not dictionary_code:
            dictionaries = await response_json(session, f"{API_BASE_URL}/dictionaries", access_key)
            dictionary_code = find_dictionary_code(dictionaries)
        if not dictionary_code:
            return {}, {}

        semaphore = asyncio.Semaphore(6)

        async def load_one(word: str) -> tuple[str, str, str | None] | None:
            async with semaphore:
                payload = await response_json(
                    session,
                    f"{API_BASE_URL}/dictionaries/{dictionary_code}/search/first",
                    access_key,
                    q=word,
                    format="html",
                )
            if not isinstance(payload, dict):
                return None
            content = str(payload.get("entryContent", ""))
            translation = find_russian_translation(content)
            if not translation:
                return None
            label = str(payload.get("entryLabel", word)).strip().lower()
            return label, translation, find_base_word(content)

        loaded = await asyncio.gather(*(load_one(word) for word in candidate_words()))

    examples: dict[str, list[tuple[str, str]]] = {}
    bases: dict[str, str] = {}
    for item in loaded:
        if item is None:
            continue
        word, translation, base = item
        group = group_for_word(word)
        if group is None:
            continue
        examples.setdefault(group.id, []).append((word, translation))
        if base:
            bases[word] = base
    return examples, bases
