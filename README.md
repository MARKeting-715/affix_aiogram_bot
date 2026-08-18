# Affix Trainer Bot

Telegram-бот на `aiogram 3.30+` для тренировки английских префиксов и суффиксов.

Главное изменение: раздел "Таблица" отправляется как Telegram Rich Message с настоящим HTML `<table>`, а не как псевдотаблица в обычном тексте. Если Telegram API или установленная версия `aiogram` не поддержит rich tables, бот автоматически покажет обычный текстовый fallback.

## Запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Вставьте токен в `.env`, затем:

```powershell
python bot.py
```

Бот не использует БД: настройки, прогресс опроса и напоминания живут в памяти процесса. После перезапуска они сбрасываются.
