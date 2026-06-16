from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.graph.graph_query import GraphData
from gw2radar.db.init_db import init_db
from gw2radar.db.repositories import GraphRepository
from gw2radar.db import session as db_session


_graph: GraphData | None = None


def load_graph() -> GraphData:
    global _graph
    _graph = build_mock_graph()
    save_graph(_graph)
    return _graph


def get_graph() -> GraphData:
    global _graph
    if _graph is None:
        _graph = load_graph_from_db()
    if _graph is None:
        _graph = build_mock_graph()
    return _graph


def save_graph(graph: GraphData) -> None:
    init_db()
    with db_session.SessionLocal() as session:
        GraphRepository(session).replace_graph(graph)


def load_graph_from_db() -> GraphData | None:
    init_db()
    with db_session.SessionLocal() as session:
        return GraphRepository(session).load_graph()


def reset_cached_graph() -> None:
    global _graph
    _graph = None
