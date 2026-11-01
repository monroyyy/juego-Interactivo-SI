"""
voz.py — Síntesis de voz local en español con pyttsx3 y Plan B automático.
Funciona de forma asíncrona en un hilo dedicado para no bloquear la interfaz
ni la lectura de la cámara.
"""

from __future__ import annotations

import queue
import threading
from typing import Optional

import config

try:
    import pyttsx3
    PYTTSX3_DISPONIBLE = True
except Exception:
    pyttsx3 = None  # type: ignore
    PYTTSX3_DISPONIBLE = False


class NarradorVoz:
    """
    Narrador de voz claro y pausado para niños de 4 a 6 años.
    Implementa selección automática de voz en español y un Plan B robusto:
    - Si no hay voz en español instalada en el sistema operativo, utiliza la
      voz disponible ajustada a velocidad infantil (135 WPM), informa en el
      estado del sistema y sincroniza siempre el texto en la burbuja del narrador.
    - Si pyttsx3 o el motor de audio del sistema no están disponibles, mantiene
      la burbuja visual activa y evita cualquier bloqueo o cierre inesperado.
    """

    PALABRAS_CLAVE_ESPANOL = (
        "spanish",
        "español",
        "espanol",
        "es_es",
        "es_mx",
        "es-es",
        "es-mx",
        "es_la",
        "es-419",
        "sabina",
        "helena",
        "pablo",
        "raul",
        "paloma",
        "mia",
        "paulina",
        "monica",
        "jorge",
        "diego",
        "carlos",
        "latam",
    )

    def __init__(self) -> None:
        self._cola_mensajes: "queue.Queue[Optional[str]]" = queue.Queue()
        self._lock = threading.Lock()
        self._texto_actual: str = "¡Hola! Vamos a contar con tus dedos."
        self._ultima_instruccion: str = self._texto_actual
        self._activo: bool = True

        self.motor_disponible: bool = False
        self.voz_espanol_encontrada: bool = False
        self.nombre_voz_activa: str = "Plan B (Subtítulos + Burbuja visual)"
        self.modo_plan_b: bool = False

        self._hilo = threading.Thread(
            target=self._bucle_trabajador_tts,
            name="HiloNarradorVoz",
            daemon=True,
        )
        self._hilo.start()

    @property
    def texto_actual(self) -> str:
        with self._lock:
            return self._texto_actual

    @property
    def ultima_instruccion(self) -> str:
        with self._lock:
            return self._ultima_instruccion

    def narrar(
        self,
        texto: str,
        es_instruccion: bool = False,
        interrumpir: bool = True,
    ) -> None:
        """
        Envía un mensaje a la burbuja del narrador y a la cola de voz.
        Si `es_instruccion=True`, se guarda para el botón 'Escuchar'.
        """
        texto_limpio = texto.strip()
        if not texto_limpio:
            return

        with self._lock:
            self._texto_actual = texto_limpio
            if es_instruccion:
                self._ultima_instruccion = texto_limpio

        if interrumpir:
            self._vaciar_cola()

        self._cola_mensajes.put(texto_limpio)

    def repetir_instruccion(self) -> str:
        """Repite la última instrucción principal (usado por el botón Escuchar)."""
        instruccion = self.ultima_instruccion
        self.narrar(instruccion, es_instruccion=False, interrumpir=True)
        return instruccion

    def _vaciar_cola(self) -> None:
        while not self._cola_mensajes.empty():
            try:
                self._cola_mensajes.get_nowait()
                self._cola_mensajes.task_done()
            except queue.Empty:
                break

    def _configurar_motor(self) -> Optional["pyttsx3.Engine"]:
        if not PYTTSX3_DISPONIBLE or pyttsx3 is None:
            self.modo_plan_b = True
            self.motor_disponible = False
            self.nombre_voz_activa = "Plan B: Sin pyttsx3 (Burbuja visual activa)"
            return None

        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", config.VELOCIDAD_VOZ_WPM)
            engine.setProperty("volume", config.VOLUMEN_VOZ)

            voces = engine.getProperty("voices") or []
            voz_elegida = None

            for voz in voces:
                id_voz = str(getattr(voz, "id", "")).lower()
                nombre_voz = str(getattr(voz, "name", "")).lower()
                idiomas = str(getattr(voz, "languages", "")).lower()
                combinado = f"{id_voz} {nombre_voz} {idiomas}"

                if any(clave in combinado for clave in self.PALABRAS_CLAVE_ESPANOL):
                    voz_elegida = voz
                    break

            if voz_elegida is not None:
                engine.setProperty("voice", voz_elegida.id)
                self.voz_espanol_encontrada = True
                self.modo_plan_b = False
                self.nombre_voz_activa = getattr(voz_elegida, "name", "Español")
            else:
                # Plan B: usar voz predeterminada con fonética simplificada + apoyo visual
                self.voz_espanol_encontrada = False
                self.modo_plan_b = True
                if voces:
                    engine.setProperty("voice", voces[0].id)
                    nombre_def = getattr(voces[0], "name", "Predeterminada")
                    self.nombre_voz_activa = f"Plan B: Voz alternativa ({nombre_def})"
                else:
                    self.nombre_voz_activa = "Plan B: Solo burbuja visual"

            self.motor_disponible = True
            return engine
        except Exception:
            self.motor_disponible = False
            self.modo_plan_b = True
            self.nombre_voz_activa = "Plan B: Motor de audio no disponible (Burbuja visual)"
            return None

    @staticmethod
    def _adaptar_texto_plan_b(texto: str) -> str:
        """
        Si el sistema no tiene una voz nativa en español, limpia signos de apertura
        para evitar que motores en otros idiomas los deletreen en voz alta.
        """
        return texto.replace("¡", "").replace("¿", "")

    def _bucle_trabajador_tts(self) -> None:
        engine = self._configurar_motor()

        while self._activo:
            try:
                mensaje = self._cola_mensajes.get(timeout=0.25)
            except queue.Empty:
                continue

            if mensaje is None:
                self._cola_mensajes.task_done()
                break

            if engine is not None and self.motor_disponible:
                try:
                    texto_hablar = (
                        mensaje
                        if self.voz_espanol_encontrada
                        else self._adaptar_texto_plan_b(mensaje)
                    )
                    engine.say(texto_hablar)
                    engine.runAndWait()
                except Exception:
                    # Si el backend de audio falla en ejecución, pasa a Plan B silencioso
                    self.modo_plan_b = True

            self._cola_mensajes.task_done()

        if engine is not None:
            try:
                engine.stop()
            except Exception:
                pass

    def cerrar(self) -> None:
        """Detiene limpiamente el hilo de voz al cerrar el juego."""
        self._activo = False
        self._vaciar_cola()
        self._cola_mensajes.put(None)
        if self._hilo.is_alive():
            self._hilo.join(timeout=1.0)