# Mini informe técnico: Bombero Torricelli
**Asignatura:** Diseño y Control de Modelos · **Unidad 5**
**Integrantes:** [NOMBRE 1] · [NOMBRE 2]
**Fecha:** 23/11/2026

> Las partes entre [CORCHETES] se completan con sus mediciones reales y con lo que muestra `resultados/resumen_validacion.txt`.

---

## 1. Fenómeno elegido

Elegimos el **vaciado de un recipiente por un orificio** y el **chorro de agua** que sale de él. Es lo que pasa en un tanque de agua, en un botellón con llave o en una clepsidra (reloj de agua). En 1643, Evangelista Torricelli mostró que el agua sale por un orificio con la misma velocidad que tendría un objeto en caída libre desde la superficie del agua.

Lo elegimos porque es un fenómeno poco común en videojuegos y porque:
- es **no lineal**: el tanque se vacía cada vez más lento, porque la velocidad depende de √h;
- combina dos modelos: el **vaciado** (una EDO) y el **tiro parabólico** del chorro;
- se puede **reproducir y medir en casa** con una botella, una regla y el celular.

En el juego, un bombero controla un tanque con 4 válvulas a distintas alturas. Para alcanzar cada fuego, tiene que escoger la válvula según el nivel de agua que queda.

## 2. Variables del sistema

| Tipo | Variable | Símbolo | Unidad | Valor en nuestro montaje |
|---|---|---|---|---|
| Parámetro | Diámetro interno del tanque | D | cm | [10.0] |
| Parámetro | Diámetro del orificio | d | mm | [5.0] |
| Parámetro | Coeficiente de descarga | Cd | – | 0.61 teórico / [ajustado] |
| Parámetro | Coeficiente de velocidad | Cv | – | 0.97 teórico / [ajustado] |
| Parámetro | Gravedad | g | m/s² | 9.81 |
| Parámetro | Altura de cada válvula sobre el fondo | z | cm | [3, 9, 15, 21] |
| Parámetro | Altura del soporte | — | cm | [30] |
| Estado | Carga de agua sobre el orificio | h(t) | m | h₀ = [24] cm |
| Salida | Velocidad de salida | v | m/s | — |
| Salida | Caudal | Q | m³/s | — |
| Salida | Alcance del chorro | R | m | — |
| Independiente | Tiempo | t | s | — |

## 3. Recolección de datos

**Materiales:** botella PET de [2] L, clavo caliente, regla, cinta métrica, cinta adhesiva, caja de soporte y celular para grabar.

**Procedimiento:**
1. Cortamos la botella por la parte de arriba para tener una sección constante y medimos D = [__] cm con un calibrador.
2. Hicimos 4 orificios de d = [__] mm a 3, 9, 15 y 21 cm del fondo.
3. Pegamos una regla vertical y colocamos la botella sobre un soporte de [__] cm.
4. **Vaciado:** llenamos hasta [27] cm, grabamos con un cronómetro en pantalla y destapamos la válvula inferior. Del video tomamos el nivel cada [10] s. Repetimos [3] veces y promediamos.
5. **Alcance:** marcamos en el suelo dónde caía el chorro cada vez que el nivel bajaba unos 3 cm, para cada válvula.

**Datos de referencia:** para orificios de pared delgada, la literatura de mecánica de fluidos da Cd ≈ 0.61 y Cv ≈ 0.97–0.98.

[Tabla de mediciones: pegar aquí datos/vaciado.csv promediado]

## 4. Construcción del modelo

**Modelo lógico.** El agua del tanque es el estado del sistema. Cada instante, el tanque pierde un volumen Q·dt por la válvula abierta, y ese volumen fija la velocidad y la parábola del chorro. El jugador decide qué válvula abrir. Esa decisión cambia la carga h y la altura y del chorro.

**Modelo matemático.**

1. Bernoulli entre la superficie libre y el orificio: v = Cv·√(2gh)
2. Caudal real (contracción del chorro): Q = Cd·a·√(2gh), con a = πd²/4
3. Conservación de masa: A·dh/dt = −Q, es decir dh/dt = −(a/A)·Cd·√(2gh)
4. Separamos variables e integramos:

   √h(t) = √h₀ − k·t, con k = (a/A)·Cd·√(g/2)
   h(t) = (√h₀ − k·t)²
   t_vaciado = √h₀ / k

