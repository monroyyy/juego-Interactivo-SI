"""
perfiles.py — Perfiles infantiles (mockup 01): nombre, animal y color.
Solo se guarda el nombre elegido y un animal; ningún dato personal ni imagen.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import List, Tuple

import config

Color = Tuple[int, int, int]


@dataclass
class Perfil:
    nombre: str
    animal: str  # "gato" | "oso" | "conejo"
    color: Color


PERFILES_BASE: List[Perfil] = [
    Perfil("Sofía", "gato", (245, 158, 123)),    # #F59E7B
    Perfil("Mateo", "oso", (167, 139, 250)),     # #A78BFA
    Perfil("Luna", "conejo", (125, 211, 192)),   # #7DD3C0
]

_NOMBRES_NUEVOS = ["Ana", "Leo", "Mía", "Teo", "Sol", "Noa"]
_ANIMALES = ["gato", "oso", "conejo"]
_COLORES_NUEVOS: List[Color] = [
    (253, 186, 116),   # naranja suave
    (147, 197, 253),   # azul suave
    (249, 168, 212),   # rosa suave
    (190, 242, 100),   # lima suave
]


class AlmacenPerfiles:
    """Lista de perfiles = 3 base + los que el adulto vaya creando con «Nuevo»."""

    def __init__(self) -> None:
        self.perfiles: List[Perfil] = list(PERFILES_BASE)
        self._cargar_extra()

    def _cargar_extra(self) -> None:
        ruta = config.ARCHIVO_PERFILES_JSON
        if not ruta.exists():
            return
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            for item in datos.get("extra", []):
                color = tuple(int(c) for c in item["color"])
                if len(color) == 3:
                    self.perfiles.append(
                        Perfil(str(item["nombre"]), str(item["animal"]), color)  # type: ignore[arg-type]
                    )
        except (OSError, ValueError, KeyError, TypeError):
            pass

    def _guardar_extra(self) -> None:
        extra = [
            {"nombre": p.nombre, "animal": p.animal, "color": list(p.color)}
            for p in self.perfiles[len(PERFILES_BASE):]
        ]
        try:
            config.ARCHIVO_PERFILES_JSON.write_text(
                json.dumps({"extra": extra}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    @property
    def puede_agregar(self) -> bool:
        return len(self.perfiles) < config.MAX_PERFILES

    def crear_perfil(
        self,
        nombre: str,
        animal: str = "gato",
        color: Optional[Color] = None,
    ) -> Perfil:
        """Crea y persiste un nuevo perfil personalizado para el niño."""
        nombre_limpio = nombre.strip()
        if not nombre_limpio:
            indice = len(self.perfiles) - len(PERFILES_BASE)
            nombre_limpio = _NOMBRES_NUEVOS[indice % len(_NOMBRES_NUEVOS)]
        else:
            nombre_limpio = nombre_limpio[:12].capitalize()

        existentes = {p.nombre.lower() for p in self.perfiles}
        nombre_final = nombre_limpio
        sufijo = 2
        while nombre_final.lower() in existentes:
            nombre_final = f"{nombre_limpio} {sufijo}"
            sufijo += 1

        animal_valido = animal.lower() if animal.lower() in _ANIMALES else "gato"

        if color is None:
            idx = len(self.perfiles) % len(_COLORES_NUEVOS)
            color_final = _COLORES_NUEVOS[idx]
        else:
            color_final = color

        perfil = Perfil(
            nombre=nombre_final,
            animal=animal_valido,
            color=color_final,
        )
        self.perfiles.append(perfil)
        self._guardar_extra()
        return perfil

    def agregar_nuevo(self) -> Perfil:
        """Crea un perfil con valores sugeridos rápidos."""
        indice = len(self.perfiles) - len(PERFILES_BASE)
        nombre = _NOMBRES_NUEVOS[indice % len(_NOMBRES_NUEVOS)]
        animal = _ANIMALES[indice % len(_ANIMALES)]
        color = _COLORES_NUEVOS[indice % len(_COLORES_NUEVOS)]
        return self.crear_perfil(nombre=nombre, animal=animal, color=color)

    def eliminar_perfil(self, nombre: str) -> bool:
        """Elimina un perfil adicional (los 3 base no se pueden borrar)."""
        nombres_base = {p.nombre for p in PERFILES_BASE}
        if nombre in nombres_base:
            return False
        for i, p in enumerate(self.perfiles):
            if p.nombre == nombre and i >= len(PERFILES_BASE):
                self.perfiles.pop(i)
                self._guardar_extra()
                return True
        return False
