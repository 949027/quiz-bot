with open('quiz-questions/1vs1201.txt', 'r', encoding='KOI8-R') as file:
    tasks = file.read().split(sep='\n\n')

tasks_dict = {}
for part in tasks:
    if 'Вопрос' in part:
        tasks_dict[part] = tasks[tasks.index(part)+1]

