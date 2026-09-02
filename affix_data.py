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


@dataclass(frozen=True)
class StudyWord:
    group_id: str
    base_word: str
    english: str
    russian: str


@dataclass(frozen=True)
class StudyExceptionSet:
    title: str
    group_ids: frozenset[str]
    words: tuple[StudyWord, ...]


@dataclass(frozen=True)
class QuizPreset:
    id: str
    title: str
    group_ids: frozenset[str]
    study_words: tuple[StudyWord, ...]
    exception_words: tuple[StudyWord, ...]


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
    AffixGroup("s_able", "Суффикс", "выражает возможность подвергнуться действию", "-able, -ible", "", (("fashionable", "модный"), ("responsible", "ответственный"), ("eatable", "съедобный"), ("reducible", "допускающий уменьшение"), ("convertible", "обратимый"))),
    AffixGroup("s_noun_common", "Суффикс", "для образования существительных", "-ade, -age, -ance (-ence), -ary, -ate, -ure", "", (("blockade", "блокада"), ("lemonade", "лимонад"), ("postage", "почтовые расходы"), ("village", "деревня, село"), ("marriage", "брак"), ("difference", "различие"), ("assistance", "помощь, содействие"), ("dictionary", "словарь"), ("directorate", "дирекция"), ("departure", "отъезд, уход"), ("pleasure", "удовольствие"))),
    AffixGroup("s_al", "Суффикс", "образует прилагательные от существительных", "-al", "", (("verbal", "устный"), ("logical", "логичный"), ("cultural", "культурный"), ("formal", "формальный"))),
    AffixGroup("s_national", "Суффикс", "для обозначения национальной принадлежности", "-an (-ian)", "", (("Mexican", "мексиканец, мексиканка; мексиканский"), ("Russian", "русский (язык); русский"))),
    AffixGroup("s_adj_common", "Суффикс", "для образования прилагательных", "-ant (-ent), -ary, -ate, -ic", "", (("significant", "важный"), ("different", "другой, отличающийся"), ("assistant", "помощник, ассистент"), ("accountant", "бухгалтер"), ("reactionary", "реакционный"), ("revolutionary", "революционный"), ("affectionate", "любящий, нежный"), ("literate", "грамотный"), ("poetic", "поэтический"), ("historic", "исторический"), ("climatic", "климатический"))),
    AffixGroup("s_ate_verb", "Суффикс", "для образования глаголов", "-ate", "", (("to elevate", "поднимать, повышать"),)),
    AffixGroup("s_cy", "Суффикс", "для образования существительных со значением состояния, качества", "-cy (-acy)", "", (("accuracy", "точность, правильность"), ("infancy", "младенчество"), ("supremacy", "превосходство"))),
    AffixGroup("s_dom", "Суффикс", "для образования существительных со значением состояния или владения", "-dom", "", (("wisdom", "мудрость"), ("freedom", "свобода"), ("kingdom", "королевство"))),
    AffixGroup("s_ee", "Суффикс", "для образования существительных, называющих лицо, занятие или деятельность которого обозначена исходным глаголом", "-ee", "", (("employee", "служащий"), ("addressee", "адресат"), ("trustee", "доверенное лицо"))),
    AffixGroup("s_eer", "Суффикс", "для образования существительных, называющих лицо, связанное по смыслу с исходным существительным", "-eer", "", (("auctioneer", "аукционер"), ("mountaineer", "альпинист, горец"))),
    AffixGroup("s_en", "Суффикс", "для образования глаголов от прилагательных и существительных", "-en", "", (("broaden", "расширять"), ("threaten", "угрожать"), ("blacken", "чернеть"))),
    AffixGroup("s_er", "Суффикс", "для образования существительных, называющих лицо, выполняющее действие", "-er", "", (("writer", "писатель"), ("reader", "читатель"), ("runner", "бегун"), ("philosopher", "философ"), ("seller", "продавец"))),
    AffixGroup("s_ery_place", "Суффикс", "место, где происходит действие", "-ery", "", (("bakery", "пекарня, булочная"), ("surgery", "кабинет хирурга"))),
    AffixGroup("s_ery_activity", "Суффикс", "занятие, деятельность", "-ery", "", (("cookery", "кулинария"), ("pottery", "гончарное дело"))),
    AffixGroup("s_ery_state", "Суффикс", "состояние, черты характера", "-ery", "", (("slavery", "рабство"), ("snobbery", "снобизм"))),
    AffixGroup("s_ese", "Суффикс", "от существительных, называющих страну или местность, образуются соответствующие прилагательные или существительные, обозначающие жителей этой страны", "-ese", "", (("Chinese", "китайский; китаец, китаянка"), ("Japanese", "японский; японец, японка"))),
    AffixGroup("s_ful", "Суффикс", "обладающий качеством или обозначает полное количество чего-либо", "-ful", "", (("fruitful", "плодотворный"), ("careful", "заботливый"), ("peaceful", "мирный"), ("doubtful", "сомнительный"), ("handful", "горсть, пригоршня"))),
    AffixGroup("s_hood", "Суффикс", "состояние, степень отношений", "-hood", "", (("brotherhood", "братство"), ("neighbourhood", "соседство"))),
    AffixGroup("s_ics", "Суффикс", "для образования существительных, называющих отрасль науки, род занятий", "-ics", "", (("physics", "физика"), ("politics", "политика"), ("athletics", "атлетика"))),
    AffixGroup("s_ism_teaching", "Суффикс", "для образования существительных со значением: учение, политическое движение и т.д.", "-ism", "", (("socialism", "социализм"), ("Buddhism", "буддизм"))),
    AffixGroup("s_ism_type", "Суффикс", "для образования существительных со значением: наиболее полное воплощение, типизация", "-ism", "", (("Americanism", "американизм"),)),
    AffixGroup("s_ist", "Суффикс", "для образования существительных, называющих лицо, занимающееся какой-либо деятельностью, специалиста в какой-либо области, последователя учения и т.д.", "-ist", "", (("artist", "художник"), ("motorist", "автомобилист"), ("marxist", "марксист"), ("terrorist", "террорист"))),
    AffixGroup("s_noun_from_adj", "Суффикс", "для образования существительных от прилагательных", "-ity, -th", "", (("brutality", "жестокость"), ("creativity", "творчество"), ("curiosity", "любознательность"), ("diversity", "разнообразие"), ("equality", "равенство"), ("generosity", "великодушие"), ("popularity", "популярность"), ("productivity", "производительность"), ("prosperity", "преуспевание"), ("responsibility", "ответственность"), ("security", "безопасность"), ("similarity", "сходство"), ("breadth", "широта"), ("depth", "глубина"), ("growth", "рост"), ("length", "длина"), ("strength", "сила"), ("warmth", "теплота"), ("width", "широта"), ("youth", "молодость"))),
    AffixGroup("s_ive", "Суффикс", "для образования прилагательных с соответствующим исходному глаголу значением", "-ive", "", (("active", "активный"), ("constructive", "конструктивный"), ("talkative", "разговорчивый"))),
    AffixGroup("s_ize", "Суффикс", "для образования глаголов с соответствующим исходному слову значением", "-ize", "", (("to criticize", "критиковать"), ("to computerize", "компьютеризировать"))),
    AffixGroup("s_less", "Суффикс", "означает отсутствие качества", "-less", "", (("priceless", "бесценный"), ("shameless", "бесстыдный"))),
    AffixGroup("s_ly_noun", "Суффикс", "для образования прилагательных со значением исходного существительного", "-ly", "", (("scholarly", "ученый; свойственный ученым"),)),
    AffixGroup("s_ly_time", "Суффикс", "для образования прилагательных или наречий от существительных, обозначающих временные понятия", "-ly", "", (("yearly", "ежегодный; один раз в год"), ("monthly", "ежемесячный; один раз в месяц"))),
    AffixGroup("s_ly_adv", "Суффикс", "для образования наречий от прилагательных", "-ly", "", (("quickly", "быстро"), ("happily", "счастливо"))),
    AffixGroup("s_ment", "Суффикс", "результат или средство действия для образования существительных от глаголов", "-ment", "", (("government", "правительство"), ("measurement", "измерение"), ("accomplishment", "выполнение"), ("achievement", "достижение"), ("advertisement", "объявление, реклама"), ("agreement", "соглашение"), ("amusement", "увеселение"), ("announcement", "объявление"), ("argument", "аргумент"), ("arrangement", "приведение в порядок"), ("development", "развитие"), ("discouragement", "разочарование"), ("equipment", "оборудование"), ("employment", "занятость"), ("entertainment", "развлечение"), ("excitement", "возбуждение"), ("improvement", "улучшение"), ("investment", "инвестиция"), ("involvement", "вовлеченность"), ("management", "управление, менеджмент"), ("movement", "движение"), ("payment", "оплата"), ("punishment", "наказание"))),
    AffixGroup("s_ness", "Суффикс", "состояние, наличие качества и т.д. для образования существительных", "-ness", "", (("bitterness", "горечь"), ("blindness", "слепота"), ("carelessness", "недобросовестность"), ("darkness", "темнота"), ("effectiveness", "эффективность"), ("goodness", "доброта"), ("happiness", "счастье"), ("hardness", "твердость"), ("illness", "болезнь"), ("kindness", "доброта"), ("loneliness", "одиночество"), ("sickness", "болезнь"), ("weakness", "слабость"))),
    AffixGroup("s_or", "Суффикс", "лицо или устройство, выполняющее действие, обозначенное исходным глаголом", "-or", "", (("governor", "правитель"), ("dictator", "диктатор"), ("elevator", "грузоподъемник, элеватор"))),
    AffixGroup("s_ous", "Суффикс", "наличие качества, выраженного исходным существительным", "-ous", "", (("dangerous", "опасный"), ("poisonous", "ядовитый"), ("furious", "взбешенный"))),
    AffixGroup("s_ship", "Суффикс", "состояние отношений, положение (в обществе) и т.д.", "-ship", "", (("friendship", "дружба"), ("partnership", "партнерство, сотрудничество"), ("professorship", "профессорство"))),
    AffixGroup("s_tion", "Суффикс", "для образования существительных, связанных по смыслу с исходными глаголами", "-tion, -sion, -ation, -ition", "", (("relation", "отношение, связь"), ("confession", "признание"), ("adhesion", "прилипание, верность"), ("hesitation", "сомнение, колебание"), ("competition", "соревнование"))),
    AffixGroup("s_ward", "Суффикс", "для образования прилагательного или наречия", "-ward", "", (("backward", "назад"), ("homeward", "домой"), ("awkward", "неуклюжий"))),
    AffixGroup("s_y", "Суффикс", "для образования прилагательных от существительных", "-y", "", (("dusty", "пыльный"), ("bushy", "покрытый кустарником"), ("cloudy", "облачный"))),
)


