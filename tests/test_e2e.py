"""Testes E2E com Playwright para o fluxo web do xadrez.

Os testes que precisam de camera real sao pulados automaticamente quando
nenhuma camera esta disponivel. Os testes de API funcionam sem camera.
"""
import threading
import time
import urllib.request

import pytest


def _wait_for_server(port, timeout=5):
    """Aguarda o servidor Flask ficar disponivel."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=1)
            return True
        except Exception:
            time.sleep(0.1)
    return False


def _find_free_port():
    """Encontra uma porta livre."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _reset_app_state():
    """Reseta variaveis globais do app para estado inicial."""
    import web.app as web_app
    web_app._detector = None
    web_app._stream_running = False
    web_app._track_running = False
    web_app._calibrando = False
    web_app._mouse_points = []
    web_app._referencia_salva = False
    web_app._historico = []
    web_app._calibrated_points = None
    web_app._frame = None
    web_app._mask_frame = None
    # Reseta jogo e voz
    from xadrez_sem_barreiras.xadrez import JogoXadrez
    from xadrez_sem_barreiras.voz import LeitorVoz
    web_app._jogo = JogoXadrez(fonetica=False)
    web_app._voz = LeitorVoz(ativo=True, velocidade=1.0)


@pytest.fixture
def flask_server():
    """Inicia o servidor Flask em uma thread com porta livre."""
    from web.app import app, socketio

    port = _find_free_port()
    app.config["TESTING"] = True
    _reset_app_state()

    def run_server():
        socketio.run(app, host="127.0.0.1", port=port, debug=False, allow_unsafe_werkzeug=True)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    _wait_for_server(port)
    yield port


@pytest.fixture
def page(flask_server):
    """Cria navegador headless para cada teste."""
    from playwright.sync_api import sync_playwright
    port = flask_server
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        pg = context.new_page()
        yield pg, port
        browser.close()


def _has_camera(page):
    """Verifica se ha camera real disponivel."""
    pg, _ = page
    result = pg.evaluate("""() =>
        fetch('/api/cameras').then(r => r.json())""")
    return len(result.get("cameras", [])) > 0


def _select_first_camera(page):
    """Seleciona a primeira camera disponivel e aguarda feed."""
    pg, _ = page
    pg.wait_for_selector("#cameraSelect")
    select = pg.locator("#cameraSelect")
    select.select_option(index=0)
    pg.locator("#btnSelectCamera").click()
    pg.wait_for_selector("#phaseFeed", state="visible", timeout=5000)


class TestSelecionarCamera:
    def test_camera_list_aparece(self, page):
        pg, port = page
        pg.goto(f"http://127.0.0.1:{port}")
        pg.wait_for_selector("#cameraSelect")
        options = pg.locator("#cameraSelect").locator("option")
        assert options.count() >= 1

    def test_selecionar_camera_muda_fase(self, page):
        pg, port = page
        pg.goto(f"http://127.0.0.1:{port}")
        if not _has_camera(page):
            pytest.skip("Nenhuma camera disponivel no sistema")

        _select_first_camera(page)

        assert pg.locator("#phaseSelect").is_visible() is False
        feed = pg.locator("#videoFeed")
        src = feed.get_attribute("src")
        assert "/video_feed" in src

    def test_botao_calibrar_visivel(self, page):
        pg, port = page
        pg.goto(f"http://127.0.0.1:{port}")
        if not _has_camera(page):
            pytest.skip("Nenhuma camera disponivel no sistema")

        _select_first_camera(page)
        pg.wait_for_selector("#controlsPreCal", state="visible", timeout=5000)

        assert pg.locator("#btnCalibrate").is_visible()
        assert pg.locator("#controlsCalibrating").is_hidden()
        assert pg.locator("#controlsPostCal").is_hidden()
        assert pg.locator("#controlsTracking").is_hidden()


