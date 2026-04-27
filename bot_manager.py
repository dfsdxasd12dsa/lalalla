from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import List

import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

BASE_DIR = Path(__file__).resolve().parent
TOKENS_PATH = BASE_DIR / "token.txt"
MESSAGE_PATH = BASE_DIR / "message.txt"
BUTTONS_PATH = BASE_DIR / "button.txt"

GREEN = "\033[92m"
RESET = "\033[0m"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s",
)


def is_conflict_marker(line: str) -> bool:
    return line.startswith(("<<<<<<<", "=======", ">>>>>>>"))


def read_non_empty_lines(path: Path) -> List[str]:
    if not path.exists():
        return []

    lines = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if is_conflict_marker(line):
            continue
        lines.append(line)
    return lines


def read_message() -> str:
    if not MESSAGE_PATH.exists():
        return "Привет! Напиши текст в message.txt"

    clean_lines = []
    for raw_line in MESSAGE_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if is_conflict_marker(line.strip()):
            continue
        clean_lines.append(line)

    text = "\n".join(clean_lines).strip()
    return text or "Привет! Файл message.txt пустой."


def build_keyboard() -> InlineKeyboardMarkup | None:
    rows = read_non_empty_lines(BUTTONS_PATH)
    if not rows:
        return None

    keyboard = InlineKeyboardMarkup()

    for row in rows:
        buttons = []
        for item in [part.strip() for part in row.split(";") if part.strip()]:
            if "|" in item:
                text, url = [x.strip() for x in item.split("|", maxsplit=1)]
                if text and url:
                    buttons.append(InlineKeyboardButton(text=text, url=url))
            else:
                buttons.append(InlineKeyboardButton(text=item, callback_data=f"noop:{item}"))

        if buttons:
            keyboard.row(*buttons)

    return keyboard if keyboard.keyboard else None


def safe_username(username: str | None) -> str:
    return f"@{username}" if username else "no_username"


def log_start_event(bot_name: str, message) -> None:  # type: ignore[no-untyped-def]
    user = message.from_user
    full_name = user.full_name if user else "unknown"
    username = safe_username(user.username if user else None)
    user_id = user.id if user else "unknown"
    chat_id = message.chat.id if message.chat else "unknown"

    log_line = (
        f"user={full_name}({username}|id={user_id}) / "
        f"bot={bot_name} / start / chat={chat_id}"
    )
    print(f"{GREEN}{log_line}{RESET}")


def run_bot(token: str) -> None:
    bot = telebot.TeleBot(token, parse_mode="HTML")

    try:
        me = bot.get_me()
        bot_name = f"@{me.username}" if me.username else f"id:{me.id}"
        bot.delete_webhook(drop_pending_updates=False)
        logging.info("Webhook removed for %s", bot_name)
    except ApiTelegramException as exc:
        if exc.error_code == 401:
            logging.error("Token is invalid (401). Bot skipped.")
            return
        logging.error("Cannot prepare bot token: %s", exc)
        return
    except Exception as exc:
        logging.error("Unexpected prepare error: %s", exc)
        return

    @bot.message_handler(commands=["start"])
    def handle_start(message):  # type: ignore[no-untyped-def]
        log_start_event(bot_name, message)
        text = read_message()
        keyboard = build_keyboard()
        bot.send_message(message.chat.id, text, reply_markup=keyboard)

    @bot.callback_query_handler(func=lambda call: True)
    def noop_callback(call):  # type: ignore[no-untyped-def]
        bot.answer_callback_query(call.id)

    logging.info("Bot polling started for %s", bot_name)

    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
        except ApiTelegramException as exc:
            if exc.error_code == 409:
                logging.warning(
                    "409 conflict for %s (webhook active). Trying to delete webhook and continue.",
                    bot_name,
                )
                try:
                    bot.delete_webhook(drop_pending_updates=False)
                except Exception as inner_exc:
                    logging.error("Webhook delete failed for %s: %s", bot_name, inner_exc)
                time.sleep(3)
                continue
            if exc.error_code == 401:
                logging.error("Unauthorized 401 for %s. Stopping this bot thread.", bot_name)
                return
            logging.error("Telegram API error for %s: %s", bot_name, exc)
            time.sleep(3)
        except Exception as exc:
            logging.error("Polling error for %s: %s", bot_name, exc)
            time.sleep(3)


def main() -> None:
    tokens = read_non_empty_lines(TOKENS_PATH)
    if not tokens:
        raise RuntimeError(
            "Не найдено токенов. Добавьте токены (по одному в строке) в token.txt"
        )

    threads: List[threading.Thread] = []

    for index, token in enumerate(tokens, start=1):
        thread = threading.Thread(
            target=run_bot,
            name=f"bot-{index}",
            args=(token,),
            daemon=True,
        )
        thread.start()
        threads.append(thread)
        logging.info("Started bot-%s", index)

    while True:
        alive = [t for t in threads if t.is_alive()]
        if not alive:
            raise RuntimeError("Все потоки ботов завершились")
        time.sleep(2)


if __name__ == "__main__":
    main()
