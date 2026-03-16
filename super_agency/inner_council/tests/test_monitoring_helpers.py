import pytest

from inner_council.agents.base_agent import MessageBus

try:
    from global_intelligence_network import GlobalIntelligenceNetwork
    _HAS_GIN = True
except ModuleNotFoundError:
    _HAS_GIN = False


def test_message_bus_status():
    bus = MessageBus()
    # initially not running and no agents
    status = bus.get_status()
    assert status["running"] is False
    assert status["registered_agents"] == []
    assert status["queue_size"] == 0

    # register a dummy agent
    class Dummy:
        def __init__(self):
            self.agent_id = "dummy"
            self.name = "DummyAgent"
    dummy = Dummy()
    bus.register_agent(dummy)
    status = bus.get_status()
    assert "dummy" in status["registered_agents"]

    # check running flag toggles
    bus.start()
    status = bus.get_status()
    assert status["running"] is True
    bus.stop()
    assert bus.get_status()["running"] is False


def test_matrix_monitor_chat_flag(monkeypatch):
    # create dummy deployment with minimal interface
    class DummyDep:
        def get_system_status(self):
            return {}
    from matrix_monitor import MatrixMonitor
    mm = MatrixMonitor(DummyDep())
    # chat_available attribute exists and is boolean
    assert hasattr(mm, 'chat_available')
    assert isinstance(mm.chat_available, bool)


@pytest.mark.skipif(not _HAS_GIN,
                    reason="global_intelligence_network archived")
def test_global_network_list_nodes():
    gin = GlobalIntelligenceNetwork({})
    nodes = gin.list_nodes()
    assert isinstance(nodes, list)
    assert len(nodes) == len(gin.nodes)
    for node_id in nodes:
        assert node_id in gin.nodes
