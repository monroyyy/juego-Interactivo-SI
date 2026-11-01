"""
componentes.py — Primitivas de dibujo y widgets del sistema de diseño
(Mockup_Figma_2.3/00_Estilos). Las coordenadas coinciden con los SVG del mockup,
sobre un lienzo de 1920x1080.
"""

from __future__ import annotations

from functools import lru_cache
import math
from typing import Any, List, Optional, Sequence, Tuple

import pygame
from pygame import gfxdraw

import config

Color = Tuple[int, int, int]
Punto = Tuple[float, float]

TINTA = config.COLOR_TINTA
BLANCO = (255, 255, 255)


# =============================================================================
# PRIMITIVAS GEOMÉTRICAS
# =============================================================================
def disco(
    sup: Any,
    centro: Punto,
    radio: float,
    relleno: Optional[Color] = None,
    borde: Optional[Color] = None,
    ancho: int = 0,
) -> None:
    """Círculo suavizado (anti-alias) con borde opcional."""
    x, y, r = int(centro[0]), int(centro[1]), int(round(radio))
    if r <= 0:
        return
    if borde is not None and ancho > 0:
        gfxdraw.filled_circle(sup, x, y, r, borde)
        gfxdraw.aacircle(sup, x, y, r, borde)
        r2 = r - ancho
        if relleno is not None and r2 > 0:
            gfxdraw.filled_circle(sup, x, y, r2, relleno)
            gfxdraw.aacircle(sup, x, y, r2, relleno)
    elif relleno is not None:
        gfxdraw.filled_circle(sup, x, y, r, relleno)
        gfxdraw.aacircle(sup, x, y, r, relleno)


def caja(
    sup: Any,
    rect: Any,
    relleno: Optional[Color] = None,
    borde: Optional[Color] = None,
    ancho: int = 4,
    radio: int = 40,
) -> None:
    """Rectángulo redondeado con relleno y/o borde."""
    rect = pygame.Rect(rect)
    radio = max(0, int(radio))
    ancho = int(ancho)
    if borde is not None and ancho > 0:
        if relleno is not None:
            pygame.draw.rect(sup, borde, rect, border_radius=radio)
            interior = rect.inflate(-2 * ancho, -2 * ancho)
            if interior.width > 0 and interior.height > 0:
                pygame.draw.rect(
                    sup, relleno, interior, border_radius=max(0, radio - ancho)
                )
        else:
            pygame.draw.rect(sup, borde, rect, width=ancho, border_radius=radio)
    elif relleno is not None:
        pygame.draw.rect(sup, relleno, rect, border_radius=radio)


def trazo(
    sup: Any, color: Color, puntos: Sequence[Punto], ancho: float, cerrado: bool = False
) -> None:
    """Polilínea gruesa con uniones y extremos redondeados."""
    pts = [(int(x), int(y)) for x, y in puntos]
    ancho_i = max(1, int(round(ancho)))
    pares = list(zip(pts[:-1], pts[1:]))
    if cerrado and len(pts) > 2:
        pares.append((pts[-1], pts[0]))
    for a, b in pares:
        pygame.draw.line(sup, color, a, b, ancho_i)
    for p in pts:
        disco(sup, p, ancho_i / 2, color)


def poligono(
    sup: Any,
    puntos: Sequence[Punto],
    relleno: Optional[Color] = None,
    borde: Optional[Color] = None,
    ancho: float = 4,
) -> None:
    pts = [(int(x), int(y)) for x, y in puntos]
    if relleno is not None:
        gfxdraw.filled_polygon(sup, pts, relleno)
        gfxdraw.aapolygon(sup, pts, relleno)
    if borde is not None and ancho > 0:
        trazo(sup, borde, pts, ancho, cerrado=True)


def curva_cuadratica(p0: Punto, p1: Punto, p2: Punto, n: int = 16) -> List[Punto]:
    pts: List[Punto] = []
    for i in range(n + 1):
        t = i / n
        pts.append(
            (
                (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1],
            )
        )
    return pts


