from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2

from .camera import BoardDetector
from .segmentador import SegmentadorTabuleiro
from .tradutor import TradutorXadrez
from .voz import LeitorVoz
from .xadrez import JogoXadrez


DEFAULT_DATA_DIR = Path("data")

_gui: object = None  # VozConfigGUI instance or None


def _iniciar_gui_voz(voz: LeitorVoz, jogo: JogoXadrez) -> None:
    """Cria a janela de configuracao de voz (chamado do loop principal)."""
    global _gui
    if _gui is not None:
        return
    try:
        from .voz_gui import VozConfigGUI
        _gui = VozConfigGUI(voz, jogo)
        print("\n>>> Janela de voz aberta. Pressione 'f' novamente para reabrir se fechar.")
    except Exception as e:
        print(f"\n>>> ERRO ao abrir janela de voz: {e}")
        import traceback
        traceback.print_exc()


def _atualizar_gui_voz() -> None:
    """Chama update() da GUI e limpa se foi fechada."""
    global _gui
    if _gui is None:
        return
    try:
        if not _gui.update():
            _gui = None
    except cv2.error:
        _gui = None


def executar_projeto(
    camera_index: int = 1,
    posicao_camera: str = "brancas_esquerda",
    voz_ativa: bool = True,
    voz_velocidade: float = 1.0,
    voz_fonetica: bool = False,
    tempo_confirmacao: float = 2.0,
    data_dir: Path | str = DEFAULT_DATA_DIR,
) -> None:
    """Executa o rastreador visual de xadrez.

    Atalhos principais:
    - c: calibrar manualmente as quinas do tabuleiro
    - v: tentar calibracao automatica
    - s: salvar o estado visual atual como referencia
    - f: abrir janela de configuracao de voz
    - z: desfazer ultimo lance
    - r: reiniciar partida
    - q: sair
    """
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    estado_visual_path = data_dir / "estado_visual_pecas.jpg"
    estado_fen_path = data_dir / "estado_partida.fen"

    olho = BoardDetector(camera_index=camera_index)
    segmentador = SegmentadorTabuleiro()
    tradutor = TradutorXadrez(posicao_camera=posicao_camera)
    jogo = JogoXadrez(fonetica=voz_fonetica)
    voz = LeitorVoz(ativo=voz_ativa, velocidade=voz_velocidade)

    tabuleiro_referencia = None
    candidato_mudancas = None
    tempo_inicio_deteccao = 0.0
    cooldown_ativo_ate = 0.0

    print("\nSISTEMA DE RASTREAMENTO INICIADO")
    print("Comandos: 'c' calibrar | 'v' auto | 's' salvar | 'f' voz | 'z' desfazer | 'r' reset | 'q' sair")
    print(jogo.imprimir_tabuleiro())

    try:
        while True:
            frame = olho.capturar_frame()
            if frame is None:
                print("Nao foi possivel capturar frame da camera.")
                break

            cv2.imshow("Captura de Video", frame)
            _atualizar_gui_voz()
            tecla = cv2.waitKey(1) & 0xFF

            if tecla == ord("c"):
                olho.calibrar_com_mouse(frame)

            elif tecla == ord("z"):
                lance_uci, sucesso = jogo.desfazer_lance()
                if sucesso:
                    print(f"\n--- LANCE DESFEITO: {lance_uci} ---")
                    print("Retorne a peca para a posicao anterior no tabuleiro fisico.")
                    print("Depois pressione 's' para salvar a nova referencia.")
                    print("\a", end="")
                    tabuleiro_referencia = None
                    candidato_mudancas = None
                    jogo.salvar_estado_fen(str(estado_fen_path))
                else:
                    print("\n[ Aviso ] Nao ha lances para desfazer.")

            elif tecla == ord("r"):
                print("\n--- REINICIANDO A PARTIDA ---")
                jogo.reiniciar_jogo()
                tabuleiro_referencia = None
                candidato_mudancas = None
                print("Arrume as pecas fisicamente e pressione 's' para comecar novamente.")
                print("\a", end="")
                jogo.salvar_estado_fen(str(estado_fen_path))

            elif tecla == ord("v"):
                print("\nIniciando busca automatica pelo tabuleiro...")
                sucesso = olho.calibrar_automatico(frame)
                if sucesso:
                    print("\a", end="")
                    print(">>> Tabuleiro encontrado. Pressione 's' para salvar o estado de referencia.")
                else:
                    print(">>> Erro: nao foi possivel detectar as quinas.")
                    print("Dica: remova as pecas e melhore a iluminacao.")

            elif tecla == ord("f"):
                _iniciar_gui_voz(voz, jogo)

            elif tecla == ord("s"):
                if olho.pontos_origem is not None:
                    tab_ref = olho.retificar_tabuleiro(frame)
                    tabuleiro_referencia = tab_ref.copy()
                    cv2.imwrite(str(estado_visual_path), tab_ref)
                    jogo.salvar_estado_fen(str(estado_fen_path))
                    print("Estado visual e FEN salvos em data/.")
                else:
                    print("Erro: calibre o tabuleiro antes de salvar o estado.")

            elif tecla == ord("q"):
                break

            if tabuleiro_referencia is not None:
                if time.time() < cooldown_ativo_ate:
                    continue

                tab_atual = olho.retificar_tabuleiro(frame)
                tab_com_grade = olho.desenhar_grade_para_teste(tab_atual)
                cv2.imshow("Grade de Divisao", tab_com_grade)

                mudancas, mapa = segmentador.detectar_mudancas_tabuleiro(tabuleiro_referencia, tab_atual)
                cv2.imshow("Mascara de Diferenca", mapa)

                if 2 <= len(mudancas) <= 4:
                    mudancas_ordenadas = sorted(mudancas)

                    if candidato_mudancas == mudancas_ordenadas:
                        tempo_decorrido = time.time() - tempo_inicio_deteccao

                        if tempo_decorrido >= tempo_confirmacao:
                            traduzidas = [tradutor.para_notacao(l, c) for l, c in mudancas_ordenadas]
                            lance_uci, mensagem, frase_voz = jogo.inferir_lance(traduzidas)

                            if lance_uci:
                                print(f"\n--- LANCE EXECUTADO: {lance_uci} ---")
                                print(mensagem)
                                if frase_voz:
                                    voz.falar(frase_voz)
                                print(jogo.imprimir_tabuleiro())

                                tabuleiro_referencia = tab_atual.copy()
                                cv2.imwrite(str(estado_visual_path), tab_atual)
                                jogo.salvar_estado_fen(str(estado_fen_path))
                                print("Referencia atualizada e salva em data/.")
                                cooldown_ativo_ate = time.time() + 1.0
                            else:
                                print("\n[ ALERTA DE MOVIMENTO ]")
                                print(f"Movimento detectado ({', '.join(traduzidas)}) nao e valido.")
                                print("Retorne a peca para a posicao original e tente novamente.")
                                print("\a", end="")
                                cooldown_ativo_ate = time.time() + 4.0

                            candidato_mudancas = None
                    else:
                        candidato_mudancas = mudancas_ordenadas
                        tempo_inicio_deteccao = time.time()
                else:
                    candidato_mudancas = None
    finally:
        olho.fechar()


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rastreador de xadrez fisico com camera, FEN e voz.")
    parser.add_argument("--camera", type=int, default=1, help="Indice da camera. Ex.: 0, 1 ou 2.")
    parser.add_argument("--sem-voz", action="store_true", help="Inicia o programa com voz desativada.")
    parser.add_argument("--voz", type=float, default=1.0, help="Velocidade da voz de 1.0 a 4.0 (ex.: 1.5, 2.0, 3.5).")
    parser.add_argument("--voz-af", type=float, nargs="?", const=1.0, default=None,
                        help="Alfabeto fonetico NATO com velocidade opcional. Ex.: --voz-af 2.0")
    parser.add_argument("--tempo-confirmacao", type=float, default=2.0, help="Tempo em segundos para confirmar movimento estavel.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Pasta onde salvar FEN e imagem de referencia.")
    parser.add_argument("--posicao-camera", default="brancas_esquerda", help="Orientacao usada pelo tradutor de casas.")
    parser.add_argument("--web", action="store_true", help="Inicia o servidor web em localhost:5000.")
    return parser


def main() -> None:
    args = criar_parser().parse_args()

    if args.web:
        from web.app import main as web_main
        web_main()
        return

    if args.sem_voz:
        voz_ativa = False
        voz_velocidade = 1.0
        voz_fonetica = False
    elif args.voz_af is not None:
        voz_ativa = True
        voz_velocidade = max(1.0, min(4.0, args.voz_af))
        voz_fonetica = True
    else:
        voz_ativa = True
        voz_velocidade = max(1.0, min(4.0, args.voz))
        voz_fonetica = False

    executar_projeto(
        camera_index=args.camera,
        posicao_camera=args.posicao_camera,
        voz_ativa=voz_ativa,
        voz_velocidade=voz_velocidade,
        voz_fonetica=voz_fonetica,
        tempo_confirmacao=args.tempo_confirmacao,
        data_dir=args.data_dir,
    )


if __name__ == "__main__":
    main()
