import cv2
import numpy as np
import chess
import pytest

from xadrez_sem_barreiras.segmentador import SegmentadorTabuleiro
from xadrez_sem_barreiras.tradutor import TradutorXadrez
from xadrez_sem_barreiras.xadrez import JogoXadrez


def _criar_tabuleiro_com_pecas(posicao_fen, tamanho=800):
    """Cria imagem sintética de tabuleiro com peças para teste.

    O tradutor mapeia: linha -> file (a-h), coluna -> rank (1-8).
    Portanto no tabuleiro sintético:
    - row (y) = índice do file (0=a .. 7=h)
    - col (x) = índice do rank (0=1 .. 7=8)
    """
    board = chess.Board(posicao_fen)
    img = np.zeros((tamanho, tamanho, 3), dtype=np.uint8)
    casa = tamanho // 8

    for row in range(8):
        for col in range(8):
            sq = chess.square(col, row)
            is_light = (row + col) % 2 == 0
            cor = (230, 210, 170) if is_light else (120, 80, 50)
            img[row * casa:(row + 1) * casa, col * casa:(col + 1) * casa] = cor

    pecas_raio = {
        chess.PAWN: 0.18,
        chess.KNIGHT: 0.22,
        chess.BISHOP: 0.22,
        chess.ROOK: 0.24,
        chess.QUEEN: 0.25,
        chess.KING: 0.26,
    }

    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is None:
            continue
        cx = chess.square_rank(sq) * casa + casa // 2
        cy = chess.square_file(sq) * casa + casa // 2
        raio = int(casa * pecas_raio.get(piece.piece_type, 0.20))
        cor = (245, 245, 240) if piece.color == chess.WHITE else (40, 40, 35)
        cv2.circle(img, (cx, cy), raio, cor, -1)

    return img


def _executar_lance_pipeline(seg, tradutor, jogo, fen_antes, fen_depois):
    """Executa o pipeline completo de detecção para um único lance."""
    jogo.tabuleiro = chess.Board(fen_antes)
    img_ref = _criar_tabuleiro_com_pecas(fen_antes)
    img_novo = _criar_tabuleiro_com_pecas(fen_depois)
    casas_ref = seg.fatiar_tabuleiro(img_ref)
    casas_novo = seg.fatiar_tabuleiro(img_novo)
    mudancas, _ = seg.detectar_mudancas(casas_ref, casas_novo)
    traduzidas = [tradutor.para_notacao(l, c) for l, c in sorted(mudancas)]
    lance, msg, voz = jogo.inferir_lance(traduzidas)
    return lance, msg, voz, mudancas


def _simular_partida(seg, tradutor, fen_inicial, lances_uci):
    """Simula uma partida completa retornando resultado por lance."""
    jogo = JogoXadrez()
    b = chess.Board(fen_inicial)
    fen_atual = fen_inicial
    img_ref = _criar_tabuleiro_com_pecas(fen_atual)
    casas_ref = seg.fatiar_tabuleiro(img_ref)

    resultados = []
    for move_uci in lances_uci:
        move = chess.Move.from_uci(move_uci)
        b.push(move)
        fen_novo = b.fen()

        jogo.tabuleiro = chess.Board(fen_atual)
        img_novo = _criar_tabuleiro_com_pecas(fen_novo)
        casas_novo = seg.fatiar_tabuleiro(img_novo)
        mudancas, _ = seg.detectar_mudancas(casas_ref, casas_novo)

        if len(mudancas) not in (2, 3, 4):
            resultados.append((move_uci, None, f"detected {len(mudancas)} squares", mudancas))
        else:
            traduzidas = [tradutor.para_notacao(l, c) for l, c in sorted(mudancas)]
            lance, msg, voz = jogo.inferir_lance(traduzidas)
            resultados.append((move_uci, lance, msg, mudancas))

        fen_atual = fen_novo
        img_ref = img_novo
        casas_ref = casas_novo

    return resultados


@pytest.fixture
def seg():
    return SegmentadorTabuleiro()


@pytest.fixture
def tradutor():
    return TradutorXadrez()


