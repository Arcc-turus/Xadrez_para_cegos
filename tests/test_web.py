"""Tests para o servidor web (routes, API, tracking)."""
import json
import threading
import time
import os
import sys
import tempfile

import numpy as np
import pytest

# Garante que o projeto esteja no path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from web.app import app, socketio


@pytest.fixture
def client():
    """Client Flask para testes HTTP."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def socket_client():
    """Client SocketIO para testes em tempo real."""
    app.config["TESTING"] = True
    sc = socketio.test_client(app)
    yield sc
    sc.disconnect()


class TestIndexRoute:
    def test_index_returns_html(self, client):
        res = client.get("/")
        assert res.status_code == 200
        html = res.data.decode()
        assert "Xadrez Sem Barreiras" in html
        assert "cameraSelect" in html
        assert "btnCalibrate" in html
        assert "videoFeed" in html

    def test_static_css_exists(self, client):
        res = client.get("/static/css/style.css")
        assert res.status_code == 200

    def test_static_js_exists(self, client):
        res = client.get("/static/js/main.js")
        assert res.status_code == 200


class TestCamerasAPI:
    def test_list_cameras_returns_array(self, client):
        res = client.get("/api/cameras")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "cameras" in data
        assert isinstance(data["cameras"], list)

    def test_camera_items_have_index(self, client):
        res = client.get("/api/cameras")
        data = json.loads(res.data)
        for cam in data["cameras"]:
            assert "index" in cam


class TestSelectCameraAPI:
    def test_select_camera_invalid(self, client):
        res = client.post("/api/select_camera",
                          json={"index": 999})
        # Pode falhar ou nao dependendo da camera
        assert res.status_code == 200

    def test_select_camera_returns_ok(self, client):
        res = client.post("/api/select_camera",
                          json={"index": 0})
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "ok" in data


class TestCalibrationAPI:
    def test_start_calibration(self, client):
        res = client.post("/api/calibration/start",
                          json={"modo": "manual"})
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["ok"] is True

    def test_start_calibration_auto(self, client):
        res = client.post("/api/calibration/start",
                          json={"modo": "auto"})
        assert res.status_code == 200

    def test_manual_click(self, client):
        res = client.post("/api/calibration/manual_click",
                          json={"x": 100, "y": 200})
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["ok"] is True

    def test_cancel_calibration(self, client):
        res = client.post("/api/calibration/cancel")
        assert res.status_code == 200


class TestTrackingAPI:
    def test_start_tracking(self, client):
        res = client.post("/api/tracking/start")
        assert res.status_code == 200

    def test_stop_tracking(self, client):
        res = client.post("/api/tracking/stop")
        assert res.status_code == 200


class TestGameAPI:
    def test_undo_no_moves(self, client):
        res = client.post("/api/undo")
        data = json.loads(res.data)
        # Sem lances, deve falhar
        assert data["ok"] is False or "lance" in data

    def test_reset_game(self, client):
        res = client.post("/api/reset")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["ok"] is True

    def test_save_reference(self, client):
        res = client.post("/api/save_reference")
        assert res.status_code == 200


class TestStatusAPI:
    def test_status_returns_fields(self, client):
        res = client.get("/api/status")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "camera_active" in data
        assert "calibrated" in data
        assert "tracking" in data
        assert "voice_speed" in data
        assert "voice_fonetica" in data

    def test_board_returns_fen(self, client):
        res = client.get("/api/board")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "fen" in data
        assert "turn" in data
        assert "board" in data


class TestVideoFeed:
    def test_video_feed_exists(self, client):
        res = client.get("/video_feed")
        # O stream pode retornar vazio se nao houver camera
        assert res.status_code == 200
        content_type = res.content_type
        assert "multipart" in content_type or content_type == ""


class TestSocketIO:
    def test_connect(self, socket_client):
        assert socket_client.is_connected()

    def test_calibration_emit(self, socket_client):
        with app.test_client() as client:
            client.post("/api/calibration/start",
                        json={"modo": "manual"})
            received = socket_client.get_received()
            assert any(r.get("name") == "calibration_status" for r in received)


class TestChessLogic:
    def test_fen_inicial(self, client):
        res = client.get("/api/board")
        data = json.loads(res.data)
        assert data["fen"] == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    def test_undo_after_move(self, client):
        # Simula um lance via API de undo (requer estado previo)
        res = client.post("/api/undo")
        data = json.loads(res.data)
        assert "ok" in data
