"""
juego_dedos.py — Aplicación principal y máquina de pantallas del sistema educativo
"Cuenta con tus dedos" (4 a 6 años), basada en los mockups de Figma.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Dict, Optional

try:
    import pygame
    PYGAME_DISPONIBLE = True
except Exception:
    pygame = None  # type: ignore
    PYGAME_DISPONIBLE = False

import config
from camara import GestorCamara
from contexto import Contexto
from detector_dedos import DetectorDedos
from interfaz import Ventana
from logica import (
    calcular_estrellas_finales,
    calcular_estrellas_ronda,
    construir_puntos_simulados,
    generar_secuencia_rondas,
)
from pantallas.adultos import PantallaAdultos
from pantallas.base import Pantalla
from pantallas.calibracion import PantallaCalibracion
from pantallas.conteo import PantallaConteo
from pantallas.menu import PantallaMenu
from pantallas.perfil import PantallaPerfil
from pantallas.resultado import PantallaResultado
from perfiles import AlmacenPerfiles
from voz import NarradorVoz


class AplicacionJuego:
    """Controlador principal de la ventana, cámara, detector y flujo de pantallas."""

    def __init__(
        self,
        pantalla_inicial: str = "perfil",
        perfil_nombre: Optional[str] = None,
        indice_camara: int = config.INDICE_CAMARA_DEFECTO,
        pantalla_completa: bool = config.PANTALLA_COMPLETA_INICIAL,
    ) -> None:
        if not PYGAME_DISPONIBLE or pygame is None:
            raise RuntimeError("Pygame no está instalado. Ejecuta: pip install -r requirements.txt")

        pygame.init()
        self.reloj = pygame.time.Clock()
        self.ejecutando = True

        # Subsistemas
        self.ventana = Ventana(pantalla_completa=pantalla_completa)
        self.camara = GestorCamara(indice_camara=indice_camara)
        self.detector = DetectorDedos()
        self.voz = NarradorVoz()
        self.almacen_perfiles = AlmacenPerfiles()

        # Contexto compartido
        self.ctx = Contexto(
            ventana=self.ventana,
            camara=self.camara,
            detector=self.detector,
            voz=self.voz,
            perfiles=self.almacen_perfiles,
        )
        self.ctx._navegar = self.cambiar_pantalla

        # Configurar perfil si se pasó por argumento
        if perfil_nombre:
            for p in self.almacen_perfiles.perfiles:
                if p.nombre.lower() == perfil_nombre.lower():
                    self.ctx.perfil = p
                    break

        # Instanciar las 6 pantallas del diseño
        self.pantallas: Dict[str, Pantalla] = {
            "perfil": PantallaPerfil(self.ctx),
            "calibracion": PantallaCalibracion(self.ctx),
            "menu": PantallaMenu(self.ctx),
            "conteo": PantallaConteo(self.ctx),
            "resultado": PantallaResultado(self.ctx),
            "adultos": PantallaAdultos(self.ctx),
        }

        self.pantalla_actual_clave = pantalla_inicial
        self.pantalla_actual: Pantalla = self.pantallas.get(pantalla_inicial, self.pantallas["perfil"])
        self._proxima_pantalla: Optional[str] = None
        self._proxima_pantalla_kwargs: dict = {}

        self.pantalla_actual.al_entrar()

    # ------------------------------------------------------------------
    # Navegación entre pantallas
    # ------------------------------------------------------------------
    def cambiar_pantalla(self, nombre: str, **kwargs) -> None:
        if nombre in self.pantallas:
            self._proxima_pantalla = nombre
            self._proxima_pantalla_kwargs = kwargs

    def _aplicar_cambio_pantalla(self) -> None:
        if self._proxima_pantalla is None:
            return
        clave = self._proxima_pantalla
        kwargs = self._proxima_pantalla_kwargs
        self._proxima_pantalla = None
        self._proxima_pantalla_kwargs = {}

        if clave == self.pantalla_actual_clave:
            return

        self.pantalla_actual.al_salir()
        self.pantalla_actual_clave = clave
        self.pantalla_actual = self.pantallas[clave]
        self.pantalla_actual.al_entrar(**kwargs)

    # ------------------------------------------------------------------
    # Bucle de eventos y procesamiento
    # ------------------------------------------------------------------
    def _procesar_eventos(self) -> None:
        self.ctx.pos_raton = self.ventana.posicion_raton()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.ejecutando = False
                return

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    # En pantallas de juego, ESC regresa al menú; en menú/perfil, sale
                    if self.pantalla_actual_clave in ("conteo", "resultado", "adultos"):
                        self.cambiar_pantalla("menu")
                        continue
                    elif self.pantalla_actual_clave == "menu":
                        self.cambiar_pantalla("perfil")
                        continue
                    else:
                        self.ejecutando = False
                        return
                elif ev.key in (pygame.K_f, pygame.K_F11):
                    self.ventana.alternar_pantalla_completa()
                    continue
                elif ev.key == pygame.K_d:
                    self.ctx.modo_depuracion = not self.ctx.modo_depuracion
                    continue
                elif ev.key == pygame.K_r:
                    self.camara.conectar()
                    continue
                elif ev.key == pygame.K_SPACE:
                    self.voz.repetir_instruccion()
                    continue

            # Delegar evento a la pantalla activa
            pos = self.ctx.pos_raton if ev.type in (
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
                pygame.MOUSEMOTION,
            ) else None

            self.pantalla_actual.manejar_evento(ev, pos)

    def _capturar_y_detectar(self) -> None:
        """Captura en memoria y procesa con MediaPipe si la pantalla lo requiere."""
        if not self.pantalla_actual.usa_camara:
            self.ctx.fotograma = None
            self.ctx.deteccion = self.detector.procesar_puntos(None)
            return

        # 1. Captura de cámara (memoria RAM)
        fotograma = self.camara.obtener_fotograma()
        self.ctx.fotograma = fotograma

        # 2. Detección con MediaPipe Tasks o simulación por teclado
        if fotograma.disponible and fotograma.frame_rgb is not None:
            self.ctx.deteccion = self.detector.procesar_fotograma_rgb(fotograma.frame_rgb)
        elif self.ctx.dedos_simulados is not None:
            pts_sim = construir_puntos_simulados(self.ctx.dedos_simulados)
            self.ctx.deteccion = self.detector.procesar_puntos(pts_sim, etiqueta_mano="Simulada")
        else:
            self.ctx.deteccion = self.detector.procesar_puntos(None)

    def _dibujar_overlay_depuracion(self, sup: pygame.Surface) -> None:
        """Panel técnico opcional activado con tecla D."""
        panel = pygame.Surface((560, 260), pygame.SRCALPHA)
        panel.fill((20, 28, 48, 220))
        f = self.ventana.fuente(20, False)

        det = self.ctx.deteccion
        lineas = [
            f"[MODO DEPURACIÓN - Tecla D]  FPS: {self.ctx.fps:.1f}",
            f"Pantalla: {self.pantalla_actual_clave} | Perfil: {self.ctx.perfil.nombre}",
            f"Backend detector: {self.detector.backend} | Activo: {self.detector.mediapipe_activo}",
            f"Mano detectada: {det.mano_detectada} ({det.etiqueta_mano})",
            f"Conteo crudo: {det.conteo_crudo} | Conteo estable: {det.conteo_estabilizado}",
            f"Dedos [P,I,M,A,Me]: {[int(d) for d in det.dedos_extendidos]}",
            f"Cámara web: {'OK' if self.camara.camara_disponible else 'No disponible'}",
            "Atajos: [D] Debug | [F11] Pantalla completa | [0-5] Simular dedos | [ESC] Atrás",
        ]
        for i, txt in enumerate(lineas):
            lbl = f.render(txt, True, (230, 240, 255))
            panel.blit(lbl, (16, 12 + i * 28))

        sup.blit(panel, (60, 160))

    def ejecutar(self) -> None:
        """Bucle principal de la aplicación a 30 FPS."""
        try:
            while self.ejecutando:
                ahora = time.monotonic()
                self._aplicar_cambio_pantalla()
                self._procesar_eventos()
                if not self.ejecutando:
                    break

                self._capturar_y_detectar()
                self.pantalla_actual.actualizar(ahora)

                # Renderizar en el lienzo lógico 1920x1080
                self.pantalla_actual.dibujar(self.ventana.lienzo)

                if self.ctx.modo_depuracion:
                    self._dibujar_overlay_depuracion(self.ventana.lienzo)

                # Proyectar lienzo escalado a la ventana
                self.ventana.volcar()

                self.reloj.tick(config.FPS)
                self.ctx.fps = self.reloj.get_fps()
        finally:
            self.cerrar()

    def cerrar(self) -> None:
        self.camara.liberar()
        self.detector.cerrar()
        self.voz.cerrar()
        if PYGAME_DISPONIBLE and pygame is not None:
            pygame.quit()


# =============================================================================
# COMPATIBILIDAD CON EL CÓDIGO ANTERIOR
# =============================================================================
JuegoCuentaConTusDedos = AplicacionJuego


def parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Sistema Educativo Interactivo: "Cuenta con tus dedos" (4 a 6 años)'
    )
    parser.add_argument(
        "--pantalla",
        type=str,
        default="perfil",
        choices=["perfil", "calibracion", "menu", "conteo", "resultado", "adultos"],
        help="Pantalla con la que iniciar la aplicación.",
    )
    parser.add_argument(
        "--perfil",
        type=str,
        default=None,
        help="Nombre del perfil del niño (Sofía, Mateo, Luna...).",
    )
    parser.add_argument(
        "--camara",
        type=int,
        default=config.INDICE_CAMARA_DEFECTO,
        help="Índice de la cámara web (por defecto 0).",
    )
    parser.add_argument(
        "--ventana",
        action="store_true",
        help="Iniciar en modo ventana escalable en lugar de pantalla completa.",
    )
    parser.add_argument(
        "--pantalla-completa",
        action="store_true",
        help="Forzar inicio en pantalla completa.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parsear_argumentos()
    usar_fullscreen = config.PANTALLA_COMPLETA_INICIAL
    if args.pantalla_completa:
        usar_fullscreen = True
    elif args.ventana:
        usar_fullscreen = False

    app = AplicacionJuego(
        pantalla_inicial=args.pantalla,
        perfil_nombre=args.perfil,
        indice_camara=args.camara,
        pantalla_completa=usar_fullscreen,
    )
    app.ejecutar()