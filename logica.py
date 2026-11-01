"""
logica.py — Reglas puras del juego "Cuenta con tus dedos" (sin pygame ni cámara).
Se mantienen aparte para poder probarlas con pruebas unitarias.
"""

from __future__ import annotations

import random
from typing import List, Optional, Sequence, Tuple

import config


def generar_secuencia_rondas(
    total_rondas: int = config.TOTAL_RONDAS,
    pools_dificultad: Optional[Sequence[Sequence[int]]] = None,
    rng: Optional[random.Random] = None,
) -> List[int]:
    """
    Genera una secuencia de `total_rondas` números (de 1 a 5) que:
    1. Empieza con números bajos en las primeras rondas y sube la dificultad
       gradualmente según `POOLS_DIFICULTAD_RONDAS`.
    2. Garantiza que NUNCA se repita el mismo número dos veces seguidas.
    """
    generador = rng or random.Random()
    pools = list(pools_dificultad or config.POOLS_DIFICULTAD_RONDAS)

    secuencia: List[int] = []
    for indice in range(total_rondas):
        pool_actual = list(pools[min(indice, len(pools) - 1)])
        if secuencia:
            ultimo = secuencia[-1]
            opciones = [n for n in pool_actual if n != ultimo]
            if not opciones:
                opciones = [
                    n
                    for n in range(config.NUMERO_MIN, config.NUMERO_MAX + 1)
                    if n != ultimo
                ]
        else:
            opciones = pool_actual

        elegido = generador.choice(opciones)
        secuencia.append(elegido)

    return secuencia


def calcular_estrellas_ronda(
    tiempo_respuesta_seg: float,
    intentos_fallidos: int,
    uso_pista: bool,
) -> int:
    """
    Calcula las estrellas ganadas en la ronda según las reglas pedagógicas:
    - 3 estrellas: si acierta a la primera (sin intentos fallidos previos),
      sin necesitar pista y en <= 10 segundos.
    - 2 estrellas: si tarda más de 10 segundos (sin llegar a usar la pista de 12s)
      o tuvo algún intento fallido antes de la pista.
    - 1 estrella: si necesitó la pista (>= 12 segundos).
    """
    if uso_pista or tiempo_respuesta_seg >= config.TIEMPO_ACTIVAR_PISTA_SEG:
        return 1
    if intentos_fallidos == 0 and tiempo_respuesta_seg <= config.TIEMPO_MAX_TRES_ESTRELLAS_SEG:
        return 3
    return 2


def calcular_estrellas_finales(estrellas_rondas: Sequence[int]) -> int:
    """
    Resume una partida completa en 1..3 estrellas (las que muestra el mockup 07):
    es el promedio de las estrellas de cada ronda, redondeado al entero más cercano.
    Sin rondas jugadas devuelve 0.
    """
    if not estrellas_rondas:
        return 0
    promedio = sum(estrellas_rondas) / len(estrellas_rondas)
    return max(1, min(3, int(promedio + 0.5)))


def construir_puntos_simulados(cantidad_dedos: int) -> List[Tuple[float, float]]:
    """
    Genera una mano sintética normalizada (21 landmarks) con `cantidad_dedos` (0..5)
    extendidos. Permite probar la lógica completa incluso si el equipo no tiene
    cámara física conectada (usando las teclas 0 a 5).
    """
    puntos: List[Tuple[float, float]] = [(0.5, 0.78)] * 21
    # Muñeca (0)
    puntos[0] = (0.50, 0.82)

    # Nudillos base (MCP)
    puntos[1] = (0.41, 0.75)
    puntos[2] = (0.36, 0.68)
    puntos[5] = (0.43, 0.58)
    puntos[9] = (0.49, 0.56)
    puntos[13] = (0.55, 0.58)
    puntos[17] = (0.61, 0.61)

    # Pulgar (se extiende en el número 5)
    if cantidad_dedos >= 5:
        puntos[3] = (0.30, 0.62)
        puntos[4] = (0.21, 0.55)
    else:
        puntos[3] = (0.43, 0.66)
        puntos[4] = (0.47, 0.65)

    # Dedos largos: Índice (1), Medio (2), Anular (3), Meñique (4)
    config_dedos = [
        (1, 5, 6, 7, 8, 0.42),
        (2, 9, 10, 11, 12, 0.49),
        (3, 13, 14, 15, 16, 0.56),
        (4, 17, 18, 19, 20, 0.63),
    ]
    for orden, mcp, pip, dip, tip, x_col in config_dedos:
        y_mcp = puntos[mcp][1]
        if cantidad_dedos >= orden:
            puntos[pip] = (x_col, y_mcp - 0.10)
            puntos[dip] = (x_col, y_mcp - 0.19)
            puntos[tip] = (x_col, y_mcp - 0.28)
        else:
            puntos[pip] = (x_col, y_mcp - 0.07)
            puntos[dip] = (x_col, y_mcp - 0.03)
            puntos[tip] = (x_col, y_mcp - 0.01)

    return puntos
