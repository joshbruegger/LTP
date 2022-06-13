import json
import os

YES_NO_LIST = ["is", "are", "can", "do", "does"]


def main():
    # read all questions from json file
    f = open('all_questions.json', 'r')
    entries = json.load(f)
    f.close()

    # Create files
    files = {'what': open('what_questions.json', 'w'),
             'where': open('where_questions.json', 'w'),
             'which': open('which_questions.json', 'w'),
             'when': open('when_questions.json', 'w'),
             'how': open('how_questions.json', 'w'),
             'yes_no': open('yes_no_questions.json', 'w')}

    # start json files
    write_to_all(files, '[')

    for entry in entries:
        question = entry['string']
        answers = entry['answer']
        only_answers = []
        for answer in answers:
            only_answers.append(answer['string'])

        q_type = get_question_type(question)
        if q_type == 'unknown':
            print('Unknown: ' + question)
        else:
            add_json_entry(question, only_answers, files[q_type])

    # end json files
    write_to_all(files, ']')
    close_all(files)


###############################################################################


def get_question_type(question):
    question = question.lower()
    first_word = question.split()[0]
    if 'what' in question:
        return 'what'
    elif 'where' in question:
        return 'where'
    elif 'which' in question:
        return 'which'
    elif 'when' in question:
        return 'when'
    elif 'how' in question:
        return 'how'
    elif first_word in YES_NO_LIST:
        return 'yes_no'
    else:
        return 'unknown'


def add_json_entry(question, expected, file):
    file.write('{')
    file.write('"question": "' + question + '",')
    file.write('"expected": "')
    for answer in expected:
        file.write(answer + ', ')
    file.write('"},')


def write_to_all(files, content):
    for file in files:
        files[file].write(content)


def close_all(files):
    for file in files:
        files[file].close()


main()
