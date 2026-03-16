"""
Pytest test suite for matrix_monitor_v4.py
Tests Flask routes, API endpoints, helper functions, and background caches.
"""

import json
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def app():
    """Create a Flask test app from matrix_monitor_v4."""
    import matrix_monitor_v4 as mm

    mm.app.config['TESTING'] = True
    # Reset shared state so tests don't bleed into each other
    mm.cpu_history.clear()
    mm.ram_history.clear()
    mm.activity_log.clear()
    yield mm.app


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def mm():
    """Direct access to the matrix_monitor_v4 module."""
    import matrix_monitor_v4
    return matrix_monitor_v4


# ---------------------------------------------------------------------------
# Health & Template Routes
# ---------------------------------------------------------------------------

class TestHealthRoute:
    def test_health_returns_200(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200

    def test_health_json_structure(self, client):
        data = client.get('/api/health').get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'matrix_monitor_v4'
        assert data['version'] == '4.0.0'
        assert 'timestamp' in data


class TestDashboardRoutes:
    """All three dashboard routes should return the HTML template."""

    @pytest.mark.parametrize('path', ['/', '/pulsar', '/titan'])
    def test_returns_200_html(self, client, path):
        resp = client.get(path)
        assert resp.status_code == 200
        assert b'MATRIX MONITOR' in resp.data


# ---------------------------------------------------------------------------
# /api/v4/status
# ---------------------------------------------------------------------------

class TestStatusEndpoint:
    @patch('matrix_monitor_v4.psutil')
    def test_status_returns_expected_keys(self, mock_psutil, client, mm):
        """The status payload must contain every key the frontend expects."""
        mock_psutil.cpu_percent.return_value = 42.0
        mock_mem = MagicMock()
        mock_mem.percent = 55.0
        mock_mem.total = 16 * 1024 ** 3
        mock_psutil.virtual_memory.return_value = mock_mem
        mock_psutil.cpu_count.return_value = 8
        mock_psutil.boot_time.return_value = datetime.now().timestamp() - 3600

        resp = client.get('/api/v4/status')
        assert resp.status_code == 200
        data = resp.get_json()

        required_keys = [
            'cpu', 'ram', 'qforge', 'qusar', 'matrix_monitor',
            'repo_depot', 'agent_activity', 'repos', 'activity_log',
            'system', 'device_sync', 'watchdog', 'timestamp',
            'cpu_history', 'ram_history',
        ]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"

    @patch('matrix_monitor_v4.psutil')
    def test_cpu_ram_are_numbers(self, mock_psutil, client, mm):
        mock_psutil.cpu_percent.return_value = 12.5
        mock_mem = MagicMock()
        mock_mem.percent = 40.0
        mock_mem.total = 8 * 1024 ** 3
        mock_psutil.virtual_memory.return_value = mock_mem
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.boot_time.return_value = datetime.now().timestamp() - 600

        data = client.get('/api/v4/status').get_json()
        assert isinstance(data['cpu'], (int, float))
        assert isinstance(data['ram'], (int, float))


# ---------------------------------------------------------------------------
# /api/v4/devices
# ---------------------------------------------------------------------------

class TestDevicesEndpoint:
    def test_devices_returns_200(self, client):
        resp = client.get('/api/v4/devices')
        assert resp.status_code == 200

    def test_devices_has_device_sync(self, client):
        data = client.get('/api/v4/devices').get_json()
        assert 'device_sync' in data
        ds = data['device_sync']
        assert 'pulsar' in ds
        assert 'titan' in ds


# ---------------------------------------------------------------------------
# /api/v4/devices/sync  (POST)
# ---------------------------------------------------------------------------

class TestDeviceSyncPost:
    def test_sync_invalid_device(self, client):
        resp = client.post(
            '/api/v4/devices/sync',
            data=json.dumps({'device': 'unknown'}),
            content_type='application/json',
        )
        assert resp.status_code == 400
        assert resp.get_json()['success'] is False

    def test_sync_missing_body(self, client):
        resp = client.post('/api/v4/devices/sync',
                           content_type='application/json')
        assert resp.status_code == 400

    def test_sync_pulsar_success(self, client, tmp_path, monkeypatch):
        """Sync a pulsar device — should write a file and return success."""
        monkeypatch.chdir(tmp_path)

        resp = client.post(
            '/api/v4/devices/sync',
            data=json.dumps({'device': 'pulsar', 'sync_type': 'auto'}),
            content_type='application/json',
        )

        assert resp.status_code == 200
        assert resp.get_json()['success'] is True
        # Verify file was actually written
        assert (tmp_path / 'data' / 'device_sync_status.json').exists()


# ---------------------------------------------------------------------------
# /docs
# ---------------------------------------------------------------------------

class TestDocsEndpoint:
    def test_docs_returns_200(self, client):
        resp = client.get('/docs')
        assert resp.status_code == 200

    def test_docs_lists_endpoints(self, client):
        data = client.get('/docs').get_json()
        assert 'endpoints' in data
        endpoints = data['endpoints']
        assert '/api/v4/status' in endpoints
        assert '/api/v4/devices' in endpoints
        assert '/pulsar' in endpoints
        assert '/titan' in endpoints

    def test_docs_lists_devices(self, client):
        data = client.get('/docs').get_json()
        assert 'devices' in data
        assert 'pulsar' in data['devices']
        assert 'titan' in data['devices']


# ---------------------------------------------------------------------------
# Helper Functions (unit-level)
# ---------------------------------------------------------------------------

class TestHelperFunctions:
    def test_get_agent_status_shape(self, mm):
        status = mm.get_agent_status()
        assert 'qforge' in status
        assert 'qusar' in status
        assert 'matrix_monitor' in status
        assert status['matrix_monitor'] == 'ACTIVE'

    def test_get_device_sync_status_shape(self, mm):
        ds = mm.get_device_sync_status()
        assert 'pulsar' in ds
        assert 'titan' in ds
        for device in ('pulsar', 'titan'):
            assert 'reachable' in ds[device]
            assert 'status' in ds[device]

    def test_get_agent_activity_shape(self, mm):
        activity = mm.get_agent_activity()
        assert isinstance(activity, dict)
        assert 'optimus' in activity
        assert 'gasket' in activity

    def test_log_activity_adds_entry(self, mm):
        mm.activity_log.clear()
        mm.log_activity('test', 'hello world', 'info')
        assert len(mm.activity_log) == 1
        entry = mm.activity_log[0]
        assert entry['category'] == 'test'
        assert entry['message'] == 'hello world'
        assert entry['level'] == 'info'

    def test_log_activity_caps_at_100(self, mm):
        mm.activity_log.clear()
        for i in range(120):
            mm.log_activity('test', f'msg {i}', 'info')
        assert len(mm.activity_log) <= 100


# ---------------------------------------------------------------------------
# Control Endpoints (smoke tests)
# ---------------------------------------------------------------------------

class TestControlEndpoints:
    @patch('matrix_monitor_v4.subprocess.Popen')
    def test_start_depot(self, mock_popen, client):
        resp = client.post('/api/v4/control/start-depot')
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    @patch('matrix_monitor_v4.psutil.process_iter', return_value=[])
    def test_stop_depot_not_found(self, mock_iter, client):
        resp = client.post('/api/v4/control/stop-depot')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is False
        assert 'not found' in data['message'].lower()
