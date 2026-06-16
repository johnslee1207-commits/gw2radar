from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.graph.graph_query import GraphData


_graph: GraphData | None = None


def load_graph() -> GraphData:
    global _graph
    _graph = build_mock_graph()
    return _graph


def get_graph() -> GraphData:
    global _graph
    if _graph is None:
        _graph = build_mock_graph()
    return _graph
