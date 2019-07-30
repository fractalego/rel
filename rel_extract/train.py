import os
import json
import logging
import time

from dgt import DGT, set_global_device
from dgt.auxiliary.misc import get_metric_or_save_pickle

logging.basicConfig(filename='example.log', level=logging.DEBUG)

_path = os.path.dirname(__file__)
_gradient_test_filename = os.path.join(_path, '../data/training_small_2goals_many_rules.json')

_metric = get_metric_or_save_pickle(_path, '../data/glove.txt', '../data/metric.pickle')
_metric._vector_matching_threshold = .7  ### THIS IS BECAUSE 0.6 is too low! Words are matched without making sense

set_global_device('cpu')

if __name__ == '__main__':
    start = time.time()
    dgt = DGT(_metric, json.load(open(_gradient_test_filename)))
    dgt.fit(epochs=20, step=1e-2, relaxation_epochs=0, relaxation_step=1e-2)
    end = time.time()
    print('Elapsed time:', (end - start))
    dgt.save(open(os.path.join(_path, '../data/saved.json'), 'w'))
