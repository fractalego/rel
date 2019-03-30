import os
import json
import logging

from dgt import DGT, set_global_device
from dgt.auxiliary.misc import get_metric_or_save_pickle

logging.basicConfig(filename='example.log', level=logging.DEBUG)

_path = os.path.dirname(__file__)
_gradient_test_filename = os.path.join(_path, '../data/training_small.json')

_metric = get_metric_or_save_pickle(_path, '../data/glove.txt', '../data/metric.pickle')

set_global_device('cpu')

if __name__ == '__main__':
    dgt = DGT(_metric, json.load(open(_gradient_test_filename)))
    dgt.fit(epochs=10, step=1e-2, relaxation_epochs=200, relaxation_step=1e-2)
    dgt.save(open(os.path.join(_path, '../data/saved.json'), 'w'))
