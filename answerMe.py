import json
import os
import re
import traceback
from cmath import e

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

SPACY_MODEL = 'en_core_web_trf'
NLP = spacy.load(SPACY_MODEL)

YES_NO_LIST = ["is", "are", "can", "do", "does"]


def log(msg):
    if PRINT_DEBUG:
        print(msg)


def clear_console(): return os.system(
    'cls' if os.name in ('nt', 'dos') else 'clear')


def try_all_questions(file):
    f = open('questions/' + file)
    questions = json.load(f)
    f.close()

    manual_check_choice = input("Manual check? (y/n): ")
    while (manual_check_choice != 'y' and manual_check_choice != 'n'):
        manual_check_choice = input("Manual check? (y/n): ")

    n_correct = 0
    n_tot = 0
    incorrect = []

    for question in questions:
        print("=============================================================================================================================")
        n_tot += 1

        q = question.get('question')
        print(q)
        print("expected answer: " + question.get('expected'))
        ans = answer(q)
        if manual_check_choice == 'y':
            choice = input("Correct? (y/n): ")
            while (choice != 'y' and choice != 'n'):
                choice = input("Correct? (y/n): ")
            if choice == 'y':
                n_correct += 1
            else:
                incorrect.append([q, question.get('expected'), ans])
        else:
            if ans == question.get('expected'):
                n_correct += 1
                print("Correct!")
            else:
                print("Incorrect!")
                incorrect.append([q, question.get('expected'), ans])

        print("Current accuracy: " + str(n_correct / n_tot))

    print("=============================================================================================================================")
    print("Score: " + str(n_correct) + "/" + str(n_tot))
    print("Accuracy: " + str(n_correct / n_tot))

    print("Incorrect questions:")
    for i in incorrect:
        print(i[0])
        print("Expected: " + i[1])
        print("Actual: " + answer(i[2]))


def questions_from_selection():
    print('''
    1. how questions
    2. when questions
    3. where questions
    4. which questions
    5. yes/no questions
    6. what questions
    ''')
    choice = input("Enter your choice: ")
    if choice == '1':
        try_all_questions('how_questions.json')
    elif choice == '2':
        try_all_questions('when_questions.json')
    elif choice == '3':
        try_all_questions('where_questions.json')
    elif choice == '4':
        try_all_questions('which_questions.json')
    elif choice == '5':
        try_all_questions('yes_no_questions.json')
    elif choice == '6':
        try_all_questions('what_questions.json')
    else:
        print("Invalid choice")


def main():
    clear_console()

    print("SlayQA 6.9")
    # while True:
    print('-----------')
    print('''
    1. Ask a question
    2. try all questions in file
    3. Turn debug on or off
    q. Quit
    ''')
    choice = input("Enter your choice: ")
    if choice == '1':
        question = input("Enter your question: ")
        answer(question)
    elif choice == '2':
        questions_from_selection()
    elif choice == '3':
        global PRINT_DEBUG
        PRINT_DEBUG = not PRINT_DEBUG
        print("Debug is now " + str(PRINT_DEBUG))
    elif choice == 'q':
        exit()
    else:
        print("Invalid choice")


def answer(question):
    question = question.replace("?", "")

    doc = NLP(question)  # parse the input

    first_word = doc[0].text.lower()  # get the first word

    if "what" in doc.text.lower():
        ans = what_question(doc)
    elif first_word in YES_NO_LIST:
        ans = yes_no_q(doc)
    elif ("where" in doc.text.lower()):
        ans = where_question(doc)
    elif "which" in doc.text.lower() or "who" in doc.text.lower():
        ans = which_question(doc)
    elif "when" in doc.text.lower():
        ans = when_q(doc)
    elif "how" in doc.text.lower():
        ans = how_q(doc)
    else:
        ans = None

    if ans is not None:
        print(ans)
        return ans
    else:
        print('Answer: I don\'t know')
        return None


def remove_article(text):
    words_to_remove = ['the', 'a', 'an', 'while',
                       'which', 'who', 'what', 'where', 'when', 'how']

    for word in words_to_remove:
        # remove beginnings
        text = re.sub('^' + word + ' ', '', text)
        text = re.sub(' ' + word + ' ', '', text)
    return text


def remove_adj(str):
    ret = ""
    for word in str:
        if word.pos_ != 'ADJ':
            ret = ret + " " + word.text
    return ret


def get_synonyms(word):
    synonyms = []
    for syn in wordnet.synsets(str(word), pos="n"):
        for l in syn.lemmas():
            synonyms.append(str(l.name()))
    return synonyms


