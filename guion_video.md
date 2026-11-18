# Guion del video (≈10 min, 2 integrantes)

| Min | Quién | Qué se muestra | Qué se dice |
|---|---|---|---|
| 0:00–0:45 | A | Portada y juego corriendo | Presentación, fenómeno elegido y por qué es poco común |
| 0:45–2:30 | A | La botella real, sus medidas y los orificios | Variables (D, d, z, h, Cd, Cv, g) y cómo se midieron |
| 2:30–4:00 | B | **Video del experimento**: vaciado y chorro cayendo en la cinta métrica | Cómo se tomaron los datos del video y la tabla del CSV |
| 4:00–5:30 | B | Pizarra o diapositiva con las ecuaciones | Bernoulli → Torricelli → EDO → solución analítica → alcance R = 2Cv√(hy) |
| 5:30–6:30 | A | Código `modelo.py` y `juego.py` | RK4, cómo el modelo mueve el chorro y apaga los fuegos |
| 6:30–8:00 | A | **Partida en modo JUEGO**, cambiando d, Cd y g en vivo | Cómo cambia el comportamiento: d×2 vacía 4 veces más rápido; en la Luna el alcance no cambia |
| 8:00–9:30 | B | Modo LABORATORIO junto al video real, luego `python validacion.py` y las gráficas | Comparación, RMSE, Cd ajustado, tiempo de vaciado |
| 9:30–10:30 | B y A | Diapositiva de conclusiones | Semejanzas, diferencias, causas de las variaciones y mejoras |

**Tip:** pongan el video real y el modo LABORATORIO (a velocidad ×1) lado a lado. Así se ve cómo el nivel baja igual en la realidad y en el juego.
