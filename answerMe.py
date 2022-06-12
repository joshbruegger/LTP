import json
import os
import re
import traceback

import nltk
import requests
import spacy
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer

wnl = WordNetLemmatizer()
# download only if not already downloaded
if not nltk.data.find('corpora/wordnet') or not nltk.data.find('corpora/omw-1.4'):
    nltk.download('wordnet')
    nltk.download('omw-1.4')
    print("=============================================================================================================================")


PRINT_DEBUG = True
SPARQL_ENDPOINT = 'https://query.wikidata.org/sparql'
API_ENDPOINT = 'https://www.wikidata.org/w/api.php'
HEADERS = {'User-Agent': 'QASys/0.0 (https://rug.nl/LTP/; dont@mail.me)'}

YES_NO_LIST = ["is", "are", "can", "do", "does"]


def log(msg):
    if PRINT_DEBUG:
        print(msg)


def clear_console(): return os.system(
    'cls' if os.name in ('nt', 'dos') else 'clear')


def try_all_questions(file, question_id):
    global PRINT_DEBUG
    PRINT_DEBUG = False
    f = open(file)
    questions = json.load(f)
    f.close()

    for question in questions:
        print("=============================================================================================================================")
        q = question.get(question_id)
        print(q)
        answer(q)


def main():
    clear_console()
    answer(input("Question: "))

    return

    print("SlayQA 1.0")
    while True:
        print('-----------')
        print('''
        1. Ask a question
        2. Try all questions
        3. try all questions in file
        4. Turn debug on or off
        q. Quit
        ''')
        choice = input("Enter your choice: ")
        if choice == '1':
            question = input("Enter your question: ")
            answer(question)
        elif choice == '2':
            try_all_questions('all_questions.json', 'string')
        elif choice == '3':
            file = input("Enter the file name: ")
            q_id = input("Enter the question ID: ")
            try_all_questions(file, q_id)
        elif choice == '4':
            global PRINT_DEBUG
            PRINT_DEBUG = not PRINT_DEBUG
            print("Debug is now " + str(PRINT_DEBUG))
        elif choice == 'q':
            exit()
        else:
            print("Invalid choice")


def answer(question):
    dependency_pars = spacy.load('en_core_web_trf')

    doc = dependency_pars(question)  # parse the input

    first_word = doc[0].text.lower()  # get the first word

    if "what" in doc.text.lower():
        ans = what_question(doc)
    elif first_word in YES_NO_LIST:
        ans = yes_no_q(doc)
    elif "where" in doc.text.lower():
        ans = where_question(doc)
    elif "which" in doc.text.lower():
        ans = which_question(doc)
    elif "how many" in doc.text.lower():
        ans = count_q(doc)
    elif "when" in doc.text.lower():
        ans = when_q(doc)
    else:
        ans = None

    if ans is not None:
        print('Answer: ' + ans)
    else:
        print('Answer: I don\'t know')


def remove_article(str):
    return re.sub('^(?:the|a|an) ', '', str)


def get_synonyms(word):
    synonyms = []
    for syn in wordnet.synsets(str(word), pos="n"):
        for l in syn.lemmas():
            synonyms.append(str(l.name()))
    return synonyms


def which_question(doc):
    all = []
    ans = None
    words = ''

    for word in doc.noun_chunks:
        words = remove_article(word.text.lower())
        #words = wnl.lemmatize(removeArticle(words))
        words = process_noun(words)
        all += [words]

    all = list(filter(None, all))
    if len(all) == 2:
        ans = solver(all[1], all[0])
    elif len(all) > 2:
        ans = solver(all[-1], all[1])
        if ans is None:
            ans = solver(all[1], all[-1])

    for word in doc:
        if (ans is None and (word.text not in all and
            word.pos_ == "NOUN" or word.pos_ == "ADJ" or
                             word.pos_ == "ADV" or word.pos_ == "VERB")):
            words = remove_article(word.text.lower())
            words = process_noun(words)
            ans = solver(all[-1], words)
            if ans is None:
                ans = solver(all[0], words)
                if ans is None:
                    ans = solver(words, all[0])

    return ans


def solver(entity, property):
    log("entity,property:" + entity + ", " + property)

    possible_objects = get_wikidata_ids(entity)
    possible_properties = get_wikidata_ids(property, True)

    for object in possible_objects:
        for prop in possible_properties:
            # log('trying: ' + prop['display']['label']['value'] +
            #    ' of ' + object['display']['label']['value'])
            ans = query_wikidata(build_query(
                object['id'], prop['id']))
            ans = format_answer(ans)
            if ans is not None:
                return ans


