"""
mano_avatar.py — La cámara NUNCA se muestra: solo una mano ilustrada.

* `ManoAvatar`: dibuja en tiempo real una mano de caricatura siguiendo los 21
  landmarks de MediaPipe (rota, se abre y se cierra como la mano real).
* `dibujar_mano_estilizada`: mano "de catálogo" (palma + 4 dedos + pulgar) con la
  geometría de los mockups 02/03/04. Se usa en el menú y en la pista de ayuda.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import pygame

import config
from componentes import caja, disco, elipse_rotada

Color = Tuple[int, int, int]

PIEL = config.COLOR_PIEL
CONTORNO = config.COLOR_PIEL_CONTORNO
SOMBRA_PALMA = config.COLOR_PIEL_SOMBRA
PUNTO_DEDO = config.COLOR_PUNTO_DEDO
BLANCO = (255, 255, 255)

# Cadenas de landmarks por dedo (pulgar, índice, medio, anular, meñique)
CADENAS_DEDOS = (
    (1, 2, 3, 4),
    (5, 6, 7, 8),
    (9, 10, 11, 12),
    (13, 14, 15, 16),
    (17, 18, 19, 20),
)
CONTORNO_PALMA = (0, 1, 5, 9, 13, 17)
PUNTAS = (4, 8, 12, 16, 20)


# =============================================================================
# MANO EN VIVO (sigue los landmarks)
# =============================================================================
class ManoAvatar:
    """Convierte landmarks normalizados en una mano de caricatura."""

    def __init__(
        self,
        tamano_camara: Tuple[int, int] = (config.ANCHO_CAPTURA_CAMARA, config.ALTO_CAPTURA_CAMARA),
        suavizado: float = config.SUAVIZADO_MANO,
        tamano_palma: float = config.TAMANO_PALMA_AVATAR,
        ganancia_movimiento: float = config.GANANCIA_MOVIMIENTO_AVATAR,
    ) -> None:
        self.cam_w, self.cam_h = tamano_camara
        self.suavizado = suavizado
        self.tamano_palma = tamano_palma
        self.ganancia = ganancia_movimiento
        self._pts: Optional[np.ndarray] = None

    def fijar_tamano_camara(self, ancho: int, alto: int) -> None:
        if ancho > 0 and alto > 0:
            self.cam_w, self.cam_h = ancho, alto

    def reiniciar(self) -> None:
        self._pts = None

    # ------------------------------------------------------------------
    def _suavizar(self, puntos: Sequence[Tuple[float, float]]) -> np.ndarray:
        nuevos = np.asarray(puntos, dtype=float)
        if self._pts is None:
            self._pts = nuevos
        else:
            a = self.suavizado
            self._pts = a * nuevos + (1.0 - a) * self._pts
        return self._pts

    def _a_pantalla(self, pts_norm: np.ndarray, rect: pygame.Rect) -> np.ndarray:
        """Mapea coordenadas de cámara a la zona guía sin deformar la mano."""
        pts = pts_norm * np.array([self.cam_w, self.cam_h], dtype=float)

        palma = float(np.linalg.norm(pts[9] - pts[0])) or 1.0
        escala = (rect.height * self.tamano_palma) / palma

        centro_palma = pts[[0, 5, 9, 13, 17]].mean(axis=0)
        centro_cam = np.array([self.cam_w / 2.0, self.cam_h / 2.0])
        origen = np.array(rect.center, dtype=float)

        out = (
            origen
            + (pts - centro_palma) * escala
            + (centro_palma - centro_cam) * escala * self.ganancia
        )

        # Mantener la mano completa dentro del marco guía
        lim = rect.inflate(-40, -30)
        minimo, maximo = out.min(axis=0), out.max(axis=0)
        ancho, alto = maximo - minimo
        k = min(1.0, lim.width / max(ancho, 1.0), lim.height / max(alto, 1.0))
        if k < 1.0:
            centro = (minimo + maximo) / 2.0
            out = centro + (out - centro) * k
            minimo, maximo = out.min(axis=0), out.max(axis=0)
        dx = dy = 0.0
        if minimo[0] < lim.left:
            dx = lim.left - minimo[0]
        elif maximo[0] > lim.right:
            dx = lim.right - maximo[0]
        if minimo[1] < lim.top:
            dy = lim.top - minimo[1]
        elif maximo[1] > lim.bottom:
            dy = lim.bottom - maximo[1]
        return out + np.array([dx, dy])

    # ------------------------------------------------------------------
    @staticmethod
    def _capsula(sup, color: Color, a, b, grosor: float) -> None:
        a_i = (int(a[0]), int(a[1]))
        b_i = (int(b[0]), int(b[1]))
        g = max(1, int(grosor))
        pygame.draw.line(sup, color, a_i, b_i, g)
        disco(sup, a_i, g / 2, color)
        disco(sup, b_i, g / 2, color)

    def _dibujar_forma(self, sup, color: Color, p, g_dedo: float, g_pulgar: float, radio_palma: float) -> None:
        contorno = [(int(p[i][0]), int(p[i][1])) for i in CONTORNO_PALMA]
        pygame.draw.polygon(sup, color, contorno)
        for i in range(len(CONTORNO_PALMA)):
            self._capsula(
                sup, color, p[CONTORNO_PALMA[i]], p[CONTORNO_PALMA[(i + 1) % len(CONTORNO_PALMA)]], g_dedo
            )
        centro = p[[0, 5, 9, 13, 17]].mean(axis=0)
        disco(sup, (centro[0], centro[1]), radio_palma, color)
        for n, cadena in enumerate(CADENAS_DEDOS):
            g = g_pulgar if n == 0 else g_dedo
            for i in range(len(cadena) - 1):
                self._capsula(sup, color, p[cadena[i]], p[cadena[i + 1]], g)

    def dibujar(
        self,
        superficie,
        rect_guia: pygame.Rect,
        puntos_normalizados: Sequence[Tuple[float, float]],
        dedos_extendidos: List[bool],
    ) -> None:
        if len(puntos_normalizados) != 21:
            return
        pts = self._a_pantalla(self._suavizar(puntos_normalizados), rect_guia)

        ancho_palma = float(np.linalg.norm(pts[5] - pts[17])) or 1.0
        g_dedo = ancho_palma * 0.26
        g_pulgar = ancho_palma * 0.29
        radio_palma = ancho_palma * 0.55
        borde = max(3, int(ancho_palma * 0.035))

        # Pasada 1: silueta (contorno). Pasada 2: piel encima → contorno solo por fuera.
        self._dibujar_forma(
            superficie, CONTORNO, pts, g_dedo + 2 * borde, g_pulgar + 2 * borde, radio_palma + borde
        )
        self._dibujar_forma(superficie, PIEL, pts, g_dedo, g_pulgar, radio_palma)

        # Brillo suave en la palma (como en el mockup)
        c = pts[[0, 5, 9, 13, 17]].mean(axis=0)
        brillo = pygame.Surface((int(ancho_palma * 0.95), int(ancho_palma * 0.42)), pygame.SRCALPHA)
        pygame.draw.ellipse(brillo, (*SOMBRA_PALMA, 150), brillo.get_rect())
        brillo = pygame.transform.rotozoom(brillo, -12, 1.0)
        superficie.blit(brillo, brillo.get_rect(center=(int(c[0]), int(c[1] + ancho_palma * 0.12))))

        # Puntos turquesa solo en las puntas de los dedos extendidos
        for n, lm in enumerate(PUNTAS):
            if n < len(dedos_extendidos) and dedos_extendidos[n]:
                disco(
                    superficie, (pts[lm][0], pts[lm][1]), g_dedo * 0.30,
                    PUNTO_DEDO, BLANCO, max(2, int(g_dedo * 0.09)),
                )


# =============================================================================
# MANO ESTILIZADA (mockups 02, 03, 04)
# =============================================================================
# Geometría en "unidades de palma": palma 230x230, dedos de 46 de ancho (escala 1.0)
_EXTENDIDO_ARRIBA = (-200.0, -235.0, -205.0, -150.0)   # índice, medio, anular, meñique
_DOBLADO_ARRIBA = -28.0
_BASE_DEDO = 110.0


def dibujar_mano_estilizada(
    sup,
    cx: float,
    y_palma: float,
    escala: float,
    dedos: Sequence[bool],
    colores: Optional[Sequence[Optional[Color]]] = None,
    con_puntos: bool = True,
) -> None:
    """
    Dibuja la mano de los mockups. (cx, y_palma) = centro horizontal y borde
    superior de la palma. `dedos` = [pulgar, índice, medio, anular, meñique].
    `colores` permite pintar de otro color (p. ej. naranja de la pista) cada dedo.
    """
    s = escala
    borde = max(2, int(3 * s))
    dedos = list(dedos) + [False] * (5 - len(dedos))
    colores = list(colores) if colores is not None else [None] * 5

    def color_de(i: int) -> Color:
        return colores[i] or PIEL

    # Dedos largos
    puntas: List[Tuple[float, float]] = []
    for i in range(4):
        idx = i + 1
        x_izq = cx + (-101 + 52 * i) * s
        extendido = dedos[idx]
        arriba = y_palma + (_EXTENDIDO_ARRIBA[i] if extendido else _DOBLADO_ARRIBA) * s
        abajo = y_palma + _BASE_DEDO * s
        rect = pygame.Rect(int(x_izq), int(arriba), int(46 * s), int(abajo - arriba))
        caja(sup, rect, color_de(idx), CONTORNO, borde, int(23 * s))
        if extendido:
            puntas.append((x_izq + 23 * s, arriba + 12 * s))

    # Pulgar (solo se dibuja cuando está extendido)
    if dedos[0]:
        elipse_rotada(
            sup, color_de(0), (cx - 150 * s, y_palma + 95 * s), 36 * s, 78 * s, -48, CONTORNO, borde
        )
        puntas.append((cx - 178 * s, y_palma + 30 * s))

    # Palma
    palma = pygame.Rect(int(cx - 115 * s), int(y_palma), int(230 * s), int(230 * s))
    caja(sup, palma, PIEL, CONTORNO, borde, int(70 * s))
    elipse_rotada(sup, SOMBRA_PALMA, (cx - 5 * s, y_palma + 140 * s), 88 * s, 36 * s, -12)

    if con_puntos:
        for (px, py) in puntas:
            disco(sup, (px, py), 14 * s, PUNTO_DEDO, BLANCO, max(2, int(4 * s)))
