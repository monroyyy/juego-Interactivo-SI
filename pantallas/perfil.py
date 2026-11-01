"""
pantallas/perfil.py — Vista 01: Inicio y selección de perfil.
Permite elegir qué niño va a jugar, paginar entre múltiples perfiles (>4)
y crear nuevos perfiles personalizados mediante un modal accesible.
"""

from __future__ import annotations

import math
import time
from typing import Any, List, Optional, Tuple

import pygame

import config
from componentes import (
    BLANCO,
    TINTA,
    Boton,
    BotonFlecha,
    BotonPildora,
    BotonRedondo,
    caja,
    dibujar_animal,
    disco,
    icono_check,
    poligono,
    rect_punteado,
    texto,
    texto_centrado_vertical,
)
from contexto import Contexto
from pantallas.base import Pantalla
from perfiles import Perfil

_PALETA_MODAL = [
    (245, 158, 123),   # Naranja cálido
    (167, 139, 250),   # Lila morado
    (125, 211, 192),   # Turquesa menta
    (253, 186, 116),   # Naranja pastel
    (249, 168, 212),   # Rosa pastel
]


class TarjetaPerfil(Boton):
    """Tarjeta de selección de niño (380x580 px)."""

    def __init__(self, rect: pygame.Rect, perfil: Optional[Perfil], es_nuevo: bool = False) -> None:
        super().__init__(rect)
        self.perfil = perfil
        self.es_nuevo = es_nuevo

    def dibujar(self, sup: Any, ventana: Any, seleccionado: bool) -> None:
        r = self.hit
        if self.es_nuevo:
            # Tarjeta de agregar nuevo perfil
            caja(sup, r, BLANCO, radio=40)
            rect_punteado(sup, config.COLOR_TEXTO_SUAVE, r, radio=40, ancho=5, trazo_px=20, hueco_px=14)
            # Signo "+" azul #3E63DD
            cx, cy = r.centerx, r.top + 235
            caja(sup, pygame.Rect(cx - 70, cy - 13, 140, 26), config.COLOR_AZUL, radio=13)
            caja(sup, pygame.Rect(cx - 13, cy - 70, 26, 140), config.COLOR_AZUL, radio=13)
            texto(sup, ventana.fuente(56, True), "Nuevo", TINTA, cx, r.top + 472)
            return

        assert self.perfil is not None
        borde_color = config.COLOR_AZUL if seleccionado else TINTA
        borde_ancho = 10 if seleccionado else 4
        caja(sup, r, BLANCO, borde_color, borde_ancho, radio=40)

        # Cara del animalito
        cx = r.centerx
        cy_cara = r.top + 250
        dibujar_animal(sup, self.perfil.animal, cx, cy_cara, self.perfil.color, s=1.0)

        # Nombre del niño
        texto(sup, ventana.fuente(56, True), self.perfil.nombre, TINTA, cx, r.top + 472)

        # Insignia de selección activa (círculo azul con check blanco en la esquina)
        if seleccionado:
            disco(sup, (r.right - 50, r.top + 50), 36, config.COLOR_AZUL)
            icono_check(sup, r.right - 50, r.top + 52, 0.4, BLANCO)