def what_question(doc):
    nouns = []
    for chunk in doc.noun_chunks:
        nouns.append(str(chunk))
    for noun in nouns:
        new = noun
        new = new.replace("average ", "")
        new = new.replace("common ", "")
        new = new.replace("mean ", "")
        new = new.replace("typical ", "")
        index = nouns.index(noun)
        nouns[index] = new

    log('Noun chunks: ' + str(nouns))

    if len(nouns) < 3:
        # If there are less than 3 noun chunks, it's probably a question like "What is a lion?"
        if ("also" in doc.text):
            entity = remove_article(nouns[1])
            possible_objects = get_wikidata_ids(entity)
            answer = query_wikidata(build_label_query(
                possible_objects[0]['id']))
            answer = format_answer(answer)
            if answer is not None:
                return answer
        else:
            entity = remove_article(nouns[1])
            possible_objects = get_wikidata_ids(entity)
            for obj in possible_objects:
                desc = obj['display']['description']['value']
                if desc is not None:
                    # check if entity starts with vowel
                    if entity[0].lower() in 'aeiou':
                        entity = "An " + entity
                    else:
                        entity = "A " + entity
                    return entity + ' is a ' + desc

    else:
        entity = remove_article(nouns[-1])

        if (len(nouns) == 3):
            prop = remove_article(nouns[1])

        # Checks if the question has "another word for/other names of" or else, and queries using "skos:altLabel"

        if (str(nouns[1]) in diffName):
            log("Property: " + prop + "Entity: " + entity)
            possible_objects = get_wikidata_ids(entity)
            answer = query_wikidata(build_label_query(
                possible_objects[0]['id']))
            answer = format_answer(answer)
            if answer is not None:
                return answer

        else:
            prop = remove_article(nouns[1])

        possible_objects = get_wikidata_ids(entity)
        possible_properties = get_wikidata_ids(prop, True)
        extra = get_synonyms(prop)
        for i in extra:
            possible_properties.extend(get_wikidata_ids(i, True))

        for object in possible_objects:
            for prop in possible_properties:
                log('trying: ' + prop['display']['label']['value'] +
                    ' of ' + object['display']['label']['value'])
                answer = query_wikidata(build_query(
                    object['id'], prop['id']))
                answer = format_answer(answer)
                if answer is not None:
                    return answer


def where_question(doc):
    nouns = list(doc.noun_chunks)
    process_noun(nouns)

    log('Noun chunks: ' + str(nouns))

    entity = wnl.lemmatize(remove_article(nouns[-1].text))

    if doc[-2].text == 'discovered':
        property1 = "location of discovery"
    else:
        property1 = "endemic to"
    property2 = "country of origin"
    property1 = process_noun(property1)
    property2 = process_noun(property2)
    possible_objects = get_wikidata_ids(entity)
    log(entity)
    possible_properties1 = get_wikidata_ids(property1, True)
    possible_properties2 = get_wikidata_ids(property2, True)

    for object in possible_objects:
        for property in possible_properties1:
            log('trying: ' + property['display']['label']['value'] +
                ' of ' + object['display']['label']['value'])
            answer = query_wikidata(build_query(
                object['id'], property['id']))
            answer = format_answer(answer)

            if answer is not None:
                return answer
            else:
                for property2 in possible_properties2:
                    log('trying: ' + property['display']['label']['value'] +
                        ' of ' + object['display']['label']['value'])
                    answer = query_wikidata(build_query(
                        object['id'], property2['id']))
                    answer = format_answer(answer)
                    if answer is not None:
                        return answer


