# 🖐️ Cuenta con tus Dedos — Sistema Educativo Interactivo

Sistema interactivo kinestésico diseñado para niños de 4 a 6 años que enseña el conteo del 1 al 5 utilizando visión artificial con **MediaPipe Hands**, retroalimentación por voz local con **pyttsx3**, e interfaz gráfica escalable con **Pygame**.

---

## 🚀 Guía de Inicio Rápido

### 1. Crear y activar el entorno virtual

**En Windows (PowerShell / CMD):**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**En Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 2. Instalar dependencias desde `requirements.txt`

Con el entorno virtual activado:
```bash
pip install -r requirements.txt
```

---

### 3. Ejecutar las pruebas unitarias del contador de dedos

Valida la robustez del detector (invarianza a rotación, histéresis temporal, periodos de gracia y asignación de estrellas):
```bash
# Windows / Linux / macOS
python test_detector_dedos.py
```
*(o `python3 test_detector_dedos.py` según tu entorno)*

---

### 4. Iniciar el juego

#### Modo pantalla completa (1920x1080):
```bash
#### Modo pantalla completa (1920x1080):
```bash
python juego_dedos.py --pantalla-completa
```

#### Modo ventana escalable:
```bash
python juego_dedos.py --ventana
```

#### Iniciar en una pantalla específica:
```bash
python juego_dedos.py --pantalla perfil      # Vista 01: Selección de perfil infantil
python juego_dedos.py --pantalla calibracion # Vista 02: Calibración y visor de mano
python juego_dedos.py --pantalla menu        # Vista 03: Menú principal de juegos
python juego_dedos.py --pantalla conteo      # Vista 04: Juego "Cuenta con tus dedos"
python juego_dedos.py --pantalla resultado   # Vista 07: Celebración y estrellas
python juego_dedos.py --pantalla adultos     # Vista 08: Panel analítico para tutores
```

#### Opciones de línea de comandos disponibles:
- `--pantalla <nombre>`: Pantalla inicial (`perfil`, `calibracion`, `menu`, `conteo`, `resultado`, `adultos`).
- `--perfil <nombre>`: Perfil inicial del niño (ej. `Sofía`, `Mateo`, `Luna`).
- `--pantalla-completa`: Inicia directamente en pantalla completa a resolución 1920x1080.
- `--ventana`: Inicia en una ventana escalable para monitores pequeños o depuración.
- `--camara <índice>`: Selecciona el índice de la cámara web (por defecto `0`).

---

## 🎮 Controles durante el Juego

- **Mano frente a la cámara**: Coloca tu mano en el visor. **La cámara real nunca se muestra en pantalla**; en su lugar, se proyecta un avatar ilustrado vectorial de tu mano en tiempo real con puntos turquesa en las yemas extendidas.
- **Teclas `0` a `5`**: Permite simular dedos mediante el teclado (ideal para pruebas y equipos sin webcam).
- **Tecla `D`**: Activa/desactiva el **Modo Depuración** (overlay técnico con FPS, landmarks, detecciones y estados).
- **Tecla `F11`**: Alterna entre pantalla completa y modo ventana en cualquier momento.
- **Tecla `ESPACIO`**: Repite la instrucción narrada actual por voz.
- **Tecla `R`**: Reintenta la reconexión de la cámara web.
- **Tecla `ESC`**: Regresa a la pantalla anterior o sale de la aplicación.

---

## 📁 Estructura del Proyecto

- [juego_dedos.py](file:///c:/Users/jormo/Documents/2026b/Sistemas%20Interactivos/proyecto/juego_dedos.py): Orquestador principal y máquina de estados con renderizado 1920x1080.
- [mano_avatar.py](file:///c:/Users/jormo/Documents/2026b/Sistemas%20Interactivos/proyecto/mano_avatar.py): Motor del avatar vectorial de la mano (reemplaza 100% el video crudo de la cámara por privacidad e inmersión infantil).
- [detector_dedos.py](file:///c:/Users/jormo/Documents/2026b/Sistemas%20Interactivos/proyecto/detector_dedos.py): Detección con MediaPipe Tasks (`HandLandmarker`), filtrado por histéresis y periodo de gracia.
- [componentes.py](file:///c:/Users/jormo/Documents/2026b/Sistemas%20Interactivos/proyecto/componentes.py): Sistema de diseño Figma 2.3 (botones redondeados, píldoras, tarjetas, mascota búho, estrellas, confeti).
- [pantallas/](file:///c:/Users/jormo/Documents/2026b/Sistemas%20Interactivos/proyecto/pantallas/): Vistas modulares del juego:
  - `perfil.py`: Vista 01 — Selector de niños y acceso tutores.
  - `calibracion.py`: Vista 02 — Estado de periféricos y guía de postura.
  - `menu.py`: Vista 03 — Menú de actividades ("Dedos", "Colores", "Letras").
  - `conteo.py`: Vista 04 — Juego de conteo con anillo de estabilidad y pista a los 12 s.
  - `resultado.py`: Vista 07 — Celebración con estrellas y mascota búho.
  - `adultos.py`: Vista 08 — Métricas y tabla de rendimiento para docentes/padres.
- [perfiles.py](file:///c:/Users/jormo/Documents/2026b/Sistemas%20Interactivos/proyecto/perfiles.py): Almacén persistente local de perfiles infantiles (`perfiles_juego.json`).
- [logica.py](file:///c:/Users/jormo/Documents/2026b/Sistemas%20Interactivos/proyecto/logica.py): Generación de secuencias no repetitivas y cálculo de estrellas.
- [camara.py](file:///c:/Users/jormo/Documents/2026b/Sistemas%20Interactivos/proyecto/camara.py): Captura de OpenCV en hilo de fondo y realce CLAHE.
- [voz.py](file:///c:/Users/jormo/Documents/2026b/Sistemas%20Interactivos/proyecto/voz.py): Narrador por voz asíncrono en español (`pyttsx3`).
- [interfaz.py](file:///c:/Users/jormo/Documents/2026b/Sistemas%20Interactivos/proyecto/interfaz.py): Manejo de ventana, escalado con letterbox y fuentes Lexend.
- [config.py](file:///c:/Users/jormo/Documents/2026b/Sistemas%20Interactivos/proyecto/config.py): Tokens de diseño, constantes y parámetros pedagógicos.
- [test_detector_dedos.py](file:///c:/Users/jormo/Documents/2026b/Sistemas%20Interactivos/proyecto/test_detector_dedos.py): Suite de pruebas unitarias automatizadas.
