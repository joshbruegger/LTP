import re
from cmath import exp

import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
import requests
import spacy
from spacy import displacy
import traceback

wnl = WordNetLemmatizer()


# Cooool code starts here

printDebug = True


def log(msg):
    if printDebug:
        print(msg)


def main():
    answer("What is the average heart rate of a chicken?")


def answer(question):
    dependencyPars = spacy.load('en_core_web_trf')

    print("=============================================================================================================================")

    # 1. get question type
    # What, where, yes/no, count, how

    doc = dependencyPars(question)  # parse the input
    firstWord = doc[0].text.lower()

    yesNoList = ["is", "are", "can", "do", "does"]

    if "what" in doc.text.lower():
        ans = whatQuestion(doc)
    elif firstWord in yesNoList:
        ans = yesNoQuestion(doc)
    elif "where" in doc.text.lower():
        ans = whereQuestion(doc)
    elif "which" in doc.text.lower():
        ans = whichQuestion(doc)
    elif "how many" in doc.text.lower():
        ans = countQuestion(doc)
    elif "when" in doc.text.lower():
        print("when huh")
        ans = whenQuestion(doc)

    print(ans)


def whatQuestion(doc):
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
        

    print(nouns)
    processProperty(nouns)

    def removeArticle(str): return re.sub('^(?:the|a|an) ', '', str)
    log('Noun chunks: ' + str(nouns))

    if len(nouns) < 3:
        # If there are less than 3 noun chunks, it's probably a question like "What is a lion?"
        if ("also" in doc.text):
            entity = removeArticle(nouns[1])
            possibleObjects = getWikidataIDs(entity)
            answer = queryWikidata(buildLabelQuery(
                    possibleObjects[0]['id']))
            if answer is not None:
                return answer
        else:
            entity = removeArticle(nouns[1])
            possibleObjects = getWikidataIDs(entity)
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
        entity = removeArticle(nouns[-1])

        if (len(nouns) == 3):
            property = removeArticle(nouns[1])
        
        # Checks if the question has "another word for/other names of" or else, and queries using "skos:altLabel"

        if (str(nouns[1]) in diffName):
            print("Property: " + property + "Entity: " + entity )
            possibleObjects = getWikidataIDs(entity)
            answer = queryWikidata(buildLabelQuery(
                    possibleObjects[0]['id']))
            if answer is not None:
                return answer

        else:
            # pattern = '(' + nouns[1] + ')' # (('.*?' + nouns[len(nouns)-2].text + )) it was searching for the same regex twice, removed it
            # m = re.search(pattern, doc.text)
            # print(type(m))
            # print(pattern)
            property = removeArticle(nouns[1])
            

        property = processProperty(property)
        possibleObjects = getWikidataIDs(entity)
        possibleProperties = getWikidataIDs(property, True)

        for object in possibleObjects:
            for property in possibleProperties:
                log('trying: ' + property['display']['label']['value'] +
                    ' of ' + object['display']['label']['value'])
                answer = queryWikidata(buildQuery(
                    object['id'], property['id']))
                if answer is not None:
                    return answer


def whereQuestion(doc):
    nouns = list(doc.noun_chunks)
    processProperty(nouns)
    
    def removeArticle(str):
        return re.sub('^(?:the|a|an) ', '', str)

    log('Noun chunks: ' + str(nouns))


    entity = wnl.lemmatize(removeArticle(nouns[-1].text))

    if doc[-2].text == 'discovered':
        property1 = "location of discovery"
    else:
        property1 = "endemic to"
    property2 = "country of origin"
    property1 = processProperty(property1)
    property2 = processProperty(property2)
    possibleObjects = getWikidataIDs(entity)
    print(entity)
    possibleProperties1 = getWikidataIDs(property1, True)
    possibleProperties2 = getWikidataIDs(property2, True)

    for object in possibleObjects:
        for property in possibleProperties1:
            log('trying: ' + property['display']['label']['value'] +
                ' of ' + object['display']['label']['value'])
            answer = queryWikidata(buildQuery(
                 object['id'], property['id']))

            if answer is not None:
                return answer
            else:
                for property2 in possibleProperties2:
                     log('trying: ' + property['display']['label']['value'] +
                     ' of ' + object['display']['label']['value'])
                     answer = queryWikidata(buildQuery(
                         object['id'], property2['id']))
                     if answer is not None:
                        return answer

