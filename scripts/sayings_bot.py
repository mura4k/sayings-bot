import logging
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import random
import sqlite3

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

data = pd.read_excel('../data/sayings.xlsx')

current_question_index = {}
score = {}
total_questions = {}

# connect to the SQLite database
conn = sqlite3.connect('../data/stats_by_saying.db', check_same_thread=False)
cursor = conn.cursor()


# start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    current_question_index[chat_id] = 0
    score[chat_id] = 0
    total_questions[chat_id] = 0
    keyboard = [
        [InlineKeyboardButton("Боюсь волков, иду в рощу", callback_data='easy')],
        [InlineKeyboardButton("Не боюсь волков, иду в лес", callback_data='medium')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите уровень сложности:', reply_markup=reply_markup)


# function to send a question
async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, difficulty: int) -> None:
    chat_id = update.effective_chat.id
    index = current_question_index[chat_id]
    filtered_data = data[data['difficulty_level'] == difficulty]
    saying = filtered_data.iloc[index]['russian_sayings']
    correct_translation = filtered_data.iloc[index]['english_correct_translation']
    incorrect_translation = filtered_data.iloc[index]['english_incorrect_translation']

    # shuffle the translations
    translations = [(correct_translation, 'correct'), (incorrect_translation, 'incorrect')]
    random.shuffle(translations)

    keyboard = [
        [InlineKeyboardButton(translations[0][0], callback_data=translations[0][1])],
        [InlineKeyboardButton(translations[1][0], callback_data=translations[1][1])]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=saying, reply_markup=reply_markup)


# button callback handler
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    if query.data == 'easy' or query.data == 'medium':
        difficulty = 0 if query.data == 'easy' else 1
        context.user_data['difficulty'] = difficulty
        await send_question(update, context, difficulty)
    elif query.data in ['correct', 'incorrect']:
        difficulty = context.user_data['difficulty']
        index = current_question_index[chat_id]
        filtered_data = data[data['difficulty_level'] == difficulty]
        correct_translation = filtered_data.iloc[index]['english_correct_translation']

        # get the saying's ID from the database
        saying = filtered_data.iloc[index]['russian_sayings']
        cursor.execute('SELECT id FROM sayings WHERE russian_saying = ?', (saying,))
        saying_id = cursor.fetchone()[0]

        total_questions[chat_id] += 1
        if query.data == 'correct':
            score[chat_id] += 1
            feedback = f"Правильно!\nПравильный перевод: {correct_translation}"
            cursor.execute(
                'UPDATE sayings SET attempts = attempts + 1, correct_attempts = correct_attempts + 1 WHERE id = ?',
                (saying_id,))
        else:
            feedback = f"Неправильно.\nПравильный перевод: {correct_translation}"
            cursor.execute('UPDATE sayings SET attempts = attempts + 1 WHERE id = ?', (saying_id,))

        conn.commit()  # commit the changes to the database

        feedback += f"\nВаш счет: {score[chat_id]} из {total_questions[chat_id]}"

        current_question_index[chat_id] += 1
        if current_question_index[chat_id] >= len(filtered_data):
            await query.message.reply_text(text=f"Ваш счет: {score[chat_id]} из {total_questions[chat_id]}")
            keyboard = [
                [InlineKeyboardButton("Повторить тест", callback_data='repeat')],
                [InlineKeyboardButton("Завершить", callback_data='end')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id=chat_id, text="Выберите действие:", reply_markup=reply_markup)
        else:
            await query.message.reply_text(text=feedback)
            await send_question(update, context, difficulty)
    elif query.data == 'repeat':
        current_question_index[chat_id] = 0
        score[chat_id] = 0
        total_questions[chat_id] = 0
        await send_question(update, context, context.user_data['difficulty'])
    elif query.data == 'end':
        await context.bot.send_message(chat_id=chat_id,
                                       text=f"Ваш окончательный счет: {score[chat_id]} из {total_questions[chat_id]}")
        await context.bot.send_photo(chat_id=chat_id, photo=open('../data/goodbye.jpg', 'rb'))


# end command handler
async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if chat_id in score and chat_id in total_questions:
        await update.message.reply_text(f"Ваш окончательный счет: {score[chat_id]} из {total_questions[chat_id]}")
    else:
        await update.message.reply_text("Вы еще не начали тест.")
    await context.bot.send_photo(chat_id=chat_id, photo=open('../data/goodbye.jpg', 'rb'))


# message handler for unrecognized input
async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Я вас не понимаю")


# main function to start the bot
def main() -> None:
    application = Application.builder().token("MY TOKEN").build()

    # set up the command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("end", end))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    # set up the bot commands
    commands = [
        BotCommand("start", "Начать тест"),
        BotCommand("end", "Завершить тест")
    ]
    application.bot.set_my_commands(commands)

    application.run_polling()


if __name__ == '__main__':
    main()
