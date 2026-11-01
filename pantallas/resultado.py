"""
pantallas/resultado.py — Vista 07: Resultado de la actividad ("¡Muy bien!").
Muestra la celebración con confeti de formas, 3 estrellas principales,
la mascota del búho interactiva y botones grandes "Otra vez" y "Siguiente".
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

import pygame

import config
from componentes import (
    BotonPildora,
    dibujar_buho,
    dibujar_confeti,
    estrella,
    texto,
)
from contexto import Contexto
from logica import calcular_estrellas_finales
from pantallas.base import Pantalla


class PantallaResultado(Pantalla):
    """Vista 07 — Resultado de la actividad."""

    nombre = "resultado"
    titulo = "¡Muy bien!"

    def __init__(self, ctx: Contexto) -> None:
        super().__init__(ctx)
        self.btn_otra_vez = BotonPildora(
            pygame.Rect(560, 750, 380, 120),
            etiqueta="Otra vez",
            variante="borde",
            nombre_icono="repetir",
            icono_a_la_izquierda=True,
            tam_fuente=46,
        )
        self.btn_siguiente = BotonPildora(
            pygame.Rect(980, 750, 380, 120),
            etiqueta="Siguiente",
            variante="verde",
            nombre_icono="siguiente",
            icono_a_la_izquierda=False,
            tam_fuente=46,
        )
        self.estrellas_finales = 3
        self.total_estrellas_partida = 15

    def al_entrar(self, **kwargs: Any) -> None:
        partida = self.ctx.ultima_partida or {}
        estrellas_rondas = partida.get("estrellas", [3, 3, 3, 3, 3])
        self.estrellas_finales = calcular_estrellas_finales(estrellas_rondas)
        self.total_estrellas_partida = sum(estrellas_rondas)

        palabra = "estrella" if self.estrellas_finales == 1 else "estrellas"
        mensaje = f"¡Lo lograste! Ganaste {self.estrellas_finales} {palabra}"
        self.ctx.voz.narrar(mensaje, es_instruccion=True, interrumpir=True)

    def manejar_evento(self, ev: Any, pos: Optional[Tuple[int, int]]) -> bool:
        if super().manejar_evento(ev, pos):
            return True

        if self.btn_otra_vez.procesar(ev, pos):
            self.ctx.navegar("conteo")
            return True

        if self.btn_siguiente.procesar(ev, pos):
            self.ctx.navegar("menu")
            return True

        return False

    def actualizar(self, ahora: float) -> None:
        super().actualizar(ahora)
        pos = self.ctx.pos_raton
        self.btn_otra_vez.actualizar(pos)
        self.btn_siguiente.actualizar(pos)

    def dibujar(self, sup: Any) -> None:
        self.dibujar_fondo(sup)
        t = pygame.time.get_ticks() / 1000.0

        # Confeti animado de formas
        dibujar_confeti(sup, t)

        # Encabezado con título gigante "¡Muy bien!" en verde
        self.dibujar_cabecera(
            sup,
            titulo="¡Muy bien!",
            color=config.COLOR_VERDE,
            tam=110,
            base_y=150,
        )

        # 3 grandes estrellas (Mockup 07: centros en x=760, 960, 1160; y=293)
        posiciones_x = [760, 960, 1160]
        for i, cx in enumerate(posiciones_x):
            activa = i < self.estrellas_finales
            estrella(sup, cx, 293, radio=68, activa=activa, ancho=6)

        # Mascota del búho en el centro
        dibujar_buho(sup, cx=960, cy=540, escala=1.0, t=t)

        # Botones "Otra vez" y "Siguiente"
        self.btn_otra_vez.dibujar(sup, self.ctx.ventana)
        self.btn_siguiente.dibujar(sup, self.ctx.ventana)

        self.dibujar_narrador(sup)
