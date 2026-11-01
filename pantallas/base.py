"""
pantallas/base.py — Clase base de las pantallas (encabezado del mockup + ciclo de vida).
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

import pygame

import config
from componentes import BotonRedondo, TINTA, dibujar_burbuja_narrador, fuente_que_cabe, texto
from contexto import Contexto


class Pantalla:
    """Cada vista del mockup es una subclase con estos métodos."""

    nombre = "base"
    titulo = ""
    usa_camara = False  # True si necesita detectar la mano en cada fotograma

    def __init__(self, ctx: Contexto) -> None:
        self.ctx = ctx
        self.btn_inicio = BotonRedondo((112, 112), "casa", "Inicio")
        self.btn_escuchar = BotonRedondo((1808, 112), "bocina", "Escuchar")
        self.botones_cabecera: List[BotonRedondo] = [self.btn_inicio, self.btn_escuchar]

    # --- ciclo de vida -------------------------------------------------
    def al_entrar(self, **kwargs: Any) -> None:
        """Se llama cada vez que la pantalla pasa a estar activa."""

    def al_salir(self) -> None:
        """Se llama al abandonar la pantalla."""

    # --- eventos / lógica / dibujo --------------------------------------
    def manejar_evento(self, ev: Any, pos: Optional[Tuple[int, int]]) -> bool:
        """Procesa un evento. `pos` = posición lógica (1920x1080) para eventos de ratón."""
        if self.btn_inicio.procesar(ev, pos):
            self.ctx.navegar("perfil")
            return True
        if self.btn_escuchar.procesar(ev, pos):
            self.ctx.voz.repetir_instruccion()
            return True
        return False

    def actualizar(self, ahora: float) -> None:
        for b in self.botones_cabecera:
            b.actualizar(self.ctx.pos_raton)

    def dibujar(self, sup: Any) -> None:
        raise NotImplementedError

    # --- utilidades de dibujo -------------------------------------------
    def dibujar_fondo(self, sup: Any) -> None:
        sup.fill(config.COLOR_FONDO)

    def dibujar_cabecera(
        self, sup: Any, titulo: Optional[str] = None, color: Tuple[int, int, int] = TINTA,
        tam: int = 64, base_y: int = 140,
    ) -> None:
        ventana = self.ctx.ventana
        cadena = self.titulo if titulo is None else titulo
        fuente = fuente_que_cabe(ventana, cadena, tam, 1250, True, 36)
        texto(sup, fuente, cadena, color, 960, base_y)
        for b in self.botones_cabecera:
            b.dibujar(sup, ventana)

    def dibujar_narrador(self, sup: Any) -> None:
        dibujar_burbuja_narrador(sup, self.ctx.ventana, self.ctx.voz.texto_actual)
