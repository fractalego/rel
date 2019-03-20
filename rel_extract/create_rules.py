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
    "entity"  ## ENTITY IS THE Other RELATION (WHY NOT CALL IT OTHER THEN?!)
]

addendum = [
    "",
    ", *(a0, a4), *(a4)",
    ", *(a1, a4), *(a4)",
    ", *(a2, a4), *(a4)",
    ", *(a3, a4), *(a4)",
]

rules_2 = [
    "MATCH *(a0), *(a0,a1), *(a1) %s CREATE (a0), #%s(a0,a1), (a1)",
    "MATCH *(a0), *(a1,a0), *(a1) %s CREATE (a0), #%s(a0,a1), (a1)",
]

rules_3 = [
    "MATCH *(a0), *(a0,a1), *(a1), *(a1,a2), *(a2) %s CREATE (a0), #%s(a0,a2), (a2)",
    "MATCH *(a0), *(a1,a0), *(a1), *(a1,a2), *(a2) %s CREATE (a0), #%s(a0,a2), (a2)",
    "MATCH *(a0), *(a0,a1), *(a1), *(a2,a1), *(a2) %s CREATE (a0), #%s(a0,a2), (a2)",
    "MATCH *(a0), *(a1,a0), *(a1), *(a2,a1), *(a2) %s CREATE (a0), #%s(a0,a2), (a2)",
]

rules_4 = [
    "MATCH *(a0), *(a0,a1), *(a1), *(a1,a2), *(a2), *(a2,a3), *(a3) %s CREATE (a0), #%s(a0,a3), (a3)",
    "MATCH *(a0), *(a1,a0), *(a1), *(a1,a2), *(a2), *(a2,a3), *(a3) %s CREATE (a0), #%s(a0,a3), (a3)",
    "MATCH *(a0), *(a0,a1), *(a1), *(a2,a1), *(a2), *(a2,a3), *(a3) %s CREATE (a0), #%s(a0,a3), (a3)",
    "MATCH *(a0), *(a0,a1), *(a1), *(a1,a2), *(a2), *(a3,a2), *(a3) %s CREATE (a0), #%s(a0,a3), (a3)",
    "MATCH *(a0), *(a1,a0), *(a1), *(a2,a1), *(a2), *(a2,a3), *(a3) %s CREATE (a0), #%s(a0,a3), (a3)",
    "MATCH *(a0), *(a1,a0), *(a1), *(a1,a2), *(a2), *(a3,a2), *(a3) %s CREATE (a0), #%s(a0,a3), (a3)",
    "MATCH *(a0), *(a1,a0), *(a1), *(a2,a3), *(a2), *(a3,a2), *(a3) %s CREATE (a0), #%s(a0,a3), (a3)",
    "MATCH *(a0), *(a0,a1), *(a1), *(a2,a3), *(a2), *(a3,a2), *(a3) %s CREATE (a0), #%s(a0,a3), (a3)",
]

if __name__ == '__main__':
    gradient_rules = []
    for relation in relations:
        for rule in rules_2:
            for add in addendum[:3]:
                gradient_rules.append(rule % (add, relation))

        for rule in rules_3:
            for add in addendum[:4]:
                gradient_rules.append(rule % (add, relation))

        for rule in rules_4:
            for add in addendum[:5]:
                gradient_rules.append(rule % (add, relation))

    json.dump({'trainable_rules': gradient_rules}, open(_rules_filename, 'w'), indent=2)
