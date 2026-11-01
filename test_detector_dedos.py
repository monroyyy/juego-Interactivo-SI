"""
test_detector_dedos.py — Pruebas unitarias del contador de dedos, invariancia a
rotación/espejo, estabilización temporal (histéresis + gracia) y reglas de juego.
"""

from __future__ import annotations

import math
import random
import tempfile
from pathlib import Path
from typing import List, Tuple
import unittest

import numpy as np

from camara import GestorCamara
from detector_dedos import (
    DetectorDedos,
    EstabilizadorConteo,
    evaluar_dedos_desde_puntos,
)
from juego_dedos import (
    calcular_estrellas_ronda,
    construir_puntos_simulados,
    generar_secuencia_rondas,
)
from sesion import GestorSesion


def rotar_puntos(
    puntos: List[Tuple[float, float]],
    angulo_grados: float,
    centro: Tuple[float, float] = (0.5, 0.5),
) -> List[Tuple[float, float]]:
    """Rota los 21 puntos de la mano alrededor de `centro` para probar manos inclinadas."""
    rad = math.radians(angulo_grados)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    cx, cy = centro
    rotados: List[Tuple[float, float]] = []
    for x, y in puntos:
        dx = x - cx
        dy = y - cy
        nx = cx + dx * cos_a - dy * sin_a
        ny = cy + dx * sin_a + dy * cos_a
        rotados.append((nx, ny))
    return rotados


def espejar_horizontalmente(
    puntos: List[Tuple[float, float]]
) -> List[Tuple[float, float]]:
    """Invierte la coordenada X (1 - x) para simular mano izquierda/derecha en espejo."""
    return [(1.0 - x, y) for (x, y) in puntos]


