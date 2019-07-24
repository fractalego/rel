import json
import os
import unittest

from dgt.auxiliary.misc import get_metric_or_save_pickle

from dgt.model import DGT

_path = os.path.dirname(__file__)

_metric = get_metric_or_save_pickle(_path, '../data/glove.txt', '../data/metric.pickle')
_metric._vector_matching_threshold = 0.7


class PynsettUnitTests(unittest.TestCase):
    def test_ten_rules_with_manually_fixed_nodes(self):
        _gradient_test_filename = os.path.join(_path, '../data/training_small10.json')
        dgt = DGT(_metric, json.load(open(_gradient_test_filename)))
        dgt.fit(epochs=50, step=1e-2, relaxation_epochs=0, relaxation_step=1e-2)
        prediction = dgt.get_json_results()
        self.assertNotEqual(prediction['non_trainable_rules'], [])
