import os
import torch
import logging

from gensim.models import KeyedVectors

from parvusdb import create_graph_from_string
from parvusdb.utils.code_container import DummyCodeContainer
from parvusdb.utils.match import Match
from parvusdb.utils.match import MatchException

from dgt.graph import GraphRule
from dgt.graph.graph import Graph
from dgt.graph.node_matcher import VectorNodeMatcher
from dgt.knowledge import Knowledge
from dgt.metric import GloveMetric
from dgt.auxiliary.config import device

from rel_extract.writer import Writer

_logger = logging.getLogger(__file__)

_path = os.path.dirname(__file__)

_small = 1e-15
_max_items_size = 30


def get_data_goal_knowledge_from_json(json_item, metric, relations_metric):
    fact_lst = json_item['facts']
    goal_lst = json_item['goals']
    if len(fact_lst) != len(goal_lst):
        raise RuntimeError('The number of facts and goals is not the same!')
    nongrad_rules = '; '.join(json_item['non_trainable_rules'])
    if 'trainable_rules' in json_item:
        grad_rules = '; '.join(json_item['trainable_rules'])
    else:
        grad_rules = ''
    data = []
    goals = []
    for fact in fact_lst:
        data.append(Graph.create_from_predicates_string(fact, metric, relations_metric, gradient=False))
    for goal in goal_lst:
        goals.append(Graph.create_from_predicates_string(goal, metric, relations_metric, gradient=False))
    k = Knowledge(metric=metric, relations_metric=relations_metric)
    k.add_rules(nongrad_rules, gradient=False)
    k.add_rules(grad_rules, gradient=True)
    return data, goals, k


def get_relations_embeddings_dict_from_json(json_item, embedding_size=50):
    relations = json_item['relations']
    embeddings = torch.nn.Embedding(len(relations), embedding_size).to(device)
    vectors = [embeddings(torch.LongTensor([i]))[0].detach().numpy() for i in range(len(relations))]
    model = KeyedVectors(embedding_size)
    model.add(relations, vectors)
    return GloveMetric(model, threshold=0.9)


def print_predicates(k):
    rules = k.get_all_rules()
    print('Predicates:')
    for rule in rules:
        print(rule[0].predicates())


def print_all_the_paths(end_graph):
    for item in end_graph:
        print('---')
        print(item[1])
        [print(item.predicates()) for item in item[2]]


def print_all_the_rules_with_weights(k):
    rules = k.get_all_rules()
    print('Predicates:')
    for rule in rules:
        print(rule[0].predicates(), rule[0].weight)


def get_string_with_all_the_rules_with_weights(k, print_gradient=False):
    rules = k.get_all_rules()
    str_list = []
    for rule in rules:
        str_list.append(
            rule[0].predicates(print_threshold=True, print_gradient=print_gradient).strip().replace('  ', ' '))
    return str_list


def create_graph_list(inference_list, goal):
    graph_list = []
    for item in inference_list:
        if type(item) is GraphRule:
            graph_list.append(str(item.get_hypothesis()))
        elif type(item) is Graph:
            graph_list.append(str(item))
    graph_list.append(str(goal))
    return graph_list


def create_rule_matrix(len_cons, len_hyp, matrix_size):
    rule_matrix = torch.zeros([matrix_size, matrix_size]).to(device)
    for i in range(len_cons):
        for j in range(len_hyp):
            rule_matrix[i, j] = 1.
    return rule_matrix


def create_all_rule_matrices(inference_list):
    rule_matrices = []
    relations_rule_matrices = []
    for item in inference_list:
        if type(item) is GraphRule:
            hyp = item.get_hypothesis()
            cons = item.get_consequence()
            weight = item.weight.clamp(min=0, max=1.)
            rule_matrix = weight * create_rule_matrix(len(cons._g.vs), len(hyp._g.vs), _max_items_size)
            relation_rule_matrix = weight * create_rule_matrix(len(cons._g.es), len(hyp._g.es), _max_items_size)
            rule_matrices.append(rule_matrix)
            relations_rule_matrices.append(relation_rule_matrix)
    return rule_matrices, relations_rule_matrices


