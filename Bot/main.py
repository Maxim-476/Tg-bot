from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

from datetime import datetime
import csv
import os

TOKEN = os.getenv("BOT_TOKEN")

# Если знаешь свой chat_id, вставь сюда число.
# Если пока не знаешь, оставь 0.
ADMIN_CHAT_ID = 0

ASK_NAME, ASK_PHONE, ASK_COMMENT = range(3)


def main_menu():
    return ReplyKeyboardMarkup(
        [
            ["Оставить заявку"],
            ["Услуги", "О боте"],
            ["Контакты"],
        ],
        resize_keyboard=True,
    )


def contact_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Отправить номер телефона", request_contact=True)],
            ["Назад"],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def save_request_to_csv(name: str, phone: str, comment: str):
    file_exists = os.path.isfile("requests.csv")

    with open("requests.csv", "a", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(["Дата", "Имя", "Телефон", "Комментарий"])

        writer.writerow([
            datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            name,
            phone,
            comment,
        ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Здравствуйте. Я бот для приема заявок.\n\n"
        "Здесь можно оставить заявку, посмотреть услуги и связаться с менеджером.",
        reply_markup=main_menu(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Доступные действия:\n"
        "Оставить заявку\n"
        "Услуги\n"
        "О боте\n"
        "Контакты",
        reply_markup=main_menu(),
    )


async def services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Наши услуги:\n"
        "1. Создание Telegram-ботов\n"
        "2. Лендинги под ключ\n"
        "3. Автоматизация заявок\n"
        "4. Интеграции с Google Sheets"
    )


async def about_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Этот бот демонстрирует прием заявок через Telegram.\n"
        "Он умеет собирать имя, телефон и комментарий клиента."
    )


async def contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Связь с менеджером:\n"
        "Ответим после получения заявки в боте."
    )


async def request_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введите ваше имя:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()

    await update.message.reply_text(
        "Теперь отправьте номер телефона.",
        reply_markup=contact_keyboard(),
    )
    return ASK_PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = ""

    if update.message.contact:
        phone = update.message.contact.phone_number
    elif update.message.text:
        if update.message.text.strip().lower() == "назад":
            await update.message.reply_text(
                "Вы вернулись в главное меню.",
                reply_markup=main_menu(),
            )
            return ConversationHandler.END
        phone = update.message.text.strip()

    context.user_data["phone"] = phone

    await update.message.reply_text(
        "Напишите комментарий к заявке.\n"
        "Например: какой бот нужен, для какого бизнеса, какие функции нужны."
    )
    return ASK_COMMENT


async def get_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment = update.message.text.strip()
    name = context.user_data.get("name", "")
    phone = context.user_data.get("phone", "")

    save_request_to_csv(name, phone, comment)

    if ADMIN_CHAT_ID != 0:
        text_for_admin = (
            "Новая заявка\n\n"
            f"Имя: {name}\n"
            f"Телефон: {phone}\n"
            f"Комментарий: {comment}"
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text_for_admin)

    await update.message.reply_text(
        "Спасибо. Ваша заявка принята.\n"
        "Мы свяжемся с вами в ближайшее время.",
        reply_markup=main_menu(),
    )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Действие отменено.",
        reply_markup=main_menu(),
    )
    return ConversationHandler.END


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()

    if text == "оставить заявку":
        return await request_start(update, context)
    elif text == "услуги":
        await services(update, context)
    elif text == "о боте":
        await about_bot(update, context)
    elif text == "контакты":
        await contacts(update, context)
    else:
        await update.message.reply_text(
            "Выберите действие из меню.",
            reply_markup=main_menu(),
        )


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    request_handler = ConversationHandler(
        entry_points=[
            CommandHandler("request", request_start),
            MessageHandler(filters.Regex("^Оставить заявку$"), request_start),
        ],
        states={
            ASK_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name),
            ],
            ASK_PHONE: [
                MessageHandler(filters.CONTACT, get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone),
            ],
            ASK_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_comment),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex("^Назад$"), cancel),
        ],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("services", services))
    app.add_handler(request_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    print("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()