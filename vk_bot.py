import logging
import random

from environs import Env
import vk_api as vk
from vk_api.keyboard import VkKeyboardColor, VkKeyboard
from vk_api.longpoll import VkLongPoll, VkEventType
import redis

from questions import get_quiz


logger = logging.getLogger(__name__)


def ask_question(event, vk_api, keyboard, redis_client, quiz):
    question = random.choice(list(quiz.keys()))
    redis_client.set(event.user_id, question)
    vk_api.messages.send(
        user_id=event.user_id,
        message=question,
        keyboard=keyboard.get_keyboard(),
        random_id=random.randint(1, 1000),
    )


def check_answer(event, vk_api, keyboard, redis_client, quiz):
    question = redis_client.get(event.user_id)
    user_answer = event.text
    right_answer = quiz[question].split(':')[1].split('(')[0].split('.')[0].strip()
    if right_answer == user_answer:
        score = redis_client.get(f'score_{event.user_id}')
        redis_client.set(f'score_{event.user_id}', int(score) + 1)
        text = 'Поздравляем! Правильно!'
        vk_api.messages.send(
            user_id=event.user_id,
            message=text,
            keyboard=keyboard.get_keyboard(),
            random_id=random.randint(1, 1000),
        )
    else:
        text = 'Неправильно! Попробуешь еще?'
        vk_api.messages.send(
            user_id=event.user_id,
            message=text,
            keyboard=keyboard.get_keyboard(),
            random_id=random.randint(1, 1000),
        )


def skip_question(event, vk_api, keyboard, redis_client, quiz):
    question = redis_client.get(event.user_id)
    right_answer = quiz[question]
    vk_api.messages.send(
        user_id=event.user_id,
        message=right_answer,
        keyboard=keyboard.get_keyboard(),
        random_id=random.randint(1, 1000),
    )


def show_score(event, vk_api, keyboard, redis_client):
    score = redis_client.get(f'score_{event.user_id}')
    text = f'Набранные очки: {score}'
    vk_api.messages.send(
        user_id=event.user_id,
        message=text,
        keyboard=keyboard.get_keyboard(),
        random_id=random.randint(1, 1000),
    )


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    env = Env()
    env.read_env()

    redis_client = redis.Redis(
        host=env('REDIS_URL'),
        port=env('REDIS_PORT'),
        charset='utf-8',
        decode_responses=True,
        username=env('REDIS_USERNAME'),
        password=env('REDIS_PASSWORD'),
    )
    quiz = get_quiz()
    vk_session = vk.VkApi(token=env('VK_GROUP_TOKEN'))
    vk_api = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)

    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('Мой счет')

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            try:
                if not redis_client.get(f'score_{event.user_id}'):
                    redis_client.set(f'score_{event.user_id}', 0)

                if event.text == 'Новый вопрос':
                    ask_question(event, vk_api, keyboard, redis_client, quiz)
                elif event.text == 'Сдаться':
                    skip_question(event, vk_api, keyboard, redis_client, quiz)
                elif event.text == 'Мой счет':
                    show_score(event, vk_api, keyboard, redis_client)
                else:
                    check_answer(event, vk_api, keyboard, redis_client, quiz)
            except Exception as err:
                logger.exception(err)


if __name__ == "__main__":
    main()
