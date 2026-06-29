import cv2
import numpy as np
import pytest

from xadrez_sem_barreiras.segmentador import SegmentadorTabuleiro


def _criar_tabuleiro_sintetico(peca_casas=None, tamanho=800):
    """Cria um tabuleiro sintético 8x8 com peças opcionais.

    peca_casas: dict {(linha, coluna): cor_bgr}
    Ex: {(1, 4): (240, 240, 240)} -> peca branca em e2
    """
    img = np.zeros((tamanho, tamanho, 3), dtype=np.uint8)
    casa = tamanho // 8
    for row in range(8):
        for col in range(8):
            cor = (200, 200, 200) if (row + col) % 2 == 0 else (100, 100, 100)
            img[row*casa:(row+1)*casa, col*casa:(col+1)*casa] = cor

    if peca_casas:
        for (row, col), cor in peca_casas.items():
            cx = col * casa + casa // 2
            cy = row * casa + casa // 2
            cv2.circle(img, (cx, cy), casa // 3, cor, -1)

    return img


class TestFatiarTabuleiro:
    def test_retorna_matriz_8x8(self):
        seg = SegmentadorTabuleiro()
        img = _criar_tabuleiro_sintetico()
        casas = seg.fatiar_tabuleiro(img)
        assert len(casas) == 8
        assert all(len(linha) == 8 for linha in casas)

    def test_cada_casa_tem_tamanho_correto(self):
        seg = SegmentadorTabuleiro(tamanho_tabuleiro=800)
        img = _criar_tabuleiro_sintetico()
        casas = seg.fatiar_tabuleiro(img)
        esperado = 100
        for row in range(8):
            for col in range(8):
                h, w = casas[row][col].shape[:2]
                assert h == esperado
                assert w == esperado

    def test_casas_preservam_cores_diferentes(self):
        seg = SegmentadorTabuleiro()
        img = _criar_tabuleiro_sintetico()
        casas = seg.fatiar_tabuleiro(img)
        # a1 (0,0) é casa clara, a2 (1,0) é casa escura
        media_clara = casas[0][0].mean()
        media_escura = casas[1][0].mean()
        assert media_clara > media_escura


class TestDetectarMudancas:
    def test_sem_mudanca_retorna_vazio(self):
        seg = SegmentadorTabuleiro()
        img = _criar_tabuleiro_sintetico()
        casas = seg.fatiar_tabuleiro(img)
        mudancas, mapa = seg.detectar_mudancas(casas, casas)
        assert mudancas == []
        assert mapa.shape == (800, 800)

    def test_detecta_lance_normal_duas_casas(self):
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico(peca_casas={(1, 4): (240, 240, 240)})
        curr = _criar_tabuleiro_sintetico(peca_casas={(3, 4): (240, 240, 240)})
        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, mapa = seg.detectar_mudancas(casas_ref, casas_curr)
        assert len(mudancas) == 2
        assert (1, 4) in mudancas
        assert (3, 4) in mudancas

    def test_detecta_captura(self):
        seg = SegmentadorTabuleiro()
        # Peão branco em e4 (3,4) captura preto em d5 (4,3)
        ref = _criar_tabuleiro_sintetico(peca_casas={
            (3, 4): (240, 240, 240),
            (4, 3): (80, 80, 80),
        })
        curr = _criar_tabuleiro_sintetico(peca_casas={
            (4, 3): (240, 240, 240),
        })
        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, mapa = seg.detectar_mudancas(casas_ref, casas_curr)
        assert len(mudancas) == 2
        assert (3, 4) in mudancas
        assert (4, 3) in mudancas

    def test_detecta_roque_quatro_casas(self):
        seg = SegmentadorTabuleiro()
        # Roque pequeno branco: rei e1->g1, torre h1->f1
        ref = _criar_tabuleiro_sintetico(peca_casas={
            (0, 4): (240, 240, 240),
            (0, 7): (240, 240, 240),
        })
        curr = _criar_tabuleiro_sintetico(peca_casas={
            (0, 6): (240, 240, 240),
            (0, 5): (240, 240, 240),
        })
        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, mapa = seg.detectar_mudancas(casas_ref, casas_curr)
        assert len(mudancas) == 4
        assert set(mudancas) == {(0, 4), (0, 7), (0, 6), (0, 5)}

    def test_detecta_en_passant_tres_casas(self):
        seg = SegmentadorTabuleiro()
        # En passant branco: peão e4 (3,4) captura f5 (4,5), vai para f6 (3,5)
        # O peão estava em (3,4) e foi para (3,5). O peão preto estava em (4,5).
        # As casas alteradas: origem (3,4), destino (3,5), capturado (4,5)
        # Colunas diferentes (4 e 5) para evitar o filtro de artefatos
        ref = _criar_tabuleiro_sintetico(peca_casas={
            (3, 4): (240, 240, 240),
            (4, 5): (80, 80, 80),
        })
        curr = _criar_tabuleiro_sintetico(peca_casas={
            (3, 5): (240, 240, 240),
        })
        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, mapa = seg.detectar_mudancas(casas_ref, casas_curr)
        assert len(mudancas) == 3
        assert (3, 4) in mudancas
        assert (4, 5) in mudancas
        assert (3, 5) in mudancas

    def test_peca_mesma_posicao_nao_detecta(self):
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico(peca_casas={(1, 4): (240, 240, 240)})
        curr = _criar_tabuleiro_sintetico(peca_casas={(1, 4): (240, 240, 240)})
        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, mapa = seg.detectar_mudancas(casas_ref, casas_curr)
        assert mudancas == []

    def test_mapa_visual_tem_dimensao_correta(self):
        seg = SegmentadorTabuleiro()
        img = _criar_tabuleiro_sintetico()
        casas = seg.fatiar_tabuleiro(img)
        _, mapa = seg.detectar_mudancas(casas, casas)
        assert mapa.shape == (800, 800)
        assert mapa.dtype == np.uint8


class TestRuidoILuminacao:
    def test_pequena_variacao_luz_nao_dispara(self):
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico()
        curr = _criar_tabuleiro_sintetico().astype(np.int16)
        curr = np.clip(curr + 5, 0, 255).astype(np.uint8)
        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, _ = seg.detectar_mudancas(casas_ref, casas_curr)
        assert mudancas == []

    def test_peca_pequena_nao_dispara_falso(self):
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico()
        curr = _criar_tabuleiro_sintetico()
        # Dot minúsculo (raio 2) no centro da ROI para testar sensibilidade
        cv2.circle(curr, (50, 65), 2, (255, 255, 255), -1)
        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, _ = seg.detectar_mudancas(casas_ref, casas_curr)
        assert mudancas == []

    def test_artefato_cabeca_peca_filtrado(self):
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico()
        curr = _criar_tabuleiro_sintetico()
        casa = 100
        peca_grande_cor = (240, 240, 240)
        # Peça em (3,4) com cabeça invadindo (2,4)
        cv2.circle(curr, (450, 380), 45, peca_grande_cor, -1)
        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, _ = seg.detectar_mudancas(casas_ref, casas_curr)
        # A mudança principal é (3,4), o artefato (2,4) deve ser filtrado
        linhas_3 = [m for m in mudancas if m[0] == 3 and m[1] == 4]
        assert len(linhas_3) == 1


class TestDeteccaoRobustaTabuleiroCompleto:
    def _deslocar(self, img, dx, dy):
        matriz = np.float32([[1, 0, dx], [0, 1, dy]])
        return cv2.warpAffine(
            img,
            matriz,
            (img.shape[1], img.shape[0]),
            borderMode=cv2.BORDER_REPLICATE,
        )

    def test_deslocamento_global_do_tabuleiro_nao_dispara_lance(self):
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico(peca_casas={
            (1, 4): (240, 240, 240),
            (6, 4): (80, 80, 80),
            (0, 1): (80, 80, 80),
        })
        curr = self._deslocar(ref, 3, -2)

        mudancas, _ = seg.detectar_mudancas_tabuleiro(ref, curr)

        assert mudancas == []
        assert seg.ultimo_diagnostico.alinhamento_ok is True

    def test_lance_com_pequena_tremida_continua_detectando(self):
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico(peca_casas={(1, 4): (240, 240, 240)})
        curr = _criar_tabuleiro_sintetico(peca_casas={(3, 4): (240, 240, 240)})
        curr = self._deslocar(curr, 3, -2)

        mudancas, _ = seg.detectar_mudancas_tabuleiro(ref, curr)

        assert set(mudancas) == {(1, 4), (3, 4)}
