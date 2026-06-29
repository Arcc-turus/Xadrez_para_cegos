from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class DiagnosticoDeteccao:
    """Resumo interno da última análise visual."""

    alinhamento_dx: float = 0.0
    alinhamento_dy: float = 0.0
    alinhamento_confianca: float = 0.0
    alinhamento_ok: bool = False
    instabilidade_global: float = 0.0
    limiar_percentual_usado: float = 0.0
    candidatos_brutos: int = 0
    candidatos_validos: int = 0
    ignorado_por_ruido_global: bool = False
    motivo: str = ""


class SegmentadorTabuleiro:
    """Detecta casas alteradas em um tabuleiro retificado.

    A versão anterior comparava pixel a pixel dentro de cada casa. Isso era muito
    sensível: um leve toque no tabuleiro, pequena vibração da câmera ou mudança de
    luz podia parecer um lance. Esta versão faz quatro coisas antes de aceitar uma
    mudança:

    1. compensa deslocamentos pequenos entre a referência e o frame atual;
    2. remove variação média de iluminação dentro da casa;
    3. exige uma área conectada mínima, típica da base de uma peça;
    4. descarta quadros com ruído espalhado em muitas casas.
    """

    def __init__(
        self,
        tamanho_tabuleiro: int = 800,
        percentual_minimo_mudanca: float = 0.040,
        limiar_pixel: int = 20,
        componente_minimo_mudanca: float = 0.010,
        max_casas_validas: int = 4,
    ):
        self.tamanho_tabuleiro = tamanho_tabuleiro
        self.tamanho_casa = tamanho_tabuleiro // 8

        # Área usada para decidir se uma casa mudou. Mantemos a região central e
        # inferior, onde a base da peça costuma aparecer, e evitamos bordas/linhas
        # da grade, que são muito sensíveis a pequenos deslocamentos.
        self.roi_x_inicio = 0.20
        self.roi_x_fim = 0.80
        self.roi_y_inicio = 0.32
        self.roi_y_fim = 0.96

        self.percentual_minimo_mudanca = percentual_minimo_mudanca
        self.limiar_pixel = limiar_pixel
        self.componente_minimo_mudanca = componente_minimo_mudanca
        self.max_casas_validas = max_casas_validas
        self.ultimo_diagnostico = DiagnosticoDeteccao()

    def fatiar_tabuleiro(self, imagem_tabuleiro):
        """Divide a imagem retificada em uma matriz 8x8 de sub-imagens (casas)."""
        casas = []
        altura, largura = imagem_tabuleiro.shape[:2]

        # Usa linspace para não acumular erro de arredondamento caso a imagem não
        # esteja exatamente no tamanho esperado.
        cortes_x = np.linspace(0, largura, 9).round().astype(int)
        cortes_y = np.linspace(0, altura, 9).round().astype(int)

        for linha in range(8):
            linha_casas = []
            for coluna in range(8):
                y1, y2 = cortes_y[linha], cortes_y[linha + 1]
                x1, x2 = cortes_x[coluna], cortes_x[coluna + 1]
                linha_casas.append(imagem_tabuleiro[y1:y2, x1:x2])
            casas.append(linha_casas)
        return casas

    def detectar_mudancas_tabuleiro(self, tabuleiro_referencia, tabuleiro_atual):
        """Detecta mudanças usando a imagem completa do tabuleiro.

        Este é o caminho recomendado para câmera real, pois antes de dividir em
        casas ele tenta alinhar o frame atual à referência. Assim, pequenas
        tremidas/deslocamentos do tabuleiro deixam de virar falsos movimentos.
        """
        atual_alinhado, diag = self._alinhar_tabuleiro(tabuleiro_referencia, tabuleiro_atual)
        casas_referencia = self.fatiar_tabuleiro(tabuleiro_referencia)
        casas_atuais = self.fatiar_tabuleiro(atual_alinhado)
        mudancas, mapa = self.detectar_mudancas(casas_referencia, casas_atuais)

        # Mescla o diagnóstico de alinhamento com o diagnóstico da comparação.
        self.ultimo_diagnostico.alinhamento_dx = diag.alinhamento_dx
        self.ultimo_diagnostico.alinhamento_dy = diag.alinhamento_dy
        self.ultimo_diagnostico.alinhamento_confianca = diag.alinhamento_confianca
        self.ultimo_diagnostico.alinhamento_ok = diag.alinhamento_ok

        # No rastreio real, mais de 4 casas não corresponde a um lance único de
        # xadrez. A função por-casas continua permissiva para testes e debug; a
        # função de tabuleiro completo é rigorosa para evitar falsos positivos.
        if len(mudancas) > self.max_casas_validas:
            self.ultimo_diagnostico.ignorado_por_ruido_global = True
            self.ultimo_diagnostico.motivo = "mais casas alteradas do que um lance de xadrez permite"
            return [], mapa

        return mudancas, mapa

    def medir_instabilidade(self, tabuleiro_referencia, tabuleiro_atual) -> float:
        """Retorna 0..1 indicando quanto o frame mudou globalmente.

        Serve para esperar o tabuleiro ficar parado antes de salvar a referência.
        """
        atual_alinhado, _ = self._alinhar_tabuleiro(tabuleiro_referencia, tabuleiro_atual)
        g1 = cv2.cvtColor(tabuleiro_referencia, cv2.COLOR_BGR2GRAY).astype(np.int16)
        g2 = cv2.cvtColor(atual_alinhado, cv2.COLOR_BGR2GRAY).astype(np.int16)
        delta = g2 - g1
        delta = delta - int(np.median(delta))
        diff = np.abs(delta).astype(np.uint8)
        _, mask = cv2.threshold(diff, 24, 255, cv2.THRESH_BINARY)
        return cv2.countNonZero(mask) / float(mask.shape[0] * mask.shape[1])

    def _alinhar_tabuleiro(self, referencia, atual):
        """Compensa pequenas translações entre referência e frame atual."""
        diag = DiagnosticoDeteccao()
        if referencia is None or atual is None or referencia.size == 0 or atual.size == 0:
            diag.motivo = "imagem ausente"
            return atual, diag

        if referencia.shape[:2] != atual.shape[:2]:
            atual = cv2.resize(atual, (referencia.shape[1], referencia.shape[0]))

        ref_gray = cv2.cvtColor(referencia, cv2.COLOR_BGR2GRAY)
        cur_gray = cv2.cvtColor(atual, cv2.COLOR_BGR2GRAY)
        ref_gray = cv2.GaussianBlur(ref_gray, (5, 5), 0).astype(np.float32) / 255.0
        cur_gray = cv2.GaussianBlur(cur_gray, (5, 5), 0).astype(np.float32) / 255.0

        warp = np.eye(2, 3, dtype=np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 60, 1e-5)

        try:
            confianca, warp = cv2.findTransformECC(
                ref_gray,
                cur_gray,
                warp,
                cv2.MOTION_TRANSLATION,
                criteria,
                None,
                3,
            )
            aligned = cv2.warpAffine(
                atual,
                warp,
                (referencia.shape[1], referencia.shape[0]),
                flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP,
                borderMode=cv2.BORDER_REPLICATE,
            )
            diag.alinhamento_dx = float(warp[0, 2])
            diag.alinhamento_dy = float(warp[1, 2])
            diag.alinhamento_confianca = float(confianca)
            diag.alinhamento_ok = True
            return aligned, diag
        except cv2.error:
            diag.motivo = "falha no alinhamento ECC"
            return atual, diag

    def _recortar_roi_peca(self, imagem):
        """Recorta a região central/baixa da casa, ignorando bordas e vazamentos."""
        altura, largura = imagem.shape[:2]
        x1 = int(largura * self.roi_x_inicio)
        x2 = int(largura * self.roi_x_fim)
        y1 = int(altura * self.roi_y_inicio)
        y2 = int(altura * self.roi_y_fim)
        return imagem[y1:y2, x1:x2], (x1, y1, x2, y2)

    def _mascara_mudanca_roi(self, roi_ref, roi_atual):
        """Cria uma máscara robusta de diferença entre duas ROIs."""
        lab_ref = cv2.cvtColor(roi_ref, cv2.COLOR_BGR2LAB).astype(np.int16)
        lab_atual = cv2.cvtColor(roi_atual, cv2.COLOR_BGR2LAB).astype(np.int16)

        delta = lab_atual - lab_ref
        # Compensa mudança local de iluminação/cor da câmera. Ex.: nuvem, reflexo
        # ou autoexposição não devem virar movimento de peça.
        mediana = np.median(delta.reshape(-1, 3), axis=0).astype(np.int16)
        delta = delta - mediana

        distancia = np.sqrt(np.sum(delta.astype(np.float32) ** 2, axis=2))
        distancia = cv2.GaussianBlur(distancia, (3, 3), 0)
        mascara = (distancia > self.limiar_pixel).astype(np.uint8) * 255

        kernel = np.ones((3, 3), np.uint8)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel, iterations=1)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel, iterations=2)
        return mascara, distancia

    def _maior_componente_ratio(self, mascara):
        area_total = max(1, mascara.shape[0] * mascara.shape[1])
        num_labels, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mascara, 8)
        if num_labels <= 1:
            return 0.0
        maior = int(stats[1:, cv2.CC_STAT_AREA].max())
        return maior / float(area_total)

    def _analisar_casa(self, casa_ref, casa_atual):
        roi_ref, (x1, y1, x2, y2) = self._recortar_roi_peca(casa_ref)
        roi_atual, _ = self._recortar_roi_peca(casa_atual)
        mascara, distancia = self._mascara_mudanca_roi(roi_ref, roi_atual)

        pixels = cv2.countNonZero(mascara)
        area_total = max(1, mascara.shape[0] * mascara.shape[1])
        percentual = pixels / float(area_total)
        maior_componente = self._maior_componente_ratio(mascara)
        intensidade_media = float(distancia[mascara > 0].mean()) if pixels else 0.0

        # Confiança: área mudada + intensidade + se a alteração é um bloco coerente.
        confianca = percentual * min(2.5, max(0.5, intensidade_media / 45.0))
        if maior_componente >= self.componente_minimo_mudanca:
            confianca *= 1.2

        return {
            "percentual": percentual,
            "maior_componente": maior_componente,
            "intensidade_media": intensidade_media,
            "confianca": confianca,
            "mascara": mascara,
            "roi": (x1, y1, x2, y2),
        }

    def detectar_mudancas(self, casas_anterior, casas_atual):
        """Identifica as casas alteradas entre referência e frame atual.

        Mantém a assinatura antiga para os testes e para compatibilidade, mas a
        lógica interna ficou mais robusta contra vibração, sombra e autoexposição.
        Para câmera real, prefira `detectar_mudancas_tabuleiro`.
        """
        diagnostico = DiagnosticoDeteccao()
        mapa_visual = np.zeros((self.tamanho_tabuleiro, self.tamanho_tabuleiro), dtype=np.uint8)
        analisadas = []

        for linha in range(8):
            for coluna in range(8):
                info = self._analisar_casa(casas_anterior[linha][coluna], casas_atual[linha][coluna])
                info.update({"linha": linha, "coluna": coluna, "is_artifact": False})
                analisadas.append(info)

                x1, y1, _x2, _y2 = info["roi"]
                mascara = info["mascara"]
                y_offset = linha * self.tamanho_casa
                x_offset = coluna * self.tamanho_casa
                h, w = mascara.shape[:2]
                mapa_visual[y_offset + y1:y_offset + y1 + h, x_offset + x1:x_offset + x1 + w] = mascara

        percentuais = np.array([a["percentual"] for a in analisadas], dtype=np.float32)
        mediana = float(np.median(percentuais))
        mad = float(np.median(np.abs(percentuais - mediana)))
        limiar_dinamico = max(self.percentual_minimo_mudanca, mediana + 8.0 * mad)

        preliminares = [
            a for a in analisadas
            if a["percentual"] >= limiar_dinamico
            and (
                a["maior_componente"] >= self.componente_minimo_mudanca
                or a["percentual"] >= self.percentual_minimo_mudanca * 1.8
            )
        ]

        # Se muitas casas mudaram um pouco ao mesmo tempo, normalmente não é lance:
        # é tabuleiro/câmera mexendo, mão passando, iluminação ou referência ruim.
        casas_acima_do_minimo = int(np.sum(percentuais >= self.percentual_minimo_mudanca * 0.70))
        instabilidade_global = float(np.mean(percentuais))
        if casas_acima_do_minimo > 10 or (len(preliminares) > 8 and instabilidade_global > 0.018):
            diagnostico.ignorado_por_ruido_global = True
            diagnostico.motivo = "ruido global ou tabuleiro em movimento"
            diagnostico.instabilidade_global = instabilidade_global
            diagnostico.limiar_percentual_usado = limiar_dinamico
            diagnostico.candidatos_brutos = len(preliminares)
            self.ultimo_diagnostico = diagnostico
            return [], mapa_visual

        # Filtro de vazamento vertical: se uma alteração pequena aparece logo acima
        # de uma alteração forte na mesma coluna, costuma ser cabeça/sombra da peça.
        preliminares.sort(key=lambda x: x["confianca"], reverse=True)
        if len(preliminares) > 4:
            for item in preliminares:
                for base in preliminares:
                    if (
                        base["linha"] == item["linha"] + 1
                        and base["coluna"] == item["coluna"]
                        and base["confianca"] >= item["confianca"] * 1.15
                    ):
                        item["is_artifact"] = True
                        break

        validos = [a for a in preliminares if not a["is_artifact"]]
        validos.sort(key=lambda x: x["confianca"], reverse=True)

        casas_alteradas = [(m["linha"], m["coluna"]) for m in validos]

        diagnostico.instabilidade_global = instabilidade_global
        diagnostico.limiar_percentual_usado = limiar_dinamico
        diagnostico.candidatos_brutos = len(preliminares)
        diagnostico.candidatos_validos = len(validos)
        self.ultimo_diagnostico = diagnostico
        return casas_alteradas, mapa_visual
