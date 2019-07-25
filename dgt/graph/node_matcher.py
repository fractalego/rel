from parvusdb.utils.node_matcher import StringNodeMatcher


class VectorNodeMatcher(StringNodeMatcher):
    """
    Checks whether one dict is contained into another one.
    The word within each node is compared according to vector distance.
    """

    def __init__(self, metric, relation_metric, gradient=False):
        self._metric = metric
        self._relation_metric = relation_metric
        self.gradient = gradient

    def _match(self, key, lhs, rhs):
        if key == 'relation':
            return True
        if self.gradient:
            return True
        if key == 'text':
            return True
        if key == 'vector':
            return self._metric.indices_have_similar_vectors(rhs, lhs)
        if key == 'rvector':
            return self._relation_metric.indices_have_similar_vectors(rhs, lhs)

        return StringNodeMatcher._match(self, key, lhs, rhs)