def yes_no_q(doc):
    nouns = list(doc.noun_chunks)
    log('Noun chunks: ' + str(nouns))

    if (len(nouns) == 1):
        adj = None
        for word in doc:
            if word.pos_ == 'ADJ':
                adj = word.text
        if adj is None:
            return "I don't know"
        else:
            if adj == 'safe' and "to eat" in doc.text:
                adj = 'edible'
            log('Adjective: ' + adj)

            entity = wnl.lemmatize(remove_article(nouns[0].text))
            log('Entity: ' + nouns[0].text)

            possible_objects = get_wikidata_ids(entity)

            for object in possible_objects:
                log('trying:' + object['display']['label']['value'])
                answer = adj in str(query_wikidata(
                    query_all_properties(object['id'])))
                if answer:
                    return "Yes"
            return "No"

    else:

        noun1 = remove_article(nouns[-1].text)
        noun2 = remove_article(nouns[0].text)

        noun1_possibilities = get_wikidata_ids(noun1)
        noun2_possibilities = get_wikidata_ids(noun2)

        for noun1try in noun1_possibilities:
            for noun2try in noun2_possibilities:
                log('trying: is a ' + noun2try['display']['label']['value'] +
                    ' a ' + noun1try['display']['label']['value'])
                answer = query_wikidata(build_yes_no_query(
                    noun2try['id'], noun1try['id']))
                answer = format_answer(answer)
                if answer is not None:
                    return answer


def count_q(doc):
    if ("old" in doc.text):
        prop = ""

    return doc


def how_q(doc):
    return


def when_q(doc):
    return doc


diffName = ["also known as", "other names", "other word", "another name"]


def process_noun(word):
    match word:
        case 'heavy':
            return "mass"
        case 'fruit type':
            return "has fruit type"
        case 'old ':
            return "highest observed lifespan"
        case 'sound ':
            return "produced sound"
        case 'definition ':
            return "Description"
        # case "pregnant" | "pregnancy":
        #     return "gestation period"
        case _:
            return word


# skos:altLabel -> for "also known as"
# schema:description -> "definition"

def format_answer(data):
    formatted_answers = []

    for current_ans in data:
        ans = str(current_ans['answerLabel']['value']).capitalize()

        unit = ''
        if 'unitLabel' in current_ans and current_ans['unitLabel']['value'] != "1":
            unit = ' ' + current_ans['unitLabel']['value']

        # If the answer is a (number > 1) + unit combination, make unit plural
        if ans.replace('.', '', 1).isdigit() and float(ans) > 1.0 and unit != '':
            unit += 's'

        formatted_answers.append(ans + unit)

    final_answer = ''

    final_answer += formatted_answers[0]
    # It was printing the same value twice if the list has only one item, added if statement
    if(len(formatted_answers) > 1):
        for ans in formatted_answers[1:-1]:
            final_answer += ', ' + ans
        final_answer += ', and ' + formatted_answers[-1]

    return final_answer


def query_wikidata(query):
    try:
        data = requests.get(SPARQL_ENDPOINT,
                            headers=HEADERS,
                            params={'query': query, 'format': 'json'}).json()
        if 'ASK' in query:
            if data['boolean']:
                return 'Yes'
            else:
                return 'No'
        else:
            data = data['results']['bindings']
    except Exception:
        traceback.print_exc()
        return 'Error: Query failed: Too many requests?'

    if len(data) == 0:
        return None

    return data


def build_query(object, property):
    q = 'SELECT ?answerLabel ?unitLabel WHERE{wd:'
    q += object + ' p:' + property + '?s.?s ps:'
    q += property + '?answer. OPTIONAL{?s psv:'
    q += property + '?u.?u wikibase:quantityUnit ?unit.}'
    q += 'SERVICE wikibase:label{bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en"}}'
    return q


def build_label_query(obj):
    q = 'SELECT ?answerLabel WHERE { wd:'
    q += obj + \
        ' skos:altLabel ?answerLabel. FILTER ( lang(?answerLabel) = "en" ) }'
    return q


def build_yes_no_query(object, property):
    q = 'ASK { wd:'
    q += object + ' wdt:P279 wd:' + property + '. }'
    return q


def query_all_properties(entity):
    return '''SELECT ?wdLabel ?ps_Label ?wdpqLabel ?pq_Label {
    VALUES (?entity) {(wd:$entity$)}
    ?entity ?p ?statement .
    ?statement ?ps ?ps_ .
    ?wd wikibase:claim ?p.
    ?wd wikibase:statementProperty ?ps.
    OPTIONAL {
    ?statement ?pq ?pq_ .
    ?wdpq wikibase:qualifier ?pq .
    }
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
    } ORDER BY ?wd ?statement ?ps_'''.replace('$entity$', entity)


def get_wikidata_ids(query, isProperty=False):
    params = {'action': 'wbsearchentities',
              'language': 'en',
              'format': 'json',
              'search': query}
    if isProperty:
        params['type'] = 'property'

    return requests.get(API_ENDPOINT, params).json()['search']


main()