class TestCalibrarManual:
    def test_abrir_modal_calibracao(self, page):
        pg, port = page
        pg.goto(f"http://127.0.0.1:{port}")
        if not _has_camera(page):
            pytest.skip("Nenhuma camera disponivel no sistema")

        _select_first_camera(page)
        pg.wait_for_selector("#btnCalibrate", state="visible", timeout=5000)

        pg.locator("#btnCalibrate").click()
        pg.wait_for_selector("#calibrationModal", state="visible", timeout=3000)

    def test_calibracao_manual_4_cliques(self, page):
        pg, port = page
        pg.goto(f"http://127.0.0.1:{port}")
        if not _has_camera(page):
            pytest.skip("Nenhuma camera disponivel no sistema")

        _select_first_camera(page)
        pg.wait_for_selector("#btnCalibrate", state="visible", timeout=5000)

        pg.locator("#btnCalibrate").click()
        pg.wait_for_selector("#calibrationModal", state="visible", timeout=3000)
        pg.locator("#btnManual").click()

        pg.wait_for_selector("#controlsCalibrating", state="visible", timeout=3000)
        assert pg.locator("#btnUndoPoint").is_visible()
        assert pg.locator("#btnResetCalibration").is_visible()

        wrapper = pg.locator("#videoWrapper")
        clicks = [(50, 50), (590, 50), (590, 450), (50, 450)]
        for x, y in clicks:
            wrapper.click(position={"x": x, "y": y})
            time.sleep(0.2)

        pg.wait_for_selector("#controlsPostCal", state="visible", timeout=5000)
        assert pg.locator("#btnSaveRef").is_visible()
        assert pg.locator("#btnCalibrateAgain").is_visible()

        status = pg.evaluate("() => fetch('/api/status').then(r => r.json())")
        assert status.get("calibrated") is True

    def test_calibracao_desfazer_ponto(self, page):
        pg, port = page
        pg.goto(f"http://127.0.0.1:{port}")
        if not _has_camera(page):
            pytest.skip("Nenhuma camera disponivel no sistema")

        _select_first_camera(page)
        pg.wait_for_selector("#btnCalibrate", state="visible", timeout=5000)

        pg.locator("#btnCalibrate").click()
        pg.locator("#btnManual").click()
        pg.wait_for_selector("#controlsCalibrating", state="visible", timeout=3000)

        wrapper = pg.locator("#videoWrapper")
        wrapper.click(position={"x": 50, "y": 50})
        time.sleep(0.1)
        wrapper.click(position={"x": 590, "y": 50})
        time.sleep(0.1)

        info = pg.locator("#calibrationStepInfo").text_content()
        assert "2" in info

        pg.locator("#btnUndoPoint").click()
        time.sleep(0.2)

        info = pg.locator("#calibrationStepInfo").text_content()
        assert "1" in info

        pg.locator("#btnResetCalibration").click()
        pg.wait_for_selector("#controlsPreCal", state="visible", timeout=3000)


class TestRecalibrar:
    def test_recalibrar_limpa_pontos(self, page):
        """Recalibrar deve voltar a imagem original (sem retificacao)."""
        pg, port = page
        pg.goto(f"http://127.0.0.1:{port}")
        if not _has_camera(page):
            pytest.skip("Nenhuma camera disponivel no sistema")

        _select_first_camera(page)
        pg.wait_for_selector("#btnCalibrate", state="visible", timeout=5000)

        pg.locator("#btnCalibrate").click()
        pg.locator("#btnManual").click()
        pg.wait_for_selector("#controlsCalibrating", state="visible", timeout=3000)

        wrapper = pg.locator("#videoWrapper")
        for x, y in [(50, 50), (590, 50), (590, 450), (50, 450)]:
            wrapper.click(position={"x": x, "y": y})
            time.sleep(0.2)

        pg.wait_for_selector("#controlsPostCal", state="visible", timeout=5000)

        status = pg.evaluate("() => fetch('/api/status').then(r => r.json())")
        assert status.get("calibrated") is True

        pg.locator("#btnCalibrateAgain").click()
        pg.wait_for_selector("#controlsPreCal", state="visible", timeout=3000)

        status = pg.evaluate("() => fetch('/api/status').then(r => r.json())")
        assert status.get("calibrated") is False

    def test_recalibrar_permitir_nova_calibracao(self, page):
        """Apos recalibrar, deve ser possivel calibrar novamente."""
        pg, port = page
        pg.goto(f"http://127.0.0.1:{port}")
        if not _has_camera(page):
            pytest.skip("Nenhuma camera disponivel no sistema")

        _select_first_camera(page)
        pg.wait_for_selector("#btnCalibrate", state="visible", timeout=5000)

        pg.locator("#btnCalibrate").click()
        pg.locator("#btnManual").click()
        pg.wait_for_selector("#controlsCalibrating", state="visible", timeout=3000)

        wrapper = pg.locator("#videoWrapper")
        for x, y in [(50, 50), (590, 50), (590, 450), (50, 450)]:
            wrapper.click(position={"x": x, "y": y})
            time.sleep(0.2)

        pg.wait_for_selector("#controlsPostCal", state="visible", timeout=5000)

        pg.locator("#btnCalibrateAgain").click()
        pg.wait_for_selector("#controlsPreCal", state="visible", timeout=3000)

        pg.locator("#btnCalibrate").click()
        pg.locator("#btnManual").click()
        pg.wait_for_selector("#controlsCalibrating", state="visible", timeout=3000)

        wrapper2 = pg.locator("#videoWrapper")
        for x, y in [(100, 100), (500, 100), (500, 400), (100, 400)]:
            wrapper2.click(position={"x": x, "y": y})
            time.sleep(0.2)

        pg.wait_for_selector("#controlsPostCal", state="visible", timeout=5000)

        status = pg.evaluate("() => fetch('/api/status').then(r => r.json())")
        assert status.get("calibrated") is True


