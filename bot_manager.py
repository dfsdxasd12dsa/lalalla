from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import List

import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

BASE_DIR = Path(__file__).resolve().parent
TOKENS_PATH = BASE_DIR / "token.txt"
MESSAGE_PATH = BASE_DIR / "message.txt"
BUTTONS_PATH = BASE_DIR / "button.txt"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s",
)


def read_non_empty_lines(path: Path) -> List[str]:
    if not path.exists():
        return []

    lines = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def read_message() -> str:
    if not MESSAGE_PATH.exists():
        return "Привет! Напиши текст в message.txt"

    text = MESSAGE_PATH.read_text(encoding="utf-8").strip()
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


def run_bot(token: str) -> None:
    bot = telebot.TeleBot(token, parse_mode="HTML")

    @bot.message_handler(commands=["start"])
    def handle_start(message):  # type: ignore[no-untyped-def]
        text = read_message()
        keyboard = build_keyboard()
        bot.send_message(message.chat.id, text, reply_markup=keyboard)

    @bot.callback_query_handler(func=lambda call: True)
    def noop_callback(call):  # type: ignore[no-untyped-def]
        bot.answer_callback_query(call.id)

    logging.info("Bot is starting polling")
    bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)


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