class TestPipelineCompleto:
    """Testa o pipeline completo: imagem → segmentação → notação → inferência."""

    def test_lance_peao_duas_casas(self, seg, tradutor):
        jogo = JogoXadrez()
        lance, msg, voz, mudancas = _executar_lance_pipeline(
            seg, tradutor, jogo,
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        )
        assert lance == "e2e4"
        assert "válido" in msg
        assert len(mudancas) == 2

    def test_lance_cavalo(self, seg, tradutor):
        jogo = JogoXadrez()
        lance, msg, voz, mudancas = _executar_lance_pipeline(
            seg, tradutor, jogo,
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        )
        assert lance == "e7e5"

    def test_captura(self, seg, tradutor):
        jogo = JogoXadrez()
        lance, msg, voz, mudancas = _executar_lance_pipeline(
            seg, tradutor, jogo,
            "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            "rnbqkbnr/ppp1pppp/8/3P4/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2",
        )
        assert lance == "e4d5"

    def test_roque_pequeno_branco(self, seg, tradutor):
        jogo = JogoXadrez()
        lance, msg, voz, mudancas = _executar_lance_pipeline(
            seg, tradutor, jogo,
            "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1",
            "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R4RK1 b kq - 1 1",
        )
        assert lance == "e1g1"
        assert len(mudancas) == 4

    def test_roque_grande_branco(self, seg, tradutor):
        jogo = JogoXadrez()
        lance, msg, voz, mudancas = _executar_lance_pipeline(
            seg, tradutor, jogo,
            "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1",
            "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/2KR3R b kq - 1 1",
        )
        assert lance == "e1c1"
        assert len(mudancas) == 4

    def test_roque_pequeno_preto(self, seg, tradutor):
        jogo = JogoXadrez()
        lance, msg, voz, mudancas = _executar_lance_pipeline(
            seg, tradutor, jogo,
            "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R b KQkq - 0 1",
            "r4rk1/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQ - 1 1",
        )
        assert lance == "e8g8"
        assert len(mudancas) == 4

    def test_roque_grande_preto(self, seg, tradutor):
        jogo = JogoXadrez()
        lance, msg, voz, mudancas = _executar_lance_pipeline(
            seg, tradutor, jogo,
            "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R b KQkq - 0 1",
            "2kr3r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w Q - 1 1",
        )
        assert lance == "e8c8"
        assert len(mudancas) == 4

    def test_en_passant_branco(self, seg, tradutor):
        jogo = JogoXadrez()
        lance, msg, voz, mudancas = _executar_lance_pipeline(
            seg, tradutor, jogo,
            "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3",
            "rnbqkbnr/ppp1p1pp/5P2/3p4/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 3",
        )
        assert lance == "e5f6"
        assert len(mudancas) == 3

    def test_en_passant_preto(self, seg, tradutor):
        jogo = JogoXadrez()
        lance, msg, voz, mudancas = _executar_lance_pipeline(
            seg, tradutor, jogo,
            "rnbqkbnr/p1pppppp/8/8/Pp6/8/1PPPPPPP/RNBQKBNR b KQkq a3 0 1",
            "rnbqkbnr/p1pppppp/8/8/8/p7/1PPPPPPP/RNBQKBNR w KQkq - 0 2",
        )
        assert lance == "b4a3"
        assert len(mudancas) == 3

    def test_promocao_dama(self, seg, tradutor):
        jogo = JogoXadrez()
        lance, msg, voz, mudancas = _executar_lance_pipeline(
            seg, tradutor, jogo,
            "8/4P3/8/8/8/8/8/4K3 w - - 0 1",
            "4Q3/8/8/8/8/8/8/4K3 b - - 0 1",
        )
        assert lance == "e7e8q"

    def test_voz_formato_peca_origem_destino(self, seg, tradutor):
        jogo = JogoXadrez()
        lance, msg, voz, mudancas = _executar_lance_pipeline(
            seg, tradutor, jogo,
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        )
        assert "para casa" not in voz
        assert "e 2" in voz
        assert "e 4" in voz
        assert "Peão" in voz

    def test_voz_formato_fonetico(self, seg, tradutor):
        jogo = JogoXadrez(fonetica=True)
        lance, msg, voz, mudancas = _executar_lance_pipeline(
            seg, tradutor, jogo,
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        )
        assert "Eco 2 Eco 4" in voz
        assert "Alfa" not in voz
        assert "Bravo" not in voz


class TestPartidasConhecidas:
    """Testa partidas inteiras conhecidas através do pipeline."""

    def test_scholars_mate(self, seg, tradutor):
        """1.e4 e5 2.Qh5 Nc6 3.Bc4 Nf6 4.Qxf7#"""
        resultados = _simular_partida(
            seg, tradutor,
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            ["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7"],
        )
        for move_uci, lance_inferido, msg, mudancas in resultados:
            assert lance_inferido == move_uci, f"{move_uci}: esperado {move_uci}, inferiu {lance_inferido}"

    def test_castling_kingside(self, seg, tradutor):
        """Partida que termina com O-O branco."""
        resultados = _simular_partida(
            seg, tradutor,
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5c6", "d7c6", "e1g1"],
        )
        for move_uci, lance_inferido, msg, mudancas in resultados:
            assert lance_inferido == move_uci, f"{move_uci}: esperado {move_uci}, inferiu {lance_inferido}"

    def test_capturas_sucessivas(self, seg, tradutor):
        """Sequência de capturas: e4 d5 exd5."""
        resultados = _simular_partida(
            seg, tradutor,
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            ["e2e4", "d7d5", "e4d5"],
        )
        for move_uci, lance_inferido, msg, mudancas in resultados:
            assert lance_inferido == move_uci, f"{move_uci}: esperado {move_uci}, inferiu {lance_inferido}"

    def test_promocao_em_partida(self, seg, tradutor):
        """Peão branco promove a dama."""
        resultados = _simular_partida(
            seg, tradutor,
            "8/4P3/8/8/8/8/8/4K3 w - - 0 1",
            ["e7e8q"],
        )
        for move_uci, lance_inferido, msg, mudancas in resultados:
            assert lance_inferido == move_uci

    def test_en_passant_em_partida(self, seg, tradutor):
        """Captura en passant."""
        resultados = _simular_partida(
            seg, tradutor,
            "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3",
            ["e5f6"],
        )
        for move_uci, lance_inferido, msg, mudancas in resultados:
            assert lance_inferido == move_uci
