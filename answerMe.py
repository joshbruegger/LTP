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


PRINT_DEBUG = False
SPARQL_ENDPOINT = 'https://query.wikidata.org/sparql'
API_ENDPOINT = 'https://www.wikidata.org/w/api.php'
HEADERS = {'User-Agent': 'QASys/0.0 (https://rug.nl/LTP/; dont@mail.me)'}


def log(msg):
    if PRINT_DEBUG:
        print(msg)


def clear_console(): return os.system(
    'cls' if os.name in ('nt', 'dos') else 'clear')


def try_all_questions():
    global PRINT_DEBUG
    PRINT_DEBUG = False
    f = open('all_questions.json')
    questions = json.load(f)
    f.close()

    for question in questions:
        print("=============================================================================================================================")
        q = question.get('string')
        print(q)
        answer(q)


def main():
    clear_console()
    print("SlayQA 0.0")

    try_all_questions()
    # answer("Can you tell me the colour of narcissi?")


def answer(question):
    dependency_pars = spacy.load('en_core_web_trf')

    # 1. get question type
    # What, where, yes/no, count, how

    doc = dependency_pars(question)  # parse the input
    first_word = doc[0].text.lower()

    yes_no_list = ["is", "are", "can", "do", "does"]

    if "what" in doc.text.lower():
        ans = what_question(doc)
    elif first_word in yes_no_list:
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
        ans = " I don't know"

    print(ans)


def remove_article(str):
    return re.sub('^(?:the|a|an) ', '', str)


def get_synonyms(word):
    synonyms = []
    for syn in wordnet.synsets(str(word), pos="n"):
        for l in syn.lemmas():
            synonyms.append(str(l.name()))
    return synonyms


def which_question(doc):
    return "Which question not implemented yet!"


def what_question(doc):
    nouns = []
    for chunk in doc.noun_chunks:
        nouns.append(str(chunk))
    for noun in nouns:
        new = noun
        if "average" in noun:
            new = str(noun).replace("average ", "")
        if "common" in noun:
            new = str(noun).replace("common ", "")
        if "mean" in noun:
            new = str(noun).replace("mean ", "")
        index = nouns.index(noun)
        nouns[index] = new

    log(nouns)
    process_noun(nouns)

    log('Noun chunks: ' + str(nouns))

    if len(nouns) < 3:
        # If there are less than 3 noun chunks, it's probably a question like "What is a lion?"
        if ("also" in doc.text):
            entity = remove_article(nouns[1])
            possibleObjects = get_wikidata_ids(entity)
            answer = query_wikidata(build_label_query(
                possibleObjects[0]['id']))
            if answer is not None:
                return answer
        else:
            entity = remove_article(nouns[1])
            possibleObjects = get_wikidata_ids(entity)
            for obj in possibleObjects:
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
            possibleObjects = get_wikidata_ids(entity)
            answer = query_wikidata(build_label_query(
                possibleObjects[0]['id']))
            if answer is not None:
                return answer

        else:
            # pattern = '(' + nouns[1] + ')' # (('.*?' + nouns[len(nouns)-2].text + )) it was searching for the same regex twice, removed it
            # m = re.search(pattern, doc.text)
            # print(type(m))
            # print(pattern)
            prop = remove_article(nouns[1])

        # prop = process_property(prop)
        possibleObjects = get_wikidata_ids(entity)
        possibleProperties = get_wikidata_ids(prop, True)
        extra = get_synonyms(prop)
        for i in extra:
            possibleProperties.extend(get_wikidata_ids(i, True))

        for object in possibleObjects:
            for prop in possibleProperties:
                log('trying: ' + prop['display']['label']['value'] +
                    ' of ' + object['display']['label']['value'])
                answer = query_wikidata(build_query(
                    object['id'], prop['id']))
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

            if answer is not None:
                return answer
            else:
                for property2 in possible_properties2:
                    log('trying: ' + property['display']['label']['value'] +
                        ' of ' + object['display']['label']['value'])
                    answer = query_wikidata(build_query(
                        object['id'], property2['id']))
                    if answer is not None:
                        return answer


def yes_no_q(doc):
    nouns = list(doc.noun_chunks)
    log('Noun chunks: ' + str(nouns))

    noun1 = remove_article(nouns[len(nouns)-1].text)

    if (len(nouns) <= 3):
        noun2 = remove_article(nouns[0].text)
    else:
        return "I don't know"
        # pattern = '(' + nouns[1].text + '.*?' + \
        #     nouns[len(nouns)-2].text + ')'
        # m = re.search(pattern, doc.text)
        # noun1 = remove_article(m.group(1))

    noun1_possibilities = get_wikidata_ids(noun1)
    noun2_possibilities = get_wikidata_ids(noun2)

    for noun1try in noun1_possibilities:
        for noun2try in noun2_possibilities:
            log('trying: is a ' + noun2try['display']['label']['value'] +
                ' a ' + noun1try['display']['label']['value'])
            answer = query_wikidata(build_yes_no_query(
                noun2try['id'], noun1try['id']))
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

    return format_answer(data)


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


def get_wikidata_ids(query, isProperty=False):
    params = {'action': 'wbsearchentities',
              'language': 'en',
              'format': 'json',
              'search': query}
    if isProperty:
        params['type'] = 'property'

    return requests.get(API_ENDPOINT, params).json()['search']


main()
