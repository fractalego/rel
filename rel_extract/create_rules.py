import os
import json

_path = os.path.dirname(__file__)
_rules_filename = os.path.join(_path, '../data/all_gradient_rules.json')

relations = [
    "Cause-Effect",
    "Instrument-Agency",
    "Product-Producer",
    "Content-Container",
    "Entity-Origin",
    "Entity-Destination",
    "Component-Whole",
    "Member-Collection",
    "Message-Topic",
    "entity"
]

rules = [
    "MATCH *(a0), *(a0,a1), *(a1) CREATE (a0), #%s(a0,a1), (a1)",
    "MATCH *(a0), *(a1,a0), *(a1) CREATE (a0), #%s(a0,a1), (a1)",

    "MATCH *(a0), *(a0,a1), *(a1), *(a1,a2), *(a2) CREATE (a0), #%s(a0,a2), (a2)",
    "MATCH *(a0), *(a1,a0), *(a1), *(a1,a2), *(a2) CREATE (a0), #%s(a0,a2), (a2)",
    "MATCH *(a0), *(a0,a1), *(a1), *(a2,a1), *(a2) CREATE (a0), #%s(a0,a2), (a2)",

    "MATCH *(a0), *(a0,a1), *(a1), *(a1,a2), *(a2), *(a2,a3), *(a3) CREATE (a0), #%s(a0,a3), (a3)",
    "MATCH *(a0), *(a1,a0), *(a1), *(a1,a2), *(a2), *(a2,a3), *(a3) CREATE (a0), #%s(a0,a3), (a3)",
    "MATCH *(a0), *(a0,a1), *(a1), *(a2,a1), *(a2), *(a2,a3), *(a3) CREATE (a0), #%s(a0,a3), (a3)",
    "MATCH *(a0), *(a0,a1), *(a1), *(a1,a2), *(a2), *(a3,a2), *(a3) CREATE (a0), #%s(a0,a3), (a3)",
]

if __name__ == '__main__':
    gradient_rules = []
    for relation in relations:
        for rule in rules:
            gradient_rules.append(rule % relation)

    json.dump({'trainable_rules': gradient_rules}, open(_rules_filename, 'w'), indent=2)
