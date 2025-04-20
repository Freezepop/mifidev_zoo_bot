import logging
import smtplib
from email.message import EmailMessage
from db import save_result, save_feedback, get_result, init_db
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, InlineQueryHandler

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = ""

STAFF_EMAIL = ""
SENDER_EMAIL = ""
SENDER_PASSWORD = ""

questions = [
    {
        "question": "Где ты мечтаешь проводить выходные?",
        "answers": [
            ("🏔 В лесу", "los"),
            ("🛏 Под пледом", "surikat"),
            ("🌴 В джунглях", "serval"),
            ("🌍 В путешествии", "kapibara")
        ]
    },
    {
        "question": "Что ты предпочитаешь на ужин?",
        "answers": [
            ("🥗 Овощи", "kapibara"),
            ("🥩 Мясо", "serval"),
            ("🍕 Пицца", "surikat"),
            ("🍌 Фрукты", "lemur")
        ]
    },
    {
        "question": "Какая у тебя суперсила?",
        "answers": [
            ("💡 Хитрость", "mangobey"),
            ("😌 Спокойствие", "los"),
            ("⚡ Быстрота", "serval"),
            ("👀 Внимательность", "surikat")
        ]
    }
]

animals = {
    "los": {
        "title": "🦌 Ты — Лось!",
        "desc": "Мудрый и независимый. Наш Лаврентий любит яблоки и одиночество.",
        "image": "photo_animals/los.jpg"
    },
    "surikat": {
        "title": "🦴 Ты — Сурикат!",
        "desc": "Ты любопытный, внимательный и командный игрок. Как Сима из зоопарка.",
        "image": "photo_animals/surikat.jpg"
    },
    "serval": {
        "title": "🐆 Ты — Сервал!",
        "desc": "Изящный охотник с характером. Любишь движение и охоту за приключениями.",
        "image": "photo_animals/serval.jpg"
    },
    "kapibara": {
        "title": "🛁 Ты — Капибара!",
        "desc": "Спокойный философ. Наш Чапа обожает лежать в ванне с травой.",
        "image": "photo_animals/kapibara.jpg"
    },
    "lemur": {
        "title": "🌴 Ты — Лемур!",
        "desc": "Обожаешь фрукты, прыжки и танцы. Очень общительный и весёлый.",
        "image": "photo_animals/lemur.jpg"
    },
    "mangobey": {
        "title": "🐒 Ты — Хохлатый мангобей!",
        "desc": "Энергичный и хулиганистый. Любишь быть в центре внимания.",
        "image": "photo_animals/mangobey.jpg"
    }
}


