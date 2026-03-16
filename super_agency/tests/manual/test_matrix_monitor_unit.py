import pytest
from unittest.mock import patch, MagicMock
from matrix_maximizer import MatrixMaximizer


class DummyRepo:
    def __init__(self, name):
        self.name = name
        self.full_name = name
        self.size_mb = 10
        self.stars = 5
        self.priority_score = 0.1
        self.activity_score = 0.2


def make_fake_project_selector(monkeypatch):
    fake = MagicMock()
    fake.repositories = [DummyRepo('a'), DummyRepo('b')]
    async def load():
        fake.repositories = [DummyRepo('a'), DummyRepo('b')]
    fake.load_repository_data = load
    def calc():
        pass
    fake.calculate_priority_scores = calc
    async def select_top(n, crit):
        return fake.repositories[:n]
    fake.select_top_projects = select_top
    monkeypatch.setattr('matrix_maximizer.project_selector',
                        fake, raising=False)
    class SelectionCriteria:
        PRIORITY = 'priority'
        SIZE = 'size'
        STARS = 'stars'
        ACTIVITY = 'activity'
    monkeypatch.setattr('matrix_maximizer.SelectionCriteria',
                        SelectionCriteria, raising=False)
    return fake


def make_fake_qusar(monkeypatch, succeed=True):
    class FakeSync:
        def ping_qusar(self):
            if succeed:
                return {'available': True, 'status': 'ok', 'timestamp': 'now'}
            else:
                raise Exception('unreachable')
    monkeypatch.setattr(
        'matrix_maximizer.QUSARMatrixMonitorSync', FakeSync, raising=False)
    return FakeSync


def make_fake_network(monkeypatch, nodes=None, fail=False):
    class FakeNet:
        def list_nodes(self):
            if fail:
                raise RuntimeError('net error')
            return nodes or []
    monkeypatch.setattr('matrix_maximizer.global_network',
                        FakeNet(), raising=False)
    return FakeNet


def test_matrix_monitor_success(monkeypatch):
    # prepare fakes
    make_fake_project_selector(monkeypatch)
    make_fake_qusar(monkeypatch, succeed=True)
    make_fake_network(monkeypatch, nodes=[1,2,3])
    class FakeOpt:
        def __init__(self):
            self.models = {'m1': {}}
    monkeypatch.setattr('matrix_maximizer.DecisionOptimizer',
                        FakeOpt, raising=False)

    mm = MatrixMaximizer()
    data = mm._collect_matrix_monitor_data()
    assert data['matrix_monitor_status'] == 'active'
    assert 'project_selector' in data
    assert 'qusar_sync' in data
    assert data['global_network']['total_nodes'] == 3


def test_matrix_monitor_partial_failures(monkeypatch):
    make_fake_project_selector(monkeypatch)
    make_fake_qusar(monkeypatch, succeed=False)
    make_fake_network(monkeypatch, fail=True)
    monkeypatch.setattr('matrix_maximizer.DecisionOptimizer', lambda: (
        _ for _ in ()).throw(Exception('opt fail')))

    mm = MatrixMaximizer()
    data = mm._collect_matrix_monitor_data()
    # should still return, with errors logged
    assert data['matrix_monitor_status'] in ('degraded', 'error')
    assert 'errors' in data
    assert any('qusar' in e for e in data['errors'])
    assert any('global_network' in e for e in data['errors'])
    assert any('decision_optimizer' in e for e in data['errors'])


def test_route_client(monkeypatch):
    # ensure route returns same structure as method
    mm = MatrixMaximizer()
    client = mm.app.test_client()
    resp = client.get('/api/matrix-monitor')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'project_selector' in data
    assert 'errors' in data


def test_cache_behavior(monkeypatch):
    mm = MatrixMaximizer()
    # first call populates cache
    d1 = mm._collect_matrix_monitor_data()
    # manually adjust timestamp to simulate near future
    mm._matrix_monitor_cache['ts'] = time.time()
    d2 = mm._collect_matrix_monitor_data()
    assert d1 is d2  # cached object returned