def yesNoQuestion(doc):
    nouns = list(doc.noun_chunks)
    def removeArticle(str): return re.sub('^(?:the|a|an) ', '', str)
    log('Noun chunks: ' + str(nouns))

    noun1 = removeArticle(nouns[len(nouns)-1].text)

    if (len(nouns) <= 3):
        noun2 = removeArticle(nouns[0].text)
    else:
        pattern = '(' + nouns[1] + '.*?' + \
            nouns[len(nouns)-2].text + ')'
        m = re.search(pattern, doc.text)
        noun1 = removeArticle(m.group(1))

    noun1Possibilities = getWikidataIDs(noun1)
    noun2Possibilities = getWikidataIDs(noun2)

    for noun1try in noun1Possibilities:
        for noun2try in noun2Possibilities:
            log('trying: is a ' + noun2try['display']['label']['value'] +
                ' a ' + noun1try['display']['label']['value'])
            answer = queryWikidata(buildYesNoQuery(
                noun2try['id'], noun1try['id']))
            if answer is not None:
                return answer

def countQuestion(doc):
    if ("old" in doc.text):
        property = ""

    return doc

def whenQuestion(doc):

    return doc


diffName = ["also known as", "other names", "other word", "another name"]

def getSynonyms(word):
    synonyms = []
    for syn in wordnet.synsets(str(word)):
        for l in syn.lemmas():
            synonyms.append(l.name())
    print(synonyms)
    

def processProperty(word):
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
        case "pregnant" | "pregnancy":
            return "gestation period"
        case "average":
            return ""
        case _:
            return word


# skos:altLabel -> for "also known as"
# schema:description -> "definition"

def formatAnswer(data):
    numOfAnswers = len(data)

    formattedAnswers = []

    for currentAns in data:
        ans = str(currentAns['answerLabel']['value']).capitalize()

        unit = ''
        if 'unitLabel' in currentAns and currentAns['unitLabel']['value'] != "1":
            unit = ' ' + currentAns['unitLabel']['value']

        # If the answer is a (number > 1) + unit combination, make unit plural
        if ans.replace('.', '', 1).isdigit() and float(ans) > 1.0 and unit != '':
            unit += 's'

        formattedAnswers.append(ans + unit)

    finalAnswer = ''

    finalAnswer += formattedAnswers[0]
    if(len(formattedAnswers) > 1): # It was printing the same value twice if the list has only one item, added if statement
        for ans in formattedAnswers[1:-1]:
            finalAnswer += ', ' + ans
        finalAnswer += ', and ' + formattedAnswers[-1]

    return finalAnswer


def queryWikidata(query):
    try:
        data = requests.get('https://query.wikidata.org/sparql',
                            headers={
                                'User-Agent': 'QASys/0.0 (https://rug.nl/LTP/; josh@bruegger.it)'},
                            params={'query': query, 'format': 'json'}).json()
        if 'ASK' in query:
            if data['boolean']:
                return 'Yes'
            else:
                return 'No'
        else:
            data = data['results']['bindings']
    except:
        traceback.print_exc()
        return 'Error: Query failed: Too many requests?'

    if len(data) == 0:
        return None

    return formatAnswer(data)


def buildQuery(object, property):
    q = 'SELECT ?answerLabel ?unitLabel WHERE{wd:'
    q += object + ' p:' + property + '?s.?s ps:'
    q += property + '?answer. OPTIONAL{?s psv:'
    q += property + '?u.?u wikibase:quantityUnit ?unit.}'
    q += 'SERVICE wikibase:label{bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en"}}'
    return q


def buildLabelQuery(obj):
    q = 'SELECT ?answerLabel WHERE { wd:'
    q += obj + ' skos:altLabel ?answerLabel. FILTER ( lang(?answerLabel) = "en" ) }'
    return q


def buildYesNoQuery(object, property):
    q = 'ASK { wd:'
    q += object + ' wdt:P279 wd:' + property + '. }'
    print(q)
    return q


def getWikidataIDs(query, isProperty=False):
    url = 'https://www.wikidata.org/w/api.php'
    params = {'action': 'wbsearchentities',
              'language': 'en',
              'format': 'json',
              'search': query}
    if isProperty:
        params['type'] = 'property'

    return requests.get(url, params).json()['search']


# Has to match (?:Who|What) (?:was|is|were) ?(?:the|a|an)? (?:.+) of ?(?:the|a|an)? (?:.+)\?
def getAnswer(question):
    propertyText, objectText = extractPropertyAndObject(question)

    # print('Looking for: ' + propertyText + ' of ' + objectText + '...')

    possibleObjects = getWikidataIDs(objectText)
    possibleProperties = getWikidataIDs(propertyText, True)

    for object in possibleObjects:
        for property in possibleProperties:
            # print('trying: ' + property['id'] + ' of ' + object['id'])
            answer = queryWikidata(buildQuery(object['id'], property['id']))
            if answer is not None:
                return answer

    return None


def answerQuestion(q):
    ans = getAnswer(q)
    if (ans != None):
        print('Question: ' + q)
        print('Answer: ' + ans)
    else:
        print("Sorry, I don't know!")


main()
