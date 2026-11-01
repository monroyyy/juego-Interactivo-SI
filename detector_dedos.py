"""
detector_dedos.py — Conteo de dedos invariante a rotación con MediaPipe Hands,
voto de mayoría (histéresis de 3 fotogramas) y periodo de gracia (4 fotogramas).
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
import math
from pathlib import Path
import time
from typing import Deque, Dict, List, Optional, Sequence, Tuple
import urllib.request

import numpy as np

import config

try:
    import mediapipe as mp
    MEDIAPIPE_DISPONIBLE = hasattr(mp, "tasks") or (
        hasattr(mp, "solutions") and hasattr(mp.solutions, "hands")
    )
except Exception:
    mp = None  # type: ignore
    MEDIAPIPE_DISPONIBLE = False


# Índices estándar de los 21 landmarks de MediaPipe Hands
WRIST = 0
THUMB_CMC = 1
THUMB_MCP = 2
THUMB_IP = 3
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_DIP = 7
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_DIP = 11
MIDDLE_TIP = 12
RING_MCP = 13
RING_PIP = 14
RING_DIP = 15
RING_TIP = 16
PINKY_MCP = 17
PINKY_PIP = 18
PINKY_DIP = 19
PINKY_TIP = 20

NOMBRES_DEDOS = ("Pulgar", "Índice", "Medio", "Anular", "Meñique")
INDICES_PUNTAS = (THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP)

# Pares de conexiones anatómicas para dibujar el esqueleto de la mano
CONEXIONES_MANO: Tuple[Tuple[int, int], ...] = (
    (0, 1), (1, 2), (2, 3), (3, 4),          # Pulgar
    (0, 5), (5, 6), (6, 7), (7, 8),          # Índice
    (5, 9), (9, 10), (10, 11), (11, 12),     # Medio
    (9, 13), (13, 14), (14, 15), (15, 16),   # Anular
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),  # Meñique y palma
)


@dataclass
class ResultadoDeteccionMano:
    """Estado instantáneo y estabilizado de la detección de dedos."""

    mano_detectada: bool
    en_periodo_gracia: bool
    conteo_crudo: int
    conteo_estabilizado: int
    dedos_extendidos: List[bool] = field(default_factory=lambda: [False] * 5)
    ratios_dedos: Dict[str, float] = field(default_factory=dict)
    puntos_normalizados: List[Tuple[float, float]] = field(default_factory=list)
    etiqueta_mano: str = "Desconocida"
    frames_gracia_restantes: int = 0
    historial_ventana: List[int] = field(default_factory=list)


def distancia_euclidiana(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calcula la distancia euclidiana 2D entre dos puntos (x, y)."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def evaluar_dedos_desde_puntos(
    puntos: Sequence[Tuple[float, float]],
) -> Tuple[List[bool], Dict[str, float]]:
    """
    Evalúa qué dedos están extendidos a partir de los 21 puntos (x, y) de MediaPipe.

    Criterio geométrico invariante a rotación e inclinación:
    1. Dedos largos (Índice, Medio, Anular, Meñique):
       Se compara la distancia desde la punta (TIP) hasta la muñeca (WRIST, lm 0)
       contra la distancia desde la articulación media (PIP) hasta la muñeca:
           ratio = dist(TIP, WRIST) / dist(PIP, WRIST)
       Además se verifica que la punta esté más lejos de la muñeca que el nudillo
       base (MCP) y que el dedo no esté replegado sobre sí mismo:
           dist(TIP, MCP) / dist(PIP, MCP) >= UMBRAL_RECTITUD_DEDO
       Como las distancias euclidianas son invariantes a la rotación 2D y al
       espejado horizontal, funciona con la mano vertical, inclinada, horizontal,
       izquierda o derecha.

    2. Pulgar (evaluado aparte):
       Se compara la distancia de la punta del pulgar (THUMB_TIP, lm 4) respecto
       a la base del dedo meñique (PINKY_MCP, lm 17) contra la distancia de la
       articulación interfalángica del pulgar (THUMB_IP, lm 3) a la misma base
       del meñique:
           ratio_pulgar = dist(THUMB_TIP, PINKY_MCP) / dist(THUMB_IP, PINKY_MCP)
       Y se comprueba que el pulgar esté separado del nudillo del índice
       (dist(THUMB_TIP, INDEX_MCP) / ancho_palma >= UMBRAL_APERTURA_PULGAR_PALMA).
    """
    if len(puntos) < 21:
        raise ValueError(f"Se requieren 21 puntos de referencia, se recibieron {len(puntos)}.")

    wrist = puntos[WRIST]
    pinky_mcp = puntos[PINKY_MCP]
    index_mcp = puntos[INDEX_MCP]
    ancho_palma = max(distancia_euclidiana(index_mcp, pinky_mcp), 1e-6)

    # --- 1. Evaluación del Pulgar respecto a la base del meñique (LM 17) ---
    d_thumb_tip_pinky = distancia_euclidiana(puntos[THUMB_TIP], pinky_mcp)
    d_thumb_ip_pinky = max(distancia_euclidiana(puntos[THUMB_IP], pinky_mcp), 1e-6)
    d_thumb_mcp_pinky = max(distancia_euclidiana(puntos[THUMB_MCP], pinky_mcp), 1e-6)
    d_thumb_tip_index_mcp = distancia_euclidiana(puntos[THUMB_TIP], index_mcp)

    ratio_pulgar = d_thumb_tip_pinky / d_thumb_ip_pinky
    ratio_pulgar_mcp = d_thumb_tip_pinky / d_thumb_mcp_pinky
    apertura_pulgar = d_thumb_tip_index_mcp / ancho_palma

    pulgar_extendido = (
        ratio_pulgar >= config.UMBRAL_RATIO_PULGAR_MENIQUE
        and ratio_pulgar_mcp >= config.UMBRAL_RATIO_PULGAR_MCP_MENIQUE
        and apertura_pulgar >= config.UMBRAL_APERTURA_PULGAR_PALMA
    )

    dedos_extendidos: List[bool] = [bool(pulgar_extendido)]
    ratios: Dict[str, float] = {"Pulgar": round(ratio_pulgar, 3)}

    # --- 2. Evaluación de Índice, Medio, Anular y Meñique respecto a la muñeca (LM 0) ---
    definicion_dedos_largos = (
        ("Índice", INDEX_MCP, INDEX_PIP, INDEX_TIP),
        ("Medio", MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP),
        ("Anular", RING_MCP, RING_PIP, RING_TIP),
        ("Meñique", PINKY_MCP, PINKY_PIP, PINKY_TIP),
    )

    for nombre, idx_mcp, idx_pip, idx_tip in definicion_dedos_largos:
        p_mcp = puntos[idx_mcp]
        p_pip = puntos[idx_pip]
        p_tip = puntos[idx_tip]

        d_tip_wrist = distancia_euclidiana(p_tip, wrist)
        d_pip_wrist = max(distancia_euclidiana(p_pip, wrist), 1e-6)
        d_mcp_wrist = max(distancia_euclidiana(p_mcp, wrist), 1e-6)

        d_tip_mcp = distancia_euclidiana(p_tip, p_mcp)
        d_pip_mcp = max(distancia_euclidiana(p_pip, p_mcp), 1e-6)

        ratio_wrist = d_tip_wrist / d_pip_wrist
        ratio_mcp_wrist = d_tip_wrist / d_mcp_wrist
        ratio_rectitud = d_tip_mcp / d_pip_mcp

        extendido = (
            ratio_wrist >= config.UMBRAL_RATIO_DEDO_WRIST
            and ratio_mcp_wrist >= config.UMBRAL_RATIO_TIP_MCP_WRIST
            and ratio_rectitud >= config.UMBRAL_RECTITUD_DEDO
        )
        dedos_extendidos.append(bool(extendido))
        ratios[nombre] = round(ratio_wrist, 3)

    return dedos_extendidos, ratios


class EstabilizadorConteo:
    """
    Aplica histéresis mediante voto de mayoría en los últimos N fotogramas (3)
    y un periodo de gracia de M fotogramas (4) cuando la mano se pierde un instante.
    """

    def __init__(
        self,
        ventana_mayoria: int = config.VENTANA_HISTÉRESIS_FRAMES,
        frames_gracia: int = config.FRAMES_GRACIA_SIN_MANO,
    ) -> None:
        self.ventana_mayoria = max(1, ventana_mayoria)
        self.frames_gracia_max = max(0, frames_gracia)
        self.historial: Deque[int] = deque(maxlen=self.ventana_mayoria)
        self.conteo_estable: int = 0
        self.frames_sin_mano: int = self.frames_gracia_max + 1
        self.ultimos_dedos: List[bool] = [False] * 5
        self.ultimos_puntos: List[Tuple[float, float]] = []
        self.ultimos_ratios: Dict[str, float] = {}
        self.ultima_etiqueta_mano: str = "Ninguna"

    def reiniciar(self) -> None:
        self.historial.clear()
        self.conteo_estable = 0
        self.frames_sin_mano = self.frames_gracia_max + 1
        self.ultimos_dedos = [False] * 5
        self.ultimos_puntos = []
        self.ultimos_ratios = {}
        self.ultima_etiqueta_mano = "Ninguna"

    def actualizar_con_deteccion(
        self,
        dedos_extendidos: List[bool],
        puntos_normalizados: Optional[List[Tuple[float, float]]] = None,
        ratios: Optional[Dict[str, float]] = None,
        etiqueta_mano: str = "Mano",
    ) -> ResultadoDeteccionMano:
        """Actualiza el estabilizador cuando se detecta una mano en el fotograma actual."""
        conteo_crudo = int(sum(1 for d in dedos_extendidos if d))
        self.frames_sin_mano = 0
        self.historial.append(conteo_crudo)

        # Voto de mayoría en los últimos 3 fotogramas
        conteos = Counter(self.historial)
        valor_mas_frecuente, frecuencia = conteos.most_common(1)[0]

        if frecuencia >= 2 or len(self.historial) == 1:
            self.conteo_estable = valor_mas_frecuente
        # Si los 3 últimos fotogramas son todos distintos (ej. 1, 2, 3),
        # mantiene el último conteo_estable para evitar parpadeo.

        self.ultimos_dedos = list(dedos_extendidos)
        if puntos_normalizados is not None:
            self.ultimos_puntos = list(puntos_normalizados)
        if ratios is not None:
            self.ultimos_ratios = dict(ratios)
        self.ultima_etiqueta_mano = etiqueta_mano

        return ResultadoDeteccionMano(
            mano_detectada=True,
            en_periodo_gracia=False,
            conteo_crudo=conteo_crudo,
            conteo_estabilizado=self.conteo_estable,
            dedos_extendidos=list(self.ultimos_dedos),
            ratios_dedos=dict(self.ultimos_ratios),
            puntos_normalizados=list(self.ultimos_puntos),
            etiqueta_mano=self.ultima_etiqueta_mano,
            frames_gracia_restantes=self.frames_gracia_max,
            historial_ventana=list(self.historial),
        )

    def actualizar_sin_mano(self) -> ResultadoDeteccionMano:
        """
        Actualiza el estado cuando no se detecta mano en el fotograma actual.
        Durante los primeros 4 fotogramas perdidos, conserva el último conteo estable.
        """
        self.frames_sin_mano += 1

        if self.frames_sin_mano <= self.frames_gracia_max and len(self.historial) > 0:
            restantes = self.frames_gracia_max - self.frames_sin_mano
            return ResultadoDeteccionMano(
                mano_detectada=True,
                en_periodo_gracia=True,
                conteo_crudo=self.conteo_estable,
                conteo_estabilizado=self.conteo_estable,
                dedos_extendidos=list(self.ultimos_dedos),
                ratios_dedos=dict(self.ultimos_ratios),
                puntos_normalizados=list(self.ultimos_puntos),
                etiqueta_mano=self.ultima_etiqueta_mano,
                frames_gracia_restantes=restantes,
                historial_ventana=list(self.historial),
            )

        # Se agotó el periodo de gracia: limpiar estado
        self.historial.clear()
        self.conteo_estable = 0
        self.ultimos_dedos = [False] * 5
        self.ultimos_puntos = []
        self.ultimos_ratios = {}
        self.ultima_etiqueta_mano = "Ninguna"

        return ResultadoDeteccionMano(
            mano_detectada=False,
            en_periodo_gracia=False,
            conteo_crudo=0,
            conteo_estabilizado=0,
            dedos_extendidos=[False] * 5,
            ratios_dedos={},
            puntos_normalizados=[],
            etiqueta_mano="Ninguna",
            frames_gracia_restantes=0,
            historial_ventana=[],
        )


def asegurar_modelo_manos() -> Optional[Path]:
    """Devuelve la ruta del modelo `hand_landmarker.task`, descargándolo si falta."""
    ruta = Path(config.RUTA_MODELO_MANOS)
    if ruta.exists() and ruta.stat().st_size > 1_000_000:
        return ruta
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(config.URL_MODELO_MANOS, timeout=30) as resp:
            datos = resp.read()
        if len(datos) < 1_000_000:
            return None
        ruta.write_bytes(datos)
        return ruta
    except Exception:
        return None


class DetectorDedos:
    """
    Detector de manos y contador de dedos basado en MediaPipe +
    EstabilizadorConteo (histéresis de 3 fotogramas y gracia de 4 fotogramas).

    Backends (en orden de preferencia):
    1. MediaPipe Tasks `HandLandmarker` (versiones nuevas de mediapipe).
    2. MediaPipe clásico `mp.solutions.hands` (versiones antiguas).
    Si ninguno está disponible, `mediapipe_activo` es False y `mensaje_error`
    explica el motivo (el juego sigue funcionando con las teclas 0-5).
    """

    def __init__(self) -> None:
        self.estabilizador = EstabilizadorConteo()
        self.mediapipe_activo = False
        self.backend = "ninguno"
        self.mensaje_error = ""
        self._hands = None
        self._landmarker = None
        self._ultimo_ts_ms = 0

        if not MEDIAPIPE_DISPONIBLE or mp is None:
            self.mensaje_error = "MediaPipe no está instalado."
            return

        if hasattr(mp, "tasks") and self._iniciar_tasks():
            return
        if hasattr(mp, "solutions") and self._iniciar_clasico():
            return
        if not self.mensaje_error:
            self.mensaje_error = "No se pudo iniciar el detector de manos."

    # ------------------------------------------------------------------
    def _iniciar_tasks(self) -> bool:
        ruta = asegurar_modelo_manos()
        if ruta is None:
            self.mensaje_error = (
                "Falta el modelo de manos (assets/modelos/hand_landmarker.task) "
                "y no se pudo descargar. Revisa tu conexión a internet."
            )
            return False
        try:
            from mediapipe.tasks.python import BaseOptions
            from mediapipe.tasks.python import vision

            opciones = vision.HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_buffer=ruta.read_bytes()),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=config.MAX_MANOS,
                min_hand_detection_confidence=config.MIN_CONFIDENCE_DETECCION,
                min_hand_presence_confidence=config.MIN_CONFIDENCE_DETECCION,
                min_tracking_confidence=config.MIN_CONFIDENCE_SEGUIMIENTO,
            )
            self._landmarker = vision.HandLandmarker.create_from_options(opciones)
            self.backend = "tasks"
            self.mediapipe_activo = True
            return True
        except Exception as exc:  # pragma: no cover - depende del entorno
            self.mensaje_error = f"No se pudo iniciar MediaPipe Tasks: {exc}"
            self._landmarker = None
            return False

    def _iniciar_clasico(self) -> bool:
        try:
            self._hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=config.MAX_MANOS,
                model_complexity=0,
                min_detection_confidence=config.MIN_CONFIDENCE_DETECCION,
                min_tracking_confidence=config.MIN_CONFIDENCE_SEGUIMIENTO,
            )
            self.backend = "solutions"
            self.mediapipe_activo = True
            return True
        except Exception as exc:  # pragma: no cover - depende del entorno
            self.mensaje_error = f"No se pudo iniciar MediaPipe Hands: {exc}"
            self._hands = None
            return False

    # ------------------------------------------------------------------
    def procesar_fotograma_rgb(self, frame_rgb: Optional[np.ndarray]) -> ResultadoDeteccionMano:
        """
        Procesa un fotograma RGB en memoria con MediaPipe y devuelve
        el resultado estabilizado.
        """
        if frame_rgb is None or not self.mediapipe_activo:
            return self.estabilizador.actualizar_sin_mano()

        puntos_norm: Optional[List[Tuple[float, float]]] = None
        etiqueta = "Mano"

        if self.backend == "tasks" and self._landmarker is not None:
            ts_ms = int(time.monotonic() * 1000)
            if ts_ms <= self._ultimo_ts_ms:
                ts_ms = self._ultimo_ts_ms + 1
            self._ultimo_ts_ms = ts_ms
            imagen = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=np.ascontiguousarray(frame_rgb, dtype=np.uint8),
            )
            try:
                resultado = self._landmarker.detect_for_video(imagen, ts_ms)
            except Exception:
                return self.estabilizador.actualizar_sin_mano()
            if resultado.hand_landmarks:
                puntos_norm = [
                    (float(lm.x), float(lm.y)) for lm in resultado.hand_landmarks[0]
                ]
                try:
                    nombre = resultado.handedness[0][0].category_name
                    etiqueta = "Derecha" if nombre == "Right" else "Izquierda"
                except Exception:
                    etiqueta = "Mano"

        elif self.backend == "solutions" and self._hands is not None:
            resultados = self._hands.process(frame_rgb)
            if resultados.multi_hand_landmarks:
                puntos_norm = [
                    (float(lm.x), float(lm.y))
                    for lm in resultados.multi_hand_landmarks[0].landmark
                ]
                try:
                    clasificacion = resultados.multi_handedness[0].classification[0]
                    etiqueta = "Derecha" if clasificacion.label == "Right" else "Izquierda"
                except Exception:
                    etiqueta = "Mano"

        if puntos_norm is None:
            return self.estabilizador.actualizar_sin_mano()
        return self.procesar_puntos(puntos_norm, etiqueta_mano=etiqueta)

    def procesar_puntos(
        self,
        puntos_normalizados: Optional[Sequence[Tuple[float, float]]],
        etiqueta_mano: str = "Mano",
    ) -> ResultadoDeteccionMano:
        """
        Evalúa directamente una lista de 21 puntos (x, y) o None cuando no hay mano.
        Útil tanto para el flujo de cámara como para pruebas unitarias deterministas.
        """
        if puntos_normalizados is None or len(puntos_normalizados) < 21:
            return self.estabilizador.actualizar_sin_mano()

        dedos_extendidos, ratios = evaluar_dedos_desde_puntos(puntos_normalizados)
        return self.estabilizador.actualizar_con_deteccion(
            dedos_extendidos=dedos_extendidos,
            puntos_normalizados=list(puntos_normalizados),
            ratios=ratios,
            etiqueta_mano=etiqueta_mano,
        )

    def reiniciar(self) -> None:
        self.estabilizador.reiniciar()

    def cerrar(self) -> None:
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception:
                pass
            self._landmarker = None
        if self._hands is not None:
            try:
                self._hands.close()
            except Exception:
                pass
            self._hands = None