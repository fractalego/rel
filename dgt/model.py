import json
import random

from dgt.graph import GraphRule
from dgt.inference import ForwardInference
from dgt.utils import get_relations_embeddings_dict_from_json, get_data_goal_knowledge_from_json, train_all_paths, \
    print_predicates, get_string_with_all_the_rules_with_weights, pre_select_paths

from rel_extract.writer import Writer


class DGT:
    def __init__(self, glove_metric, json_dict):
        self._metric = glove_metric
        self.__load_from_json(json_dict)
        self._used_rules = []

    @property
    def goals(self):
        return self._goals

    def fit(self, epochs=20, step=5e-3, relaxation_epochs=50, relaxation_step=1e-3):
        shifts_and_finished_paths = []
        print('Training all paths.')
        metric = self._metric
        relations_metric = self._relations_metric

        for fact, goal in zip(self._data, self._goals):
            i = 0
            fw = ForwardInference(data=fact, knowledge=self._k, permutation_shift=i)
            end_graphs = fw.compute()
            metric.set_threshold(0.7)
            relations_metric.set_threshold(0.7)
            pre_select_paths(goal, end_graphs)

            finished_paths, metric, relations_metric = train_all_paths(metric, relations_metric, self._k,
                                                                       end_graphs, goal, i,
                                                                       0.6, epochs, step)
            
            if finished_paths:
                ### HERE YOU MUST UPDATE THE METRIC AS WELL!!
                #    train_all_paths(metric, relations_metric, self._k, finished_paths, goal, i,
                #                    1, 3, step)
                shifts_and_finished_paths.append((i, finished_paths, goal))
                break

        print('Relaxing.')
        for _ in range(relaxation_epochs):
            random.shuffle(shifts_and_finished_paths)
            for i, path, goal in shifts_and_finished_paths:
                _, metric, relations_metric = train_all_paths(metric, relations_metric, self._k, path, goal,
                                                              i, 1, 1, relaxation_step)

        self._used_rules = []
        writer = Writer(metric, relations_metric)
        for paths in shifts_and_finished_paths:
            for path in paths[1]:
                for rule in path[2]:
                    if type(rule) == GraphRule:
                        self._used_rules.append(writer.write(rule))
        self._used_rules = list(set(self._used_rules))

    def predict(self, fact):
        fw = ForwardInference(data=fact, knowledge=self._k, permutation_shift=0)
        end_graphs = fw.compute()
        return [{'graph': item[0], 'score': item[1]} for item in end_graphs]

    def predict_best(self):
        to_return = []
        for fact in self._data:
            fw = ForwardInference(data=fact, knowledge=self._k, permutation_shift=0)
            end_graphs = fw.compute()
            if end_graphs:
                graph = end_graphs[0]
                to_return.append({'graph': graph[0], 'score': graph[1]})
            else:
                to_return.append(None)
        return to_return

    def save(self, filestream):
        to_return = self.get_json_results()
        json.dump(to_return, filestream, indent=2)

    def get_json_results(self):
        writer = Writer(self._metric, self._relations_metric, print_thresholds=True)
        to_return = {'facts': [writer.write(item) for item in self._data],
                     'goals': [writer.write(item) for item in self._goals],
                     'relations': [word for word in self._relations_metric._model.index2word],
                     'non_trainable_rules': self._used_rules
                     }
        return to_return

    def print_all_rules(self):
        print_predicates(self._k)

    def get_all_rules_with_weights(self, print_gradient=False):
        return get_string_with_all_the_rules_with_weights(self._k, print_gradient=False)

    def __load_from_json(self, json_dict):
        self._relations_metric = get_relations_embeddings_dict_from_json(json_dict)
        self._data, self._goals, self._k = get_data_goal_knowledge_from_json(json_dict,
                                                                             self._metric,
                                                                             self._relations_metric)