class PruebasDetectorDedos(unittest.TestCase):
    """Verifica precisión geométrica, invariancia a rotación y estabilización."""

    def test_conteo_exacto_0_a_5_dedos(self) -> None:
        """Comprueba que los puntos de ejemplo de 0 a 5 dedos se cuenten sin error."""
        for esperado in range(6):
            puntos = construir_puntos_simulados(esperado)
            dedos, _ = evaluar_dedos_desde_puntos(puntos)
            self.assertEqual(
                sum(dedos),
                esperado,
                f"Fallo en mano vertical con {esperado} dedos: se detectaron {sum(dedos)}",
            )

    def test_invariancia_rotacion_mano_inclinada(self) -> None:
        """
        Verifica que al usar distancias respecto a la muñeca y a la base del meñique,
        el conteo funciona incluso con la mano inclinada a 35°, -45°, 90° o 150°.
        """
        angulos = [-60.0, -35.0, 25.0, 45.0, 90.0, 145.0]
        aciertos = 0
        total_pruebas = 0

        for esperado in range(6):
            base = construir_puntos_simulados(esperado)
            for angulo in angulos:
                pts_rotados = rotar_puntos(base, angulo)
                dedos, _ = evaluar_dedos_desde_puntos(pts_rotados)
                total_pruebas += 1
                if sum(dedos) == esperado:
                    aciertos += 1

        precision = aciertos / total_pruebas
        self.assertGreaterEqual(
            precision,
            0.95,
            f"La precisión en rotación ({precision:.2%}) debe superar ampliamente el 85%.",
        )

    def test_mano_izquierda_y_derecha_en_espejo(self) -> None:
        """Verifica que el conteo sea idéntico al espejar horizontalmente la mano."""
        for esperado in range(6):
            pts_derecha = construir_puntos_simulados(esperado)
            pts_izquierda = espejar_horizontalmente(pts_derecha)

            dedos_der, _ = evaluar_dedos_desde_puntos(pts_derecha)
            dedos_izq, _ = evaluar_dedos_desde_puntos(pts_izquierda)

            self.assertEqual(sum(dedos_der), esperado)
            self.assertEqual(sum(dedos_izq), esperado)

    def test_histeresis_voto_mayoria_3_fotogramas(self) -> None:
        """
        Verifica que un fotograma espurio aislado no haga parpadear el conteo
        gracias al voto de mayoría en los últimos 3 fotogramas.
        """
        estabilizador = EstabilizadorConteo(ventana_mayoria=3, frames_gracia=4)

        # Fotograma 1 y 2: niño muestra 3 dedos
        r1 = estabilizador.actualizar_con_deteccion([False, True, True, True, False])
        r2 = estabilizador.actualizar_con_deteccion([False, True, True, True, False])
        self.assertEqual(r1.conteo_estabilizado, 3)
        self.assertEqual(r2.conteo_estabilizado, 3)

        # Fotograma 3: ruido momentáneo de 2 dedos -> mayoría de [3, 3, 2] sigue siendo 3
        r3 = estabilizador.actualizar_con_deteccion([False, True, True, False, False])
        self.assertEqual(r3.conteo_estabilizado, 3)

        # Fotograma 4: el niño realmente cambió a 2 dedos -> ventana [3, 2, 2] -> pasa a 2
        r4 = estabilizador.actualizar_con_deteccion([False, True, True, False, False])
        self.assertEqual(r4.conteo_estabilizado, 2)

    def test_periodo_gracia_4_fotogramas_sin_mano(self) -> None:
        """
        Verifica que si se pierde la mano hasta por 4 fotogramas se conserva el conteo,
        y en el 5.º fotograma sin mano pasa a no detectada (conteo 0).
        """
        detector = DetectorDedos()
        pts_4 = construir_puntos_simulados(4)

        detector.procesar_puntos(pts_4)
        res = detector.procesar_puntos(pts_4)
        self.assertTrue(res.mano_detectada)
        self.assertEqual(res.conteo_estabilizado, 4)

        # 4 fotogramas de gracia perdidos
        for i in range(1, 5):
            res_gracia = detector.procesar_puntos(None)
            self.assertTrue(
                res_gracia.mano_detectada,
                f"En fotograma perdido {i}/4 debería seguir en periodo de gracia",
            )
            self.assertTrue(res_gracia.en_periodo_gracia)
            self.assertEqual(res_gracia.conteo_estabilizado, 4)

        # 5.º fotograma sin mano: termina el periodo de gracia
        res_perdida = detector.procesar_puntos(None)
        self.assertFalse(res_perdida.mano_detectada)
        self.assertEqual(res_perdida.conteo_estabilizado, 0)

    def test_secuencia_5_rondas_sin_repetidos_consecutivos(self) -> None:
        """Comprueba 100 partidas generadas: 5 rondas, valores 1..5 y sin repetidos seguidos."""
        rng = random.Random(42)
        for _ in range(100):
            rondas = generar_secuencia_rondas(5, rng=rng)
            self.assertEqual(len(rondas), 5)
            for n in rondas:
                self.assertIn(n, (1, 2, 3, 4, 5))
            for i in range(1, len(rondas)):
                self.assertNotEqual(
                    rondas[i],
                    rondas[i - 1],
                    f"Se repitió el número en rondas consecutivas: {rondas}",
                )
            # Primeras rondas bajas (1 o 2) y últimas altas (4 o 5)
            self.assertIn(rondas[0], (1, 2))
            self.assertIn(rondas[-1], (4, 5))

    def test_reglas_estrellas_y_calibracion_luz_y_sesion_json(self) -> None:
        """Verifica el cálculo de estrellas, el ajuste CLAHE y el guardado JSON sin imágenes."""
        self.assertEqual(calcular_estrellas_ronda(4.2, intentos_fallidos=0, uso_pista=False), 3)
        self.assertEqual(calcular_estrellas_ronda(10.8, intentos_fallidos=0, uso_pista=False), 2)
        self.assertEqual(calcular_estrellas_ronda(6.0, intentos_fallidos=1, uso_pista=False), 2)
        self.assertEqual(calcular_estrellas_ronda(12.5, intentos_fallidos=0, uso_pista=True), 1)

        # Calibración CLAHE en fotograma oscuro
        cam = GestorCamara(indice_camara=-1)
        frame_oscuro = np.full((120, 160, 3), 25, dtype=np.uint8)
        frame_corr, brillo, ajustando = cam.calibrar_iluminacion(frame_oscuro)
        self.assertTrue(ajustando)
        self.assertLess(brillo, 75.0)
        self.assertEqual(frame_corr.shape, frame_oscuro.shape)

        # Persistencia JSON
        with tempfile.TemporaryDirectory() as tmpdir:
            ruta_json = Path(tmpdir) / "test_sesiones.json"
            gestor = GestorSesion(perfil="Nino_Prueba", ruta_archivo=ruta_json)
            gestor.registrar_ronda(
                numero_ronda=1,
                numero_pedido=2,
                numero_detectado=2,
                aciertos=1,
                intentos=1,
                tiempo_respuesta_seg=3.4,
                estrellas=3,
                uso_pista=False,
            )
            gestor.finalizar_sesion()
            historial = gestor.cargar_historial()
            self.assertIn("Nino_Prueba", historial["perfiles"])
            sesion_guardada = historial["perfiles"]["Nino_Prueba"][0]
            self.assertEqual(sesion_guardada["total_estrellas"], 3)
            self.assertEqual(len(sesion_guardada["rondas"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)