import chess
import pytest

from xadrez_sem_barreiras.xadrez import JogoXadrez


class TestLancesNormais:
    def test_peao_duas_casas(self):
        jogo = JogoXadrez()
        lance, msg, voz = jogo.inferir_lance(["e2", "e4"])
        assert lance == "e2e4"
        assert "válido" in msg
        assert "Peão" in voz
        assert "e 4" in voz
        assert jogo.tabuleiro.fen().startswith("rnbqkbnr/pppppppp/8/8/4P3")

    def test_cavalo(self):
        jogo = JogoXadrez()
        jogo.tabuleiro.push_uci("e2e4")
        jogo.tabuleiro.push_uci("e7e5")
        lance, msg, voz = jogo.inferir_lance(["g1", "f3"])
        assert lance == "g1f3"
        assert "Cavalo" in voz
        assert "f 3" in voz

    def test_captura(self):
        jogo = JogoXadrez()
        jogo.tabuleiro.push_uci("e2e4")
        jogo.tabuleiro.push_uci("d7d5")
        lance, msg, voz = jogo.inferir_lance(["e4", "d5"])
        assert lance == "e4d5"
        assert "Peão" in voz

    def test_lance_invalido(self):
        jogo = JogoXadrez()
        lance, msg, voz = jogo.inferir_lance(["e2", "e5"])
        assert lance is None
        assert "ilegal" in msg.lower() or "reconhecido" in msg.lower()
        assert voz is None

    def test_muito_poucas_casas(self):
        jogo = JogoXadrez()
        lance, msg, voz = jogo.inferir_lance(["e2"])
        assert lance is None

    def test_muitas_casas(self):
        jogo = JogoXadrez()
        lance, msg, voz = jogo.inferir_lance(["e2", "e4", "a1", "b2", "c3", "d4"])
        assert lance is None

    def test_lance_preto(self):
        jogo = JogoXadrez()
        jogo.tabuleiro.push_uci("e2e4")
        lance, msg, voz = jogo.inferir_lance(["e7", "e5"])
        assert lance == "e7e5"
        assert "Peão" in voz


class TestRoque:
    def _setup_castling_position(self):
        """Position where both sides can castle:
        r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1
        """
        jogo = JogoXadrez()
        jogo.tabuleiro = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1")
        return jogo

    def test_roque_pequeno_branco(self):
        jogo = self._setup_castling_position()
        lance, msg, voz = jogo.inferir_lance(["e1", "g1", "h1", "f1"])
        assert lance == "e1g1"
        assert "válido" in msg
        assert "Rei" in voz
        assert "g 1" in voz
        assert jogo.tabuleiro.piece_at(chess.G1).piece_type == chess.KING
        assert jogo.tabuleiro.piece_at(chess.F1).piece_type == chess.ROOK
        assert jogo.tabuleiro.piece_at(chess.E1) is None
        assert jogo.tabuleiro.piece_at(chess.H1) is None

    def test_roque_grande_branco(self):
        jogo = self._setup_castling_position()
        lance, msg, voz = jogo.inferir_lance(["e1", "c1", "a1", "d1"])
        assert lance == "e1c1"
        assert "válido" in msg
        assert jogo.tabuleiro.piece_at(chess.C1).piece_type == chess.KING
        assert jogo.tabuleiro.piece_at(chess.D1).piece_type == chess.ROOK

    def test_roque_pequeno_preto(self):
        jogo = self._setup_castling_position()
        jogo.tabuleiro.push(chess.Move.from_uci("e1g1"))
        lance, msg, voz = jogo.inferir_lance(["e8", "g8", "h8", "f8"])
        assert lance == "e8g8"
        assert "Rei" in voz
        assert "g 8" in voz
        assert jogo.tabuleiro.piece_at(chess.G8).piece_type == chess.KING
        assert jogo.tabuleiro.piece_at(chess.F8).piece_type == chess.ROOK

    def test_roque_grande_preto(self):
        jogo = self._setup_castling_position()
        jogo.tabuleiro = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R b KQkq - 0 1")
        lance, msg, voz = jogo.inferir_lance(["e8", "c8", "a8", "d8"])
        assert lance == "e8c8"
        assert jogo.tabuleiro.piece_at(chess.C8).piece_type == chess.KING
        assert jogo.tabuleiro.piece_at(chess.D8).piece_type == chess.ROOK

    def test_roque_realistico(self):
        """Castling after realistic opening moves."""
        jogo = JogoXadrez()
        jogo.tabuleiro.push_uci("e2e4")
        jogo.tabuleiro.push_uci("e7e5")
        jogo.tabuleiro.push_uci("g1f3")
        jogo.tabuleiro.push_uci("g8f6")
        jogo.tabuleiro.push_uci("f1c4")
        jogo.tabuleiro.push_uci("f8c5")
        lance, msg, voz = jogo.inferir_lance(["e1", "g1", "h1", "f1"])
        assert lance == "e1g1"
        assert "válido" in msg
        assert "K1" in jogo.tabuleiro.fen()


