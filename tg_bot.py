from functools import partial
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, \
    ConversationHandler, RegexHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import logging
import random
from environs import Env
import redis

from questions import get_quiz

env = Env()
env.read_env()

logger = logging.getLogger(__name__)

ASK, CHECK, CHOOSING = range(3)

reply_markup = ReplyKeyboardMarkup([['Новый вопрос', 'Сдаться'], ['Мой счет']])


def start(redis_client, bot, update):
    chat_id = update.message.chat_id
    redis_client.set(f'score_{chat_id}', 0)
    bot.send_message(
        chat_id=chat_id,
        text='Привет! Давай сыграем!',
        reply_markup=reply_markup,
    )
    return CHOOSING


def ask_question(redis_client, quiz, bot, update):
    chat_id = update.message.chat_id
    question = random.choice(list(quiz.keys()))
    bot.send_message(chat_id=chat_id, text=question)
    redis_client.set(chat_id, question)
    return CHOOSING


def check_answer(redis_client, quiz, bot, update):
    chat_id = update.message.chat_id
    question = redis_client.get(chat_id)
    user_answer = update.message.text
    right_answer = quiz[question]
    short_right_answer = right_answer.split(':')[1].split('(')[0].split('.')[0].strip()
    if short_right_answer == user_answer:
        score = redis_client.get(f'score_{chat_id}')
        redis_client.set(f'score_{chat_id}', int(score) + 1)
        text = 'Поздравляем! Правильно!'
        bot.send_message(chat_id=chat_id, text=text)
    else:
        text = 'Неправильно! Попробуешь еще?'
        bot.send_message(chat_id=chat_id, text=text)
    return CHOOSING


def skip_question(redis_client, quiz, bot, update):
    chat_id = update.message.chat_id
    question = redis_client.get(chat_id)
    right_answer = quiz[question]
    bot.send_message(chat_id=chat_id, text=right_answer)
    return CHOOSING


def show_score(redis_client, bot, update):
    chat_id = update.message.chat_id
    score = redis_client.get(f'score_{chat_id}')
    text = f'Набранные очки: {score}'
    bot.send_message(chat_id=chat_id, text=text)


def cancel(bot, update):
    user = update.message.from_user
    logger.info(f'User {user.first_name} canceled the conversation.')
    update.message.reply_text('Bye! I hope we can talk again some day.',
                              reply_markup=ReplyKeyboardRemove())


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    redis_client = redis.Redis(
        host=env('REDIS_URL'),
        port=env('REDIS_PORT'),
        charset='utf-8',
        decode_responses=True,
        username=env('REDIS_USERNAME'),
        password=env('REDIS_PASSWORD'),
    )

    quiz = get_quiz()

    updater = Updater(env("TG_BOT_TOKEN"))
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', partial(start, redis_client))],
        states={
            CHOOSING: [
                RegexHandler('Новый вопрос', partial(ask_question, redis_client, quiz)),
                RegexHandler('Сдаться', partial(skip_question, redis_client, quiz)),
                RegexHandler('Мой счет', partial(show_score, redis_client)),
                MessageHandler(Filters.text, partial(check_answer, redis_client, quiz)),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(conv_handler)
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
