import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from analyzer import analyze_contract, format_result
from parser import parse_document

load_dotenv()

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Анализатор договоров*\n\n"
        "Я проверю договор на юридические риски и соответствие 214-ФЗ.\n\n"
        "Отправь мне:\n"
        "• 📄 Файл договора (PDF, DOCX, TXT)\n"
        "• 📝 Текст договора сообщением\n\n"
        "_Анализ занимает 15-30 секунд._",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Справка*\n\n"
        "/start — начало работы\n"
        "/help — эта справка\n\n"
        "Поддерживаемые форматы: PDF, DOCX, TXT\n"
        "Максимальный размер файла: 20 МБ\n\n"
        "При анализе проверяются:\n"
        "• Общие юридические риски (ответственность, сроки, штрафы)\n"
        "• Соответствие 214-ФЗ (для ДДУ)",
        parse_mode=ParseMode.MARKDOWN,
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if len(text) < 100:
        await update.message.reply_text(
            "Текст слишком короткий. Пришли полный текст договора (минимум 100 символов)."
        )
        return

    msg = await update.message.reply_text("⏳ Анализирую договор...")

    try:
        result = await analyze_contract(text)
        formatted = format_result(result)
        await msg.edit_text(formatted, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка анализа текста: {e}")
        await msg.edit_text(f"❌ Ошибка анализа: {e}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file_name = doc.file_name or "document"
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""

    if ext not in ("pdf", "docx", "txt"):
        await update.message.reply_text(
            "❌ Неподдерживаемый формат. Пришли PDF, DOCX или TXT."
        )
        return

    msg = await update.message.reply_text("📥 Скачиваю файл...")

    try:
        tg_file = await context.bot.get_file(doc.file_id)
        content = await tg_file.download_as_bytearray()
        content = bytes(content)
    except Exception as e:
        logger.error(f"Ошибка скачивания файла: {e}")
        await msg.edit_text(f"❌ Не удалось скачать файл: {e}")
        return

    await msg.edit_text("🔍 Извлекаю текст...")

    try:
        text = parse_document(content, file_name)
    except ValueError as e:
        await msg.edit_text(f"❌ {e}")
        return
    except Exception as e:
        logger.error(f"Ошибка парсинга {file_name}: {e}")
        await msg.edit_text(f"❌ Не удалось прочитать файл: {e}")
        return

    if len(text.strip()) < 100:
        await msg.edit_text("❌ Не удалось извлечь текст из документа.")
        return

    await msg.edit_text("⏳ Анализирую договор...")

    try:
        result = await analyze_contract(text)
        formatted = format_result(result)
        await msg.edit_text(formatted, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка анализа {file_name}: {e}")
        await msg.edit_text(f"❌ Ошибка анализа: {e}")


def main():
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN не задан в .env")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Бот запущен")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
