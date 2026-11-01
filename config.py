"""
config.py — Parámetros ajustables para el JUEGO 1: "Cuenta con tus dedos".
Sistema interactivo educativo para niños de 4 a 6 años.
"""

from pathlib import Path

DIRECTORIO_PROYECTO = Path(__file__).resolve().parent
DIRECTORIO_ASSETS = DIRECTORIO_PROYECTO / "assets"

# =============================================================================
# 1. PANTALLA Y RENDIMIENTO
# =============================================================================
TITULO_VENTANA = "Cuenta con tus dedos — Juego Educativo (4 a 6 años)"
ANCHO_BASE = 1920
ALTO_BASE = 1080
FPS = 30
PANTALLA_COMPLETA_INICIAL = False  # Presionar F11 alterna pantalla completa

# Tamaño mínimo de botones interactivos para motricidad infantil (4-6 años)
TAMANO_MIN_BOTON_PX = 160

# =============================================================================
# 2. PALETA DE COLORES (RGB) — tomada de Mockup_Figma_2.3/00_Estilos
# =============================================================================
COLOR_TINTA = (27, 37, 64)               # #1B2540 — Texto y bordes
COLOR_FONDO = (255, 248, 234)            # #FFF8EA — Fondo crema cálido
COLOR_AZUL = (62, 99, 221)               # #3E63DD
COLOR_ROJO = (217, 48, 54)               # #D93036
COLOR_AMARILLO = (247, 198, 0)           # #F7C600
COLOR_VERDE = (43, 154, 102)             # #2B9A66
COLOR_APOYO = (25, 167, 160)             # #19A7A0 — Turquesa (narrador, puntos de dedos)
COLOR_TEXTO_SUAVE = (95, 104, 132)       # #5F6884

# Alias semánticos (se conservan los nombres usados antes en el proyecto)
COLOR_TEXTO = COLOR_TINTA
COLOR_AZUL_NUMERO = COLOR_AZUL
COLOR_TARJETA = (255, 255, 255)          # Superficie de tarjetas
COLOR_BORDE_TARJETA = COLOR_TINTA        # Las tarjetas del mockup llevan borde tinta
COLOR_VERDE_ETIQUETA = COLOR_VERDE
COLOR_AMARILLO_ESTRELLA = COLOR_AMARILLO

# Superficies específicas del mockup
COLOR_CIRCULO_CLARO = (228, 234, 255)    # #E4EAFF — Círculo bajo el número objetivo
COLOR_PANEL_OSCURO = (38, 48, 79)        # #26304F — Panel donde se dibuja la mano
COLOR_NARANJA_PISTA = (245, 130, 32)     # #F58220 — Dedos que faltan en la pista
COLOR_BARRA_FONDO = (233, 227, 211)      # #E9E3D3 — Fondo de barras de progreso
COLOR_FONDO_ADULTOS = (244, 246, 251)    # #F4F6FB — Vista para adultos
COLOR_BORDE_ADULTOS = (213, 218, 232)    # #D5DAE8
COLOR_BARRA_ADULTOS = (233, 236, 245)    # #E9ECF5

# Botones (Estilos: Normal / Hover / Presionado / Deshabilitado)
COLOR_BOTON_PRIMARIO = COLOR_AZUL
COLOR_BOTON_HOVER = (47, 79, 196)        # #2F4FC4
COLOR_BOTON_PRESIONADO = (31, 60, 156)   # #1F3C9C
COLOR_BOTON_DESHABILITADO = (213, 216, 229)
COLOR_TEXTO_DESHABILITADO = (140, 147, 170)
COLOR_VERDE_HOVER = (35, 128, 87)
COLOR_VERDE_PRESIONADO = (27, 105, 71)

# La mano ilustrada (mockups 03/04)
COLOR_PIEL = (243, 201, 165)             # #F3C9A5
COLOR_PIEL_CONTORNO = (201, 154, 116)    # #C99A74
COLOR_PIEL_SOMBRA = (237, 195, 155)      # #EDC39B
COLOR_PUNTO_DEDO = COLOR_APOYO

# =============================================================================
# 3. TIPOGRAFÍA
# =============================================================================
# Lexend incluida en assets/fonts (Mockup 00_Estilos). Si falta, se usan las del sistema.
RUTA_FUENTE_REGULAR = DIRECTORIO_ASSETS / "fonts" / "Lexend-Regular.ttf"
RUTA_FUENTE_NEGRITA = DIRECTORIO_ASSETS / "fonts" / "Lexend-Bold.ttf"
FUENTES_PREFERIDAS = [
    "Lexend",
    "Lexend Deca",
    "Nunito",
    "Quicksand",
    "Arial Rounded MT Bold",
    "DejaVu Sans",
    "Liberation Sans",
]

# =============================================================================
# 4. LÓGICA DEL JUEGO Y TIEMPOS
# =============================================================================
TOTAL_RONDAS = 5
NUMERO_MIN = 1
NUMERO_MAX = 5

# Progresión pedagógica por ronda (de números bajos a altos)
POOLS_DIFICULTAD_RONDAS = [
    [1, 2],       # Ronda 1: números muy sencillos
    [1, 2, 3],    # Ronda 2: introduce el 3
    [2, 3, 4],    # Ronda 3: dificultad media
    [3, 4, 5],    # Ronda 4: introduce el 5
    [4, 5],       # Ronda 5: cierre con números altos
]