def get_weight_list(inference_list):
    weight_list = []
    for item in inference_list:
        if type(item) is GraphRule:
            weight_list.append(item.weight.clamp(min=0, max=1.))
    return weight_list


def get_proper_vector(metric, item, key):
    vector_index = item[key]
    vector = metric.get_vector_from_index(vector_index) / metric.get_vector_from_index(vector_index).norm(2)
    return vector


def graph_iterations(g):
    length = len(g.vs)
    permutations = []
    for i in range(length):
        permutation = [(s + i) % length for s in range(length)]
        permutations.append(g.permute_vertices(permutation))
    return permutations


def get_weighted_match(lhs, rhs, matching_variables, metric):
    w = 0
    for k, v in matching_variables[0].items():
        rindex = rhs.vs['name' == v]['vector']
        lindex = lhs.vs['name' == k]['vector']
        w += metric.indices_dot_product(lindex, rindex)
    return w


def get_matching_variables(match, gl, gr, metric):
    all_matches = []
    for left_g in graph_iterations(gl):
        matching_variables = match.get_variables_substitution_dictionaries(left_g, gr)
        w = get_weighted_match(left_g, gr, matching_variables, metric)
        all_matches.append((matching_variables, w))

    return sorted(all_matches, key=lambda x: -x[1])[0][0]


def create_list_of_states(metric, relations_metric, graph_list, match, permutation_shift):
    pre_match = []
    post_match = []
    post_thresholds = []
    substitutions = []
    for i in range(0, len(graph_list), 2):
        gl = create_graph_from_string(str(graph_list[i]))
        gr = create_graph_from_string(str(graph_list[i + 1]))

        try:
            iterations = graph_iterations(gl)
            gl = iterations[permutation_shift % len(iterations)]
            substitutions.append(match.get_variables_substitution_dictionaries(gl, gr))
            # substitutions.append(get_matching_variables(match, gl, gr, metric))
            pre_items = [[item['name'], get_proper_vector(metric, item, 'vector')] for item in gl.vs]
            post_items = [[item['name'], get_proper_vector(metric, item, 'vector')] for item in gr.vs]

            len_pre_items = len(pre_items)
            len_post_items = len(post_items)

            pre_items += [['dummy', torch.zeros(metric.vector_size).to(device)] for _ in
                          range(_max_items_size - len_pre_items)]
            post_items += [['dummy', torch.zeros(metric.vector_size).to(device)] for _ in
                           range(_max_items_size - len_post_items)]

            pre_match.append(pre_items)
            post_match.append(post_items)

            post_thrs = [metric.get_threshold_from_index(item['vector']) for item in gr.vs]
            post_thrs += [torch.zeros(1).to(device) for _ in range(_max_items_size - len(post_thrs))]
            post_thresholds.append(post_thrs)

        except MatchException:
            return [], [], [], []
    return pre_match, post_match, post_thresholds, substitutions


def create_list_of_states_without_weight_matching(metric, relations_metric, graph_list, match):
    pre_match = []
    post_match = []
    post_thresholds = []
    substitutions = []
    for i in range(0, len(graph_list), 2):
        gl = create_graph_from_string(str(graph_list[i]))
        gr = create_graph_from_string(str(graph_list[i + 1]))

        try:
            substitutions.append(match.get_variables_substitution_dictionaries(gl, gr))
            pre_items = [[item['name'], get_proper_vector(metric, item, 'vector')] for item in gl.vs]
            post_items = [[item['name'], get_proper_vector(metric, item, 'vector')] for item in gr.vs]

            len_pre_items = len(pre_items)
            len_post_items = len(post_items)

            pre_items += [['dummy', torch.zeros(metric.vector_size).to(device)] for _ in
                          range(_max_items_size - len_pre_items)]
            post_items += [['dummy', torch.zeros(metric.vector_size).to(device)] for _ in
                           range(_max_items_size - len_post_items)]

            pre_match.append(pre_items)
            post_match.append(post_items)

            post_thrs = [metric.get_threshold_from_index(item['vector']) for item in gr.vs]
            post_thrs += [torch.zeros(1).to(device) for _ in range(_max_items_size - len(post_thrs))]
            post_thresholds.append(post_thrs)

        except MatchException:
            return [], [], [], []
    return pre_match, post_match, post_thresholds, substitutions