class TestCalibracaoAutomatica:
    def test_auto_sem_texto_na_tela(self, page):
        """Calibracao automatica nao deve mostrar texto overlay."""
        pg, port = page
        pg.goto(f"http://127.0.0.1:{port}")
        if not _has_camera(page):
            pytest.skip("Nenhuma camera disponivel no sistema")

        _select_first_camera(page)
        pg.wait_for_selector("#btnCalibrate", state="visible", timeout=5000)

        pg.locator("#btnCalibrate").click()
        pg.locator("#btnAuto").click()

        pg.wait_for_selector("#controlsCalibrating", state="visible", timeout=3000)

        overlay = pg.locator("#overlayContent")
        hidden = overlay.is_hidden() or overlay.evaluate("el => el.style.display === 'none'")
        assert hidden


class TestAPIIntegration:
    """Testes de integracao via browser que nao dependem de camera real."""

    def test_selecionar_camera_retorna_ok(self, page):
        pg, port = page
        pg.goto(f"http://127.0.0.1:{port}")
        resp = pg.evaluate("""() =>
            fetch('/api/select_camera', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({index: 0})
            }).then(r => r.json())""")
        assert "ok" in resp

    def test_calibracao_manual_click_api(self, page):
        """API manual_click deve aceitar 4 pontos e calibrar."""
        pg, port = page
        pg.goto(f"http://127.0.0.1:{port}")
        for i in range(4):
            resp = pg.evaluate(f"""() =>
                fetch('/api/calibration/manual_click', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{x: {50 + i*100}, y: {50 + i*100}}})
                }}).then(r => r.json())""")
            assert resp.get("ok") is True

        status = pg.evaluate("() => fetch('/api/status').then(r => r.json())")
        assert status.get("calibrated") is True

    def test_recalibrar_limpa_via_api(self, page):
        """API reset_points deve limpar calibracao."""
        pg, port = page
        pg.goto(f"http://127.0.0.1:{port}")

        for i in range(4):
            pg.evaluate(f"""() =>
                fetch('/api/calibration/manual_click', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{x: {50 + i*100}, y: {50 + i*100}}})
                }}).then(r => r.json())""")

        status = pg.evaluate("() => fetch('/api/status').then(r => r.json())")
        assert status.get("calibrated") is True

        resp = pg.evaluate("""() =>
            fetch('/api/calibration/reset_points', {
                method: 'POST'
            }).then(r => r.json())""")
        assert resp.get("ok") is True

        status = pg.evaluate("() => fetch('/api/status').then(r => r.json())")
        assert status.get("calibrated") is False

    def test_voice_config_api(self, page):
        """API voice/config deve aceitar configuracoes."""
        pg, port = page
        pg.goto(f"http://127.0.0.1:{port}")

        resp = pg.evaluate("""() =>
            fetch('/api/voice/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ativo: true, fonetica: true, velocidade: 2.5})
            }).then(r => r.json())""")
        assert resp.get("ok") is True

        status = pg.evaluate("() => fetch('/api/status').then(r => r.json())")
        assert status.get("voice_fonetica") is True
        assert abs(status.get("voice_speed", 0) - 2.5) < 0.01

    def test_undo_reset_api(self, page):
        """API undo e reset devem funcionar."""
        pg, port = page
        pg.goto(f"http://127.0.0.1:{port}")

        resp = pg.evaluate("""() =>
            fetch('/api/undo', {method: 'POST'}).then(r => r.json())""")
        assert resp.get("ok") is False

        resp = pg.evaluate("""() =>
            fetch('/api/reset', {method: 'POST'}).then(r => r.json())""")
        assert resp.get("ok") is True

        board = pg.evaluate("() => fetch('/api/board').then(r => r.json())")
        assert "rnbqkbnr" in board.get("fen", "")
