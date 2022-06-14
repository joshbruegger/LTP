import re
from shutil import ExecError

import requests
import spacy

SPACY_MODEL = 'en_core_web_trf'
SPARQL_ENDPOINT = 'https://query.wikidata.org/sparql'

HEADERS = {'User-Agent': 'QASys/0.0 (https://rug.nl/LTP/; no@email.com)'}

nlp = spacy.load(SPACY_MODEL)


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


def query_wikidata(query):
    try:
        return requests.get(SPARQL_ENDPOINT,
                            headers=HEADERS,
                            params={'query': query, 'format': 'json'}).json()['results']['bindings']
    except Exception:
        print('Error: Query failed: Too many requests?')


def main():
    # question = "What is a lion?"

    query = query_all_properties('Q670887')

    data = query_wikidata(query)

    print('edible' in str(data))

    # print(data)

    properties = []
    for item in data:
        p = item['wdLabel']['value']
        v = item['ps_Label']['value']
        if 'ID' not in p:
            properties.append(p + ': ' + v)

    print(properties)


main()

# query = '''SELECT DISTINCT ?wdLabel WHERE {
# wd:Q144 ?wdt ?a.
# ?wd wikibase:directClaim ?wdt .
# SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
# }'''
