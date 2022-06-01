import re

import requests
import spacy


def main():
    nlp = spacy.load('en_core_web_trf')
    question = "What is a lion?"

    query = '''SELECT DISTINCT ?wdLabel WHERE {
    wd:Q144 ?wdt ?a.
    ?wd wikibase:directClaim ?wdt .
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }'''

    try:
        data = requests.get('https://query.wikidata.org/sparql',
                            headers={
                                'User-Agent': 'QASys/0.0 (https://rug.nl/LTP/; josh@bruegger.it)'},
                            params={'query': query, 'format': 'json'}).json()['results']['bindings']
    except:
        print('Error: Query failed: Too many requests?')

    print('mammal' in data)

    properties = []
    for item in data:
        p = item['wdLabel']['value']
        if 'ID' not in p:
            properties.append(p)

    print(properties)


main()