def what_question(doc):
    nouns = []
    for chunk in doc.noun_chunks:
        nouns.append(str(chunk))

    to_remove = ['average', 'common', 'mean', 'typical']
    completey_remove = ['bpm']
    # substitute word in all nouns with an empty string
    for noun in nouns:
        # if noun is not in to_remove:
        if noun in completey_remove:
            nouns.remove(noun)
        else:
            for word in to_remove:
                if word in noun:
                    nouns.remove(noun)
                    noun = re.sub(word + ' ', '', noun)
                    nouns.append(noun)

    log('Noun chunks: ' + str(nouns))

    if len(nouns) < 3:
        # If there are less than 2 noun chunks, it's probably a question like "What is a lion?"
        entity = wnl.lemmatize(remove_article(nouns[1]))
        if ("also" in doc.text):
            possible_objects = get_wikidata_ids(entity)
            answer = query_wikidata(build_label_query(
                possible_objects[0]['id']))
            if answer is not None:
                return format_answer(answer)
        else:
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
        entity = wnl.lemmatize(remove_article(nouns[-1]))

        if (len(nouns) == 3):
            prop = remove_article(nouns[1])

        # Checks if the question has "another word for/other names of" or else, and queries using "skos:altLabel"

        if (str(nouns[1]) in diffName):
            log("Property: " + prop + "Entity: " + entity)
            possible_objects = get_wikidata_ids(entity)
            answer = query_wikidata(build_label_query(
                possible_objects[0]['id']))
            if answer is not None:
                return format_answer(answer)

        else:
            prop = remove_article(nouns[1])

    ans = solver(entity, prop)
    if ans is not None:
        return ans
    return solver(prop, entity)


def where_question(doc):
    nouns = list(doc.noun_chunks)
    nouns = process_noun(nouns)

    log('Noun chunks: ' + str(nouns))

    entity = wnl.lemmatize(remove_article(process_noun(nouns[0].text)))

    if doc[-1].text == 'discovered':
        property1 = "location of discovery"
    else:
        property1 = "endemic to"

    property2 = "country of origin"
    property1 = process_noun(property1)
    property2 = process_noun(property2)

    ans = None
    ans = solver(entity, property1)
    if ans is None:
        ans = solver(entity, property2)

    return ans


def which_question(doc):
    nouns = []
    ans = None
    words = ''

    for word in doc.noun_chunks:
        words = remove_article(word.text.lower())
        log('words: ' + str(words))
        words = wnl.lemmatize(words)
        words = process_noun(words)
        if len(words.split()) > 1:
            treeCheck = words.split()
            if treeCheck[-1] == 'tree' and treeCheck[0] != treeCheck[-1]:
                words = words.rsplit(' ', 1)[0]
        nouns += [words]

    nouns = list(filter(None, nouns))
    log('Nouns: ' + str(nouns))

    if (len(nouns)) == 2:
        ans = solver(nouns[1], nouns[0])
    elif (len(nouns)) > 2:
        ans = solver(nouns[-1], nouns[1])
        if ans is None:
            ans = solver(nouns[1], nouns[-1])

    for word in doc:
        if (ans is None and word.text.lower() not in nouns and
            (word.pos_ == "NOUN" or word.pos_ == "ADJ" or
             word.pos_ == "ADV" or word.pos_ == "VERB")):
            words = remove_article(word.text.lower())
            words = process_noun(words)
            ans = solver(nouns[-1], words)
            if ans is None:
                ans = solver(nouns[0], words)
                if ans is None:
                    ans = solver(words, nouns[0])

    return ans