class TestEnPassant:
    def test_en_passant_branco(self):
        """White pawn on e5 captures black pawn on d5 en passant."""
        jogo = JogoXadrez()
        jogo.tabuleiro.push_uci("e2e4")
        jogo.tabuleiro.push_uci("d7d5")
        jogo.tabuleiro.push_uci("e4e5")
        jogo.tabuleiro.push_uci("f7f5")
        lance, msg, voz = jogo.inferir_lance(["e5", "f6", "f5"])
        assert lance == "e5f6"
        assert "válido" in msg
        assert "Peão" in voz
        assert "f 6" in voz
        assert jogo.tabuleiro.piece_at(chess.F6).piece_type == chess.PAWN
        assert jogo.tabuleiro.piece_at(chess.F5) is None

    def test_en_passant_preto(self):
        """Black pawn on b4 captures white pawn on a4 en passant (b4->a3, captured pawn at a4)."""
        jogo = JogoXadrez()
        jogo.tabuleiro = chess.Board("rnbqkbnr/p1pppppp/8/8/1p6/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        jogo.tabuleiro.push_uci("a2a4")
        lance, msg, voz = jogo.inferir_lance(["b4", "a3", "a4"])
        assert lance == "b4a3"
        assert "válido" in msg
        assert "Peão" in voz
        assert "a 3" in voz
        assert jogo.tabuleiro.piece_at(chess.A3).piece_type == chess.PAWN
        assert jogo.tabuleiro.piece_at(chess.A4) is None

    def test_en_passant_fen_apos_captura(self):
        """After en passant, FEN should not have ep square."""
        jogo = JogoXadrez()
        jogo.tabuleiro.push_uci("e2e4")
        jogo.tabuleiro.push_uci("d7d5")
        jogo.tabuleiro.push_uci("e4e5")
        jogo.tabuleiro.push_uci("f7f5")
        jogo.inferir_lance(["e5", "f6", "f5"])
        assert " - " in jogo.tabuleiro.fen()


class TestPromocao:
    def test_promocao_para_dama(self):
        """White pawn on e7 promotes to queen on e8 (empty 8th rank)."""
        jogo = JogoXadrez()
        jogo.tabuleiro = chess.Board("8/4P3/8/8/8/8/8/4K3 w - - 0 1")
        lance, msg, voz = jogo.inferir_lance(["e7", "e8"])
        assert lance == "e7e8q"
        assert "Peão" in voz
        assert "e 7" in voz
        assert "e 8" in voz
        assert "Promoção para Dama" in voz
        assert jogo.tabuleiro.piece_at(chess.E8).piece_type == chess.QUEEN

    def test_promocao_prioriza_dama(self):
        """When multiple promotion candidates, choose queen."""
        jogo = JogoXadrez()
        jogo.tabuleiro = chess.Board("8/4P3/8/8/8/8/8/4K3 w - - 0 1")
        lance, msg, voz = jogo.inferir_lance(["e7", "e8"])
        assert lance == "e7e8q"


class TestVozFormato:
    def test_formato_peca_origem_destino(self):
        jogo = JogoXadrez()
        lance, msg, voz = jogo.inferir_lance(["e2", "e4"])
        assert "para casa" not in voz
        assert "e 2" in voz
        assert "e 4" in voz
        assert "Peão" in voz

    def test_cavalo_formato_voz(self):
        jogo = JogoXadrez()
        jogo.tabuleiro.push_uci("e2e4")
        jogo.tabuleiro.push_uci("e7e5")
        lance, msg, voz = jogo.inferir_lance(["g1", "f3"])
        assert voz == "Cavalo g 1 f 3."

    def test_torre_formato_voz(self):
        jogo = JogoXadrez()
        jogo.tabuleiro.push_uci("e2e4")
        jogo.tabuleiro.push_uci("e7e5")
        jogo.tabuleiro.push_uci("g1f3")
        jogo.tabuleiro.push_uci("g8f6")
        jogo.tabuleiro.push_uci("f1c4")
        jogo.tabuleiro.push_uci("f8c5")
        lance, msg, voz = jogo.inferir_lance(["e1", "g1", "h1", "f1"])
        lance2, msg2, voz2 = jogo.inferir_lance(["e8", "g8"])
        lance3, msg3, voz3 = jogo.inferir_lance(["h8", "f8"])
        assert "Torre" in voz3

    def test_bispo_formato_voz(self):
        jogo = JogoXadrez()
        jogo.tabuleiro.push_uci("e2e4")
        jogo.tabuleiro.push_uci("e7e5")
        lance, msg, voz = jogo.inferir_lance(["f1", "c4"])
        assert "Bispo" in voz

    def test_dama_formato_voz(self):
        jogo = JogoXadrez()
        jogo.tabuleiro.push_uci("e2e4")
        jogo.tabuleiro.push_uci("e7e5")
        lance, msg, voz = jogo.inferir_lance(["d1", "e2"])
        assert "Dama" in voz

    def test_rei_formato_voz(self):
        jogo = JogoXadrez()
        jogo.tabuleiro.push_uci("e2e4")
        jogo.tabuleiro.push_uci("e7e5")
        jogo.tabuleiro.push_uci("g1f3")
        jogo.tabuleiro.push_uci("g8f6")
        jogo.tabuleiro.push_uci("f1c4")
        jogo.tabuleiro.push_uci("f8c5")
        lance, msg, voz = jogo.inferir_lance(["e1", "g1", "h1", "f1"])
        assert "Rei" in voz
        assert "e " in voz
        assert "g " in voz
        assert "Roque pequeno" in voz


class TestVozFonetica:
    def test_lance_normal_fonetico(self):
        jogo = JogoXadrez(fonetica=True)
        lance, msg, voz = jogo.inferir_lance(["e2", "e4"])
        assert "Eco" in voz
        assert "e " not in voz

    def test_cavalo_fonetico(self):
        jogo = JogoXadrez(fonetica=True)
        jogo.tabuleiro.push_uci("e2e4")
        jogo.tabuleiro.push_uci("e7e5")
        lance, msg, voz = jogo.inferir_lance(["g1", "f3"])
        assert "Golfe" in voz
        assert "Foxtrote" in voz

    def test_todas_letras_fonetico(self):
        jogo = JogoXadrez(fonetica=True)
        jogo.tabuleiro.push_uci("e2e4")
        jogo.tabuleiro.push_uci("e7e5")
        lance, msg, voz = jogo.inferir_lance(["f1", "c4"])
        assert "Foxtrote" in voz


class TestCLI:
    def test_voz_af_sinaliza_fonetica(self):
        from xadrez_sem_barreiras.app import criar_parser
        parser = criar_parser()
        args = parser.parse_args(["--voz-af"])
        assert args.voz_af == 1.0

    def test_voz_af_com_velocidade(self):
        from xadrez_sem_barreiras.app import criar_parser
        parser = criar_parser()
        args = parser.parse_args(["--voz-af", "2.5"])
        assert args.voz_af == 2.5

    def test_voz_sem_af(self):
        from xadrez_sem_barreiras.app import criar_parser
        parser = criar_parser()
        args = parser.parse_args(["--voz", "2.0"])
        assert args.voz == 2.0
        assert args.voz_af is None

    def test_main_logic_voz_af_somente(self):
        from xadrez_sem_barreiras.app import criar_parser
        parser = criar_parser()
        args = parser.parse_args(["--voz-af"])
        voz_ativa = not args.sem_voz
        voz_velocidade = max(1.0, min(4.0, args.voz)) if args.voz_af is None else max(1.0, min(4.0, args.voz_af))
        voz_fonetica = args.voz_af is not None and not args.sem_voz
        assert voz_ativa is True
        assert voz_velocidade == 1.0
        assert voz_fonetica is True

    def test_main_logic_voz_af_com_velocidade(self):
        from xadrez_sem_barreiras.app import criar_parser
        parser = criar_parser()
        args = parser.parse_args(["--voz-af", "3.0"])
        voz_ativa = not args.sem_voz
        voz_velocidade = max(1.0, min(4.0, args.voz)) if args.voz_af is None else max(1.0, min(4.0, args.voz_af))
        voz_fonetica = args.voz_af is not None and not args.sem_voz
        assert voz_ativa is True
        assert voz_velocidade == 3.0
        assert voz_fonetica is True

    def test_main_logic_sem_voz(self):
        from xadrez_sem_barreiras.app import criar_parser
        parser = criar_parser()
        args = parser.parse_args(["--sem-voz"])
        voz_ativa = not args.sem_voz
        assert voz_ativa is False


class TestDesfazerReiniciar:
    def test_desfazer_lance(self):
        jogo = JogoXadrez()
        jogo.inferir_lance(["e2", "e4"])
        lance, sucesso = jogo.desfazer_lance()
        assert sucesso
        assert lance == "e2e4"
        assert jogo.tabuleiro.fen() == chess.Board().fen()

    def test_desfazer_sem_lances(self):
        jogo = JogoXadrez()
        lance, sucesso = jogo.desfazer_lance()
        assert lance is None
        assert not sucesso

    def test_reiniciar_jogo(self):
        jogo = JogoXadrez()
        jogo.inferir_lance(["e2", "e4"])
        jogo.inferir_lance(["e7", "e5"])
        jogo.reiniciar_jogo()
        assert jogo.tabuleiro.fen() == chess.Board().fen()

    def test_desfazer_multiplos_lances(self):
        jogo = JogoXadrez()
        jogo.inferir_lance(["e2", "e4"])
        jogo.inferir_lance(["e7", "e5"])
        jogo.inferir_lance(["g1", "f3"])
        lance, sucesso = jogo.desfazer_lance()
        assert lance == "g1f3"
        assert len(jogo.tabuleiro.move_stack) == 2


class TestCasasAfetadas:
    def test_lance_normal_duas_casas(self):
        jogo = JogoXadrez()
        move = chess.Move.from_uci("e2e4")
        casas = jogo._casas_afetadas_por_lance(move)
        assert casas == {"e2", "e4"}

    def test_captura_duas_casas(self):
        jogo = JogoXadrez()
        jogo.tabuleiro.push_uci("e2e4")
        jogo.tabuleiro.push_uci("d7d5")
        move = chess.Move.from_uci("e4d5")
        casas = jogo._casas_afetadas_por_lance(move)
        assert casas == {"e4", "d5"}

    def test_roque_quatro_casas(self):
        jogo = JogoXadrez()
        jogo.tabuleiro = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1")
        move = chess.Move.from_uci("e1g1")
        casas = jogo._casas_afetadas_por_lance(move)
        assert casas == {"e1", "g1", "h1", "f1"}

    def test_roque_grande_quatro_casas(self):
        jogo = JogoXadrez()
        jogo.tabuleiro = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1")
        move = chess.Move.from_uci("e1c1")
        casas = jogo._casas_afetadas_por_lance(move)
        assert casas == {"e1", "c1", "a1", "d1"}

    def test_en_passant_tres_casas(self):
        jogo = JogoXadrez()
        jogo.tabuleiro.push_uci("e2e4")
        jogo.tabuleiro.push_uci("d7d5")
        jogo.tabuleiro.push_uci("e4e5")
        jogo.tabuleiro.push_uci("f7f5")
        move = chess.Move.from_uci("e5f6")
        casas = jogo._casas_afetadas_por_lance(move)
        assert casas == {"e5", "f6", "f5"}
