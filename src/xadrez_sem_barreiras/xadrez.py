import itertools

import chess


class JogoXadrez:
    def __init__(self, fonetica=False):
        self.tabuleiro = chess.Board()
        self.fonetica = fonetica
        self._alfabeto = {
            "a": "Alfa", "b": "Bravo", "c": "Charlie", "d": "Delta",
            "e": "Eco", "f": "Foxtrote", "g": "Golfe", "h": "Hotel",
        }

    def inferir_lance(self, casas_alteradas):
        """
        Recebe uma lista com casas em notação algébrica, por exemplo:
        - lance normal: ['e2', 'e4']
        - en passant: ['e5', 'd6', 'd5']
        - roque: ['e1', 'g1', 'h1', 'f1']

        A função compara essas casas com as casas afetadas por todos os lances
        legais do tabuleiro atual. Assim o roque vira UM lance, mesmo alterando
        quatro casas fisicamente.
        """
        if not casas_alteradas or len(casas_alteradas) not in (2, 3, 4):
            return (
                None,
                "São necessárias 2, 3 ou 4 casas alteradas para inferir um lance.",
                None,
            )

        casas = [c for c in casas_alteradas if c]
        casas_detectadas = set(casas)

        candidatos = []
        for movimento in self.tabuleiro.legal_moves:
            casas_do_lance = self._casas_afetadas_por_lance(movimento)
            if casas_do_lance == casas_detectadas:
                candidatos.append(movimento)

        # Se a detecção veio com ruído extra, tenta recuperar o lance por pares
        # de casas. Isso mantém o sistema tolerante a sombra/cabeça de peça, mas
        # sem perder o suporte correto ao roque com 4 casas.
        if not candidatos and len(casas) > 2:
            candidatos = self._candidatos_por_pares(casas)

        if candidatos:
            movimento_realizado = self._escolher_melhor_candidato(candidatos)
            frase_voz = self._frase_voz_para_lance(movimento_realizado)

            # Aplica o lance no tabuleiro virtual
            self.tabuleiro.push(movimento_realizado)
            return movimento_realizado.uci(), "Lance válido e registrado!", frase_voz

        casas_txt = ", ".join(casas_alteradas)
        return None, f"Lance ilegal ou não reconhecido entre as casas: {casas_txt}.", None

    def _candidatos_por_pares(self, casas):
        """Tenta achar um lance legal usando qualquer par de casas detectadas."""
        encontrados = []
        vistos = set()

        for casa_a, casa_b in itertools.combinations(casas, 2):
            for origem, destino in ((casa_a, casa_b), (casa_b, casa_a)):
                base = f"{origem}{destino}"
                tentativas = [base, base + "q", base + "r", base + "b", base + "n"]

                for uci in tentativas:
                    try:
                        movimento = chess.Move.from_uci(uci)
                    except ValueError:
                        continue

                    if movimento in self.tabuleiro.legal_moves and movimento.uci() not in vistos:
                        encontrados.append(movimento)
                        vistos.add(movimento.uci())

        return encontrados

    def _casas_afetadas_por_lance(self, movimento):
        """Retorna todas as casas que mudam visualmente em um lance legal."""
        casas = {
            chess.square_name(movimento.from_square),
            chess.square_name(movimento.to_square),
        }

        # Roque: além do rei, a torre também muda de casa.
        if self.tabuleiro.is_castling(movimento):
            cor = self.tabuleiro.turn
            file_origem = chess.square_file(movimento.from_square)
            file_destino = chess.square_file(movimento.to_square)
            linha = "1" if cor == chess.WHITE else "8"

            if file_destino > file_origem:
                # Roque pequeno: torre h -> f
                casas.update({f"h{linha}", f"f{linha}"})
            else:
                # Roque grande: torre a -> d
                casas.update({f"a{linha}", f"d{linha}"})

        # En passant: a casa do peão capturado também fica vazia.
        if self.tabuleiro.is_en_passant(movimento):
            deslocamento = -8 if self.tabuleiro.turn == chess.WHITE else 8
            casa_capturada = movimento.to_square + deslocamento
            casas.add(chess.square_name(casa_capturada))

        return casas

    def _escolher_melhor_candidato(self, candidatos):
        """
        Em promoção, quatro lances podem afetar as mesmas duas casas.
        O padrão aqui é promover para dama, que é o caso mais comum.
        """
        for movimento in candidatos:
            if movimento.promotion == chess.QUEEN:
                return movimento
        return candidatos[0]

    def _frase_voz_para_lance(self, movimento):
        """Cria a frase falada: [peça] [posição atual] [posição final]."""
        peca = self.tabuleiro.piece_at(movimento.from_square)
        origem = chess.square_name(movimento.from_square)
        destino = chess.square_name(movimento.to_square)
        origem_falada = self._casa_para_fala(origem)
        destino_falado = self._casa_para_fala(destino)

        nomes = {
            chess.PAWN: "Peão",
            chess.KNIGHT: "Cavalo",
            chess.BISHOP: "Bispo",
            chess.ROOK: "Torre",
            chess.QUEEN: "Dama",
            chess.KING: "Rei",
        }

        nome_peca = nomes.get(peca.piece_type, "Peça") if peca else "Peça"

        if self.tabuleiro.is_castling(movimento):
            tipo = "pequeno" if chess.square_file(movimento.to_square) > chess.square_file(movimento.from_square) else "grande"
            return f"Rei {origem_falada} {destino_falado}. Roque {tipo}."

        if movimento.promotion:
            nome_promocao = nomes.get(movimento.promotion, "peça")
            return f"Peão {origem_falada} {destino_falado}. Promoção para {nome_promocao}."

        return f"{nome_peca} {origem_falada} {destino_falado}."

    def _casa_para_fala(self, casa):
        """Deixa a casa mais fácil para a voz ler. Ex.: e4 -> e 4."""
        if len(casa) != 2:
            return casa
        letra = casa[0].lower()
        numero = casa[1]
        if self.fonetica:
            letra_falada = self._alfabeto.get(letra, letra)
        else:
            letra_falada = letra
        return f"{letra_falada} {numero}"

    def imprimir_tabuleiro(self):
        """Retorna uma representação em texto do tabuleiro atual para debug no terminal."""
        return str(self.tabuleiro)

    def salvar_estado_fen(self, arquivo="estado_partida.fen"):
        """
        Salva a posição atual das peças em um arquivo de texto no formato FEN.
        Isso é muito útil para integrações futuras, como sintetizadores de voz.
        """
        try:
            with open(arquivo, "w", encoding="utf-8") as f:
                f.write(self.tabuleiro.fen())
        except Exception as e:
            print(f"Erro ao salvar o estado das peças: {e}")

    def desfazer_lance(self):
        """Desfaz o último lance realizado no tabuleiro virtual."""
        if len(self.tabuleiro.move_stack) > 0:
            lance_desfeito = self.tabuleiro.pop()
            return lance_desfeito.uci(), True
        return None, False

    def reiniciar_jogo(self):
        """Reseta o tabuleiro virtual para a posição inicial."""
        self.tabuleiro.reset()
