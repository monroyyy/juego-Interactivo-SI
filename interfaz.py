"""
interfaz.py — Ventana de Pygame sobre un lienzo lógico fijo de 1920x1080.

* Escala el lienzo a cualquier tamaño de ventana o pantalla completa sin deformarlo
  (barras laterales si la proporción no es 16:9).
* Convierte las coordenadas del ratón/dedo al espacio lógico del mockup.
* Carga la tipografía Lexend incluida en assets/fonts (con respaldo del sistema).
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

try:
    import pygame
    PYGAME_DISPONIBLE = True
except Exception:
    pygame = None  # type: ignore
    PYGAME_DISPONIBLE = False

import config


class Ventana:
    """Administra la ventana real, el lienzo 1920x1080 y las fuentes."""

    def __init__(self, pantalla_completa: bool = config.PANTALLA_COMPLETA_INICIAL) -> None:
        if not PYGAME_DISPONIBLE or pygame is None:
            raise RuntimeError(
                "Pygame no está instalado. Ejecuta: pip install -r requirements.txt"
            )

        pygame.font.init()
        self.pantalla_completa = pantalla_completa
        self._tam_ventana = self._tamano_inicial_ventana()
        self._fuentes: Dict[Tuple[int, bool], Any] = {}

        self._crear_ventana()
        pygame.display.set_caption(config.TITULO_VENTANA)
        self.lienzo = pygame.Surface((config.ANCHO_BASE, config.ALTO_BASE))

    # ------------------------------------------------------------------
    # Ventana y pantalla completa
    # ------------------------------------------------------------------
    @staticmethod
    def _tamano_inicial_ventana() -> Tuple[int, int]:
        ancho, alto = config.ANCHO_BASE, config.ALTO_BASE
        try:
            info = pygame.display.Info()
            if info.current_w > 0 and info.current_h > 0:
                k = min(1.0, 0.92 * info.current_w / ancho, 0.88 * info.current_h / alto)
                ancho, alto = int(ancho * k), int(alto * k)
        except Exception:
            pass
        return max(640, ancho), max(360, alto)

    def _crear_ventana(self) -> None:
        if self.pantalla_completa:
            pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.RESIZABLE)
        else:
            pygame.display.set_mode(self._tam_ventana, pygame.RESIZABLE)

    def alternar_pantalla_completa(self) -> None:
        if not self.pantalla_completa:
            self._tam_ventana = pygame.display.get_surface().get_size()
        self.pantalla_completa = not self.pantalla_completa
        self._crear_ventana()

    # ------------------------------------------------------------------
    # Geometría lienzo <-> ventana
    # ------------------------------------------------------------------
    def _geometria(self) -> Tuple[float, Tuple[int, int], Tuple[int, int]]:
        ancho_v, alto_v = pygame.display.get_surface().get_size()
        escala = min(ancho_v / config.ANCHO_BASE, alto_v / config.ALTO_BASE)
        tam = (
            max(1, int(config.ANCHO_BASE * escala)),
            max(1, int(config.ALTO_BASE * escala)),
        )
        desfase = ((ancho_v - tam[0]) // 2, (alto_v - tam[1]) // 2)
        return escala, tam, desfase

    def convertir_coordenadas(self, pos_ventana: Tuple[int, int]) -> Tuple[int, int]:
        """Convierte coordenadas de la ventana real al espacio lógico 1920x1080."""
        escala, _, desfase = self._geometria()
        if escala <= 0:
            return (0, 0)
        return (
            int((pos_ventana[0] - desfase[0]) / escala),
            int((pos_ventana[1] - desfase[1]) / escala),
        )

    def posicion_raton(self) -> Tuple[int, int]:
        return self.convertir_coordenadas(pygame.mouse.get_pos())

    def volcar(self) -> None:
        """Escala el lienzo lógico al tamaño actual de la ventana y lo muestra."""
        ventana = pygame.display.get_surface()
        _, tam, desfase = self._geometria()
        if tam == (config.ANCHO_BASE, config.ALTO_BASE) and desfase == (0, 0):
            ventana.blit(self.lienzo, (0, 0))
        else:
            if desfase != (0, 0):
                ventana.fill(config.COLOR_FONDO)
            escalado = pygame.transform.smoothscale(self.lienzo, tam)
            ventana.blit(escalado, desfase)
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Tipografía
    # ------------------------------------------------------------------
    def fuente(self, tamano: int, negrita: bool = True) -> Any:
        """Devuelve una fuente Lexend (Regular o Bold) del tamaño pedido, con caché."""
        clave = (int(tamano), bool(negrita))
        if clave not in self._fuentes:
            self._fuentes[clave] = self._cargar_fuente(int(tamano), negrita)
        return self._fuentes[clave]

    @staticmethod
    def _cargar_fuente(tamano: int, negrita: bool) -> Any:
        ruta = config.RUTA_FUENTE_NEGRITA if negrita else config.RUTA_FUENTE_REGULAR
        if ruta.exists():
            try:
                return pygame.font.Font(str(ruta), tamano)
            except Exception:
                pass
        for nombre in config.FUENTES_PREFERIDAS:
            ruta_sis = pygame.font.match_font(nombre, bold=negrita)
            if ruta_sis:
                try:
                    return pygame.font.Font(ruta_sis, tamano)
                except Exception:
                    continue
        return pygame.font.SysFont("sans", tamano, bold=negrita)