NOUNS_FROM_VERBS_TITLE = "8.1. Nouns from verbs"
NOUNS_FROM_VERBS_GROUPS: tuple[AffixGroup, ...] = (
    AffixGroup("nv_age", "Суффикс", f"{NOUNS_FROM_VERBS_TITLE}: результат или место действия", "-age", "", (("passage", "проход, отрывок"),)),
    AffixGroup("nv_al", "Суффикс", f"{NOUNS_FROM_VERBS_TITLE}: существительное от глагола", "-al", "", (("arrival", "прибытие"),)),
    AffixGroup("nv_ance", "Суффикс", f"{NOUNS_FROM_VERBS_TITLE}: существительное от глагола", "-ance", "", (("ignorance", "невежество"),)),
    AffixGroup("nv_ation", "Суффикс", f"{NOUNS_FROM_VERBS_TITLE}: действие или результат действия", "-ation", "", (("admiration", "восхищение"),)),
    AffixGroup("nv_ence", "Суффикс", f"{NOUNS_FROM_VERBS_TITLE}: существительное от глагола", "-ence", "", (("dependence", "зависимость"),)),
    AffixGroup("nv_er", "Суффикс", f"{NOUNS_FROM_VERBS_TITLE}: лицо, выполняющее действие", "-er", "", (("employer", "работодатель"),)),
    AffixGroup("nv_ion", "Суффикс", f"{NOUNS_FROM_VERBS_TITLE}: действие или результат действия", "-ion", "", (("confusion", "путаница"),)),
    AffixGroup("nv_or", "Суффикс", f"{NOUNS_FROM_VERBS_TITLE}: лицо или устройство", "-or", "", (("detector", "детектор"),)),
    AffixGroup("nv_ment", "Суффикс", f"{NOUNS_FROM_VERBS_TITLE}: действие или результат действия", "-ment", "", (("improvement", "улучшение"),)),
    AffixGroup("nv_sion", "Суффикс", f"{NOUNS_FROM_VERBS_TITLE}: действие или результат действия", "-sion", "", (("division", "разделение"),)),
    AffixGroup("nv_tion", "Суффикс", f"{NOUNS_FROM_VERBS_TITLE}: действие или результат действия", "-tion", "", (("invention", "изобретение"),)),
    AffixGroup("nv_ure", "Суффикс", f"{NOUNS_FROM_VERBS_TITLE}: действие или результат действия", "-ure", "", (("failure", "неудача"),)),
    AffixGroup("nv_y", "Суффикс", f"{NOUNS_FROM_VERBS_TITLE}: действие или результат действия", "-y", "", (("recovery", "восстановление"),)),
    AffixGroup("nv_ee", "Суффикс", f"{NOUNS_FROM_VERBS_TITLE}: лицо, на которое направлено действие", "-ee", "", (("employee", "сотрудник"),)),
    AffixGroup("nv_ant", "Суффикс", f"{NOUNS_FROM_VERBS_TITLE}: лицо или предмет, связанный с действием", "-ant", "", (("inhabitant", "житель"),)),
)
NOUNS_FROM_VERBS_GROUP_IDS = frozenset(group.id for group in NOUNS_FROM_VERBS_GROUPS)
NOUNS_FROM_VERBS_EXCEPTION_GROUP = AffixGroup(
    "nv_exceptions",
    "Суффикс",
    f"{NOUNS_FROM_VERBS_TITLE}: слова-исключения",
    "исключения",
    "",
    (),
)

