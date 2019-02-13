import os
import re
import nltk
import json

from igraph import Graph as IGraph
from parvusdb import GraphDatabase

from dgt.auxiliary.misc import get_metric_or_save_pickle
from dgt.graph.graph import Graph
from dgt.utils import get_relations_embeddings_dict_from_json

from rel_extract.nl import SpacyParser

_path = os.path.dirname(__file__)

_dataset_path = os.path.join(_path,
                             '../data/SemEval2010_task8_all_data/SemEval2010_task8_testing_keys/TEST_FILE_FULL.TXT')

_metric = get_metric_or_save_pickle(_path, '../data/glove.txt', '../data/metric.pickle')
_relations = ['acomp',
              'advcl',
              'advmod',
              'agent',
              'amod',
              'appos',
              'attr',
              'aux',
              'auxpass',
              'cc',
              'ccomp',
              'complm',
              'conj',
              'cop',
              'csubj',
              'csubjpass',
              'dep',
              'det',
              'dobj',
              'expl',
              'hmod',
              'hyph',
              'infmod',
              'intj',
              'iobj',
              'mark',
              'meta',
              'neg',
              'nmod',
              'nn',
              'npadvmod',
              'nsubj',
              'nsubjpass',
              'num',
              'number',
              'oprd',
              'obj',
              'obl',
              'parataxis',
              'partmod',
              'pcomp',
              'pobj',
              'poss',
              'possessive',
              'preconj',
              'prep',
              'prt',
              'punct',
              'quantmod',
              'rcmod',
              'root',
              'Cause-Effect',  # Rels for the goal
              'Instrument-Agency',
              'Product-Producer',
              'Content-Container',
              'Entity-Origin',
              'Entity-Destination',
              'Component-Whole',
              'Member-Collection',
              'Message-Topic',
              'entity']  # Generic relation
_rel_metric = get_relations_embeddings_dict_from_json({'relations': _relations})


def get_words(text):
    tokenizer = nltk.tokenize.TweetTokenizer()
    words = tokenizer.tokenize(text)
    to_return = []
    prior_word = None
    words.append(' ')
    for word in words:
        if word[0] == '#':
            to_return.append(prior_word + word)
            prior_word = None
        else:
            to_return.append(prior_word)
            prior_word = word
    return [item for item in to_return if item]


def get_text_and_entity_indices(raw_html):
    ### THIS IS NOT COMPLETE!!!
    ### YOU MUST ALSO CAPTURE THE SENSE OF THE RELATION!!

    cleanr = re.compile('</(.*?)>')
    cleantext = re.sub(cleanr, '#\\1', raw_html)
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', cleantext)
    words = get_words(cleantext)
    first_entity = None
    second_entity = None
    sentence = ''
    for i, word in enumerate(words):
        splitted = word.split('#')
        if len(splitted) > 1:
            w = splitted[0]
            entity = splitted[1]
            if entity == 'e1':
                first_entity = (w, 'v' + str(i))
            if entity == 'e2':
                second_entity = (w, 'v' + str(i))
            sentence += w + ' '
        else:
            sentence += word + ' '
    sentence = sentence.replace('  ', ' ')
    return sentence, first_entity, second_entity


def create_goal(rel_type, entity1_and_name, entity2_and_name, _metric, _rel_metric):
    pred_string = entity1_and_name[0] + '(' + entity1_and_name[1] + ')' + ', ' \
                  + rel_type + '(' + entity1_and_name[1] + ',' + entity2_and_name[1] + ')' + ', ' \
                  + entity2_and_name[0] + '(' + entity2_and_name[1] + ')'
    return Graph.create_from_predicates_string(pred_string, _metric, _rel_metric, gradient=False)


if __name__ == '__main__':
    lines = open(_dataset_path).readlines()
    facts = []
    goals = []
    for index in range(0, len(lines), 4):
        text = lines[index].strip().split('\t')[1][1:][:-1]
        text, e1, e2 = get_text_and_entity_indices(text)
        rel_type = lines[index + 1]
        rel_type = rel_type[:rel_type.find('(')]
        _parser = SpacyParser(GraphDatabase(IGraph(directed=True)))
        try:
            dep_graph = Graph(_parser.execute(text).get_graph(), _metric, _rel_metric)
            goal_graph = create_goal(rel_type, e1, e2, _metric, _rel_metric)
        except:
            continue  ### CHECK THIS (SOME SENTENCES THROW)
        facts.append(dep_graph.predicates())
        goals.append(goal_graph.predicates())

    dict = {'facts': facts, 'goals': goals, 'relations': _relations}
    json.dump(dict, open(os.path.join(_path, '../data/training.json'), 'w'), indent=2)