def elipse_rotada(
    sup: Any,
    color: Color,
    centro: Punto,
    rx: float,
    ry: float,
    angulo_svg_grados: float = 0.0,
    borde: Optional[Color] = None,
    ancho: float = 0,
) -> None:
    """Elipse rotada (misma convención que `rotate()` de SVG: positivo = horario)."""
    margen = int(ancho) + 4
    w, h = int(2 * rx) + 2 * margen, int(2 * ry) + 2 * margen
    tmp = pygame.Surface((w, h), pygame.SRCALPHA)
    rect = pygame.Rect(margen, margen, int(2 * rx), int(2 * ry))
    if borde is not None and ancho > 0:
        pygame.draw.ellipse(tmp, borde, rect.inflate(2 * ancho, 2 * ancho))
    pygame.draw.ellipse(tmp, color, rect)
    if angulo_svg_grados:
        tmp = pygame.transform.rotozoom(tmp, -angulo_svg_grados, 1.0)
    sup.blit(tmp, tmp.get_rect(center=(int(centro[0]), int(centro[1]))))


@lru_cache(maxsize=64)
def _perimetro_redondeado(
    x: int, y: int, w: int, h: int, r: int, paso: float = 3.0
) -> Tuple[Tuple[Tuple[int, int], ...], Tuple[float, ...]]:
    r = max(0, min(r, w // 2, h // 2))
    pts: List[Tuple[float, float]] = []

    def linea(a: Punto, b: Punto) -> None:
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / paso))
        for i in range(n):
            t = i / n
            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))

    def arco(c: Punto, a0: float, a1: float) -> None:
        n = max(2, int(r * math.pi / 2 / paso))
        for i in range(n):
            a = math.radians(a0 + (a1 - a0) * i / n)
            pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))

    linea((x + r, y), (x + w - r, y))
    arco((x + w - r, y + r), -90, 0)
    linea((x + w, y + r), (x + w, y + h - r))
    arco((x + w - r, y + h - r), 0, 90)
    linea((x + w - r, y + h), (x + r, y + h))
    arco((x + r, y + h - r), 90, 180)
    linea((x, y + h - r), (x, y + r))
    arco((x + r, y + r), 180, 270)

    acum: List[float] = [0.0]
    for i in range(1, len(pts)):
        acum.append(
            acum[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        )
    return tuple((int(px), int(py)) for px, py in pts), tuple(acum)


def rect_punteado(
    sup: Any,
    color: Color,
    rect: Any,
    radio: int = 24,
    ancho: int = 6,
    trazo_px: int = 24,
    hueco_px: int = 16,
) -> None:
    """Rectángulo redondeado de línea punteada (marco guía del mockup)."""
    rect = pygame.Rect(rect)
    pts, acum = _perimetro_redondeado(rect.x, rect.y, rect.w, rect.h, radio)
    periodo = trazo_px + hueco_px
    n = len(pts)
    for i in range(n):
        if (acum[i] % periodo) < trazo_px:
            pygame.draw.line(sup, color, pts[i], pts[(i + 1) % n], ancho)


# =============================================================================
# TEXTO
# =============================================================================
def texto(
    sup: Any,
    fuente: Any,
    cadena: str,
    color: Color,
    x: float,
    y_base: float,
    ancla: str = "centro",
) -> int:
    """Dibuja texto usando la línea base (igual que el atributo `y` del SVG)."""
    img = fuente.render(cadena, True, color)
    arriba = int(y_base - fuente.get_ascent())
    if ancla == "centro":
        px = int(x - img.get_width() / 2)
    elif ancla == "der":
        px = int(x - img.get_width())
    else:
        px = int(x)
    sup.blit(img, (px, arriba))
    return img.get_width()


def texto_centrado_vertical(
    sup: Any, fuente: Any, cadena: str, color: Color, x: float, cy: float, tam: int,
    ancla: str = "centro",
) -> int:
    """Centra visualmente (altura de mayúsculas) el texto alrededor de `cy`."""
    return texto(sup, fuente, cadena, color, x, cy + 0.36 * tam, ancla)


def fuente_que_cabe(
    ventana: Any, cadena: str, tam: int, ancho_max: int, negrita: bool = True, minimo: int = 20
) -> Any:
    """Reduce el tamaño de la fuente hasta que el texto quepa en `ancho_max`."""
    t = tam
    while t > minimo:
        f = ventana.fuente(t, negrita)
        if f.size(cadena)[0] <= ancho_max:
            return f
        t -= 2
    return ventana.fuente(minimo, negrita)


def recortar_texto(fuente: Any, cadena: str, ancho_max: int) -> str:
    if fuente.size(cadena)[0] <= ancho_max:
        return cadena
    while cadena and fuente.size(cadena + "…")[0] > ancho_max:
        cadena = cadena[:-1]
    return cadena + "…"


# =============================================================================
# ÍCONOS VECTORIALES (geometría de los SVG, centrados en (cx, cy))
# =============================================================================
def _xf(cx: float, cy: float, s: float):
    return lambda p: (cx + p[0] * s, cy + p[1] * s)


def icono_casa(sup: Any, cx: float, cy: float, s: float, color: Color = TINTA, puerta: Color = BLANCO) -> None:
    t = _xf(cx, cy, s)
    poligono(sup, [t((-44, 0)), t((0, -42)), t((44, 0))], color, color, 6 * s)
    a = t((-30, -2))
    caja(sup, pygame.Rect(int(a[0]), int(a[1]), int(60 * s), int(44 * s)), color, radio=int(6 * s))
    p = t((-9, 16))
    caja(sup, pygame.Rect(int(p[0]), int(p[1]), int(18 * s), int(26 * s)), puerta, radio=int(3 * s))


def icono_bocina(sup: Any, cx: float, cy: float, s: float, color: Color = TINTA) -> None:
    t = _xf(cx, cy, s)
    poligono(
        sup,
        [t(p) for p in ((-38, -16), (-16, -16), (12, -40), (12, 40), (-16, 16), (-38, 16))],
        color,
    )
    trazo(sup, color, [t(p) for p in curva_cuadratica((28, -22), (46, 0), (28, 22))], 8 * s)
    trazo(sup, color, [t(p) for p in curva_cuadratica((40, -38), (70, 0), (40, 38))], 8 * s)


def icono_candado(sup: Any, cx: float, cy: float, s: float, color: Color = TINTA, hueco: Color = BLANCO) -> None:
    t = _xf(cx, cy, s)
    a = t((-32, -4))
    caja(sup, pygame.Rect(int(a[0]), int(a[1]), int(64 * s), int(46 * s)), color, radio=int(9 * s))
    arco = [(-19, -4), (-19, -22)]
    for ang in range(180, 361, 10):
        arco.append((19 * math.cos(math.radians(ang)), -22 + 19 * math.sin(math.radians(ang))))
    arco += [(19, -22), (19, -4)]
    trazo(sup, color, [t(p) for p in arco], 9 * s)
    disco(sup, t((0, 20)), 7 * s, hueco)


def icono_check(sup: Any, cx: float, cy: float, s: float, color: Color = BLANCO) -> None:
    t = _xf(cx, cy, s)
    trazo(sup, color, [t(p) for p in ((-32, 2), (-10, 24), (34, -24))], 14 * s)


def icono_repetir(sup: Any, cx: float, cy: float, s: float, color: Color = TINTA) -> None:
    t = _xf(cx, cy, s)
    pts = []
    ang = -25.0
    while ang >= -324.5:
        pts.append((34 * math.cos(math.radians(ang)), 34 * math.sin(math.radians(ang))))
        ang -= 8
    trazo(sup, color, [t(p) for p in pts], 11 * s)
    poligono(sup, [t((38, -40)), t((38, 0)), t((6, -14))], color, color, 3 * s)


def icono_siguiente(sup: Any, cx: float, cy: float, s: float, color: Color = BLANCO) -> None:
    t = _xf(cx, cy, s)
    trazo(sup, color, [t((-38, 0)), t((26, 0))], 12 * s)
    poligono(sup, [t((24, -28)), t((56, 0)), t((24, 28))], color, color, 3 * s)


def icono_caret(sup: Any, cx: float, cy: float, color: Color = TINTA) -> None:
    poligono(sup, [(cx - 11, cy - 8), (cx + 11, cy - 8), (cx, cy + 8)], color, color, 2)


def icono(sup: Any, nombre: str, cx: float, cy: float, s: float, color: Color, fondo: Color = BLANCO) -> None:
    if nombre == "casa":
        icono_casa(sup, cx, cy + 2 * s, s, color, fondo)
    elif nombre == "bocina":
        icono_bocina(sup, cx - 2 * s, cy, s, color)
    elif nombre == "candado":
        icono_candado(sup, cx, cy, s, color, fondo)
    elif nombre == "repetir":
        icono_repetir(sup, cx, cy, s, color)
    elif nombre == "siguiente":
        icono_siguiente(sup, cx, cy, s, color)
    elif nombre == "check":
        icono_check(sup, cx, cy, s, color)


# =============================================================================
# FORMAS DECORATIVAS: estrellas, confeti, búho, animales de perfil
# =============================================================================
def puntos_estrella(cx: float, cy: float, radio: float) -> List[Punto]:
    pts: List[Punto] = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = radio if i % 2 == 0 else radio * 0.45
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return pts


def estrella(
    sup: Any, cx: float, cy: float, radio: float, activa: bool = True, ancho: float = 6,
    relleno: Color = config.COLOR_AMARILLO,
) -> None:
    poligono(sup, puntos_estrella(cx, cy, radio), relleno if activa else None, TINTA, ancho)


_CONFETI = (
    ("circulo", 220, 330, config.COLOR_ROJO),
    ("cuadrado", 330, 520, config.COLOR_AZUL),
    ("triangulo", 180, 640, config.COLOR_AMARILLO),
    ("estrella", 440, 270, config.COLOR_VERDE),
    ("circulo", 560, 600, config.COLOR_AZUL),
    ("circulo", 1700, 320, config.COLOR_AMARILLO),
    ("triangulo", 1560, 540, config.COLOR_ROJO),
    ("cuadrado", 1740, 640, config.COLOR_VERDE),
    ("estrella", 1480, 270, config.COLOR_AZUL),
    ("circulo", 1360, 610, config.COLOR_ROJO),
    ("cuadrado", 700, 420, config.COLOR_AMARILLO),
    ("triangulo", 1230, 430, config.COLOR_AZUL),
)


def dibujar_confeti(sup: Any, t: float) -> None:
    """Confeti de formas (mockup 07) con un suave balanceo."""
    for i, (tipo, x, y, color) in enumerate(_CONFETI):
        yy = y + 7 * math.sin(t * 1.8 + i * 1.3)
        if tipo == "circulo":
            disco(sup, (x, yy), 18, color)
        elif tipo == "cuadrado":
            caja(sup, pygame.Rect(int(x - 16), int(yy - 16), 32, 32), color, radio=3)
        elif tipo == "triangulo":
            poligono(sup, [(x, yy - 20), (x + 20, yy + 16), (x - 20, yy + 16)], color)
        else:
            poligono(sup, puntos_estrella(x, yy, 21), color)


def dibujar_buho(sup: Any, cx: float, cy: float, escala: float = 1.0, t: float = 0.0) -> None:
    """Mascota del mockup 07, centrada en (cx, cy) = centro del cuerpo."""
    cy = cy + 6 * math.sin(t * 2.2)

    def p(dx: float, dy: float) -> Punto:
        return (cx + dx * escala, cy + dy * escala)

    oscuro, claro, panza, pico = (18, 138, 132), config.COLOR_APOYO, (191, 240, 236), (245, 165, 36)
    elipse_rotada(sup, oscuro, p(-120.75, -57.5), 27.6 * escala, 63.25 * escala, 28)
    elipse_rotada(sup, oscuro, p(120.75, -57.5), 27.6 * escala, 63.25 * escala, -28)
    poligono(sup, [p(-92, -69), p(-74.8, -138), p(-23, -105.8)], claro)
    poligono(sup, [p(92, -69), p(74.8, -138), p(23, -105.8)], claro)
    elipse_rotada(sup, claro, p(0, 0), 115 * escala, 126.5 * escala)
    elipse_rotada(sup, panza, p(0, 40.25), 71.3 * escala, 80.5 * escala)
    for sx in (-41.4, 41.4):
        disco(sup, p(sx, -32.2), 31.05 * escala, BLANCO, TINTA, max(2, int(4 * escala)))
        disco(sup, p(sx, -29.9), 13.8 * escala, TINTA)
    poligono(sup, [p(-12.6, -2.3), p(12.6, -2.3), p(0, 25.3)], pico)
    elipse_rotada(sup, pico, p(-34.5, 128.8), 29.9 * escala, 11.5 * escala)
    elipse_rotada(sup, pico, p(34.5, 128.8), 29.9 * escala, 11.5 * escala)


def _mezclar(a: Color, b: Color, k: float) -> Color:
    return (
        int(a[0] * (1 - k) + b[0] * k),
        int(a[1] * (1 - k) + b[1] * k),
        int(a[2] * (1 - k) + b[2] * k),
    )


def dibujar_animal(sup: Any, tipo: str, cx: float, cy: float, color: Color, s: float = 1.0) -> None:
    """Cara de animal de los perfiles (mockup 01). (cx, cy) = centro de la cara."""
    borde = max(2, int(4 * s))

    def p(dx: float, dy: float) -> Punto:
        return (cx + dx * s, cy + dy * s)

    # Orejas (detrás de la cara)
    if tipo == "gato":
        for sg in (-1, 1):
            poligono(sup, [p(sg * 102, -24), p(sg * 84, -138), p(sg * 12, -96)], color, TINTA, borde)
    elif tipo == "oso":
        for sg in (-1, 1):
            disco(sup, p(sg * 86.4, -93.6), 36 * s, color, TINTA, borde)
    else:  # conejo
        for sg in (-1, 1):
            elipse_rotada(sup, color, p(sg * 50.4, -120), 24 * s, 74.4 * s, 0, TINTA, borde)

    disco(sup, (cx, cy), 120 * s, color, TINTA, borde)
    mejilla = _mezclar(color, BLANCO, 0.55)
    for sg in (-1, 1):
        disco(sup, p(sg * 72, 24), 14.4 * s, mejilla)
        disco(sup, p(sg * 43.2, -14.4), 12 * s, TINTA)
    elipse_rotada(sup, TINTA, p(0, 14.4), 12 * s, 8.4 * s)
    boca = curva_cuadratica(p(-33.6, 40.8), p(0, 74.4), p(33.6, 40.8))
    trazo(sup, TINTA, boca, 5 * s)


# =============================================================================
# WIDGETS
# =============================================================================
class Boton:
    """Zona interactiva con estados hover / presionado / deshabilitado."""

    def __init__(self, hit: Any, habilitado: bool = True) -> None:
        self.hit = pygame.Rect(hit)
        self.habilitado = habilitado
        self.hover = False
        self.presionado = False
        self._armado = False

    def actualizar(self, pos: Optional[Tuple[int, int]]) -> None:
        dentro = bool(pos is not None and self.habilitado and self.hit.collidepoint(pos))
        self.hover = dentro
        self.presionado = self._armado and dentro

    def procesar(self, ev: Any, pos: Optional[Tuple[int, int]]) -> bool:
        """Devuelve True cuando se completa un clic (soltar dentro del botón)."""
        if not self.habilitado or pos is None:
            return False
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.hit.collidepoint(pos):
                self._armado = True
                self.presionado = True
            return False
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            clic = self._armado and self.hit.collidepoint(pos)
            self._armado = False
            self.presionado = False
            return clic
        return False


class BotonRedondo(Boton):
    """Botón circular del encabezado (r = 52) con etiqueta debajo (mockup)."""

    def __init__(self, centro: Tuple[int, int], nombre_icono: str, etiqueta: str) -> None:
        cx, cy = centro
        # Área táctil >= 160 px aunque el dibujo sea de 104 px
        super().__init__(pygame.Rect(cx - 80, cy - 60, 160, 160))
        self.centro = centro
        self.nombre_icono = nombre_icono
        self.etiqueta = etiqueta

    def dibujar(self, sup: Any, ventana: Any) -> None:
        cx, cy = self.centro
        radio = 49 if self.presionado else 52
        if self.presionado:
            fondo = (222, 229, 250)
        elif self.hover:
            fondo = (241, 244, 255)
        else:
            fondo = BLANCO
        disco(sup, (cx, cy), radio, fondo, TINTA, 4)
        icono(sup, self.nombre_icono, cx, cy + 2, 0.76 if self.nombre_icono != "candado" else 0.7, TINTA, fondo)
        texto(sup, ventana.fuente(24, False), self.etiqueta, config.COLOR_TEXTO_SUAVE, cx, cy + 86)


class BotonFlecha(Boton):
    """Botón circular táctil para navegación de páginas (anterior/siguiente)."""

    def __init__(self, centro: Tuple[int, int], direccion: str = "der", radio: int = 44) -> None:
        cx, cy = centro
        super().__init__(pygame.Rect(cx - 55, cy - 55, 110, 110))
        self.centro = centro
        self.direccion = direccion
        self.radio = radio

    def dibujar(self, sup: Any) -> None:
        cx, cy = self.centro
        r = self.radio - (3 if self.presionado else 0)
        fondo = (220, 230, 255) if self.presionado else ((240, 245, 255) if self.hover else BLANCO)
        disco(sup, (cx, cy), r, fondo, TINTA, 4)
        if self.direccion == "der":
            poligono(sup, [(cx - 8, cy - 18), (cx + 14, cy), (cx - 8, cy + 18)], TINTA, TINTA, 2)
        else:
            poligono(sup, [(cx + 8, cy - 18), (cx - 14, cy), (cx + 8, cy + 18)], TINTA, TINTA, 2)


class BotonPildora(Boton):
    """Botón en píldora: azul, verde o con borde (Normal / Hover / Presionado / Deshabilitado)."""

    def __init__(
        self,
        rect: Any,
        etiqueta: str,
        variante: str = "azul",
        nombre_icono: Optional[str] = None,
        icono_a_la_izquierda: bool = True,
        tam_fuente: int = 46,
    ) -> None:
        rect = pygame.Rect(rect)
        rect.width = max(rect.width, config.TAMANO_MIN_BOTON_PX)
        super().__init__(rect)
        self.rect = rect
        self.etiqueta = etiqueta
        self.variante = variante
        self.nombre_icono = nombre_icono
        self.icono_izq = icono_a_la_izquierda
        self.tam_fuente = tam_fuente

    def dibujar(self, sup: Any, ventana: Any) -> None:
        r = self.rect
        borde: Optional[Color] = None
        if not self.habilitado:
            fondo, color_txt = config.COLOR_BOTON_DESHABILITADO, config.COLOR_TEXTO_DESHABILITADO
        elif self.variante == "borde":
            color_txt, borde = TINTA, TINTA
            fondo = (225, 231, 250) if self.presionado else ((241, 244, 255) if self.hover else BLANCO)
        elif self.variante == "verde":
            color_txt = BLANCO
            fondo = (
                config.COLOR_VERDE_PRESIONADO if self.presionado
                else config.COLOR_VERDE_HOVER if self.hover
                else config.COLOR_VERDE
            )
        else:
            color_txt = BLANCO
            fondo = (
                config.COLOR_BOTON_PRESIONADO if self.presionado
                else config.COLOR_BOTON_HOVER if self.hover
                else config.COLOR_BOTON_PRIMARIO
            )

        caja(sup, r, fondo, borde, 5, r.height // 2)
        fuente = ventana.fuente(self.tam_fuente, True)
        k = r.height / 120.0
        if self.nombre_icono and self.icono_izq:
            icono(sup, self.nombre_icono, r.left + 0.667 * r.height, r.centery, 0.72 * k, color_txt, fondo)
            texto_centrado_vertical(sup, fuente, self.etiqueta, color_txt, r.left + 0.671 * r.width, r.centery, self.tam_fuente)
        elif self.nombre_icono:
            texto_centrado_vertical(sup, fuente, self.etiqueta, color_txt, r.left + 0.355 * r.width, r.centery, self.tam_fuente)
            icono(sup, self.nombre_icono, r.left + 0.816 * r.width, r.centery, 0.72 * k, color_txt, fondo)
        else:
            texto_centrado_vertical(sup, fuente, self.etiqueta, color_txt, r.centerx, r.centery, self.tam_fuente)


def dibujar_pildora_estado(
    sup: Any, ventana: Any, rect: Any, cadena: str, color_fondo: Color, con_check: bool = True, tam: int = 38
) -> None:
    """Etiqueta de estado (p. ej. «Veo 3 dedos» o «Conectado»), no interactiva."""
    rect = pygame.Rect(rect)
    caja(sup, rect, color_fondo, radio=rect.height // 2)
    fuente = ventana.fuente(tam, True)
    if con_check:
        icono_check(sup, rect.left + 56, rect.centery, 0.46, BLANCO)
        texto_centrado_vertical(sup, fuente, cadena, BLANCO, rect.left + 0.656 * rect.width, rect.centery, tam)
    else:
        texto_centrado_vertical(sup, fuente, cadena, BLANCO, rect.centerx, rect.centery, tam)


def dibujar_burbuja_narrador(sup: Any, ventana: Any, cadena: str) -> None:
    """Burbuja del narrador (x 410..1510, y 950..1034) con borde turquesa."""
    rect = pygame.Rect(410, 950, 1100, 84)
    caja(sup, rect, BLANCO, config.COLOR_APOYO, 5, 42)
    icono_bocina(sup, 482, 992, 0.52, config.COLOR_APOYO)
    ancho_disp = rect.right - 40 - 540
    fuente = fuente_que_cabe(ventana, cadena, 40, ancho_disp, True, 28)
    cadena = recortar_texto(fuente, cadena, ancho_disp)
    texto(sup, fuente, cadena, TINTA, 540, 1004, "izq")


def dibujar_barra_progreso(
    sup: Any, rect: Any, fraccion: float, fondo: Color, relleno: Color
) -> None:
    rect = pygame.Rect(rect)
    caja(sup, rect, fondo, radio=rect.height // 2)
    fraccion = max(0.0, min(1.0, fraccion))
    if fraccion > 0:
        ancho = max(rect.height, int(rect.width * fraccion))
        caja(sup, pygame.Rect(rect.x, rect.y, ancho, rect.height), relleno, radio=rect.height // 2)
