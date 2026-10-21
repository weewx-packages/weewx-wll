# Copyright 2026 weewx-packages
# Distributed under the terms of the GNU Public License (GPLv3)
import importlib.util
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import threading
from unittest.mock import Mock

import pytest
import requests


def load():
    spec = importlib.util.spec_from_file_location('wll', Path(__file__).parents[1] / 'bin/user/wll.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_import_is_passive(caplog):
    load()
    assert 'hostname or ip address' not in caplog.text


def test_host_required():
    with pytest.raises(ValueError, match='hostname'):
        load().WLL()


def packet(conditions, **options):
    module = load()
    driver = module.WLL(host='localhost', **options)
    module.requests.get = Mock(return_value=Mock(json=lambda: {'data': {'ts': 1234, 'conditions': conditions}}))
    result = next(driver.genLoopPackets())
    module.requests.get.assert_called_once_with(driver.service_url, timeout=5.0)
    return result


def test_separate_transmitters_preserve_zero_and_ignore_null():
    result = packet([
        {'data_structure_type': 1, 'txid': 1, 'temp': 0, 'hum': 50, 'wind_speed_last': None},
        {'data_structure_type': 1, 'txid': 2, 'temp': None, 'hum': None, 'wind_speed_last': 0},
    ])
    assert result['outTemp'] == 0
    assert result['outHumidity'] == 50
    assert result['windSpeed'] == 0


def test_selected_transmitters():
    result = packet([
        {'data_structure_type': 1, 'txid': 1, 'temp': 41, 'wind_speed_last': 99},
        {'data_structure_type': 1, 'txid': 2, 'temp': 99, 'wind_speed_last': 3},
    ], iss_id=1, wind_id=2)
    assert result['outTemp'] == 41
    assert result['windSpeed'] == 3


@pytest.mark.parametrize('size,inches', [(1, .01), (2, .2 / 25.4), (3, .1 / 25.4), (4, .001)])
def test_daily_rain_units(size, inches):
    result = packet([{'data_structure_type': 1, 'rain_size': size, 'rainfall_daily': 10}])
    assert result['dayRain'] == pytest.approx(10 * inches, rel=1e-5)


def test_pressure_and_soil_mapping():
    result = packet([
        {'data_structure_type': 3, 'bar_absolute': 29, 'bar_sea_level': 30},
        {'data_structure_type': 2, 'moist_soil_2': 20, 'moist_soil_3': 30},
    ])
    assert result['altimeter'] == 30
    assert result['pressure'] == 29
    assert 'barometer' not in result
    assert result['soilMoist2'] == 20
    assert result['soilMoist3'] == 30


def test_real_http_and_timeout(monkeypatch):
    module = load()
    # Other tests replace this shared module attribute.
    monkeypatch.setattr(module.requests, 'get', requests.api.get)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({'data': {'ts': 1234, 'conditions': []}}).encode())
        def log_message(self, *args):
            pass
    server = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        driver = module.WLL(host='127.0.0.1')
        driver.service_url = 'http://127.0.0.1:%d/v1/current_conditions' % server.server_port
        assert next(driver.genLoopPackets())['dateTime'] == 1234
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
    monkeypatch.setattr(module.requests, 'get', Mock(side_effect=requests.Timeout('blocked')))
    monkeypatch.setattr(module.time, 'sleep', Mock(side_effect=RuntimeError('retry wait')))
    with pytest.raises(RuntimeError, match='retry wait'):
        next(driver.genLoopPackets())
    module.requests.get.assert_called_once_with(driver.service_url, timeout=5.0)
