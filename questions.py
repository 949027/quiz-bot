import os


def get_quiz():
    questions = []
    for path in os.listdir('quiz-questions'):
        with open(f'quiz-questions/{path}', 'r', encoding='KOI8-R') as file:
            questions += file.read().split(sep='\n\n')
    quiz = {}
    for part in questions:
        if 'Вопрос' in part:
            quiz[part] = questions[questions.index(part)+1]
    return quiz
