import cv2
import numpy as np
import pytest

from xadrez_sem_barreiras.segmentador import SegmentadorTabuleiro


def _criar_tabuleiro_sintetico(peca_casas=None, tamanho=800):
    """Cria um tabuleiro sintético 8x8 com peças opcionais."""
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


def _desenhar_peca(img, linha, col, tamanho, cor, raio=None, offset_x=0, offset_y=0):
    """Desenha uma peça em uma casa específica."""
    casa = tamanho // 8
    cx = col * casa + casa // 2 + offset_x
    cy = linha * casa + casa // 2 + offset_y
    r = raio if raio is not None else casa // 3
    cv2.circle(img, (cx, cy), r, cor, -1)


def _aplicar_perspectiva(img, pontos_origem, pontos_destino, tamanho_saida=None):
    """Aplica transformação de perspectiva (homografia) na imagem."""
    if tamanho_saida is None:
        tamanho_saida = img.shape[:2][::-1]

    M = cv2.getPerspectiveTransform(
        np.float32(pontos_origem),
        np.float32(pontos_destino)
    )
    result = cv2.warpPerspective(img, M, tamanho_saida)
    return result


def _criar_sombra_peca(img, px, py, comprimento, angulo_graus, cor=(40, 40, 40), espessura=8):
    """Desenha uma sombra projetada por uma peça."""
    rad = np.radians(angulo_graus)
    dx = int(comprimento * np.cos(rad))
    dy = int(comprimento * np.sin(rad))
    pts = [(px, py), (px + dx, py + dy)]
    cv2.line(img, pts[0], pts[1], cor, espessura)


class TestPerspectivaCamera:
    """Testa detecção quando o tabuleiro está em ângulo (perspectiva)."""

    def test_pequeno_angulo_lance_normal(self):
        """Lance normal com tabuleiro levemente inclinado."""
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico(peca_casas={(3, 4): (240, 240, 240)})
        curr = _criar_tabuleiro_sintetico(peca_casas={(4, 4): (240, 240, 240)})

        # Simula ângulo leve: tabuleiro mais largo embaixo
        src = [(0, 0), (800, 0), (800, 800), (0, 800)]
        dst = [(40, 0), (760, 0), (800, 800), (0, 800)]
        ref = _aplicar_perspectiva(ref, src, dst, (800, 800))
        curr = _aplicar_perspectiva(curr, src, dst, (800, 800))

        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, _ = seg.detectar_mudancas(casas_ref, casas_curr)

        # Deve detectar pelo menos as casas envolvidas no lance
        assert len(mudancas) >= 2

    def test_pequeno_angulo_captura(self):
        """Captura com tabuleiro em perspectiva."""
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico(peca_casas={
            (3, 4): (240, 240, 240),
            (4, 3): (80, 80, 80),
        })
        curr = _criar_tabuleiro_sintetico(peca_casas={
            (4, 3): (240, 240, 240),
        })

        src = [(0, 0), (800, 0), (800, 800), (0, 800)]
        dst = [(40, 0), (760, 0), (800, 800), (0, 800)]
        ref = _aplicar_perspectiva(ref, src, dst, (800, 800))
        curr = _aplicar_perspectiva(curr, src, dst, (800, 800))

        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, _ = seg.detectar_mudancas(casas_ref, casas_curr)
        assert len(mudancas) >= 2

    def test_angulo_moderado_lance_normal(self):
        """Lance com tabuleiro visto de ângulo mais acentuado."""
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico(peca_casas={(1, 4): (240, 240, 240)})
        curr = _criar_tabuleiro_sintetico(peca_casas={(3, 4): (240, 240, 240)})

        # Ângulo mais forte
        src = [(0, 0), (800, 0), (800, 800), (0, 800)]
        dst = [(80, 0), (720, 0), (800, 800), (0, 800)]
        ref = _aplicar_perspectiva(ref, src, dst, (800, 800))
        curr = _aplicar_perspectiva(curr, src, dst, (800, 800))

        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, _ = seg.detectar_mudancas(casas_ref, casas_curr)
        assert len(mudancas) >= 2