# Tiempo que el niño debe mantener el número correcto de forma continua (segundos)
TIEMPO_ESTABLE_ACIERTO_SEG = 0.8

# Reglas de estrellas por ronda
TIEMPO_MAX_TRES_ESTRELLAS_SEG = 10.0  # <= 10s y a la primera -> 3 estrellas
TIEMPO_ACTIVAR_PISTA_SEG = 12.0       # >= 12s -> muestra pista animada y otorga 1 estrella

# Tiempo sosteniendo un número distinto para contar como intento y dar ánimo por voz
TIEMPO_SOSTENIDO_INTENTO_ERRONEO_SEG = 1.1
ENFRIAMIENTO_MENSAJE_ANIMO_SEG = 5.0
TIEMPO_RECORDATORIO_SIN_MANO_SEG = 8.0

# Pausa breve de celebración entre rondas
TIEMPO_CELEBRACION_RONDA_SEG = 1.8

# =============================================================================
# 5. DETECCIÓN DE DEDOS E HISTÉRESIS (MediaPipe Hands)
# =============================================================================
MAX_MANOS = 1

# Modelo de MediaPipe Tasks (las versiones nuevas de mediapipe ya no incluyen
# `mp.solutions`). Se descarga automáticamente la primera vez si no existe.
RUTA_MODELO_MANOS = DIRECTORIO_ASSETS / "modelos" / "hand_landmarker.task"
URL_MODELO_MANOS = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
MIN_CONFIDENCE_DETECCION = 0.65
MIN_CONFIDENCE_SEGUIMIENTO = 0.60

# Estabilización temporal
VENTANA_HISTÉRESIS_FRAMES = 3   # Voto de mayoría en los últimos 3 fotogramas
FRAMES_GRACIA_SIN_MANO = 4      # Mantiene conteo hasta 4 fotogramas si se pierde la mano

# Umbrales geométricos invariantes a rotación
# Índice, medio, anular y meñique: dist(TIP, WRIST) / dist(PIP, WRIST)
UMBRAL_RATIO_DEDO_WRIST = 1.18
UMBRAL_RATIO_TIP_MCP_WRIST = 1.12
UMBRAL_RECTITUD_DEDO = 1.15     # dist(TIP, MCP) / dist(PIP, MCP)

# Pulgar: evaluado respecto a la base del meñique (PINKY_MCP, landmark 17)
UMBRAL_RATIO_PULGAR_MENIQUE = 1.12
UMBRAL_RATIO_PULGAR_MCP_MENIQUE = 1.08
UMBRAL_APERTURA_PULGAR_PALMA = 0.45  # dist(THUMB_TIP, INDEX_MCP) / ancho_palma

# =============================================================================
# 6. CÁMARA Y CALIBRACIÓN AUTOMÁTICA DE LUZ
# =============================================================================
INDICE_CAMARA_DEFECTO = 0
ANCHO_CAPTURA_CAMARA = 1280
ALTO_CAPTURA_CAMARA = 720
MODO_ESPEJO = True

# Rango óptimo de brillo promedio (0 a 255)
BRILLO_MIN_OPTIMO = 75.0
BRILLO_MAX_OPTIMO = 195.0

# Parámetros de CLAHE para corrección de iluminación
CLAHE_CLIP_LIMIT = 2.5
CLAHE_TILE_GRID_SIZE = (8, 8)

# =============================================================================
# 7. VOZ Y NARRACIÓN (pyttsx3)
# =============================================================================
VELOCIDAD_VOZ_WPM = 135  # Habla clara y pausada para niños de 4 a 6 años
VOLUMEN_VOZ = 1.0
IDIOMA_PREFERIDO = "es"

FRASES_EXITO = [
    "¡Muy bien!",
    "¡Excelente trabajo!",
    "¡Lo lograste, genial!",
]

FRASES_ANIMO = [
    "Casi, inténtalo otra vez",
    "¡Tú puedes! Prueba otra vez",
    "Casi lo tienes, intenta de nuevo",
]

# =============================================================================
# 8. PRIVACIDAD Y DATOS DE SESIÓN
# =============================================================================
# Por protección de menores de edad, NUNCA se guardan ni graban imágenes en disco
PERMITIR_GUARDAR_IMAGENES = False

DIRECTORIO_DATOS = Path(__file__).resolve().parent
ARCHIVO_SESIONES_JSON = DIRECTORIO_DATOS / "sesiones_juego_dedos.json"
PERFIL_POR_DEFECTO = "Sofía"
ARCHIVO_PERFILES_JSON = DIRECTORIO_DATOS / "perfiles_juego.json"
MAX_PERFILES = 24

# Mano ilustrada en pantalla (la cámara nunca se muestra)
SUAVIZADO_MANO = 0.55           # 1.0 = sin suavizado
TAMANO_PALMA_AVATAR = 0.40      # largo muñeca->nudillo respecto al alto del marco guía
GANANCIA_MOVIMIENTO_AVATAR = 0.6
SEGUNDOS_MANTENER_ADULTOS = 1.2  # Mantener presionado el candado para entrar

# =============================================================================
# 9. MODO DEPURACIÓN
# =============================================================================
MODO_DEPURACION_INICIAL = False  # Se activa/desactiva en vivo con la tecla D