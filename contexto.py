"""
contexto.py — Estado compartido entre pantallas (cámara, detector, voz, perfil…).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

import config
from camara import FotogramaProcesado, GestorCamara
from detector_dedos import DetectorDedos, ResultadoDeteccionMano
from interfaz import Ventana
from mano_avatar import ManoAvatar
from perfiles import AlmacenPerfiles, Perfil
from voz import NarradorVoz


class Contexto:
    """Objeto que reciben todas las pantallas para compartir recursos."""

    def __init__(
        self,
        ventana: Ventana,
        camara: GestorCamara,
        detector: DetectorDedos,
        voz: NarradorVoz,
        perfiles: AlmacenPerfiles,
    ) -> None:
        self.ventana = ventana
        self.camara = camara
        self.detector = detector
        self.voz = voz
        self.perfiles = perfiles
        self.mano = ManoAvatar()

        self.perfil: Perfil = perfiles.perfiles[0]
        self.calibrado: bool = False
        self.ultima_partida: Optional[Dict[str, Any]] = None

        self.fotograma: Optional[FotogramaProcesado] = None
        self.deteccion: ResultadoDeteccionMano = detector.procesar_puntos(None)
        self.dedos_simulados: Optional[int] = None
        self.modo_depuracion: bool = config.MODO_DEPURACION_INICIAL
        self.fps: float = 0.0
        self.pos_raton: Tuple[int, int] = (0, 0)

        self._navegar: Callable[..., None] = lambda nombre, **kw: None

    # ------------------------------------------------------------------
    def navegar(self, nombre: str, **kwargs: Any) -> None:
        """Pide cambiar de pantalla (se aplica al inicio del siguiente fotograma)."""
        self._navegar(nombre, **kwargs)

    @property
    def usa_deteccion_real(self) -> bool:
        """True si hay cámara y detector funcionando (si no, se usan las teclas 0–5)."""
        return bool(
            self.fotograma is not None
            and self.fotograma.disponible
            and self.detector.mediapipe_activo
        )

    def hay_mano(self) -> bool:
        return bool(self.deteccion.mano_detectada)