def order_pre_post_matches_according_to_substitutions(pre_match, post_match, substitutions, nodes_or_relations=0):
    """
    Reorders the matching vectors so that they are in the order of substitution (the scattering matrix becomes diagonal)
    :param pre_match:
    :param post_match:
    :param substitutions:
    :param nodes_or_relations:
    :return:
    """
    new_pre_match = []
    new_post_match = []
    for i in range(len(substitutions)):
        l_vector = []
        r_vector = []
        used_l_indices = []
        used_r_indices = []
        for k, v in substitutions[i][nodes_or_relations].items():
            l_index = [item[0] for item in pre_match[i]].index(v)
            r_index = [item[0] for item in post_match[i]].index(k)
            l_vector.append(pre_match[i][l_index])
            r_vector.append(post_match[i][r_index])
            used_l_indices.append(v)
            used_r_indices.append(k)

        for item in pre_match[i]:
            index = item[0]
            if index in used_l_indices:
                continue
            l_vector.append(item)

        for item in post_match[i]:
            index = item[0]
            if index in used_r_indices:
                continue
            r_vector.append(item)

        # Sometimes indices can repeat themselves (due to the matching algorithm. This normalises the length to the max length
        len_pre_items = len(l_vector)
        len_post_items = len(r_vector)
        l_vector += [['dummy', torch.zeros(pre_match[i][0][1].shape[0]).to(device)] for _ in
                     range(_max_items_size - len_pre_items)]
        r_vector += [['dummy', torch.zeros(post_match[i][0][1].shape[0]).to(device)] for _ in
                     range(_max_items_size - len_post_items)]

        new_pre_match.append(l_vector)
        new_post_match.append(r_vector)

    return new_pre_match, new_post_match


def create_list_of_states_for_relations(nodes_metric, metric, graph_list, match, permutation_shift):
    pre_match = []
    post_match = []
    post_thresholds = []
    substitutions = []
    for i in range(0, len(graph_list), 2):
        gl = create_graph_from_string(str(graph_list[i]))
        gr = create_graph_from_string(str(graph_list[i + 1]))

        try:
            iterations = graph_iterations(gl)
            gl = iterations[permutation_shift % len(iterations)]
            substitutions.append(match.get_variables_substitution_dictionaries(gl, gr))
            # substitutions.append(get_matching_variables(match, gl, gr, nodes_metric))
            pre_items = [[item['name'], get_proper_vector(metric, item, 'rvector')] for item in gl.es]
            post_items = [[item['name'], get_proper_vector(metric, item, 'rvector')] for item in gr.es]

            len_pre_items = len(pre_items)
            len_post_items = len(post_items)

            pre_items += [['dummy', torch.zeros(metric.vector_size).to(device)] for _ in
                          range(_max_items_size - len_pre_items)]
            post_items += [['dummy', torch.zeros(metric.vector_size).to(device)] for _ in
                           range(_max_items_size - len_post_items)]

            pre_match.append(pre_items)
            post_match.append(post_items)

            post_thrs = [metric.get_threshold_from_index(item['rvector']) for item in gr.es]
            post_thrs += [torch.ones(1).to(device) for _ in range(_max_items_size - len(post_thrs))]
            post_thresholds.append(post_thrs)

        except MatchException:
            return [], [], [], []
    return pre_match, post_match, post_thresholds, substitutions