class TestPecasSobrepostas:
    """Testa detecção quando peças causam sombras ou oclusão em casas vizinhas."""

    def test_sombra_projeta_vizinho_nao_dispara(self):
        """Sombra de uma peça projeta na casa vizinha sem causar falso positivo."""
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico()
        curr = _criar_tabuleiro_sintetico()

        casa = 100
        # Peça branca em (3,4)
        cx, cy = 450, 350
        _desenhar_peca(curr, 3, 4, 800, (240, 240, 240))
        # Sombra projetando para baixo
        _criar_sombra_peca(curr, cx, cy + 35, 50, 90)

        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, _ = seg.detectar_mudancas(casas_ref, casas_curr)

        # Deve detectar apenas a casa (3,4), não (4,4)
        assert (4, 4) not in mudancas

    def test_pecas_adjacentes_nao_confunde(self):
        """Duas peças em casas adjacentes devem ser distinguidas."""
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico(peca_casas={
            (3, 4): (240, 240, 240),
            (3, 3): (80, 80, 80),
        })
        curr = _criar_tabuleiro_sintetico(peca_casas={
            (3, 3): (240, 240, 240),
            (3, 5): (240, 240, 240),
        })

        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, _ = seg.detectar_mudancas(casas_ref, casas_curr)

        # (3,4) saiu, (3,3) mudou cor, (3,5) apareceu
        assert len(mudancas) >= 2
        assert (3, 4) in mudancas

    def test_pecas_sobrepostas_mesma_casa(self):
        """Duas peças muito próximas na mesma casa devem ser detectadas como 1 mudança."""
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico()
        curr = _criar_tabuleiro_sintetico()

        # Duas peças pequenas na mesma casa (simulando peças empilhadas)
        _desenhar_peca(curr, 3, 4, 800, (240, 240, 240), raio=20, offset_x=-15, offset_y=-10)
        _desenhar_peca(curr, 3, 4, 800, (200, 200, 200), raio=18, offset_x=12, offset_y=8)

        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, _ = seg.detectar_mudancas(casas_ref, casas_curr)

        # Deve detectar apenas 1 casa alterada
        assert len(mudancas) == 1
        assert (3, 4) in mudancas


class TestOclusaoParcial:
    """Testa detecção quando peças estão parcialmente fora da casa."""

    def test_peca_deslocada_borda_superior(self):
        """Peça em (3,4) deslocada para cima, invadindo (2,4)."""
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico()
        curr = _criar_tabuleiro_sintetico()

        # Peça grande deslocada para cima
        _desenhar_peca(curr, 3, 4, 800, (240, 240, 240), raio=40, offset_y=-35)

        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, _ = seg.detectar_mudancas(casas_ref, casas_curr)

        # (3,4) deve ser detectada, (2,4) pode ou não dependendo da invasão
        assert (3, 4) in mudancas

    def test_peca_deslocada_borda_lateral(self):
        """Peça em (3,4) deslocada para direita, invadindo (3,5)."""
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico()
        curr = _criar_tabuleiro_sintetico()

        _desenhar_peca(curr, 3, 4, 800, (240, 240, 240), raio=40, offset_x=30)

        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, _ = seg.detectar_mudancas(casas_ref, casas_curr)

        # (3,4) deve ser detectada
        assert (3, 4) in mudancas

    def test_peca_na_borda_entre_casas(self):
        """Peça posicionada exatamente na linha entre duas casas."""
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico()
        curr = _criar_tabuleiro_sintetico()

        # Peça no centro da borda entre (3,4) e (3,5)
        casa = 100
        cx = 5 * casa  # borda entre col 4 e 5
        cy = 3 * casa + casa // 2
        cv2.circle(curr, (cx, cy), 35, (240, 240, 240), -1)

        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, _ = seg.detectar_mudancas(casas_ref, casas_curr)

        # Pelo menos uma das casas deve ser detectada
        assert len(mudancas) >= 1
        assert (3, 4) in mudancas or (3, 5) in mudancas


class TestCenariosComplexos:
    """Testa combinações de cenários realistas."""

    def test_lance_com_sombra_e_perspectiva(self):
        """Lance normal com tabuleiro em perspectiva e sombra projetada."""
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico(peca_casas={(3, 4): (240, 240, 240)})
        curr = _criar_tabuleiro_sintetico(peca_casas={(4, 4): (240, 240, 240)})

        # Adiciona sombra na imagem atual
        casa = 100
        cx = 450
        cy = 450
        _criar_sombra_peca(curr, cx, cy + 30, 60, 85, espessura=10)

        # Aplica perspectiva
        src = [(0, 0), (800, 0), (800, 800), (0, 800)]
        dst = [(40, 0), (760, 0), (800, 800), (0, 800)]
        ref = _aplicar_perspectiva(ref, src, dst, (800, 800))
        curr = _aplicar_perspectiva(curr, src, dst, (800, 800))

        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, _ = seg.detectar_mudancas(casas_ref, casas_curr)
        assert len(mudancas) >= 2

    def test_multiplas_pecas_deslocadas(self):
        """Várias peças ligeiramente fora do centro."""
        seg = SegmentadorTabuleiro()
        ref = _criar_tabuleiro_sintetico(peca_casas={
            (0, 0): (240, 240, 240),
            (0, 1): (80, 80, 80),
            (1, 4): (240, 240, 240),
        })
        curr = _criar_tabuleiro_sintetico(peca_casas={
            (0, 1): (240, 240, 240),
            (0, 2): (80, 80, 80),
            (3, 4): (240, 240, 240),
        })

        # Desloca peças levemente
        casa = 100
        _desenhar_peca(curr, 0, 1, 800, (240, 240, 240), offset_x=15, offset_y=-10)
        _desenhar_peca(curr, 0, 2, 800, (80, 80, 80), offset_x=-12)
        _desenhar_peca(curr, 3, 4, 800, (240, 240, 240), offset_y=10)

        casas_ref = seg.fatiar_tabuleiro(ref)
        casas_curr = seg.fatiar_tabuleiro(curr)
        mudancas, _ = seg.detectar_mudancas(casas_ref, casas_curr)
        # Devem detectar múltiplas mudanças
        assert len(mudancas) >= 2
