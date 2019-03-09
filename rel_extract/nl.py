import spacy

parser = spacy.load('en')


def tag_is_cardinal(tag):
    return tag == "CD"


def tag_is_determiner(tag):
    return tag == "DT" or tag == "WDT"


def tag_is_adjective(tag):
    return tag == "j" or tag == "J" or tag == "JJ" or tag == "JJS" or tag == "JJR" or tag == "PRP$"


def tag_is_noun(tag):
    return tag == "k" or tag == "viz" or tag == "rb" or tag == "n" or tag == "N" or tag == "j" or tag == "J" \
           or tag == "NN" or tag == "NNS" or tag == "NNP" or tag == "NNPS" or tag == "JJ" or tag == "JJS" \
           or tag == "PRP" or tag == "WP" or tag == "PRP"


def tag_is_only_noun(tag):
    return tag == "n" or tag == "N" or tag == "NN" or tag == "NNS" or tag == "NNP" or tag == "NNPS"


def tag_is_verb(tag):
    return tag == "v" or tag == "V" or tag == "VB" or tag == "VBP" or tag == "VBZ" or tag == "VBD" or tag == "VBN" or tag == "VBG"


def tag_is_modal(tag):
    return tag == "MD"


def tag_is_negation(tag, word):
    return (tag == 'AFX' or tag == 'RB') and (word == 'non' or word == 'not')


def simplify_tag(tag):
    if tag == 'PRP' or tag == 'PRP$':
        return tag
    if tag_is_adjective(tag):
        return 'j'
    if tag_is_noun(tag):
        return 'n'
    if tag_is_verb(tag):
        return 'v'
    return tag


class SpacyParser:
    _character_that_defines_unifier_string = '#'
    _word_substitution = {'(': 'LRB', ')': 'RRB'}

    def __init__(self, graph_database):
        self.parser = parser
        self.db = graph_database

    def execute(self, sentence):
        words = self.__get_words(sentence)
        names, words = self.__get_names(words)
        entities, words = self.__get_entities(words)

        edges, tags, types, lemmas = self.__get_edges_tags_types_and_entities(words, entities)
        g = self.__create_graph_from_elements(names, words, edges, tags, types, lemmas, entities)
        return g

    # Private

    def __get_words(self, sentence):
        words = []
        tokens = self.parser.tokenizer(sentence)
        for _, item in enumerate(tokens):
            word = item.orth_
            if word in self._word_substitution:
                word = self._word_substitution[word]
            words.append(word)
        return words

    def __get_names(self, words):
        new_words = []
        names = []
        for index, item in enumerate(words):
            splitted_word = item.split(self._character_that_defines_unifier_string)
            word = splitted_word[0].strip()
            new_words.append(word)
            if len(splitted_word) > 1:
                names.append(splitted_word[1])
            else:
                names.append("v" + str(index))
        return names, new_words

    def __get_entities(self, words):
        new_words = []
        entities = []
        for word in words:
            entity = ''
            new_words.append(word)
            entities.append(entity)
        return entities, new_words

    def __get_lemma_with_correct_capital_letters(self, lemma, word, tag):
        if tag == 'PRP$' or tag == 'PRP':
            return word.lower()
        if lemma.lower() == word.lower() or word in self._word_substitution:
            return word
        return lemma

    def __get_edges_tags_types_and_entities(self, words, entities):
        sentence = ' '.join(words)
        parsed = self.parser(sentence, 'utf8')
        edges = []
        tags = []
        types = []
        lemmas = []
        i = 0
        items_dict = dict()
        for item in parsed:
            items_dict[item.idx] = i
            i += 1
        for item in parsed:
            index = items_dict[item.idx]
            for child_index in [items_dict[l.idx] for l in item.children]:
                edges.append((index, child_index))
            tags.append(simplify_tag(item.tag_))
            types.append(item.dep_)
            lemmas.append(self.__get_lemma_with_correct_capital_letters(item.lemma_, item.orth_, item.tag_))
        for i, entity in enumerate(entities):
            token = parsed[i]
            if not entity:
                entities[i] = token.ent_type_
            if token.tag_ == 'PRP' and token.orth_.lower() != 'it':
                entities[i] = 'PERSON'
                lemmas[i] = token.orth_.lower()
        return edges, tags, types, lemmas

    def __get_head_token_idx(self, tokens):
        for token in tokens:
            if token.dep_ == 'ROOT':
                return token.idx
        return -1

    def __create_graph_from_elements(self, names, words, edges, tags, types, lemmas, entities):
        db = self.db
        for edge in edges:
            lhs_vertex = edge[0]
            rhs_vertex = edge[1]
            lhs_name = names[lhs_vertex]
            rhs_name = names[rhs_vertex]
            lhs_word = words[lhs_vertex]
            rhs_word = words[rhs_vertex]
            lhs_lemma = lemmas[lhs_vertex]
            rhs_lemma = lemmas[rhs_vertex]
            lhs_entity = entities[lhs_vertex]
            rhs_entity = entities[rhs_vertex]
            lhs_compound = lhs_word
            rhs_compound = rhs_word
            lhs_tag = tags[lhs_vertex]
            rhs_tag = tags[rhs_vertex]
            edge_type = types[rhs_vertex]

            if lhs_entity == lhs_word:
                lhs_word = '*'
                lhs_tag = '*'
                lhs_compound = '*'
                lhs_lemma = '*'
            if rhs_entity == rhs_word:
                rhs_word = '*'
                rhs_tag = '*'
                rhs_compound = '*'
                rhs_lemma = '*'

            lhs_dict = {'text': lhs_word,
                        'tag': lhs_tag,
                        'compound': lhs_compound,
                        'entity': lhs_entity,
                        'lemma': lhs_lemma}
            lhs_string = str(lhs_dict) + '(' + lhs_name + ')'
            rhs_dict = {'text': rhs_word,
                        'tag': rhs_tag,
                        'compound': rhs_compound,
                        'entity': rhs_entity,
                        'lemma': rhs_lemma}
            rhs_string = str(rhs_dict) + '(' + rhs_name + ')'

            edge_dict = {'relation': edge_type}
            edge_string = str(edge_dict) + '(' + lhs_name + ',' + rhs_name + ')'
            query_string = 'CREATE ' + lhs_string + ',' + edge_string + ',' + rhs_string
            db.query(query_string)
        return db