def create_scattering_sequence(pre_match, post_match, post_thresholds, substitutions, rule_matrices,
                               nodes_or_relations, clamp):
    scattering_matrices = []
    adjacency_matrices = []
    for i in range(len(substitutions)):
        pre_vectors = torch.stack([item[1] for item in pre_match[i]])
        post_vectors = torch.stack([item[1] for item in post_match[i]])
        post_biases = torch.stack([item[0] for item in post_thresholds[i]])

        bias_matrix = torch.ones([_max_items_size, _max_items_size]).to(device)
        for i2 in range(_max_items_size):
            for j2 in range(_max_items_size):
                bias_matrix[i2, j2] = post_biases[j2].clamp(min=clamp, max=1)

        softmax = torch.nn.Softmax()
        scattering_matrix = softmax(torch.mm(post_vectors, torch.transpose(pre_vectors, 0, 1)) - bias_matrix)
        adjacency_matrix = torch.zeros(scattering_matrix.shape).to(device)
        for k, v in substitutions[i][nodes_or_relations].items():
            l_index = [item[0] for item in pre_match[i]].index(v)
            r_index = [item[0] for item in post_match[i]].index(k)
            adjacency_matrix[l_index, r_index] = 1.
        scattering_matrix = torch.mul(adjacency_matrix, scattering_matrix)
        scattering_matrices.append(scattering_matrix)
        adjacency_matrices.append(adjacency_matrix)

    scattering_sequence = torch.eye(_max_items_size).to(device)
    for i, scattering_matrix in enumerate(scattering_matrices):
        scattering_sequence = torch.mm(scattering_matrix, scattering_sequence)
        try:
            rule_matrix = rule_matrices[i]
            scattering_sequence = torch.mm(rule_matrix, scattering_sequence)
        except:
            pass

    return scattering_sequence


def train_a_single_path(path, goal, metric, relations_metric, match_factory, optimizer, epochs,
                        permutation_shift, clamp):
    for i in range(epochs):
        graph_list = create_graph_list(path[2], goal)
        rule_matrices, relations_rule_matrices = create_all_rule_matrices(path[2])

        # Skip training for paths that do not have a differentiable rule
        has_gradient_rule = False
        for it in path[2]:
            if it.gradient:
                has_gradient_rule = True
                break
        if not has_gradient_rule:
            break

        # Printing path out while training
        # print('new path:')
        # [print(it.predicates()) for it in path[2]]

        pre_match, post_match, post_thresholds, substitutions = create_list_of_states(metric,
                                                                                      relations_metric,
                                                                                      graph_list,
                                                                                      match_factory.create_no_threshold_match(),
                                                                                      permutation_shift)
        relations_pre_match, relations_post_match, relations_post_thresholds, substitutions \
            = create_list_of_states_for_relations(metric, relations_metric, graph_list,
                                                  match_factory.create_no_threshold_match(),
                                                  permutation_shift)

        if not substitutions:
            break
        pre_match, post_match = order_pre_post_matches_according_to_substitutions(pre_match, post_match, substitutions,
                                                                                  nodes_or_relations=0)
        if not substitutions:
            break
        # print(substitutions)

        scattering_sequence = create_scattering_sequence(pre_match, post_match, post_thresholds, substitutions,
                                                         rule_matrices, nodes_or_relations=0, clamp=clamp)

        relations_pre_match, relations_post_match = order_pre_post_matches_according_to_substitutions(
            relations_pre_match, relations_post_match,
            substitutions,
            nodes_or_relations=1)
        relations_scattering_sequence = create_scattering_sequence(relations_pre_match, relations_post_match,
                                                                   relations_post_thresholds, substitutions,
                                                                   relations_rule_matrices, nodes_or_relations=1,
                                                                   clamp=clamp)
        initial_vector = torch.ones(_max_items_size).to(device)
        final_vector = torch.mv(scattering_sequence, initial_vector)
        goal_vector = torch.Tensor([0 if item[0] is 'dummy' else 1 for item in post_match[-1]]).to(device)

        relations_initial_vector = torch.ones(_max_items_size).to(device)
        relations_final_vector = torch.mv(relations_scattering_sequence, relations_initial_vector)
        relations_goal_vector = torch.Tensor([0 if item[0] is 'dummy' else 1 for item in relations_post_match[-1]]).to(
            device)

        criterion = torch.nn.BCEWithLogitsLoss()
        # criterion = torch.nn.MSELoss()
        loss = (criterion(final_vector, goal_vector)
                + criterion(relations_final_vector, relations_goal_vector)
                ).to(device)
        optimizer.zero_grad()
        loss.backward(retain_graph=True)
        optimizer.step()

        # Check if the trained sequence of rules actually satisfy the goal
        new_graph_list = create_graph_list(path[2], goal)
        _, _, _, substitutions = create_list_of_states(metric, relations_metric, new_graph_list,
                                                       match_factory.create_threshold_match(),
                                                       permutation_shift)
        if substitutions:
            print('Making the substitution!', loss)
            return metric, relations_metric

    return None


