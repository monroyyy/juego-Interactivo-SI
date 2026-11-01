"""
pantallas/menu.py — Vista 03: Menú de selección de minijuegos ("¿A qué quieres jugar?").
Ofrece acceso directo a "Los dedos" (Juego 1) y muestra el avance de estrellas
por actividad.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

import pygame

import config
from componentes import (
    BLANCO,
    TINTA,
    Boton,
    caja,
    disco,
    estrella,
    poligono,
    puntos_estrella,
    texto,
)
from contexto import Contexto
from logica import calcular_estrellas_finales
from mano_avatar import dibujar_mano_estilizada
from pantallas.base import Pantalla


class TarjetaJuego(Boton):
    """Tarjeta interactiva de juego (520x600 px)."""

    def __init__(self, rect: pygame.Rect, clave: str, titulo: str) -> None:
        super().__init__(rect)
        self.clave = clave
        self.titulo = titulo

    def dibujar_base(self, sup: Any, ventana: Any, estrellas_activas: int) -> None:
        r = self.hit
        fondo = (248, 250, 255) if self.hover else BLANCO
        caja(sup, r, fondo, TINTA, 4, radio=44)
        texto(sup, ventana.fuente(58, True), self.titulo, TINTA, r.centerx, r.top + 410)

        # 3 estrellas debajo del título
        cx = r.centerx
        cy_estrellas = r.top + 500
        for i in range(3):
            pos_x = cx + (i - 1) * 100
            estrella(sup, pos_x, cy_estrellas, radio=26, activa=(i < estrellas_activas), ancho=4)


class PantallaMenu(Pantalla):
    """Vista 03 — ¿A qué quieres jugar?"""

    nombre = "menu"
    titulo = "¿A qué quieres jugar?"

    def __init__(self, ctx: Contexto) -> None:
        super().__init__(ctx)
        self.tarjetas: List[TarjetaJuego] = [
            TarjetaJuego(pygame.Rect(120, 250, 520, 600), "dedos", "Los dedos"),
            TarjetaJuego(pygame.Rect(700, 250, 520, 600), "colores", "Los colores"),
            TarjetaJuego(pygame.Rect(1280, 250, 520, 600), "letras", "Las letras"),
        ]

    def al_entrar(self, **kwargs: Any) -> None:
        self.ctx.voz.narrar("Elige un juego", es_instruccion=True, interrumpir=True)

    def manejar_evento(self, ev: Any, pos: Optional[Tuple[int, int]]) -> bool:
        if super().manejar_evento(ev, pos):
            return True

        for t in self.tarjetas:
            if t.procesar(ev, pos):
                if t.clave == "dedos":
                    self.ctx.navegar("conteo")
                elif t.clave == "colores":
                    self.ctx.voz.narrar(
                        "¡Próximamente! Por ahora juguemos a contar con los dedos.",
                        es_instruccion=False,
                        interrumpir=True,
                    )
                elif t.clave == "letras":
                    self.ctx.voz.narrar(
                        "¡Las letras vienen muy pronto! Elige los dedos para jugar.",
                        es_instruccion=False,
                        interrumpir=True,
                    )
                return True

        return False

    def actualizar(self, ahora: float) -> None:
        super().actualizar(ahora)
        pos = self.ctx.pos_raton
        for t in self.tarjetas:
            t.actualizar(pos)

    def _dibujar_icono_dedos(self, sup: Any, rect: pygame.Rect) -> None:
        # Mano estilizada mostrando 3 dedos (índice, medio, anular)
        dibujar_mano_estilizada(
            sup,
            cx=rect.centerx,
            y_palma=rect.top + 170,
            escala=0.55,
            dedos=[False, True, True, True, False],
            con_puntos=False,
        )

    def _dibujar_icono_colores(self, sup: Any, rect: pygame.Rect) -> None:
        # 4 fichas redondeadas (2x2)
        cx = rect.centerx
        cy = rect.top + 160
        r_fichas = [
            (pygame.Rect(cx - 132, cy - 72, 120, 120), config.COLOR_ROJO, "circulo"),
            (pygame.Rect(cx + 12, cy - 72, 120, 120), config.COLOR_AZUL, "cuadrado"),
            (pygame.Rect(cx - 132, cy + 72, 120, 120), config.COLOR_AMARILLO, "triangulo"),
            (pygame.Rect(cx + 12, cy + 72, 120, 120), config.COLOR_VERDE, "estrella"),
        ]
        for f_rect, col, forma in r_fichas:
            caja(sup, f_rect, col, radio=24)
            fcx, fcy = f_rect.center
            if forma == "circulo":
                disco(sup, (fcx, fcy), 28, BLANCO)
            elif forma == "cuadrado":
                caja(sup, pygame.Rect(fcx - 25, fcy - 25, 50, 50), BLANCO, radio=4)
            elif forma == "triangulo":
                poligono(sup, [(fcx, fcy - 28), (fcx + 30, fcy + 28), (fcx - 30, fcy + 28)], TINTA)
            elif forma == "estrella":
                poligono(sup, puntos_estrella(fcx, fcy, 28), BLANCO)

    def _dibujar_icono_letras(self, sup: Any, rect: pygame.Rect) -> None:
        ventana = self.ctx.ventana
        cx = rect.centerx
        fuente_letras = ventana.fuente(130, True)
        texto(sup, fuente_letras, "A", config.COLOR_AZUL, cx - 120, rect.top + 190)
        texto(sup, fuente_letras, "E", config.COLOR_AZUL, cx, rect.top + 190)
        texto(sup, fuente_letras, "O", config.COLOR_AZUL, cx + 120, rect.top + 190)
        # Línea de base beige
        caja(sup, pygame.Rect(cx - 170, rect.top + 220, 340, 10), (207, 200, 180), radio=5)

    def dibujar(self, sup: Any) -> None:
        self.dibujar_fondo(sup)
        self.dibujar_cabecera(sup)

        # Consultar estrellas guardadas en sesión para el perfil actual
        estrellas_dedos = 0
        if self.ctx.ultima_partida is not None:
            estrellas_dedos = calcular_estrellas_finales(
                self.ctx.ultima_partida.get("estrellas", [])
            )
        else:
            estrellas_dedos = 2  # Muestra inicial representativa como en el mockup

        for t in self.tarjetas:
            if t.clave == "dedos":
                t.dibujar_base(sup, self.ctx.ventana, estrellas_activas=estrellas_dedos)
                self._dibujar_icono_dedos(sup, t.hit)
            elif t.clave == "colores":
                t.dibujar_base(sup, self.ctx.ventana, estrellas_activas=1)
                self._dibujar_icono_colores(sup, t.hit)
            else:
                t.dibujar_base(sup, self.ctx.ventana, estrellas_activas=0)
                self._dibujar_icono_letras(sup, t.hit)

        self.dibujar_narrador(sup)
