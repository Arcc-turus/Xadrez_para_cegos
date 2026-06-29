from __future__ import annotations

import threading

import cv2
import numpy as np

from .voz import LeitorVoz
from .xadrez import JogoXadrez

LARGURA_JANELA = 540
ALTURA_JANELA = 200

COR_FUNDO = (30, 30, 30)
COR_BORDA = (120, 120, 120)
COR_DESTAQUE = (72, 145, 220)
COR_BRANCO = (255, 255, 255)
COR_HOVER = (90, 160, 240)
NOME_JANELA = "Configuracao de Voz"


class VozConfigGUI:
    """Painel de configuracao de voz com janela OpenCV customizada."""

    def __init__(
        self,
        voz: LeitorVoz,
        jogo: JogoXadrez,
        frase_teste: str = "Ola, este e um teste de voz.",
    ) -> None:
        self.voz = voz
        self.jogo = jogo
        self.frase_teste = frase_teste
        self.aberta = True

        self._voz_ativo = voz.ativo
        self._fonetica = jogo.fonetica
        self._velocidade = max(1.0, min(4.0, voz.velocidade))

        self._hover_voz = False
        self._hover_fonetica = False
        self._hover_testar = False
        self._hover_slider = False
        self._dragging_slider = False

        # Layout - checkboxes
        self._cb_tamanho = 40
        self._cb_y = 40
        self._cx_voz = 40
        self._cx_fonetica = 260

        # Layout - slider
        self._slider_y = 110
        self._slider_x = 40
        self._slider_w = 340
        self._slider_h = 18
        self._knob_raio = 18

        # Layout - botao testar
        self._btn_testar = {"x": 405, "y": 148, "w": 110, "h": 40}

        self._slider_min = self._slider_x
        self._slider_max = self._slider_x + self._slider_w

        self._criar_janela()

    def _criar_janela(self) -> None:
        try:
            cv2.destroyWindow(NOME_JANELA)
        except cv2.error:
            pass
        cv2.namedWindow(NOME_JANELA, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(NOME_JANELA, LARGURA_JANELA, ALTURA_JANELA)
        cv2.setMouseCallback(NOME_JANELA, self._on_mouse)

    def update(self) -> bool:
        if not self.aberta:
            return False

        try:
            visivel = cv2.getWindowProperty(NOME_JANELA, cv2.WND_PROP_VISIBLE)
            if visivel is None or visivel < 1:
                self._fechar()
                return False
        except cv2.error:
            self._fechar()
            return False

        frame = self._desenhar_frame()
        try:
            cv2.imshow(NOME_JANELA, frame)
        except cv2.error:
            self._fechar()
            return False

        tecla = cv2.waitKey(1) & 0xFF
        if tecla == 27:
            self._fechar()
            return False

        return True

    def _desenhar_frame(self) -> np.ndarray:
        frame = np.full((ALTURA_JANELA, LARGURA_JANELA, 3), COR_FUNDO, dtype=np.uint8)

        # Checkbox Voz
        self._desenhar_checkbox(frame, self._cx_voz, self._cb_y, self._cb_tamanho,
                                self._voz_ativo, self._hover_voz, "Voz")

        # Checkbox Fonetica
        self._desenhar_checkbox(frame, self._cx_fonetica, self._cb_y, self._cb_tamanho,
                                self._fonetica, self._hover_fonetica, "Fonetico")

        # Slider trilha
        cv2.rectangle(
            frame,
            (self._slider_x, self._slider_y),
            (self._slider_x + self._slider_w, self._slider_y + self._slider_h),
            COR_BORDA,
            -1,
        )

        # Knob
        progresso = (self._velocidade - 1.0) / 3.0
        knob_x = int(self._slider_min + progresso * self._slider_w)
        knob_y = self._slider_y + self._slider_h // 2
        cor_knob = COR_HOVER if (self._hover_slider or self._dragging_slider) else COR_DESTAQUE
        cv2.circle(frame, (knob_x, knob_y), self._knob_raio, cor_knob, -1)
        cv2.circle(frame, (knob_x, knob_y), self._knob_raio, COR_BRANCO, 2)

        # Valor acima do knob
        texto_valor = f"{self._velocidade:.1f}x"
        (tw, th), _ = cv2.getTextSize(texto_valor, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        tx = int(knob_x - tw // 2)
        ty = int(self._slider_y - 12)
        cv2.rectangle(frame, (tx - 8, ty - th - 6), (tx + tw + 8, ty + 6), COR_FUNDO, -1)
        cv2.putText(frame, texto_valor, (tx, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, COR_BRANCO, 2, cv2.LINE_AA)

        # Rotulo
        cv2.putText(frame, "Velocidade:",
                    (self._slider_x, self._slider_y + self._slider_h + 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (160, 160, 160), 1, cv2.LINE_AA)

        # Botao testar
        cor_btn = COR_HOVER if self._hover_testar else COR_DESTAQUE
        cv2.rectangle(frame,
                      (self._btn_testar["x"], self._btn_testar["y"]),
                      (self._btn_testar["x"] + self._btn_testar["w"],
                       self._btn_testar["y"] + self._btn_testar["h"]),
                      cor_btn, -1)
        cv2.rectangle(frame,
                      (self._btn_testar["x"], self._btn_testar["y"]),
                      (self._btn_testar["x"] + self._btn_testar["w"],
                       self._btn_testar["y"] + self._btn_testar["h"]),
                      COR_BRANCO, 2)
        (bw, bh), _ = cv2.getTextSize("Testar", cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        bx = self._btn_testar["x"] + (self._btn_testar["w"] - bw) // 2
        by = self._btn_testar["y"] + self._btn_testar["h"] // 2 + 7
        cv2.putText(frame, "Testar", (bx, by),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, COR_BRANCO, 2, cv2.LINE_AA)

        return frame

    def _desenhar_checkbox(
        self, frame: np.ndarray, cx: int, cy: int, tamanho: int,
        ativo: bool, hover: bool, texto: str
    ) -> None:
        cor = COR_HOVER if hover else COR_DESTAQUE if ativo else COR_BORDA
        cv2.rectangle(frame, (cx, cy), (cx + tamanho, cy + tamanho), cor, 3)
        if ativo:
            inner = max(10, tamanho // 2)
            offset = (tamanho - inner) // 2
            cv2.rectangle(
                frame,
                (cx + offset, cy + offset),
                (cx + offset + inner, cy + offset + inner),
                COR_BRANCO, -1,
            )
        cv2.putText(frame, texto,
                    (cx + tamanho + 14, cy + tamanho - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, COR_BRANCO, 2, cv2.LINE_AA)

    def _on_mouse(self, event: int, x: int, y: int, _flags: int, _param: int) -> None:
        if not self.aberta:
            return

        try:
            self._hover_voz = False
            self._hover_fonetica = False
            self._hover_testar = False
            self._hover_slider = False

            knob_x = int(self._slider_min + ((self._velocidade - 1.0) / 3.0) * self._slider_w)
            knob_y = self._slider_y + self._slider_h // 2

            # Checkbox voz
            vx2 = self._cx_voz + self._cb_tamanho + 80
            if self._cx_voz <= x <= vx2 and self._cb_y <= y <= self._cb_y + self._cb_tamanho:
                self._hover_voz = True
                if event == cv2.EVENT_LBUTTONDOWN:
                    self._voz_ativo = not self._voz_ativo
                    self.voz.ativo = self._voz_ativo

            # Checkbox fonetica
            fx2 = self._cx_fonetica + self._cb_tamanho + 110
            if self._cx_fonetica <= x <= fx2 and self._cb_y <= y <= self._cb_y + self._cb_tamanho:
                self._hover_fonetica = True
                if event == cv2.EVENT_LBUTTONDOWN:
                    self._fonetica = not self._fonetica
                    self.jogo.fonetica = self._fonetica

            # Slider
            dist_knob = ((x - knob_x) ** 2 + (y - knob_y) ** 2) ** 0.5
            na_trilha = (self._slider_x <= x <= self._slider_max and
                         self._slider_y - 20 <= y <= self._slider_y + self._slider_h + 20)

            if event == cv2.EVENT_LBUTTONDOWN and (dist_knob <= self._knob_raio + 5 or na_trilha):
                self._dragging_slider = True
                self._hover_slider = True
                self._atualizar_slider_por_x(x)

            elif event == cv2.EVENT_MOUSEMOVE and self._dragging_slider:
                self._atualizar_slider_por_x(x)

            elif event == cv2.EVENT_LBUTTONUP:
                self._dragging_slider = False
                if na_trilha or dist_knob <= self._knob_raio + 5:
                    self._hover_slider = True

            if not self._dragging_slider and na_trilha:
                self._hover_slider = True

            # Botao testar
            bt = self._btn_testar
            if bt["x"] <= x <= bt["x"] + bt["w"] and bt["y"] <= y <= bt["y"] + bt["h"]:
                self._hover_testar = True
                if event == cv2.EVENT_LBUTTONDOWN:
                    t = threading.Thread(target=self.voz.falar, args=(self.frase_teste,), daemon=True)
                    t.start()
        except cv2.error:
            pass

    def _atualizar_slider_por_x(self, x: int) -> None:
        progresso = max(0.0, min(1.0, (x - self._slider_min) / self._slider_w))
        self._velocidade = round(1.0 + progresso * 3.0, 1)
        self.voz.velocidade = self._velocidade

    def _fechar(self) -> None:
        self.voz.velocidade = self._velocidade
        self.aberta = False
        try:
            cv2.destroyWindow(NOME_JANELA)
        except cv2.error:
            pass
