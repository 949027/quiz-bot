import os
import random


def get_quiz_set():
    os.makedirs('quiz-questions', exist_ok=True)
    filename = random.choice(os.listdir('quiz-questions'))
    with open(f'quiz-questions/{filename}', 'r', encoding='KOI8-R') as file:
        tasks = file.read().split(sep='\n\n')

    quiz_set = {}
    for part in tasks:
        if 'Вопрос' in part:
            quiz_set[part] = tasks[tasks.index(part)+1]

    return quiz_set