class PantallaPerfil(Pantalla):
    """Vista 01 — ¿Quién va a jugar?"""

    nombre = "perfil"
    titulo = "¿Quién va a jugar?"

    def __init__(self, ctx: Contexto) -> None:
        super().__init__(ctx)
        self.btn_adultos = BotonRedondo((1688, 112), "candado", "Adultos")
        self.botones_cabecera.append(self.btn_adultos)

        # Paginación
        self.pagina_actual = 0
        self.total_paginas = 1
        self.tarjetas: List[TarjetaPerfil] = []
        self.btn_anterior = BotonFlecha((64, 540), direccion="izq", radio=44)
        self.btn_siguiente = BotonFlecha((1856, 540), direccion="der", radio=44)

        # Modal para crear nuevo perfil
        self.modal_abierto = False
        self.nombre_input = ""
        self.animal_seleccionado = "gato"
        self.color_seleccionado = _PALETA_MODAL[0]
        self.cursor_visible = True
        self._ultimo_parpadeo = 0.0

        self.btn_modal_cancelar = BotonPildora(
            pygame.Rect(580, 730, 350, 80),
            etiqueta="Cancelar",
            variante="borde",
            tam_fuente=32,
        )
        self.btn_modal_guardar = BotonPildora(
            pygame.Rect(990, 730, 350, 80),
            etiqueta="¡Guardar!",
            variante="verde",
            tam_fuente=32,
        )

        self._construir_tarjetas()

    def _construir_tarjetas(self) -> None:
        self.tarjetas.clear()
        perfiles = self.ctx.perfiles.perfiles
        items: List[Optional[Perfil]] = list(perfiles)
        if self.ctx.perfiles.puede_agregar:
            items.append(None)  # None representa la tarjeta "Nuevo" (+)

        total_items = len(items)
        self.total_paginas = max(1, (total_items + 3) // 4)
        self.pagina_actual = max(0, min(self.pagina_actual, self.total_paginas - 1))

        xs = [128, 556, 984, 1412]
        inicio = self.pagina_actual * 4
        fin = min(total_items, inicio + 4)

        for i in range(inicio, fin):
            slot = i - inicio
            rect = pygame.Rect(xs[slot], 250, 380, 580)
            item = items[i]
            if item is None:
                self.tarjetas.append(TarjetaPerfil(rect, None, es_nuevo=True))
            else:
                self.tarjetas.append(TarjetaPerfil(rect, item, es_nuevo=False))

    def al_entrar(self, **kwargs: Any) -> None:
        self._construir_tarjetas()
        self.modal_abierto = False
        self.ctx.voz.narrar("Hola, ¿quién va a jugar?", es_instruccion=True, interrumpir=True)

    def _guardar_nuevo_perfil(self) -> None:
        nuevo = self.ctx.perfiles.crear_perfil(
            nombre=self.nombre_input,
            animal=self.animal_seleccionado,
            color=self.color_seleccionado,
        )
        self.ctx.perfil = nuevo
        self.modal_abierto = False

        # Desplazar a la página que contiene al nuevo perfil creado
        idx = len(self.ctx.perfiles.perfiles) - 1
        self.pagina_actual = idx // 4
        self._construir_tarjetas()
        self.ctx.voz.narrar(f"¡Bienvenido {nuevo.nombre}!", es_instruccion=False, interrumpir=True)

    def manejar_evento(self, ev: Any, pos: Optional[Tuple[int, int]]) -> bool:
        # Si el modal está abierto, todos los eventos pertenecen al modal
        if self.modal_abierto:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.modal_abierto = False
                    return True
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._guardar_nuevo_perfil()
                    return True
                elif ev.key == pygame.K_BACKSPACE:
                    self.nombre_input = self.nombre_input[:-1]
                    return True
                elif ev.unicode:
                    char = ev.unicode
                    # Permitir letras, espacios, números y caracteres acentuados
                    if len(self.nombre_input) < 12 and (char.isalnum() or char in " -_áéíóúÁÉÍÓÚñÑ"):
                        self.nombre_input += char
                    return True

            if self.btn_modal_cancelar.procesar(ev, pos):
                self.modal_abierto = False
                return True

            if self.btn_modal_guardar.procesar(ev, pos):
                self._guardar_nuevo_perfil()
                return True

            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and pos:
                # Opciones de animales
                animales = [
                    ("gato", pygame.Rect(570, 420, 230, 150)),
                    ("oso", pygame.Rect(845, 420, 230, 150)),
                    ("conejo", pygame.Rect(1120, 420, 230, 150)),
                ]
                for ani, r_ani in animales:
                    if r_ani.collidepoint(pos):
                        self.animal_seleccionado = ani
                        return True

                # Opciones de colores
                xs_col = [740, 850, 960, 1070, 1180]
                for c_center_x, c_val in zip(xs_col, _PALETA_MODAL):
                    if math.hypot(pos[0] - c_center_x, pos[1] - 645) <= 32:
                        self.color_seleccionado = c_val
                        return True

            return True

        # Flujo normal de eventos (sin modal)
        if super().manejar_evento(ev, pos):
            return True

        if self.btn_adultos.procesar(ev, pos):
            self.ctx.navegar("adultos")
            return True

        # Flechas de paginación
        if self.pagina_actual > 0 and self.btn_anterior.procesar(ev, pos):
            self.pagina_actual -= 1
            self._construir_tarjetas()
            return True

        if self.pagina_actual < self.total_paginas - 1 and self.btn_siguiente.procesar(ev, pos):
            self.pagina_actual += 1
            self._construir_tarjetas()
            return True

        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_LEFT and self.pagina_actual > 0:
                self.pagina_actual -= 1
                self._construir_tarjetas()
                return True
            elif ev.key == pygame.K_RIGHT and self.pagina_actual < self.total_paginas - 1:
                self.pagina_actual += 1
                self._construir_tarjetas()
                return True

        for tarjeta in self.tarjetas:
            if tarjeta.procesar(ev, pos):
                if tarjeta.es_nuevo:
                    if self.ctx.perfiles.puede_agregar:
                        self.modal_abierto = True
                        self.nombre_input = ""
                        self.animal_seleccionado = "gato"
                        self.color_seleccionado = _PALETA_MODAL[len(self.ctx.perfiles.perfiles) % len(_PALETA_MODAL)]
                        self.ctx.voz.narrar(
                            "Escribe tu nombre y elige tu personaje",
                            es_instruccion=True,
                            interrumpir=True,
                        )
                elif tarjeta.perfil is not None:
                    self.ctx.perfil = tarjeta.perfil
                    self.ctx.voz.narrar(f"¡Hola {tarjeta.perfil.nombre}!", es_instruccion=False, interrumpir=True)
                    if not self.ctx.calibrado:
                        self.ctx.navegar("calibracion")
                    else:
                        self.ctx.navegar("menu")
                return True

        return False

    def actualizar(self, ahora: float) -> None:
        super().actualizar(ahora)
        pos = self.ctx.pos_raton

        if self.modal_abierto:
            self.btn_modal_cancelar.actualizar(pos)
            self.btn_modal_guardar.actualizar(pos)
            if ahora - self._ultimo_parpadeo > 0.5:
                self.cursor_visible = not self.cursor_visible
                self._ultimo_parpadeo = ahora
            return

        for tarjeta in self.tarjetas:
            tarjeta.actualizar(pos)

        if self.pagina_actual > 0:
            self.btn_anterior.actualizar(pos)
        if self.pagina_actual < self.total_paginas - 1:
            self.btn_siguiente.actualizar(pos)

    def _dibujar_modal(self, sup: Any) -> None:
        ventana = self.ctx.ventana

        # Sombra / fondo atenuado
        velo = pygame.Surface((1920, 1080), pygame.SRCALPHA)
        velo.fill((20, 28, 48, 175))
        sup.blit(velo, (0, 0))

        # Tarjeta central del modal
        rect_modal = pygame.Rect(460, 130, 1000, 780)
        caja(sup, rect_modal, BLANCO, TINTA, 4, radio=40)

        # Encabezado
        texto(sup, ventana.fuente(44, True), "¿Cómo te llamas?", TINTA, 960, 195)
        texto(sup, ventana.fuente(24, False), "Escribe tu nombre y elige tu personaje", config.COLOR_TEXTO_SUAVE, 960, 240)

        # Campo de entrada de texto
        rect_input = pygame.Rect(560, 275, 800, 76)
        caja(sup, rect_input, (244, 246, 252), config.COLOR_AZUL, 3, radio=20)

        fuente_input = ventana.fuente(36, True)
        if self.nombre_input:
            cursor_str = "|" if self.cursor_visible else ""
            texto(sup, fuente_input, self.nombre_input + cursor_str, TINTA, 590, 326, ancla="izq")
        else:
            texto(sup, ventana.fuente(30, False), "Escribe el nombre aquí...", (160, 170, 195), 590, 324, ancla="izq")
            if self.cursor_visible:
                texto(sup, fuente_input, "|", config.COLOR_AZUL, 590, 326, ancla="izq")

        # Sección de animales
        texto(sup, ventana.fuente(24, True), "Elige tu personaje:", TINTA, 960, 395)
        animales = [
            ("gato", "Gatito", pygame.Rect(570, 420, 230, 150)),
            ("oso", "Osito", pygame.Rect(845, 420, 230, 150)),
            ("conejo", "Conejito", pygame.Rect(1120, 420, 230, 150)),
        ]
        for clave_ani, etiqueta_ani, r_ani in animales:
            sel = (self.animal_seleccionado == clave_ani)
            borde = config.COLOR_AZUL if sel else (210, 218, 235)
            ancho_borde = 6 if sel else 3
            caja(sup, r_ani, BLANCO, borde, ancho_borde, radio=24)
            dibujar_animal(sup, clave_ani, r_ani.centerx, r_ani.top + 70, self.color_seleccionado, s=0.46)
            texto(sup, ventana.fuente(26, True), etiqueta_ani, TINTA, r_ani.centerx, r_ani.bottom - 12)
            if sel:
                disco(sup, (r_ani.right - 24, r_ani.top + 24), 18, config.COLOR_AZUL)
                icono_check(sup, r_ani.right - 24, r_ani.top + 25, 0.22, BLANCO)

        # Sección de colores
        texto(sup, ventana.fuente(24, True), "Elige tu color:", TINTA, 960, 615)
        xs_col = [740, 850, 960, 1070, 1180]
        y_col = 650
        for cx_c, col in zip(xs_col, _PALETA_MODAL):
            sel_col = (self.color_seleccionado == col)
            disco(sup, (cx_c, y_col), 28, col, TINTA, 3)
            if sel_col:
                disco(sup, (cx_c, y_col), 34, config.COLOR_AZUL, ancho=4)
                disco(sup, (cx_c, y_col), 12, BLANCO)

        # Botones Cancelar y Guardar
        self.btn_modal_cancelar.dibujar(sup, ventana)
        self.btn_modal_guardar.dibujar(sup, ventana)

    def dibujar(self, sup: Any) -> None:
        self.dibujar_fondo(sup)
        self.dibujar_cabecera(sup)

        perfil_actual = self.ctx.perfil
        for tarjeta in self.tarjetas:
            seleccionado = (
                not tarjeta.es_nuevo
                and tarjeta.perfil is not None
                and tarjeta.perfil.nombre == perfil_actual.nombre
            )
            tarjeta.dibujar(sup, self.ctx.ventana, seleccionado)

        # Flechas táctiles de paginación
        if self.pagina_actual > 0:
            self.btn_anterior.dibujar(sup)
        if self.pagina_actual < self.total_paginas - 1:
            self.btn_siguiente.dibujar(sup)

        # Indicador de puntos de página si hay más de 1 página
        if self.total_paginas > 1:
            espacio_dot = 32
            ancho_total = (self.total_paginas - 1) * espacio_dot
            x_ini = 960 - ancho_total / 2
            y_dot = 868
            for p in range(self.total_paginas):
                xd = x_ini + p * espacio_dot
                if p == self.pagina_actual:
                    caja(sup, pygame.Rect(int(xd - 16), int(y_dot - 7), 32, 14), config.COLOR_AZUL, radio=7)
                else:
                    disco(sup, (int(xd), int(y_dot)), 6, (195, 205, 225))

        self.dibujar_narrador(sup)

        # Dibujar modal superpuesto si está activo
        if self.modal_abierto:
            self._dibujar_modal(sup)