5. Chorro: sale horizontal desde una altura y. El tiempo de caída es t = √(2y/g), así que

   R = v·t = 2·Cv·√(h·y)

   Un resultado curioso: **el alcance no depende de g**. En la Luna, el chorro dibuja la misma parábola, pero el tanque tarda 2.5 veces más en vaciarse.

**Implementación en el videojuego** (`modelo.py` + `juego.py`):
- La EDO se integra con **Runge-Kutta de orden 4** y un paso de 5 ms. Si el juego se acelera, se hacen más subpasos para no perder precisión.
- Con la carga actual se calcula en cada frame la parábola del chorro, que se dibuja. Un fuego se apaga cuando el punto de impacto queda a menos de 2.2 cm de él durante 2 s.
- **Parámetros modificables en vivo:** d (teclas 1/2), Cd (3/4), D (5/6), g (G) y velocidad (+/−).
- **Modo laboratorio:** reproduce el experimento y exporta h(t) a CSV para compararlo con la realidad.
- Verificamos que la integración numérica es correcta: el tiempo de vaciado con RK4 (145.05 s) coincide con la solución analítica (145.05 s) para D = 10 cm, d = 5 mm y h₀ = 24 cm.

**Ajuste del modelo** (`validacion.py`): como √h es lineal en t, una regresión lineal de √h contra t da la pendiente k. De ella despejamos el Cd real de nuestra botella. Con mínimos cuadrados sobre R = 2·Cv·√(hy) obtenemos el Cv real.

## 5. Resultados y comparación

[Insertar resultados/fig1_vaciado.png, fig2_linealizacion.png y fig3_alcance.png]

| Indicador | Modelo teórico (Cd = 0.61) | Modelo ajustado (Cd = [__]) |
|---|---|---|
| RMSE del nivel h(t) | [__] cm | [__] cm |
| Error máximo | [__] cm | [__] cm |
| Tiempo de vaciado (medido: [__] s) | [__] s ([__] %) | [__] s |
| R² de la linealización √h vs t | — | [__] |
| RMSE del alcance R | [__] cm | [__] cm |
| RMSE juego vs real | [__] cm | — |

**Efecto de los parámetros (en el juego):**
- Duplicar d multiplica el área por 4, así que el tanque se vacía 4 veces más rápido. El alcance no cambia.
- Con g de la Luna (1.62 m/s²), el vaciado es √(9.81/1.62) ≈ 2.46 veces más lento y el alcance es igual.
- Al bajar Cd, el vaciado es más lento, en proporción 1/Cd.

## 6. Semejanzas, diferencias y causas

**Semejanzas:** [la forma de la curva es parabólica, el vaciado se hace cada vez más lento, √h es casi una recta (R² ≈ __) y la válvula de abajo con el tanque lleno da el mayor alcance].

**Diferencias:** [p. ej. el tanque real se vació un __ % más rápido/lento que el modelo teórico].

**Posibles causas:**
- El orificio hecho con un clavo caliente no es circular ni de pared delgada. Tiene rebabas, así que Cd ≠ 0.61.
- Error de lectura del nivel en el video (±1–2 mm). Pesa más cuando h es pequeño.
- La tensión superficial y la viscosidad frenan el flujo cuando la carga es pequeña (últimos centímetros).
- La botella se deforma y su sección no es perfectamente constante.
- El chorro no sale exactamente horizontal, y hay rozamiento con el aire y salpicaduras al medir dónde cae.
- Error al medir el diámetro del orificio: Q depende de d², así que un 10 % de error en d da cerca de un 20 % de error en el tiempo.

## 7. Conclusiones

- La Ley de Torricelli, con un **coeficiente de descarga ajustado experimentalmente**, reproduce el vaciado real con un error de [__] cm (RMSE). Esto valida el modelo para usarlo en el juego.
- El Cd teórico de libro (0.61) da una aproximación razonable, pero calibrarlo con datos reales reduce el error de [__] a [__] cm. Esto muestra por qué **un modelo debe validarse con datos**.
- El juego convierte el modelo en una mecánica: el jugador debe **entender** el fenómeno (cuándo usar cada válvula) para ganar.
- Mejoras posibles: modelar la viscosidad para cargas pequeñas, tanques de sección variable (cónicos) o varias válvulas abiertas a la vez.

## Repositorio

GitHub: [https://github.com/USUARIO/bombero-torricelli]