NOUNS_FROM_VERBS_STUDY_WORDS: tuple[StudyWord, ...] = (
    StudyWord("nv_ance", "accept", "acceptance", "принятие"),
    StudyWord("nv_sion", "admit", "admission", "допуск, прием"),
    StudyWord("nv_ment", "advertise", "advertisement", "объявление, реклама"),
    StudyWord("nv_ment", "announce", "announcement", "объявление"),
    StudyWord("nv_ation", "apply", "application", "заявление, применение"),
    StudyWord("nv_al", "approve", "approval", "одобрение"),
    StudyWord("nv_ment", "arrange", "arrangement", "договоренность, расположение"),
    StudyWord("nv_ance", "assist", "assistance", "помощь"),
    StudyWord("nv_ance", "attend", "attendance", "посещаемость"),
    StudyWord("nv_ion", "attract", "attraction", "привлекательность"),
    StudyWord("nv_ion", "celebrate", "celebration", "празднование"),
    StudyWord("nv_ation", "combine", "combination", "сочетание"),
    StudyWord("nv_sion", "confess", "confession", "признание"),
    StudyWord("nv_ation", "continue", "continuation", "продолжение"),
    StudyWord("nv_sion", "decide", "decision", "решение"),
    StudyWord("nv_al", "deny", "denial", "отрицание"),
    StudyWord("nv_tion", "describe", "description", "описание"),
    StudyWord("nv_tion", "dictate", "dictation", "диктовка"),
    StudyWord("nv_ment", "disappoint", "disappointment", "разочарование"),
    StudyWord("nv_y", "discover", "discovery", "открытие"),
    StudyWord("nv_sion", "divide", "division", "разделение"),
    StudyWord("nv_ation", "educate", "education", "образование"),
    StudyWord("nv_ion", "elect", "election", "выборы"),
    StudyWord("nv_ment", "employ", "employment", "занятость"),
    StudyWord("nv_ment", "excite", "excitement", "возбуждение"),
    StudyWord("nv_ence", "exist", "existence", "существование"),
    StudyWord("nv_ation", "explain", "explanation", "объяснение"),
    StudyWord("nv_ation", "hesitate", "hesitation", "колебание"),
    StudyWord("nv_ation", "imagine", "imagination", "воображение"),
    StudyWord("nv_ation", "imitate", "imitation", "имитация"),
    StudyWord("nv_ion", "impress", "impression", "впечатление"),
    StudyWord("nv_ment", "improve", "improvement", "улучшение"),
    StudyWord("nv_ence", "insist", "insistence", "настойчивость"),
    StudyWord("nv_ion", "interrupt", "interruption", "прерывание"),
    StudyWord("nv_tion", "introduce", "introduction", "введение"),
    StudyWord("nv_sion", "invade", "invasion", "вторжение"),
    StudyWord("nv_tion", "invent", "invention", "изобретение"),
    StudyWord("nv_age", "marry", "marriage", "брак"),
    StudyWord("nv_ure", "mix", "mixture", "смесь"),
    StudyWord("nv_ation", "operate", "operation", "операция"),
    StudyWord("nv_age", "pass", "passage", "проход, отрывок"),
    StudyWord("nv_ance", "perform", "performance", "исполнение, производительность"),
    StudyWord("nv_sion", "permit", "permission", "разрешение"),
    StudyWord("nv_sion", "possess", "possession", "владение"),
    StudyWord("nv_ence", "prefer", "preference", "предпочтение"),
    StudyWord("nv_ation", "prepare", "preparation", "подготовка"),
    StudyWord("nv_er", "produce", "producer", "производитель"),
    StudyWord("nv_tion", "produce", "production", "производство"),
    StudyWord("nv_tion", "protect", "protection", "защита"),
    StudyWord("nv_ment", "punish", "punishment", "наказание"),
    StudyWord("nv_ation", "qualify", "qualification", "квалификация"),
    StudyWord("nv_tion", "receive", "reception", "прием"),
    StudyWord("nv_ence", "refer", "reference", "ссылка"),
    StudyWord("nv_al", "refuse", "refusal", "отказ"),
    StudyWord("nv_tion", "repeat", "repetition", "повторение"),
    StudyWord("nv_er", "research", "researcher", "исследователь"),
    StudyWord("nv_ation", "restore", "restoration", "восстановление"),
    StudyWord("nv_sion", "revise", "revision", "пересмотр"),
    StudyWord("nv_ion", "satisfy", "satisfaction", "удовлетворение"),
    StudyWord("nv_ion", "solve", "solution", "решение"),
    StudyWord("nv_ion", "suggest", "suggestion", "предложение"),
    StudyWord("nv_tion", "translate", "translation", "перевод"),
    StudyWord("nv_ment", "treat", "treatment", "лечение, обращение"),
)

