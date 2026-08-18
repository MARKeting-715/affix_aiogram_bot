from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class AffixGroup:
    id: str
    kind: str
    group: str
    affixes: str
    ru_analog: str
    examples: tuple[tuple[str, str], ...]

    @property
    def parts_count(self) -> int:
        return len(split_affixes(self.affixes))


def split_affixes(value: str) -> list[str]:
    parts = re.split(r",\s*", value)
    return [part.strip() for part in parts if part.strip()]


AFFIX_GROUPS: tuple[AffixGroup, ...] = (
    AffixGroup("p_bio", "Префикс", "Жизнь, живые существа", "bio-", "био-", (("biography", "биография"), ("biology", "биология"))),
    AffixGroup("p_by", "Префикс", "Второстепенность, побочность", "by-", "", (("by-play", "эпизод"), ("by-work", "побочная работа"), ("bystreet", "переулок, улочка"))),
    AffixGroup("p_centi", "Префикс", "Количество: сто, сотая часть", "cent(i)-", "санти-", (("centimetre", "сантиметр"), ("centigrade", "стоградусный, разделенный на сто градусов"))),
    AffixGroup("p_co", "Префикс", "Совместность, общность действий", "co-", "ко-, со-", (("co-operate", "сотрудничать"), ("co-education", "совместное обучение"), ("co-pilot", "второй пилот"), ("co-author", "соавтор"), ("co-existence", "сосуществование"))),
    AffixGroup("p_negative", "Префикс", "Противоположное или отрицательное значение", "contra-, de-, dis-, in-/il-/ir-/im-, non-, un-", "контр-, де-, дис-, не-, без-/бес-, нон-", (("to disagree", "не соглашаться"), ("to dislike", "не любить"), ("to disappear", "исчезать"), ("incorrect", "неправильный"), ("inexpensive", "недорогой"), ("illegal", "незаконный"), ("irregular", "нерегулярный"), ("impolite", "невежливый"), ("non-stop", "без перерыва"), ("unhappy", "несчастливый"), ("unusual", "необычный"))),
    AffixGroup("p_reverse", "Префикс", "Обратное действие, отмена сделанного", "un-, re-", "раз-/рас-, пере-, снова", (("to unpack", "распаковывать"), ("to unfold", "распускаться"), ("to undo", "уничтожать сделанное"), ("to redo", "переделать"))),
    AffixGroup("p_en", "Префикс", "Включение внутрь или приведение в состояние", "en-/em-", "", (("to encase", "упаковывать, класть в ящик"), ("to enslave", "порабощать"), ("to encourage", "ободрять"), ("to enrich", "обогащать"))),
    AffixGroup("p_ex", "Префикс", "Изъятие, исключение; бывший, прежний", "ex-", "экс-", (("to extract", "вытаскивать"), ("ex-president", "экс-президент"))),
    AffixGroup("p_over", "Префикс", "Сверх-, над-, пере-, чрезмерно", "extra-, over-, super-, ultra-", "экстра-, сверх-, супер-, ультра-", (("extraordinary", "чрезвычайный, необычный"), ("to overcharge", "перегружать"), ("to overheat", "перегревать"), ("overcrowded", "переполненный людьми"), ("supermarket", "универсам"), ("ultramodern", "сверхсовременный"))),
    AffixGroup("p_inter", "Префикс", "Меж-, между-, среди", "inter-", "интер-, меж-", (("international", "международный"), ("interstellar", "межзвездный"))),
    AffixGroup("p_mis", "Префикс", "Неправильно, ложно", "mis-", "мис- (редко), не-/зло- по смыслу", (("to misunderstand", "неправильно понимать"), ("to misapply", "злоупотреблять"))),
    AffixGroup("p_multi", "Префикс", "Много-, поли-, мульти-", "multi-, poly-", "мульти-, поли-", (("multimillionaire", "мультимиллионер"), ("polyglot", "полиглот"), ("polytechnic", "политехнический"))),
    AffixGroup("p_out", "Префикс", "Превосходство, выход наружу, удаленность", "out-", "пере-, вы-, вне-", (("to outcry", "перекричать"), ("outbreak", "взрыв, вспышка"), ("outdoor", "находящийся вне дома"))),
    AffixGroup("p_pre", "Префикс", "До-, пред-, впереди, заранее", "pre-", "пре-/пред-", (("preface", "предисловие"), ("prehistoric", "доисторический"))),
    AffixGroup("p_semi", "Префикс", "Полу-", "semi-", "семи-, полу-", (("semifinal", "полуфинал"), ("semicircle", "полукруг"))),
    AffixGroup("p_sub", "Префикс", "Ниже, подчинение, неполнота", "sub-, under-", "суб-, под-, недо-", (("submarine", "подводная лодка"), ("subnormal", "ниже нормального"), ("underground", "подземный"), ("undersized", "маломерный, низкорослый"), ("under-age", "несовершеннолетний"))),
    AffixGroup("p_tele", "Префикс", "Связь на расстоянии", "tele-", "теле-", (("telegram", "телеграмма"), ("television", "телевидение"))),
    AffixGroup("p_trans", "Префикс", "Через, транс-, изменение формы или состояния", "trans-", "транс-", (("transatlantic", "трансатлантический"), ("to transform", "изменять, трансформировать"), ("transplantation", "пересадка, трансплантация"))),
    AffixGroup("p_up", "Префикс", "Вверх, кверху, наверху", "up-", "", (("upstairs", "вверх по лестнице"), ("upside", "верхняя сторона или часть"))),
    AffixGroup("s_able", "Суффикс", "Возможность подвергнуться действию", "-able, -ible", "-абельн-, -ибельн-; по смыслу: -мый", (("fashionable", "модный"), ("responsible", "ответственный"), ("eatable", "съедобный"), ("reducible", "допускающий уменьшение"), ("convertible", "обратимый"))),
    AffixGroup("s_nouns", "Суффикс", "Образование существительных", "-ade, -age, -ance/-ence, -cy/-acy, -dom, -hood, -ics, -ity, -ment, -ness, -th, -tion/-sion/-ation/-ition, -ure", "-ада, -аж, -ция, -ика, -изм, -мент, -ость, -ство, -ура", (("blockade", "блокада"), ("difference", "различие"), ("freedom", "свобода"), ("kingdom", "королевство"), ("creativity", "творчество"), ("responsibility", "ответственность"), ("government", "правительство"), ("development", "развитие"), ("improvement", "улучшение"), ("darkness", "темнота"), ("happiness", "счастье"), ("growth", "рост"), ("relation", "отношение, связь"), ("departure", "отъезд, уход"), ("pleasure", "удовольствие"))),
    AffixGroup("s_adj_nouns", "Суффикс", "Образование прилагательных от существительных", "-al, -an/-ian, -ant/-ent, -ary, -ate, -ese, -ful, -ic, -less, -ly, -ous, -y", "-альн-, -анск-, -антн-, -арн-, -ик/-ическ-, без-/бес- по смыслу", (("verbal", "устный"), ("logical", "логичный"), ("cultural", "культурный"), ("significant", "важный"), ("different", "другой, отличающийся"), ("Chinese", "китайский"), ("fruitful", "плодотворный"), ("careful", "заботливый"), ("poetic", "поэтический"), ("priceless", "бесценный"), ("dangerous", "опасный"), ("cloudy", "облачный"))),
    AffixGroup("s_ive", "Суффикс", "Образование прилагательных со значением исходного глагола", "-ive", "-ивн-", (("active", "активный"), ("constructive", "конструктивный"), ("talkative", "разговорчивый"))),
    AffixGroup("s_verbs", "Суффикс", "Образование глаголов", "-ate, -en, -ize", "-ировать, -изировать, -изовать", (("to elevate", "поднимать, повышать"), ("broaden", "расширять"), ("threaten", "угрожать"), ("blacken", "чернеть"), ("to criticize", "критиковать"), ("to computerize", "компьютеризировать"))),
    AffixGroup("s_person", "Суффикс", "Лицо, выполняющее действие или связанное с основой", "-ee, -eer, -er, -ese, -ist, -or", "-ер, -ёр, -ист, -ор; -ец/-анин по смыслу", (("employee", "служащий"), ("addressee", "адресат"), ("writer", "писатель"), ("reader", "читатель"), ("runner", "бегун"), ("artist", "художник"), ("motorist", "автомобилист"), ("governor", "правитель"), ("dictator", "диктатор"))),
    AffixGroup("s_ery", "Суффикс", "Место, занятие, деятельность, состояние", "-ery", "-ерия/-ария; -ство по смыслу", (("bakery", "пекарня, булочная"), ("surgery", "кабинет хирурга"), ("cookery", "кулинария"), ("pottery", "гончарное дело"), ("slavery", "рабство"))),
    AffixGroup("s_ship", "Суффикс", "Состояние отношений, положение в обществе", "-ship", "-ство", (("friendship", "дружба"), ("partnership", "партнерство, сотрудничество"), ("professorship", "профессорство"))),
    AffixGroup("s_ism", "Суффикс", "Учение, политическое движение, типизация", "-ism", "-изм", (("socialism", "социализм"), ("Buddhism", "буддизм"), ("Americanism", "американизм"))),
    AffixGroup("s_adv_ly", "Суффикс", "Наречия от прилагательных", "-ly", "", (("quickly", "быстро"), ("happily", "счастливо"))),
    AffixGroup("s_period_ly", "Суффикс", "Временная периодичность: прилагательное или наречие", "-ly", "", (("yearly", "ежегодный, один раз в год"), ("monthly", "ежемесячный, один раз в месяц"))),
    AffixGroup("s_ward", "Суффикс", "Направление: прилагательное или наречие", "-ward", "", (("backward", "назад"), ("homeward", "домой"), ("awkward", "неуклюжий"))),
    AffixGroup("s_ful", "Суффикс", "Полное количество или обладание качеством", "-ful", "по смыслу: -ный, полный", (("fruitful", "плодотворный"), ("careful", "заботливый"), ("peaceful", "мирный"), ("doubtful", "сомнительный"), ("handful", "горсть, пригоршня"))),
    AffixGroup("s_national", "Суффикс", "Национальная принадлежность", "-an/-ian, -ese", "-анин/-янин, -ец, -ск- по смыслу", (("Mexican", "мексиканец, мексиканский"), ("Russian", "русский язык, русский"), ("Chinese", "китайский, китаец"), ("Japanese", "японский, японец"))),
    AffixGroup("s_multi_meaning", "Суффикс", "Существительные или прилагательные с несколькими значениями", "-ary, -ate, -ly", "-арн-, -атн-, -ат; иногда -ный/-но по смыслу", (("dictionary", "словарь"), ("directorate", "дирекция"), ("scholarly", "ученый, свойственный ученым"), ("yearly", "ежегодный"), ("quickly", "быстро"))),
)

GROUP_BY_ID = {group.id: group for group in AFFIX_GROUPS}


def groups_by_kind(kind: str) -> list[AffixGroup]:
    return sorted(
        [group for group in AFFIX_GROUPS if group.kind == kind],
        key=lambda group: (group.parts_count, group.affixes.lower(), group.group.lower()),
    )
