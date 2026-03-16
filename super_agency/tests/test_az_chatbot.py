import pytest

import importlib


def test_azure_chatbot_import():
    """AzureChatbot class should be importable even if sdk missing"""
    try:
        module = importlib.import_module('az_chatbot')
    except ImportError:
        # skip removed; CI should install az_chatbot or stub
        pytest.fail('az_chatbot module not available')

    assert hasattr(module, 'AzureChatbot')


def test_azure_chatbot_instantiation(monkeypatch):
    """Instantiate stub chatbot when SDK not installed or with dummy config"""
    module = importlib.import_module('az_chatbot')
    cls = getattr(module, 'AzureChatbot')

    if not getattr(module, 'AZURE_AVAILABLE', False):
        with pytest.raises(ImportError):
            cls()
    else:
        # if SDK present, try creating with invalid endpoint to provoke ValueError
        with pytest.raises(ValueError):
            cls(endpoint=None)
