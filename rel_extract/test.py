import os
import json

from dgt import DGT, set_global_device
from dgt.auxiliary.misc import get_metric_or_save_pickle
from dgt.graph.graph_matcher import GraphMatcher

_path = os.path.dirname(__file__)
_test_filename = os.path.join(_path, '../data/saved.json')

_metric = get_metric_or_save_pickle(_path, '../data/glove.txt', '../data/metric.pickle')

set_global_device('cpu')


def test(dgt, predictions, goals):
    total = 0
    true_positives = 0
    false_negatives = 0
    for prediction, goal in zip(predictions, goals):
        total += 1
        if not prediction:
            false_negatives += 1
            continue
        big_graph = prediction['graph']
        small_graph = goal
        match = GraphMatcher(small_graph, dgt._k._metric, dgt._k._relations_metric)
        is_match = big_graph.visit(match)
        if is_match:
            true_positives += 1

    print('Precision:', true_positives / total)
    print('Recall:', false_negatives / total)


if __name__ == '__main__':
    dgt = DGT(_metric, json.load(open(_test_filename)))
    goals = dgt.goals
    predictions = dgt.predict_best()
    test(dgt, predictions, goals)