def yes_no_q(doc):
    log('Yes/No question')

    nouns = []
    adj_verb = None

    # Find the nouns in the question and the adjective/verb
    for word in doc:
        if word.pos_ == "ADJ" or word.pos_ == "VERB":
            adj_verb = word.text
        if word.pos_ == "NOUN":
            lemma = wnl.lemmatize(word.text)  # lemmatize the word
            nouns.append(lemma)

    log('Noun chunks: ' + str(nouns))
    if adj_verb is not None:
        log('Adjective/Verb: ' + adj_verb)
    else:
        log('No adjective found')

    if len(nouns) == 0:
        log('No nouns found!')
        return None

    if len(nouns) == 1:
        log('Only one noun found, trying with the adjective/verb')
        if adj_verb is None:
            log('No adjective/verb found')
            return None

        possible_objects = get_wikidata_ids(nouns[0])
        for obj in possible_objects:
            log('finding: ' + adj_verb + ' in ' +
                obj['display']['label']['value'] + '...')
            data = str(query_wikidata(query_all_properties(obj['id'])))
            if adj_verb in data:
                log('Found!')
                return "Yes"

        log("Not found")
        return "No"

    noun1_ids = get_wikidata_ids(nouns[0])
    noun2_ids = get_wikidata_ids(nouns[1])
    for noun1_id in noun1_ids:
        for noun2_id in noun2_ids:
            log('trying: ' + noun2_id['display']['label']['value'] +
                ' in ' + noun1_id['display']['label']['value'])

            noun1_data = query_wikidata(query_all_properties(noun1_id['id']))
            noun2_data = query_wikidata(query_all_properties(noun2_id['id']))
            if noun2_id['display']['label']['value'] in str(noun1_data) or noun1_id['display']['label']['value'] in str(noun2_data):
                different_from_text = 'different from'
                log('found references')
                if different_from_text in str(noun1_data):
                    log('Different from in n1')
                    for item in noun1_data:
                        p = item['wdLabel']['value']
                        if p == different_from_text:
                            if item['ps_Label']['value'] == noun2_id['display']['label']['value']:
                                return "No"
                if different_from_text in str(noun2_data):
                    log('Different from in n2')
                    for item in noun2_data:
                        p = item['wdLabel']['value']
                        if p == different_from_text:
                            if item['ps_Label']['value'] == noun1_id['display']['label']['value']:
                                return "No"
                return "Yes"
    return "No"


def try_count(thing_to_count, entity):
    if (thing_to_count == 'puppy'):
        thing_to_count = 'litter'

    log('Entity: ' + str(entity))
    log('thing to count: ' + str(thing_to_count))

    if entity == 'earth':
        entity = thing_to_count
        thing_to_count = 'population'

    # Find the wikidata id of the entity
    entity_ids = get_wikidata_ids(entity)

    for entity_id in entity_ids:
        log('trying: ' + entity_id['display']['label']['value'])
        data = query_wikidata(query_all_properties(entity_id['id']))
        if thing_to_count in str(data):
            log('Thing to count in data')
            for item in data:
                ps = item['ps_Label']['value']

                if ps.replace('.', '', 1).replace(',', '', 1).isdigit():
                    log("ps is a number")
                    pq = ps
                    ps = item['wdLabel']['value']
                else:
                    if 'pq_Label' not in item:
                        continue
                    pq = item['pq_Label']['value']

                log('property: ' + str(ps))
                log('qualifier: ' + str(pq))

                if pq.replace('.', '', 1).replace(',', '', 1).isdigit() and thing_to_count in ps:
                    return pq
    return None


def count_q(doc):
    log("Count question")
    nouns = list(doc.noun_chunks)

    log('Noun chunks: ' + str(nouns))

    # Cant find the nouns in the question
    if len(nouns) == 0:
        return None

    if len(nouns) == 1:
        nouns = nouns[0].text.lower().replace('how many ', '').split()
        if len(nouns) != 2:
            thing_to_count = 'population'
        else:
            thing_to_count = wnl.lemmatize(nouns[1])
        entity = wnl.lemmatize(nouns[0])
        r = try_count(thing_to_count, entity)
        if r is not None:
            return r
        return try_count(entity, thing_to_count)
    else:
        thing_to_count = nouns[0].text.lower().replace('how many ', '')
        thing_to_count = wnl.lemmatize(thing_to_count)
        if len(nouns) == 2:
            entity = wnl.lemmatize(remove_article(nouns[1].text.lower()))
            r = try_count(thing_to_count, entity)
            if r is not None:
                return r
            return try_count(entity, thing_to_count)
        else:
            entity = wnl.lemmatize(remove_article(nouns[-1].text.lower()))
            r = try_count(thing_to_count, entity)
            if r is not None:
                return r
            r = try_count(entity, thing_to_count)
            if r is not None:
                return r
            entity = wnl.lemmatize(remove_article(nouns[1].text.lower()))
            r = try_count(thing_to_count, entity)
            if r is not None:
                return r
            return try_count(entity, thing_to_count)


