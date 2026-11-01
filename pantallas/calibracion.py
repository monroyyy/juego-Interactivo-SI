"""
pantallas/calibracion.py — Vista 02: Conexión y calibración ("Preparando todo").
Verifica el estado del controlador y la cámara web, guiando al niño
a colocar su mano frente al sensor. La cámara física NUNCA se muestra,
solo la mano interactiva ilustrada.
"""

from __future__ import annotations

import math
from typing import Any, Optional, Tuple

import pygame

import config
from componentes import (
    BLANCO,
    TINTA,
    BotonPildora,
    caja,
    dibujar_barra_progreso,
    dibujar_pildora_estado,
    disco,
    poligono,
    puntos_estrella,
    rect_punteado,
    texto,
    trazo,
)
from contexto import Contexto
from mano_avatar import dibujar_mano_estilizada
from pantallas.base import Pantalla


class PantallaCalibracion(Pantalla):
    """Vista 02 — Preparando todo."""

    nombre = "calibracion"
    titulo = "Preparando todo"
    usa_camara = True

    def __init__(self, ctx: Contexto) -> None:
        super().__init__(ctx)
        self.btn_listo = BotonPildora(
            pygame.Rect(740, 810, 440, 110),
            etiqueta="¡Listo!",
            variante="verde",
            tam_fuente=54,
        )
        self.progreso_calibracion = 0.5
        self._t_inicio = 0.0

    def al_entrar(self, **kwargs: Any) -> None:
        import time
        self._t_inicio = time.monotonic()
        self.progreso_calibracion = 0.5
        self.ctx.voz.narrar(
            "Pon tu mano frente a la cámara",
            es_instruccion=True,
            interrumpir=True,
        )

    def manejar_evento(self, ev: Any, pos: Optional[Tuple[int, int]]) -> bool:
        if super().manejar_evento(ev, pos):
            return True

        if self.btn_listo.procesar(ev, pos):
            self.ctx.calibrado = True
            self.ctx.navegar("menu")
            return True

        return False

    def actualizar(self, ahora: float) -> None:
        super().actualizar(ahora)
        self.btn_listo.actualizar(self.ctx.pos_raton)

        if self._t_inicio <= 0:
            self._t_inicio = ahora

        dt = max(0.0, ahora - self._t_inicio)
        # Simular avance suave de calibración o usar señal real de la cámara
        if self.ctx.hay_mano():
            self.progreso_calibracion = min(1.0, max(0.0, self.progreso_calibracion + 0.015))
        else:
            self.progreso_calibracion = min(0.85, max(0.0, 0.5 + 0.35 * (1.0 - math.exp(-(dt / 3.0)))))

    def _dibujar_tarjeta_controlador(self, sup: Any) -> None:
        ventana = self.ctx.ventana
        rect = pygame.Rect(120, 210, 620, 570)
        caja(sup, rect, BLANCO, TINTA, 4, radio=36)
        texto(sup, ventana.fuente(38, True), "Controlador", TINTA, 430, 276)

        # Consola física con 4 botones
        caja(sup, pygame.Rect(200, 320, 460, 200), (237, 231, 216), TINTA, 4, radio=44)

        # Botón 1: Rojo con círculo blanco
        disco(sup, (280, 420), 40, config.COLOR_ROJO, TINTA, 4)
        disco(sup, (280, 420), 17, BLANCO)

        # Botón 2: Azul con cuadrado blanco
        disco(sup, (380, 420), 40, config.COLOR_AZUL, TINTA, 4)
        caja(sup, pygame.Rect(365, 405, 30, 30), BLANCO, radio=3)

        # Botón 3: Amarillo con triángulo tinta
        disco(sup, (480, 420), 40, config.COLOR_AMARILLO, TINTA, 4)
        poligono(sup, [(480, 401), (499, 435), (461, 435)], TINTA)

        # Botón 4: Verde con estrella blanca
        disco(sup, (580, 420), 40, config.COLOR_VERDE, TINTA, 4)
        poligono(sup, puntos_estrella(580, 420, 18), BLANCO)

        # Cable USB estilizado
        trazo(sup, TINTA, [(430, 520), (430, 560), (380, 580), (380, 600)], 8)
        caja(sup, pygame.Rect(356, 596, 48, 34), TINTA, radio=6)

        # Píldora de estado: Conectado
        dibujar_pildora_estado(
            sup, ventana, pygame.Rect(220, 650, 420, 70), "Conectado", config.COLOR_VERDE, con_check=True, tam=38
        )

    def _dibujar_tarjeta_camara(self, sup: Any) -> None:
        ventana = self.ctx.ventana
        rect = pygame.Rect(780, 210, 1020, 570)
        caja(sup, rect, BLANCO, TINTA, 4, radio=36)
        texto(sup, ventana.fuente(38, True), "Cámara", TINTA, 1290, 276)

        # Panel oscuro donde se proyecta la mano (NO se proyecta la cámara real)
        panel = pygame.Rect(820, 306, 940, 330)
        caja(sup, panel, config.COLOR_PANEL_OSCURO, radio=24)

        # Marco guía punteado blanco
        rect_guia = pygame.Rect(1010, 326, 560, 290)
        rect_punteado(sup, BLANCO, rect_guia, radio=18, ancho=5, trazo_px=20, hueco_px=14)

        # Dibujar la mano dentro del visor
        if self.ctx.hay_mano():
            self.ctx.mano.dibujar(
                sup,
                rect_guia,
                self.ctx.deteccion.puntos_normalizados,
                self.ctx.deteccion.dedos_extendidos,
            )
        else:
            # Si no hay mano frente al lente, dibujar la mano de guía del mockup 02
            # 5 dedos extendidos con puntos turquesa
            dibujar_mano_estilizada(
                sup,
                cx=rect_guia.centerx,
                y_palma=rect_guia.top + 140,
                escala=0.68,
                dedos=[True, True, True, True, True],
                con_puntos=True,
            )

        # Texto "Ajustando la luz" y porcentaje
        texto(sup, ventana.fuente(30, True), "Ajustando la luz", TINTA, 1290, 694)
        pct = int(self.progreso_calibracion * 100)
        texto(sup, ventana.fuente(30, True), f"{pct}%", TINTA, 1750, 698, ancla="der")

        # Barra de progreso
        dibujar_barra_progreso(
            sup,
            pygame.Rect(820, 716, 940, 28),
            self.progreso_calibracion,
            config.COLOR_BARRA_FONDO,
            config.COLOR_AZUL,
        )

    def dibujar(self, sup: Any) -> None:
        self.dibujar_fondo(sup)
        self.dibujar_cabecera(sup)

        self._dibujar_tarjeta_controlador(sup)
        self._dibujar_tarjeta_camara(sup)

        # Botón ¡Listo!
        self.btn_listo.dibujar(sup, self.ctx.ventana)

        self.dibujar_narrador(sup)
