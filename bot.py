#!/usr/bin/env python3
"""
Telegram бот: принимает Instagram ссылки и отправляет их с "kk" перед "instagram" в группу.
Конфигурация через переменные окружения:
  BOT_TOKEN  — токен бота от @BotFather (обязательно)
  GROUP_ID   — chat_id целевой группы (можно задать командой /setgroup)
"""

import asyncio
import logging
import re
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# ========================
#  НАСТРОЙКИ (из окружения)
# ========================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8689479853:AAFkghfWKIVKyHxNFTpdQAsD_ZucK84BHNM")

# ID группы: сначала смотрим переменную окружения, потом временную переменную
_runtime_group_id: int | None = None

def get_group_id() -> int | None:
    env_val = os.environ.get("GROUP_ID")
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            pass
    return _runtime_group_id

# ========================
#  ЛОГИРОВАНИЕ
# ========================
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========================
#  ТРАНСФОРМАЦИЯ ССЫЛКИ
# ========================
INSTAGRAM_PATTERN = re.compile(r'https?://(?:www\.)?instagram\.com\S*')

def transform_link(url: str) -> str:
    """Добавляет 'kk' перед 'instagram' в URL."""
    return re.sub(r'(https?://(?:www\.)?)instagram', r'\1kkinstagram', url)

# ========================
#  ОБРАБОТЧИКИ
# ========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает сообщения с Instagram-ссылками."""
    if not update.message or not update.message.text:
        return

    text = update.message.text

    if not INSTAGRAM_PATTERN.search(text):
        return

    modified = INSTAGRAM_PATTERN.sub(lambda m: transform_link(m.group()), text)
    group_id = get_group_id()

    if group_id:
        try:
            await context.bot.send_message(chat_id=group_id, text=modified)
            logger.info(f"Отправлено в группу {group_id}: {modified}")
            if update.message.chat.type == "private":
                await update.message.reply_text("✅ Готово! Ссылка отправлена в группу.")
        except Exception as e:
            logger.error(f"Ошибка отправки в группу: {e}")
            await update.message.reply_text(
                f"❌ Ошибка отправки в группу: {e}\n\nМодифицированная ссылка:\n{modified}"
            )
    else:
        await update.message.reply_text(
            f"⚠️ Группа не настроена.\n\n"
            f"Напиши /setgroup в целевой группе.\n\n"
            f"Модифицированная ссылка:\n{modified}"
        )


async def cmd_setgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/setgroup — запоминает текущую группу как целевую (до перезапуска)."""
    global _runtime_group_id
    chat = update.message.chat
    if chat.type in ("group", "supergroup"):
        _runtime_group_id = chat.id
        await update.message.reply_text(
            f"✅ Группа «{chat.title}» установлена!\n"
            f"ID: `{chat.id}`\n\n"
            f"⚠️ Чтобы сохранить навсегда на Railway — добавь переменную:\n"
            f"`GROUP_ID = {chat.id}`",
            parse_mode="Markdown"
        )
        logger.info(f"Целевая группа: {chat.title} ({chat.id})")
    else:
        await update.message.reply_text("❗ Эту команду нужно использовать в группе.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/status — показывает текущие настройки."""
    group_id = get_group_id()
    source = "переменная окружения GROUP_ID" if os.environ.get("GROUP_ID") else "временная (до перезапуска)"

    if group_id:
        try:
            chat = await context.bot.get_chat(group_id)
            await update.message.reply_text(
                f"✅ Бот активен\n"
                f"📢 Группа: «{chat.title}»\n"
                f"ID: `{group_id}`\n"
                f"Источник: {source}",
                parse_mode="Markdown"
            )
        except Exception:
            await update.message.reply_text(
                f"⚠️ GROUP_ID = `{group_id}` задан, но группа недоступна.\n"
                f"Убедись, что бот добавлен в группу.",
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text(
            "⚠️ Группа не настроена.\n"
            "Напиши /setgroup в группе или задай переменную GROUP_ID на Railway."
        )


async def on_bot_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Автоматически запоминает группу при добавлении бота."""
    global _runtime_group_id
    if not update.message or not update.message.new_chat_members:
        return
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            _runtime_group_id = update.message.chat_id
            await update.message.reply_text(
                f"👋 Привет! Я готов к работе!\n"
                f"Буду пересылать Instagram-ссылки с заменой на kkinstagram.com\n\n"
                f"Отправь мне ссылку в личку — я перешлю её сюда ✅\n\n"
                f"ID этой группы: `{update.message.chat_id}`",
                parse_mode="Markdown"
            )
            logger.info(f"Бот добавлен в группу: {update.message.chat.title} ({update.message.chat_id})")


# ========================
#  ЗАПУСК
# ========================
async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не задан!")

    logger.info("Запуск бота...")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("setgroup", cmd_setgroup))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_bot_added))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    group_id = get_group_id()
    logger.info(f"Бот запущен. GROUP_ID = {group_id or 'не задан'}")

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