def how_q(doc):
    if 'how many' in doc.text.lower():
        return count_q(doc)

    nouns = list(doc.noun_chunks)

    entity = process_noun(wnl.lemmatize(remove_article(nouns[-1].text)))

    log('Entity: ' + str(entity))

    if doc[-1].pos_ == "NOUN":
        # if there are two noun chunks, then it has a structure similar to a "what-question"
        if len(nouns) >= 2:
            prop = process_noun(remove_article(nouns[-2].text))
        # check if adjective in the last to second position is part of noun chunks
        elif doc[-2].pos_ == "ADJ" and doc[-2].head == doc[-1] and (doc[-2].text not in nouns[-1].text):
            entity = process_noun(wnl.lemmatize(remove_article(doc[-1].text)))
            prop = process_noun(doc[-2].text)
        # any type of "how fast" / "how strong" question, except "how long"
        elif doc[1].pos_ == "ADV" or doc[1].pos_ == "ADJ" and doc[1].text != "long":
            prop = process_noun(doc[1].text)
        # other questions, assume that entity is at the end of query and the property is the only noun chunk
        else:
            entity = process_noun(remove_article(doc[-1].text))
            prop = process_noun(nouns[-1].text)

    elif doc[-1].pos_ == "VERB":
        if (doc[1].text == "old" or doc[1].text == "long") and doc[1].head == doc[-1]:
            prop = "life expectancy"
            # people think when they ask "can", it means the highest an animal can achieve, so highest lifespan
            if (doc[2].text == "can"):
                prop = "highest observed lifespan"
        elif doc[1].pos_ == "ADV":
            prop = process_noun(doc[1].text)
        else:
            prop = process_noun(doc[-1].text)
    elif doc[-1].pos_ == "ADJ":
        prop = process_noun(doc[-1].text)
    elif doc[-1].pos_ == "ADP":
        print("correct")
        prop = process_noun(doc[-2].text)
    else:
        print("sorry, not implemented yet!")
        return nouns

    entity = re.sub('adult ', '', entity)
    entity = re.sub('birth ', '', entity)
    entity = re.sub('newborn ', '', entity)

    log('Entity: ' + str(entity))

    ans = solver(entity, prop)
    return ans


def when_q(doc):
    nouns = list(doc.noun_chunks)
    if "extinct" in doc.text:
        prop1 = "end time"
        prop2 = "extinction date"
    elif "first" or "come to exist" or "exist" or "start" in doc.text:
        prop1 = "start time"
        prop2 = None
    elif "born" in doc.text:
        prop1 = "date of birth"
        prop2 = None
    elif "invented" in doc.text:
        prop1 = "time of discovery or invention"
        prop2 = None
    elif "die" in doc.text:
        prop1 = "date of death"
        prop2 = None
    noun = remove_article(nouns[0].text)
    entity = wnl.lemmatize(noun)
    entity = process_noun(entity)
    ans = solver(entity, prop1)
    if ans == None and prop2 != None:
        ans = solver(entity, prop2)
    if ans:
        if ans[0] == '-':
            ans = ans[1:]
            if "-01-01t00:00:00z" in ans:
                ans = ans.replace("-01-01t00:00:00z", " years BCE")
        else:
            ans = datetime.datetime.strptime(ans, "%Y-%m-%dt%H:%M:%Sz")

    return ans


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
        case 'pregnant' | 'pregnancy':
            return "gestation period"
        case 'Dodo' | 'dodo':
            return "Raphus cucullatus"
        case "bonsai tree" | "bonsai trees":
            return "bonsai"
        case 'component' | 'the components':
            return "has parts"
        case 'family':
            return "parent taxon"
        case 'made' | 'produces':
            return "natural product of taxon"
        case "move":
            return "locomotion"
        case "fast":
            return "speed"
        case "tall" | "high" | "big":
            return "height"
        case "lactate" | "breastfed":
            return "period of lactation"
        case "wolf":
            return "grey wolf"
        case _:
            return word


def solver(entity, property):
    entity = process_noun(entity)
    property = process_noun(property)

    log("entity,property:" + entity + ", " + property)

    possible_objects = get_wikidata_ids(entity)
    possible_properties = get_wikidata_ids(property, True)
    # extra = get_synonyms(property)
    # for i in extra:
    # possible_properties.extend(get_wikidata_ids(i, True))

    for object in possible_objects:
        for prop in possible_properties:
            log('trying: ' + prop['display']['label']['value'] +
                ' of ' + object['display']['label']['value'])
            ans = query_wikidata(build_query(object['id'], prop['id']))
            if ans is not None:
                return format_answer(ans)


def format_answer(data):
    formatted_answers = []

    for current_ans in data:
        ans = str(current_ans['answerLabel']['value']).capitalize()

        unit = ''
        if 'unitLabel' in current_ans and current_ans['unitLabel']['value'] != "1":
            unit = ' ' + current_ans['unitLabel']['value']

        # If the answer is a (number > 1) + unit combination, make unit plural
        if ans.replace('.', '', 1).replace(',', '', 1).isdigit() and float(ans) > 1.0 and unit != '':
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
    log(q)
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