NOUNS_FROM_VERBS_EXCEPTION_SETS: tuple[StudyExceptionSet, ...] = (
    StudyExceptionSet(
        "Слова-исключения: Nouns from verbs",
        NOUNS_FROM_VERBS_GROUP_IDS,
        (
            StudyWord("nv_exceptions", "advise", "advice", "совет"),
            StudyWord("nv_exceptions", "behave", "behaviour", "поведение"),
            StudyWord("nv_exceptions", "believe", "belief", "вера"),
            StudyWord("nv_exceptions", "fly", "flight", "полет"),
            StudyWord("nv_exceptions", "grow", "growth", "рост"),
            StudyWord("nv_exceptions", "hate", "hatred", "ненависть"),
            StudyWord("nv_exceptions", "know", "knowledge", "знание"),
            StudyWord("nv_exceptions", "live", "life", "жизнь"),
            StudyWord("nv_exceptions", "lose", "loss", "потеря"),
            StudyWord("nv_exceptions", "choose", "choice", "выбор"),
            StudyWord("nv_exceptions", "complain", "complaint", "жалоба"),
            StudyWord("nv_exceptions", "die", "death", "смерть"),
            StudyWord("nv_exceptions", "practise", "practice", "практика"),
            StudyWord("nv_exceptions", "prove", "proof", "доказательство"),
            StudyWord("nv_exceptions", "serve", "service", "услуга, служба"),
            StudyWord("nv_exceptions", "speak", "speech", "речь"),
            StudyWord("nv_exceptions", "think", "thought", "мысль"),
            StudyWord("nv_exceptions", "weigh", "weight", "вес"),
        ),
    ),
)