class MatchFactory:
    def __init__(self, metric, relations_metric, match_index):
        self._match_index = match_index
        self._metric = metric
        self._relations_metric = relations_metric

    def create_no_threshold_match(self):
        return Match(matching_code_container=DummyCodeContainer(),
                     node_matcher=VectorNodeMatcher(self._metric, self._relations_metric, gradient=True),
                     match_index=self._match_index)

    def create_threshold_match(self):
        return Match(matching_code_container=DummyCodeContainer(),
                     node_matcher=VectorNodeMatcher(self._metric, self._relations_metric, gradient=False),
                     match_index=self._match_index)


def train_all_paths(old_metric, old_relations_metric, k, paths, goal, permutation_shift, clamp, epochs=50, step=1e-2):
    import copy

    finished_paths = []
    for item in paths:
        try:
            for match_index in range(10):
                metric = copy.deepcopy(old_metric)
                relations_metric = copy.deepcopy(old_relations_metric)

                vectors_to_modify = metric.get_indexed_vectors()
                threshold_to_modify = metric.get_indexed_thresholds()
                rules_weights_to_modify = [rule[0].weight for rule in k.get_all_rules()]
                relations_vectors_to_modify = relations_metric.get_indexed_vectors()
                relations_threshold_to_modify = relations_metric.get_indexed_thresholds()

                optimizer = torch.optim.Adam(vectors_to_modify + threshold_to_modify + rules_weights_to_modify
                                             + relations_threshold_to_modify + relations_vectors_to_modify,
                                             lr=step)

                results = train_a_single_path(item, goal, metric, relations_metric,
                                              MatchFactory(metric, relations_metric, match_index=match_index),
                                              optimizer,
                                              epochs, permutation_shift, clamp)

                if results:
                    finished_paths.append(item)
                    old_metric = metric
                    old_relations_metric = relations_metric
                    #break
                    print('Match index:', match_index)
                    return finished_paths, old_metric, old_relations_metric
        except Exception as e:
            _logger.warning(str(e))

    if finished_paths:
        return finished_paths, old_metric, old_relations_metric

    return None


def pre_select_paths(goal, paths, metric, relations_metric):
    match = Match(matching_code_container=DummyCodeContainer(),
                  node_matcher=VectorNodeMatcher(metric, relations_metric, gradient=False),
                  match_index=0)

    reasonable_paths = []
    for path in paths:
        graph_list = create_graph_list(path[2], goal)
        graph_list.reverse()

        goal_graph = create_graph_from_string(str(graph_list[0]))
        last_consequence_graph = create_graph_from_string(str(graph_list[1]))
        try:
            substitutions = match.get_variables_substitution_dictionaries(last_consequence_graph, goal_graph)
        except MatchException:
            continue

        reasonable_paths.append(path)
        for k, v in substitutions[0].items():
            rules_metric_index = last_consequence_graph.vs.find(name=v)['vector']
            rules_threshold = metric.get_threshold_from_index(rules_metric_index)
            goal_metric_index = goal_graph.vs.find(name=k)['vector']
            print(metric.get_most_similar_string_from_index(rules_metric_index),
                  metric.get_threshold_from_index(rules_metric_index))
            print(metric.get_most_similar_string_from_index(goal_metric_index),
                  metric.get_threshold_from_index(goal_metric_index))
            if metric.indices_dot_product(rules_metric_index, goal_metric_index) < rules_threshold:
                metric.copy_index_to_index(goal_metric_index, rules_metric_index, gradient=False)

    return metric, relations_metric, reasonable_paths
