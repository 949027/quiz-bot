from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, \
    ConversationHandler, RegexHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import logging
import random
from environs import Env
import redis

from questions import get_quiz_set

env = Env()
env.read_env()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

ASK, CHECK, CHOOSING = range(3)

reply_markup = ReplyKeyboardMarkup([['Новый вопрос', 'Сдаться'], ['Мой счет']])

redis_client = redis.Redis(
    host=env('REDIS_URL'),
    port=env('REDIS_PORT'),
    charset='utf-8',
    decode_responses=True,
    username=env('REDIS_USERNAME'),
    password=env('REDIS_PASSWORD'),
)

quiz_set = get_quiz_set()


def start(bot, update):
    chat_id = update.message.chat_id
    redis_client.set(f'score_{chat_id}', 0)
    bot.send_message(
        chat_id=chat_id,
        text='Привет! Давай сыграем!',
        reply_markup=reply_markup,
    )
    return CHOOSING


def ask_question(bot, update):
    chat_id = update.message.chat_id
    question = random.choice(list(quiz_set.keys()))
    bot.send_message(chat_id=chat_id, text=question)
    redis_client.set(chat_id, question)
    return CHOOSING


def check_answer(bot, update):
    chat_id = update.message.chat_id
    question = redis_client.get(chat_id)
    user_answer = update.message.text
    right_answer = quiz_set[question]
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


def skip_question(bot, update):
    chat_id = update.message.chat_id
    question = redis_client.get(chat_id)
    right_answer = quiz_set[question]
    bot.send_message(chat_id=chat_id, text=right_answer)
    return CHOOSING


def show_score(bot, update):
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
    updater = Updater(env("TG_BOT_TOKEN"))
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [RegexHandler('Новый вопрос', ask_question),
                       RegexHandler('Сдаться', skip_question),
                       RegexHandler('Мой счет', show_score),
                       MessageHandler(Filters.text, check_answer),
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
