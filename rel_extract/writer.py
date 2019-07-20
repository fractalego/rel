from dgt.graph import GraphRule
from dgt.graph.graph import Graph, convert_graph_to_string_with_predicates


class Writer:
    def __init__(self, metric, relations_metric, print_gradient=False, print_thresholds=True):
        self._metric = metric
        self._relations_metric = relations_metric
        self._print_gradient = print_gradient
        self._print_thresholds = print_thresholds

    def write(self, graph):
        if type(graph) == Graph:
            return self._process_graph(graph)
        if type(graph) == GraphRule:
            return self._process_graph_rule(graph)
        return ''

    def _process_graph(self, graph):
        return convert_graph_to_string_with_predicates(graph._g,
                                                       self._metric,
                                                       self._relations_metric,
                                                       print_thresholds=self._print_thresholds)

    def _process_graph_rule(self, rule):
        action_pairs = rule.action_pairs
        string = ''
        for action, context in action_pairs:
            string += action + ' '
            if type(context) is Graph:
                string += self._process_graph(context) + ' '
            else:
                string += context + ' '
        if self._print_gradient and rule.gradient:
            string += ' ' + '*GRADIENT RULE*'
        return string
