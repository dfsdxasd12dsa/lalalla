# Multi-token Telegram start bot

Софт запускает сразу несколько Telegram-ботов из `token.txt`.

## Что умеет

- Поддержка **множества токенов** (каждый токен на новой строке в `token.txt`).
- Команда `/start` отправляет текст из `message.txt`.
- Кнопки берутся из `button.txt`.
- Изменения в `message.txt` и `button.txt` применяются **сразу** (без перезапуска), потому что файлы читаются на каждый `/start`.

## Формат файлов

### `token.txt`

Каждая строка — отдельный токен бота:

```text
12345:AA...
67890:BB...
```

### `message.txt`

Любой текст, который нужно отправлять в `/start`.

### `button.txt`

- Одна строка = один ряд кнопок.
- Кнопки в ряду разделяются `;`.
- Формат кнопки со ссылкой: `Текст|https://example.com`
- Если без `|`, создаётся обычная callback-кнопка (без действия).

Пример:

```text
Канал|https://t.me/example;Сайт|https://example.com
Поддержка|https://t.me/support
```

## Запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 bot_manager.py
```
