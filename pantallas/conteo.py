"""
pantallas/conteo.py — Vista 04: Conteo con los dedos (Juego 1).
La cámara NUNCA se muestra: se detecta la mano con MediaPipe (o teclas 0-5)
y se renderiza exclusivamente la mano ilustrada dentro del marco guía.
"""

from __future__ import annotations

import math
import random
import time
from typing import Any, List, Optional, Tuple

import pygame

import config
from componentes import (
    BLANCO,
    TINTA,
    caja,
    dibujar_pildora_estado,
    disco,
    fuente_que_cabe,
    rect_punteado,
    texto,
    texto_centrado_vertical,
)
from contexto import Contexto
from logica import (
    calcular_estrellas_ronda,
    construir_puntos_simulados,
    generar_secuencia_rondas,
)
from mano_avatar import dibujar_mano_estilizada
from pantallas.base import Pantalla
from sesion import GestorSesion


class PantallaConteo(Pantalla):
    """Vista 04 — Cuenta con tus dedos."""

    nombre = "conteo"
    titulo = "Cuenta con tus dedos"
    usa_camara = True

    ESTADO_JUGANDO = "JUGANDO"
    ESTADO_CELEBRANDO = "CELEBRANDO"

    def __init__(self, ctx: Contexto) -> None:
        super().__init__(ctx)
        self.gestor_sesion = GestorSesion(perfil=ctx.perfil.nombre)
        self.estado = self.ESTADO_JUGANDO

        # Estado de la partida
        self.secuencia: List[int] = []
        self.estrellas_por_ronda: List[int] = []
        self.indice_ronda: int = 0

        # Temporizadores de ronda
        self.t_inicio_ronda: float = 0.0
        self.t_inicio_acierto: Optional[float] = None
        self.t_inicio_error: Optional[float] = None
        self.ultimo_conteo_error: int = -1
        self.t_ultimo_animo: float = 0.0
        self.t_fin_celebracion: float = 0.0
        self.intentos_fallidos: int = 0
        self.pista_activada: bool = False
        self.progreso_estabilidad: float = 0.0

    @property
    def numero_objetivo(self) -> int:
        if 0 <= self.indice_ronda < len(self.secuencia):
            return self.secuencia[self.indice_ronda]
        return 1

    def al_entrar(self, **kwargs: Any) -> None:
        self.gestor_sesion.perfil = self.ctx.perfil.nombre
        self.iniciar_partida()

    def iniciar_partida(self) -> None:
        self.secuencia = generar_secuencia_rondas(config.TOTAL_RONDAS)
        self.estrellas_por_ronda = []
        self.indice_ronda = 0
        self.estado = self.ESTADO_JUGANDO
        self.gestor_sesion.iniciar_nueva_sesion()
        self._preparar_ronda()

    def _preparar_ronda(self) -> None:
        self.ctx.detector.reiniciar()
        self.ctx.mano.reiniciar()
        self.ctx.dedos_simulados = None

        self.t_inicio_ronda = time.monotonic()
        self.t_inicio_acierto = None
        self.t_inicio_error = None
        self.ultimo_conteo_error = -1
        self.t_ultimo_animo = self.t_inicio_ronda
        self.intentos_fallidos = 0
        self.pista_activada = False
        self.progreso_estabilidad = 0.0

        objetivo = self.numero_objetivo
        palabra = "dedo" if objetivo == 1 else "dedos"
        instruccion = f"Muestra {objetivo} {palabra}"
        self.ctx.voz.narrar(instruccion, es_instruccion=True, interrumpir=True)

    def manejar_evento(self, ev: Any, pos: Optional[Tuple[int, int]]) -> bool:
        if super().manejar_evento(ev, pos):
            return True

        if ev.type == pygame.KEYDOWN:
            # Teclas 0 a 5 para simulación directa si no hay cámara física
            if ev.key in (pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                self.ctx.dedos_simulados = int(ev.unicode)
                return True

        return False

    def actualizar(self, ahora: float) -> None:
        super().actualizar(ahora)

        if self.estado == self.ESTADO_CELEBRANDO:
            if ahora >= self.t_fin_celebracion:
                self._avanzar_ronda()
            return

        # Evaluación en vivo durante el juego
        tiempo_ronda = ahora - self.t_inicio_ronda
        objetivo = self.numero_objetivo

        # Activar pista visual a los 12 segundos si aún no ha acertado
        if not self.pista_activada and tiempo_ronda >= config.TIEMPO_ACTIVAR_PISTA_SEG:
            self.pista_activada = True
            palabra = "dedo" if objetivo == 1 else "dedos"
            self.ctx.voz.narrar(
                f"Mira la pista en pantalla. Pon {objetivo} {palabra}.",
                es_instruccion=False,
                interrumpir=False,
            )

        conteo_actual = self.ctx.deteccion.conteo_estabilizado if self.ctx.hay_mano() else 0

        # Caso 1: El niño muestra el número objetivo
        if self.ctx.hay_mano() and conteo_actual == objetivo:
            self.t_inicio_error = None
            if self.t_inicio_acierto is None:
                self.t_inicio_acierto = ahora

            tiempo_mantenido = ahora - self.t_inicio_acierto
            self.progreso_estabilidad = min(1.0, tiempo_mantenido / config.TIEMPO_ESTABLE_ACIERTO_SEG)

            if tiempo_mantenido >= config.TIEMPO_ESTABLE_ACIERTO_SEG:
                self._completar_ronda(tiempo_ronda, ahora)
            return

        # Si cambió el número, reiniciar el tiempo de acierto
        self.t_inicio_acierto = None
        self.progreso_estabilidad = 0.0

        # Caso 2: El niño muestra otro número de dedos (> 0 y != objetivo)
        if self.ctx.hay_mano() and conteo_actual > 0 and conteo_actual != objetivo:
            if self.t_inicio_error is None or self.ultimo_conteo_error != conteo_actual:
                self.t_inicio_error = ahora
                self.ultimo_conteo_error = conteo_actual
            else:
                duracion_error = ahora - self.t_inicio_error
                if (
                    duracion_error >= config.TIEMPO_SOSTENIDO_INTENTO_ERRONEO_SEG
                    and (ahora - self.t_ultimo_animo) >= config.ENFRIAMIENTO_MENSAJE_ANIMO_SEG
                ):
                    self.intentos_fallidos += 1
                    self.t_ultimo_animo = ahora
                    self.t_inicio_error = ahora
                    frase = random.choice(config.FRASES_ANIMO)
                    self.ctx.voz.narrar(frase, es_instruccion=False, interrumpir=False)
        else:
            self.t_inicio_error = None
            if not self.ctx.hay_mano() and (ahora - self.t_ultimo_animo) >= config.TIEMPO_RECORDATORIO_SIN_MANO_SEG:
                self.t_ultimo_animo = ahora
                self.ctx.voz.narrar(
                    "Casi, inténtalo otra vez. Pon tu manita frente a la cámara.",
                    es_instruccion=False,
                    interrumpir=False,
                )

    def _completar_ronda(self, tiempo_ronda: float, ahora: float) -> None:
        objetivo = self.numero_objetivo
        estrellas = calcular_estrellas_ronda(
            tiempo_respuesta_seg=tiempo_ronda,
            intentos_fallidos=self.intentos_fallidos,
            uso_pista=self.pista_activada,
        )
        self.estrellas_por_ronda.append(estrellas)

        intentos_totales = self.intentos_fallidos + 1
        self.gestor_sesion.registrar_ronda(
            numero_ronda=self.indice_ronda + 1,
            numero_pedido=objetivo,
            numero_detectado=objetivo,
            aciertos=1,
            intentos=intentos_totales,
            tiempo_respuesta_seg=tiempo_ronda,
            estrellas=estrellas,
            uso_pista=self.pista_activada,
        )

        frase = config.FRASES_EXITO[self.indice_ronda % len(config.FRASES_EXITO)]
        self.ctx.voz.narrar(frase, es_instruccion=False, interrumpir=True)

        self.estado = self.ESTADO_CELEBRANDO
        self.t_fin_celebracion = ahora + config.TIEMPO_CELEBRACION_RONDA_SEG

    def _avanzar_ronda(self) -> None:
        self.indice_ronda += 1
        if self.indice_ronda < config.TOTAL_RONDAS:
            self.estado = self.ESTADO_JUGANDO
            self._preparar_ronda()
        else:
            # Fin de la partida: guardar y navegar a la pantalla de resultados
            sesion_guardada = self.gestor_sesion.finalizar_sesion()
            self.ctx.ultima_partida = {
                "estrellas": list(self.estrellas_por_ronda),
                "numeros": list(self.secuencia),
                "total_estrellas": sum(self.estrellas_por_ronda),
                "sesion": sesion_guardada,
            }
            self.ctx.navegar("resultado")

    # ------------------------------------------------------------------
    # DIBUJO DE PANTALLA
    # ------------------------------------------------------------------
    def _dibujar_tarjeta_reto(self, sup: Any) -> None:
        ventana = self.ctx.ventana
        rect = pygame.Rect(120, 210, 580, 690)
        caja(sup, rect, BLANCO, TINTA, 4, radio=40)

        # "Muestra este número"
        texto(sup, ventana.fuente(40, True), "Muestra este número", TINTA, 410, 290)

        # Círculo azul claro central
        cx, cy = 410, 560
        disco(sup, (cx, cy), 210, config.COLOR_CIRCULO_CLARO)

        # Arco o anillo de progreso cuando mantiene el número correcto
        if self.progreso_estabilidad > 0.01:
            radio_halo = 222
            rect_arco = pygame.Rect(cx - radio_halo, cy - radio_halo, radio_halo * 2, radio_halo * 2)
            ang_inicio = math.pi / 2
            ang_fin = ang_inicio + (2 * math.pi * min(1.0, self.progreso_estabilidad))
            pygame.draw.arc(sup, config.COLOR_VERDE, rect_arco, ang_inicio, ang_fin, width=16)

        # Número gigante (1 a 5) en azul #3E63DD
        fuente_num = ventana.fuente(400, True)
        texto_centrado_vertical(sup, fuente_num, str(self.numero_objetivo), config.COLOR_AZUL, cx, cy, 380)

        # "Ronda X de 5"
        texto(
            sup,
            ventana.fuente(32, True),
            f"Ronda {self.indice_ronda + 1} de {config.TOTAL_RONDAS}",
            config.COLOR_TEXTO_SUAVE,
            410,
            852,
        )

    def _dibujar_panel_mano(self, sup: Any) -> None:
        ventana = self.ctx.ventana
        # Panel oscuro plano (sin cámara real)
        rect_panel = pygame.Rect(740, 210, 1060, 690)
        caja(sup, rect_panel, config.COLOR_PANEL_OSCURO, radio=40)

        # Marco guía punteado blanco
        rect_guia = pygame.Rect(940, 240, 660, 520)
        rect_punteado(sup, BLANCO, rect_guia, radio=24, ancho=6, trazo_px=24, hueco_px=16)

        # Mano interactiva ilustrada dentro del marco
        if self.ctx.hay_mano():
            self.ctx.mano.dibujar(
                sup,
                rect_guia,
                self.ctx.deteccion.puntos_normalizados,
                self.ctx.deteccion.dedos_extendidos,
            )
        else:
            self.ctx.mano.reiniciar()
            # Si no hay mano frente a la cámara, sugerir colocarla
            fuente_aviso = ventana.fuente(34, True)
            texto_centrado_vertical(
                sup,
                fuente_aviso,
                "Pon tu manita aquí",
                (200, 210, 235),
                rect_guia.centerx,
                rect_guia.centery + 140,
                34,
            )
            # Dibujar silueta de mano reposada tenue
            dibujar_mano_estilizada(
                sup,
                cx=rect_guia.centerx,
                y_palma=rect_guia.top + 160,
                escala=0.62,
                dedos=[False, True, True, True, False],
                con_puntos=False,
            )

        # Pista animada a los 12 segundos (silueta en la esquina inferior del panel)
        if self.pista_activada:
            self._dibujar_pista_en_panel(sup, rect_panel)

        # Etiqueta inferior "Veo X dedos" con checkmark
        conteo = self.ctx.deteccion.conteo_estabilizado if self.ctx.hay_mano() else 0
        palabra = "dedo" if conteo == 1 else "dedos"
        cadena_veo = f"Veo {conteo} {palabra}"
        dibujar_pildora_estado(
            sup,
            ventana,
            pygame.Rect(1020, 794, 500, 76),
            cadena_veo,
            config.COLOR_VERDE,
            con_check=True,
            tam=38,
        )

    def _dibujar_pista_en_panel(self, sup: Any, rect_panel: pygame.Rect) -> None:
        """Dibuja una pequeña mano de guía mostrando los dedos sugeridos."""
        t = pygame.time.get_ticks() / 1000.0
        pulso = 0.5 + 0.5 * math.sin(t * 6.0)

        # Dónde poner la minitarjeta de pista
        r_pista = pygame.Rect(rect_panel.right - 260, rect_panel.top + 30, 230, 220)
        caja(sup, r_pista, (255, 252, 242), config.COLOR_NARANJA_PISTA, ancho=4, radio=24)
        texto(sup, self.ctx.ventana.fuente(24, True), "¡Pista!", config.COLOR_NARANJA_PISTA, r_pista.centerx, r_pista.top + 28)

        obj = self.numero_objetivo
        # Sugerencia de qué dedos levantar
        dedos_sugeridos = [
            obj >= 5,  # Pulgar
            obj >= 1,  # Índice
            obj >= 2,  # Medio
            obj >= 3,  # Anular
            obj >= 4,  # Meñique
        ]
        colores_dedo = [
            config.COLOR_NARANJA_PISTA if d else None for d in dedos_sugeridos
        ]
        dibujar_mano_estilizada(
            sup,
            cx=r_pista.centerx,
            y_palma=r_pista.top + 105,
            escala=0.40,
            dedos=dedos_sugeridos,
            colores=colores_dedo,
            con_puntos=True,
        )

    def dibujar(self, sup: Any) -> None:
        self.dibujar_fondo(sup)
        self.dibujar_cabecera(sup)

        self._dibujar_tarjeta_reto(sup)
        self._dibujar_panel_mano(sup)

        self.dibujar_narrador(sup)
