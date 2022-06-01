const AJV = require("ajv")
const ajv = new AJV({allErrors: true})


/**
 * Determines whether `data` adheres to our JSON QA schema.
 *
 * The result is logged to the console.
 *
 * @param {object} data - The data to validate.
 */
function validateData(data) {
    const valid = validate(data)
    if (valid) {
        console.log("Valid!")
    } else {
        console.warn("Invalid: " + ajv.errorsText(validate.errors))
    }
}


/* Learn how to write your own JSON schemata at
 * https://json-schema.org/understanding-json-schema/index.html. */
const qaSchema = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "definitions": {
        "answer": {
            "type": "object",
            "properties": {
                "string": { "type": "string" },
                "uri": {
                    "type": "string",
                    "pattern": "^(https://www\.wikidata\.org/wiki/)[QP][1-9][0-9]*$"
                }
            },
            "required": ["string", "uri"],
            "additionalProperties": false
        },
        "question": {
            "type": "object",
            "properties": {
                "string": {
                    "type": "string",
                    "pattern": "^[A-Z][^\?]+(\\?)$"
                },
                "answer": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "$ref": "#/definitions/answer",
                    }
                },
                "studentnumber": {
                    "type": "string",
                    "pattern": "^[sp][0-9]{7,}$"
                }
            },
            "required": ["string", "answer", "studentnumber"],
            "additionalProperties": false
        }
    },
    "type": "array",
    "items": {
        "$ref": "#/definitions/question"
    }
}



const validate = ajv.compile(qaSchema)


/* Paste your own set of QA pairs below. */
const questions = [
  {
    "studentnumber": "s4361687",
    "string": "What is the scientific name for cat?",
    "answer": [
      {
        "string": "Felis silvestris catus",
        "uri": "https://www.wikidata.org/wiki/Q146"
      },
      {
        "string": "Felis catus",
        "uri": "https://www.wikidata.org/wiki/Q146"
      }
    ]
  },
  {
    "studentnumber": "s4361687",
    "string": "What is the oldest cat?",
    "answer": [
      {
        "string": "Cream Puff",
        "uri": "https://www.wikidata.org/wiki/Q2597104"
      }
    ]
  },
  {
    "studentnumber": "s4361687",
    "string": "When did Unsinkable Sam die?",
    "answer": [
      {
        "string": "1955",
        "uri": "https://www.wikidata.org/wiki/Q893453"
      }
    ]
  },
  {
    "studentnumber": "s4361687",
    "string": "How many dog breeds are there?",
    "answer": [
      {
        "string": "813",
        "uri": "https://www.wikidata.org/wiki/Q39367"
      }
    ]
  },
  {
    "studentnumber": "s4361687",
    "string": "Are bananas berries?",
    "answer": [
      {
        "string": "Yes",
        "uri": "https://www.wikidata.org/wiki/Q503"
      }
    ]
  },
  {
    "studentnumber": "s4361687",
    "string": "What is the hottest chili pepper?",
    "answer": [
      {
        "string": "Carolina Reaper",
        "uri": "https://www.wikidata.org/wiki/Q15427475"
      }
    ]
  },
  {
    "studentnumber": "s4361687",
    "string": "How heigh is an elephant?",
    "answer": [
      {
        "string": "4 metres",
        "uri": "https://www.wikidata.org/wiki/Q7378"
      }
    ]
  },
  {
    "studentnumber": "s4361687",
    "string": "Are sheeps herbivores?",
    "answer": [
      {
        "string": "Yes",
        "uri": "https://www.wikidata.org/wiki/Q7368"
      }
    ]
  },
  {
    "studentnumber": "s4361687",
    "string": "What is the sound of an eagle called?",
    "answer": [
      {
        "string": "Eagle cry",
        "uri": "https://www.wikidata.org/wiki/Q2092297"
      }
    ]
  },
  {
    "studentnumber": "s4361687",
    "string": "When did we start cultivating cucumbers?",
    "answer": [
      {
        "string": "Circa 3000 BCE",
        "uri": "https://www.wikidata.org/wiki/Q2735883"
      }
    ]
  }
]


/* If the console outputs 'Valid!', your QA pairs are valid. */
validateData(questions)

