import requests, re, spacy


### Cooool code starts here



def main():
    nlp = spacy.load('en_core_web_trf')

    question = input()

    # 1. get question type
    # What, where, yes/no, count, how

    doc = nlp(question) # parse the input
    firstWord = doc[0].text.lower()
    match firstWord:
        case 'what'  :
            ans = whatQuestion(doc)
        case "is" |'does' | 'are' | 'do' | 'can':
            ans = yesNoQuestion(doc)
        case "where":
            ans = whereQuestion(doc)
        case "which":
            ans = whichQuestion(doc)
        case _:
            print("IDK")


    print(ans)



### What is a Lion doesnt work!!!
### population question returns 1s as unit!!
def whatQuestion(doc):
    nouns = list(doc.noun_chunks)
    removeArticle = lambda str: re.sub('^(?:the|a|an) ', '', str)

    if len(nouns) < 3:
        # If there are less than 3 noun chunks, it's probably a question like "What is a lion?"
        entity = removeArticle(nouns[1].text)
        ## GET WIKIDATA:DESCRIPTION!!1

    else:
        entity = removeArticle(nouns[len(nouns)-1].text)
        if (len(nouns) >= 3):
            pattern = '(' + nouns[1].text + '.*?' + nouns[len(nouns)-2].text + ')'
            m = re.search(pattern, doc.text)
            property = removeArticle(m.group(1))
        else:
            property = removeArticle(nouns[1].text)

    possibleObjects = getWikidataIDs(entity)
    possibleProperties = getWikidataIDs(property, True)

    for object in possibleObjects:
        for property in possibleProperties:
            print('trying: ' + property['id'] + ' of ' + object['id'])
            answer = queryWikidata(buildQuery(object['id'], property['id']))
            if answer is not None:
                return answer






























def formatAnswer(data):
    data = data[0]
    ans = str(data['answerLabel']['value']).capitalize()

    unit = ''
    if 'unitLabel' in data:
        unit =  ' ' + data['unitLabel']['value']

    # If the answer is a (number > 1) + unit combination, make unit plural
    if ans.replace('.','',1).isdigit() and float(ans) > 1.0:
       unit += 's'

    return ans + unit



def queryWikidata(query) :
    try:
        data = requests.get('https://query.wikidata.org/sparql',
            headers = {'User-Agent': 'QASys/0.0 (https://rug.nl/LTP/; josh@bruegger.it)'},
            params={'query': query, 'format': 'json'}).json()['results']['bindings']
    except:
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



def getWikidataIDs(query, isProperty = False):
    url = 'https://www.wikidata.org/w/api.php'
    params = {'action':'wbsearchentities',
            'language':'en',
            'format':'json',
            'search': query}
    if isProperty:
        params['type'] = 'property'

    return requests.get(url,params).json()['search']








# Has to match (?:Who|What) (?:was|is|were) ?(?:the|a|an)? (?:.+) of ?(?:the|a|an)? (?:.+)\?
def getAnswer(question):
    propertyText, objectText = extractPropertyAndObject(question)

    #print('Looking for: ' + propertyText + ' of ' + objectText + '...')

    possibleObjects = getWikidataIDs(objectText)
    possibleProperties = getWikidataIDs(propertyText, True)

    for object in possibleObjects:
        for property in possibleProperties:
            #print('trying: ' + property['id'] + ' of ' + object['id'])
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