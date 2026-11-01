"""
sesion.py — Registro local de sesiones en JSON para padres y docentes.
Cumple estrictamente con privacidad infantil: no almacena imágenes ni datos
personales más allá del identificador del perfil.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import config


@dataclass
class RegistroRonda:
    """Datos cuantitativos de una ronda individual."""

    numero_ronda: int
    fecha: str
    numero_pedido: int
    numero_detectado: int
    aciertos: int
    intentos: int
    tiempo_respuesta_seg: float
    estrellas: int
    uso_pista: bool = False


@dataclass
class SesionJuego:
    """Resumen completo de una partida de 5 rondas."""

    id_sesion: str
    perfil: str
    fecha_inicio: str
    fecha_fin: Optional[str] = None
    rondas: List[RegistroRonda] = field(default_factory=list)
    total_aciertos: int = 0
    total_intentos: int = 0
    total_estrellas: int = 0
    tiempo_promedio_respuesta_seg: float = 0.0


class GestorSesion:
    """
    Gestiona el almacenamiento local en JSON por perfil y por sesión.
    Nunca guarda fotogramas ni información biométrica.
    """

    def __init__(
        self,
        perfil: str = config.PERFIL_POR_DEFECTO,
        ruta_archivo: Path = config.ARCHIVO_SESIONES_JSON,
    ) -> None:
        self.perfil = self._sanitizar_perfil(perfil)
        self.ruta_archivo = Path(ruta_archivo)
        self.sesion_actual: Optional[SesionJuego] = None
        self.iniciar_nueva_sesion()

    @staticmethod
    def _sanitizar_perfil(nombre: str) -> str:
        limpio = "".join(c for c in nombre.strip() if c.isalnum() or c in ("_", "-"))
        return limpio or config.PERFIL_POR_DEFECTO

    def iniciar_nueva_sesion(self) -> SesionJuego:
        """Crea una nueva sesión en memoria lista para registrar las 5 rondas."""
        ahora = datetime.now()
        id_sesion = f"sesion_{ahora.strftime('%Y%m%d_%H%M%S')}"
        self.sesion_actual = SesionJuego(
            id_sesion=id_sesion,
            perfil=self.perfil,
            fecha_inicio=ahora.isoformat(timespec="seconds"),
        )
        return self.sesion_actual

    def registrar_ronda(
        self,
        numero_ronda: int,
        numero_pedido: int,
        numero_detectado: int,
        aciertos: int,
        intentos: int,
        tiempo_respuesta_seg: float,
        estrellas: int,
        uso_pista: bool = False,
    ) -> RegistroRonda:
        """Agrega el resultado de una ronda a la sesión activa y guarda en disco."""
        if self.sesion_actual is None:
            self.iniciar_nueva_sesion()

        assert self.sesion_actual is not None
        registro = RegistroRonda(
            numero_ronda=int(numero_ronda),
            fecha=datetime.now().isoformat(timespec="seconds"),
            numero_pedido=int(numero_pedido),
            numero_detectado=int(numero_detectado),
            aciertos=int(aciertos),
            intentos=max(1, int(intentos)),
            tiempo_respuesta_seg=round(float(tiempo_respuesta_seg), 2),
            estrellas=max(1, min(3, int(estrellas))),
            uso_pista=bool(uso_pista),
        )
        self.sesion_actual.rondas.append(registro)
        self._recalcular_totales()
        self.guardar_en_disco()
        return registro

    def finalizar_sesion(self) -> Optional[SesionJuego]:
        """Marca la hora de cierre de la partida y persiste el archivo JSON."""
        if self.sesion_actual is None:
            return None
        self.sesion_actual.fecha_fin = datetime.now().isoformat(timespec="seconds")
        self._recalcular_totales()
        self.guardar_en_disco()
        return self.sesion_actual

    def _recalcular_totales(self) -> None:
        if self.sesion_actual is None:
            return
        rondas = self.sesion_actual.rondas
        self.sesion_actual.total_aciertos = sum(r.aciertos for r in rondas)
        self.sesion_actual.total_intentos = sum(r.intentos for r in rondas)
        self.sesion_actual.total_estrellas = sum(r.estrellas for r in rondas)
        if rondas:
            promedio = sum(r.tiempo_respuesta_seg for r in rondas) / len(rondas)
            self.sesion_actual.tiempo_promedio_respuesta_seg = round(promedio, 2)
        else:
            self.sesion_actual.tiempo_promedio_respuesta_seg = 0.0

    def cargar_historial(self) -> Dict[str, Any]:
        """Carga el diccionario completo de perfiles y sesiones desde el JSON local."""
        if not self.ruta_archivo.exists():
            return {"perfiles": {}}
        try:
            with self.ruta_archivo.open("r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
                if isinstance(datos, dict) and "perfiles" in datos:
                    return datos
        except (OSError, json.JSONDecodeError):
            pass
        return {"perfiles": {}}

    def guardar_en_disco(self) -> bool:
        """
        Guarda la sesión actual dentro de la estructura por perfil en JSON.
        Incluye verificación explícita de que no existan campos de imagen.
        """
        if self.sesion_actual is None:
            return False

        datos = self.cargar_historial()
        perfiles = datos.setdefault("perfiles", {})
        sesiones_perfil: List[Dict[str, Any]] = perfiles.setdefault(self.perfil, [])

        dict_sesion = asdict(self.sesion_actual)
        # Garantía de privacidad: jamás permitir claves de imagen o fotograma
        claves_prohibidas = {"imagen", "frame", "foto", "captura", "video"}
        assert not any(k in dict_sesion for k in claves_prohibidas)

        # Actualizar si la sesión ya existe o agregarla al final
        actualizada = False
        for i, existente in enumerate(sesiones_perfil):
            if existente.get("id_sesion") == self.sesion_actual.id_sesion:
                sesiones_perfil[i] = dict_sesion
                actualizada = True
                break
        if not actualizada:
            sesiones_perfil.append(dict_sesion)

        try:
            self.ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
            with self.ruta_archivo.open("w", encoding="utf-8") as archivo:
                json.dump(datos, archivo, ensure_ascii=False, indent=2)
            return True
        except OSError:
            return False