user_data = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await init_db()

    user_id = update.effective_user.id

    existing = await get_result(user_id)

    if existing and existing in animals:
        info = animals[existing]

        keyboard = [
            [InlineKeyboardButton("Узнать об опеке 🐾", url="https://moscowzoo.ru/contacts")],
            [InlineKeyboardButton("Попробовать ещё раз? 🔁", callback_data="restart")],
            [InlineKeyboardButton("Оставить отзыв 💬", callback_data="feedback")],
            [InlineKeyboardButton("Связаться с сотрудником 📩", callback_data="contact_staff")],
            [InlineKeyboardButton("Поделиться с друзьями 📢", switch_inline_query=f" - попробуй этого бота!\nЯ прошел викторину и мой результат:\n{info['title']}\n{info['desc']}\nПопробуй и ты! https://t.me/{context.bot.username}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        with open(info["image"], "rb") as photo:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=photo,
                caption=f"{info['title']}\n\n{info['desc']}",
                reply_markup=reply_markup
            )
        return

    user_data[user_id] = {"current_q": 0, "score": {}}

    await update.message.reply_text(
        "Привет! 🐾 Хочешь узнать своё тотемное животное в Московском зоопарке?\n\nПоехали!"
    )
    await send_question(update, context)


async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    q_index = data["current_q"]

    if q_index >= len(questions):
        await show_result(update, context)
        return

    question = questions[q_index]
    buttons = [
        [InlineKeyboardButton(text=ans[0], callback_data=ans[1])] for ans in question["answers"]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        try:
            # Пытаемся отредактировать текст, если это возможно
            await update.callback_query.edit_message_text(
                question["question"], reply_markup=reply_markup
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=question["question"],
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text(question["question"], reply_markup=reply_markup)



async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    answer = query.data
    data = user_data[user_id]

    data["score"][answer] = data["score"].get(answer, 0) + 1
    data["current_q"] += 1

    await send_question(update, context)


async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_data.get(user_id, {}).get("result_shown"):
        await update.callback_query.answer("Результат уже показан.")
        return

    scores = user_data[user_id]["score"]
    top_animal = max(scores, key=scores.get)
    info = animals[top_animal]

    try:
        await save_result(user_id, top_animal)
    except Exception as e:
        print(f"Ошибка при сохранении результата в БД: {e}")

    keyboard = [
        [InlineKeyboardButton("Узнать об опеке 🐾", url="https://moscowzoo.ru/contacts")],
        [InlineKeyboardButton("Попробовать ещё раз? 🔁", callback_data="restart")],
        [InlineKeyboardButton("Оставить отзыв 💬", callback_data="feedback")],
        [InlineKeyboardButton("Связаться с сотрудником 📩", callback_data="contact_staff")],
        [InlineKeyboardButton("Поделиться с друзьями 📢", switch_inline_query=f" - попробуй этого бота!\nЯ прошел викторину и мой результат:\n{info['title']}\n{info['desc']}\nПопробуй и ты! https://t.me/{context.bot.username}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    with open(info["image"], "rb") as photo:
        media = InputMediaPhoto(media=photo, caption=f"{info['title']}\n\n{info['desc']}")
        try:
            await update.callback_query.edit_message_media(
                media=media,
                reply_markup=reply_markup
            )
            user_data[user_id]["result_shown"] = True
        except Exception as e:
            print(f"Ошибка при редактировании медиа: {e}")
            await update.callback_query.answer("Ошибка при отображении результата.")


async def contact_staff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Неизвестен"

    scores = user_data.get(user_id, {}).get("score")

    if scores:
        top_animal = max(scores, key=scores.get)
    else:
        top_animal = await get_result(user_id)

    if not top_animal or top_animal not in animals:
        await update.callback_query.answer("Результат викторины не найден.", show_alert=True)
        return

    info = animals[top_animal]

    subject = f"Запрос на обратную связь от пользователя Telegram @{username}"
    body = (
        f"Пользователь @{username} ({user_id}) прошёл викторину.\n\n"
        f"Результат: {info['title']}\n{info['desc']}\n"
    )

    try:
        msg = EmailMessage()
        msg["From"] = SENDER_EMAIL
        msg["To"] = STAFF_EMAIL
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)

        await update.callback_query.answer("Информация отправлена сотруднику!", show_alert=True)
        await context.bot.send_message(
            chat_id=user_id,
            text="Мы передали информацию сотруднику зоопарка 🐾 Он свяжется с Вами!"
        )

    except Exception as e:
        print(f"Ошибка при отправке email: {e}")
        await update.callback_query.answer("Не удалось связаться с сотрудником 🐢", show_alert=True)


async def request_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    await update.callback_query.answer()

    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id]["awaiting_feedback"] = True

    await context.bot.send_message(chat_id=user_id, text="Пожалуйста, напиши свой отзыв:")



async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_data.get(user_id, {}).get("awaiting_feedback"):
        try:
            await save_feedback(user_id, text)
            await update.message.reply_text("Спасибо за отзыв! 💚")
        except Exception as e:
            print(f"Ошибка при сохранении отзыва: {e}")
            await update.message.reply_text("Произошла ошибка при сохранении отзыва 😓")
        user_data[user_id]["awaiting_feedback"] = False


async def inline_share(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.inline_query.from_user.id
    top_animal = await get_result(user_id)

    if not top_animal or top_animal not in animals:
        return

    info = animals[top_animal]

    text = (
        f"Посмотри, какое у меня тотемное животное в Московском зоопарке! {info['title']}\n\n"
        f"{info['desc']}\n\n"
        f"🐾 Узнай и ты своё животное! Попробуй бота 👉 https://t.me/{context.bot.username}"
    )

    result = InlineQueryResultArticle(
        id="share_result",
        title="🦁 Поделиться результатом викторины",
        input_message_content=InputTextMessageContent(text),
        description="Поделись своим результатом и пригласи друзей!",
    )

    await update.inline_query.answer([result], cache_time=0)


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"current_q": 0, "score": {}}
    await send_question(update, context)


def main():

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(InlineQueryHandler(inline_share))
    app.add_handler(CallbackQueryHandler(restart, pattern="^restart$"))
    app.add_handler(CallbackQueryHandler(request_feedback, pattern="^feedback$"))
    app.add_handler(CallbackQueryHandler(contact_staff, pattern="^contact_staff$"))
    app.add_handler(CallbackQueryHandler(handle_answer, pattern="^(?!restart$|feedback$|contact_staff$).*"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))

    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
