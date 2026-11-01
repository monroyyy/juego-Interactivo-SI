"""
camara.py — Captura de cámara en modo espejo y calibración automática de luz.
Procesa todos los fotogramas exclusivamente en memoria RAM (sin guardar ni
grabar imágenes en disco, protegiendo la privacidad de menores de edad).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np

import config


@dataclass
class FotogramaProcesado:
    """Resultado en memoria de la lectura y ajuste de un fotograma de la cámara."""

    disponible: bool
    frame_bgr: Optional[np.ndarray]
    frame_rgb: Optional[np.ndarray]
    brillo_promedio: float
    ajustando_luz: bool
    mensaje_error: str = ""


class GestorCamara:
    """
    Administra la cámara web con:
    1. Modo espejo horizontal para interacción kinestésica natural.
    2. Medición en vivo del brillo promedio del fotograma.
    3. Corrección automática mediante CLAHE + ajuste suave de gamma cuando la
       iluminación es muy baja o muy alta, activando el aviso "Ajustando la luz".
    4. Detección clara de cámara ausente o desconectada para avisar al adulto.
    """

    def __init__(
        self,
        indice_camara: int = config.INDICE_CAMARA_DEFECTO,
        ancho: int = config.ANCHO_CAPTURA_CAMARA,
        alto: int = config.ALTO_CAPTURA_CAMARA,
    ) -> None:
        # Garantía de privacidad: prohibido guardar imágenes en disco
        assert config.PERMITIR_GUARDAR_IMAGENES is False

        self.indice_camara = indice_camara
        self.ancho = ancho
        self.alto = alto
        self.cap: Optional[cv2.VideoCapture] = None
        self.camara_disponible: bool = False
        self.brillo_promedio: float = 128.0
        self.ajustando_luz: bool = False
        self.mensaje_error: str = ""

        self._clahe = cv2.createCLAHE(
            clipLimit=config.CLAHE_CLIP_LIMIT,
            tileGridSize=config.CLAHE_TILE_GRID_SIZE,
        )

        self.conectar()

    def conectar(self) -> bool:
        """Intenta abrir el dispositivo de captura de video."""
        self.liberar()
        try:
            cap = cv2.VideoCapture(self.indice_camara)
            if cap is not None and cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.ancho)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.alto)
                cap.set(cv2.CAP_PROP_FPS, config.FPS)
                ret, frame_prueba = cap.read()
                if ret and frame_prueba is not None and frame_prueba.size > 0:
                    self.cap = cap
                    self.camara_disponible = True
                    self.mensaje_error = ""
                    return True
                cap.release()
        except Exception:
            pass

        self.cap = None
        self.camara_disponible = False
        self.mensaje_error = (
            "No se encontró la cámara web. Por favor pide a un adulto que "
            "verifique que la cámara esté conectada y no esté en uso por otro programa."
        )
        return False

    @staticmethod
    def medir_brillo(frame_bgr: np.ndarray) -> float:
        """Calcula el brillo promedio (0..255) usando luminancia perceptual."""
        gris = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gris))

    def calibrar_iluminacion(
        self, frame_bgr: np.ndarray
    ) -> Tuple[np.ndarray, float, bool]:
        """
        Mide el brillo promedio del fotograma; si es muy bajo (< 75) o muy alto
        (> 195), aplica ecualización adaptativa CLAHE en el canal de luminancia
        (LAB) y compensación suave de exposición.
        """
        brillo = self.medir_brillo(frame_bgr)
        requiere_ajuste = (
            brillo < config.BRILLO_MIN_OPTIMO or brillo > config.BRILLO_MAX_OPTIMO
        )

        if not requiere_ajuste:
            return frame_bgr, brillo, False

        # Convertir a espacio LAB para mejorar el contraste sin distorsionar tonos de piel
        lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
        canal_l, canal_a, canal_b = cv2.split(lab)

        # Aplicar CLAHE sobre el canal de luminancia
        canal_l_eq = self._clahe.apply(canal_l)

        # Compensación adicional de gamma si está muy oscuro o sobreexpuesto
        gamma = 1.0
        if brillo < config.BRILLO_MIN_OPTIMO:
            gamma = 0.72  # Aclara sombras
        elif brillo > config.BRILLO_MAX_OPTIMO:
            gamma = 1.35  # Atenúa altas luces

        if gamma != 1.0:
            inv_gamma = 1.0 / gamma
            tabla = np.array(
                [((i / 255.0) ** inv_gamma) * 255 for i in range(256)],
                dtype=np.uint8,
            )
            canal_l_eq = cv2.LUT(canal_l_eq, tabla)

        lab_ajustado = cv2.merge((canal_l_eq, canal_a, canal_b))
        frame_corregido = cv2.cvtColor(lab_ajustado, cv2.COLOR_LAB2BGR)
        return frame_corregido, brillo, True

    def obtener_fotograma(self) -> FotogramaProcesado:
        """
        Lee un fotograma de la cámara, lo voltea en modo espejo y ejecuta la
        calibración automática de luz en memoria.
        """
        if self.cap is None or not self.cap.isOpened():
            self.camara_disponible = False
            return FotogramaProcesado(
                disponible=False,
                frame_bgr=None,
                frame_rgb=None,
                brillo_promedio=0.0,
                ajustando_luz=False,
                mensaje_error=self.mensaje_error
                or "Cámara no disponible. Verifica la conexión del dispositivo.",
            )

        ret, frame = self.cap.read()
        if not ret or frame is None or frame.size == 0:
            self.camara_disponible = False
            self.mensaje_error = (
                "Se perdió la señal de la cámara web. Por favor revisa el cable USB "
                "o presiona R para reintentar la conexión."
            )
            return FotogramaProcesado(
                disponible=False,
                frame_bgr=None,
                frame_rgb=None,
                brillo_promedio=0.0,
                ajustando_luz=False,
                mensaje_error=self.mensaje_error,
            )

        # Modo espejo (volteo horizontal)
        if config.MODO_ESPEJO:
            frame = cv2.flip(frame, 1)

        # Calibración automática de luz (CLAHE si el brillo sale del rango óptimo)
        frame_ajustado, brillo, ajustando = self.calibrar_iluminacion(frame)
        frame_rgb = cv2.cvtColor(frame_ajustado, cv2.COLOR_BGR2RGB)

        self.camara_disponible = True
        self.brillo_promedio = brillo
        self.ajustando_luz = ajustando
        self.mensaje_error = ""

        return FotogramaProcesado(
            disponible=True,
            frame_bgr=frame_ajustado,
            frame_rgb=frame_rgb,
            brillo_promedio=brillo,
            ajustando_luz=ajustando,
            mensaje_error="",
        )

    def liberar(self) -> None:
        """Libera el recurso de hardware de la cámara."""
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.camara_disponible = False