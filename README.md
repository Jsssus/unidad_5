# 🔥 Bombero Torricelli

Juego en Python/Pygame cuya mecánica principal funciona con un **modelo matemático validado con un experimento real**: el vaciado de un tanque por un orificio (**Ley de Torricelli**) y el alcance del chorro (**tiro parabólico**).

Hay que apagar fuegos que aparecen a distintas distancias usando un tanque con 4 válvulas a diferentes alturas. Mientras el agua baja, el chorro pierde alcance, así que hay que elegir **qué válvula abrir y cuándo**.

## Modelo

| Ecuación | Significado |
|---|---|
| `v = Cv·√(2gh)` | velocidad de salida (Torricelli) |
| `Q = Cd·a·√(2gh)` | caudal por el orificio |
| `A·dh/dt = −Q` | conservación de masa (EDO) |
| `h(t) = (√h₀ − k·t)²`, `k = (a/A)·Cd·√(g/2)` | solución analítica |
| `R = 2·Cv·√(h·y)` | alcance del chorro (¡no depende de g!) |

El juego integra la EDO con **Runge-Kutta 4** (paso de 5 ms) y la validación la compara con la solución analítica y con las mediciones reales.

## Instalación y uso

```bash
pip install -r requirements.txt
python juego.py            # el juego
python validacion.py       # compara el modelo con datos/vaciado.csv y datos/alcance.csv
python validacion.py --demo  # solo para probar el script con datos sintéticos
```

### Controles
| Tecla | Acción |
|---|---|
| ↑ / ↓ | elegir válvula |
| ESPACIO | abrir / cerrar |
| 1 / 2 | diámetro del orificio − / + |
| 3 / 4 | coeficiente de descarga Cd − / + |
| 5 / 6 | diámetro del tanque − / + |
| G | gravedad (Tierra, Luna, Marte, Júpiter) |
| + / − | velocidad de simulación |
| TAB | modo JUEGO ↔ LABORATORIO |
| R | reiniciar |

**Modo LABORATORIO:** abre la válvula del experimento y registra h(t). Dibuja la curva de la simulación, la analítica y los puntos medidos (si existe `datos/vaciado.csv`). Cada partida se guarda en `resultados/partida_*.csv`.

## Experimento real (cómo recolectar los datos)

1. Botella de 2–3 L de paredes rectas. Corta la parte de arriba y mide su **diámetro interno D**.
2. Con un clavo caliente, haz 4 orificios en línea vertical (por ejemplo a 3, 9, 15 y 21 cm del fondo). Mide el **diámetro d** con una broca o un calibrador. Tapa los orificios con cinta.
3. Pega una regla vertical (0 = fondo) y pon la botella sobre una caja de altura conocida (**altura del soporte**).
4. Anota todas las medidas en `config.json`.
5. **Vaciado:** llena hasta el nivel inicial, graba con el celular (con un cronómetro en cámara), destapa la válvula 1 y deja que se vacíe. Del video, anota el nivel cada 5–10 s en `datos/vaciado.csv`. Repite 3 veces y promedia.
6. **Alcance:** pon una cinta métrica en el suelo desde la pared de la botella. Anota dónde cae el chorro cada vez que el nivel baje unos 3 cm, para cada válvula, en `datos/alcance.csv`.
7. Ejecuta `python validacion.py`. Genera las gráficas y el resumen de errores en `resultados/`.

## Estructura
```
modelo.py        ecuaciones (las usan el juego y la validación)
juego.py         videojuego Pygame
validacion.py    ajuste de Cd y Cv, errores (RMSE, MAE) y gráficas
config.json      medidas de la botella real
datos/           mediciones reales (plantillas incluidas)
resultados/      gráficas, resumen y registros de partidas
```
