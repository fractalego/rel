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

if __name__ == '__main__':

    #### CREATE RULES LIKE THIS
    "MATCH *(a0), *(a1,a0), *(a1), *(a1,a2), *(a2), *(a2,a3), *(a3) CREATE (a0), #Message-Topic(a0,a3), (a3)"