AFFIX_GROUPS = AFFIX_GROUPS + NOUNS_FROM_VERBS_GROUPS
NOUNS_FROM_VERBS_PRESET = QuizPreset(
    "nouns_from_verbs",
    "Suffixes forming nouns from verbs",
    NOUNS_FROM_VERBS_GROUP_IDS,
    NOUNS_FROM_VERBS_STUDY_WORDS,
    tuple(word for exception_set in NOUNS_FROM_VERBS_EXCEPTION_SETS for word in exception_set.words),
)
QUIZ_PRESETS: tuple[QuizPreset, ...] = (NOUNS_FROM_VERBS_PRESET,)
PRESET_BY_ID = {preset.id: preset for preset in QUIZ_PRESETS}
PRESET_GROUP_IDS = frozenset(group_id for preset in QUIZ_PRESETS for group_id in preset.group_ids)
SELECTABLE_AFFIX_GROUPS = tuple(group for group in AFFIX_GROUPS if group.id not in PRESET_GROUP_IDS)
GROUP_BY_ID = {
    **{group.id: group for group in AFFIX_GROUPS},
    NOUNS_FROM_VERBS_EXCEPTION_GROUP.id: NOUNS_FROM_VERBS_EXCEPTION_GROUP,
}


def groups_by_kind(kind: str) -> list[AffixGroup]:
    return sorted(
        [group for group in AFFIX_GROUPS if group.kind == kind],
        key=lambda group: (group.parts_count, group.affixes.lower(), group.group.lower()),
    )
