"""
modelo.py - Modelo matemático del vaciado de un tanque (Ley de Torricelli)
y del alcance del chorro (tiro parabólico).

Este módulo lo usan tanto el juego (juego.py) como el script de validación
(validacion.py), así ambos trabajan EXACTAMENTE con las mismas ecuaciones.

Ecuaciones
----------
1) Velocidad de salida por un orificio (Torricelli corregida):
       v = Cv * sqrt(2 g h)
   h  = altura de agua por encima del orificio ("carga") [m]
   Cv = coeficiente de velocidad (~0.97)

2) Caudal que sale:
       Q = Cd * a * sqrt(2 g h)          Cd = coeficiente de descarga (~0.61)
   a = área del orificio = pi d^2 / 4

3) Conservación de masa en el tanque (área A = pi D^2 / 4):
       A dh/dt = -Q   =>   dh/dt = -(a/A) Cd sqrt(2 g h)

4) Solución analítica (EDO separable):
       sqrt(h(t)) = sqrt(h0) - k t ,   k = (a/A) Cd sqrt(g/2)
       h(t) = (sqrt(h0) - k t)^2
       t_vaciado = sqrt(h0) / k

5) Alcance horizontal del chorro (el orificio está a una altura y del suelo):
       t_caida = sqrt(2 y / g)
       R = v * t_caida = 2 Cv sqrt(h y)      <- ¡no depende de g!
"""
import math
from dataclasses import dataclass

GRAVEDADES = [
    ("Tierra", 9.81),
    ("Luna", 1.62),
    ("Marte", 3.71),
    ("Júpiter", 24.79),
]


@dataclass
class ParametrosTanque:
    D_tanque: float      # diámetro interno del tanque [m]
    d_orificio: float    # diámetro del orificio [m]
    Cd: float = 0.61     # coeficiente de descarga
    Cv: float = 0.97     # coeficiente de velocidad
    g: float = 9.81      # gravedad [m/s^2]

    @property
    def A(self) -> float:
        return math.pi * self.D_tanque ** 2 / 4

    @property
    def a(self) -> float:
        return math.pi * self.d_orificio ** 2 / 4

    @property
    def k(self) -> float:
        """Constante de la solución analítica sqrt(h) = sqrt(h0) - k t."""
        return (self.a / self.A) * self.Cd * math.sqrt(self.g / 2)


# ------------------------------------------------------------------ vaciado
def caudal(h: float, p: ParametrosTanque) -> float:
    """Caudal de salida Q [m^3/s] para una carga h [m]."""
    if h <= 0:
        return 0.0
    return p.Cd * p.a * math.sqrt(2 * p.g * h)


def dhdt(h: float, p: ParametrosTanque) -> float:
    """Derecha de la EDO: dh/dt = -Q/A."""
    return -caudal(h, p) / p.A


def paso_rk4(h: float, dt: float, p: ParametrosTanque) -> float:
    """Integra un paso de la EDO con Runge-Kutta de 4º orden (lo usa el juego)."""
    if h <= 0:
        return 0.0
    k1 = dhdt(h, p)
    k2 = dhdt(max(h + 0.5 * dt * k1, 0.0), p)
    k3 = dhdt(max(h + 0.5 * dt * k2, 0.0), p)
    k4 = dhdt(max(h + dt * k3, 0.0), p)
    return max(h + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4), 0.0)


def h_analitica(t: float, h0: float, p: ParametrosTanque) -> float:
    """Solución exacta h(t) [m]."""
    s = math.sqrt(max(h0, 0.0)) - p.k * t
    return s * s if s > 0 else 0.0


def tiempo_vaciado(h0: float, p: ParametrosTanque) -> float:
    """Tiempo [s] para que la carga pase de h0 a 0."""
    return math.sqrt(max(h0, 0.0)) / p.k


# ------------------------------------------------------------------- chorro
def velocidad_salida(h: float, p: ParametrosTanque) -> float:
    return p.Cv * math.sqrt(2 * p.g * h) if h > 0 else 0.0


def alcance(h: float, y: float, p: ParametrosTanque) -> float:
    """Distancia horizontal [m] donde el chorro toca el suelo."""
    if h <= 0 or y <= 0:
        return 0.0
    return 2 * p.Cv * math.sqrt(h * y)


def trayectoria_chorro(h: float, y: float, p: ParametrosTanque, n: int = 40):
    """Puntos (x, y) [m] de la parábola del chorro, desde el orificio al suelo."""
    v = velocidad_salida(h, p)
    if v <= 0:
        return []
    t_caida = math.sqrt(2 * y / p.g)
    pts = []
    for i in range(n + 1):
        t = t_caida * i / n
        pts.append((v * t, y - 0.5 * p.g * t * t))
    return pts


# ------------------------------------------------------- ajuste a los datos
def ajustar_Cd(t, h, p: ParametrosTanque):
    """
    Ajusta Cd a mediciones reales usando la linealización
        sqrt(h) = sqrt(h0) - k t     (recta)
    Devuelve (Cd_ajustado, sqrt_h0_ajustado, R^2).
    """
    pares = [(ti, math.sqrt(hi)) for ti, hi in zip(t, h) if hi > 0]
    n = len(pares)
    if n < 3:
        raise ValueError("Se necesitan al menos 3 mediciones con h > 0")
    mx = sum(x for x, _ in pares) / n
    my = sum(y for _, y in pares) / n
    sxx = sum((x - mx) ** 2 for x, _ in pares)
    sxy = sum((x - mx) * (y - my) for x, y in pares)
    pendiente = sxy / sxx
    b0 = my - pendiente * mx
    ss_tot = sum((y - my) ** 2 for _, y in pares)
    ss_res = sum((y - (b0 + pendiente * x)) ** 2 for x, y in pares)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    k = -pendiente
    Cd = k / ((p.a / p.A) * math.sqrt(p.g / 2))
    return Cd, b0, r2


def ajustar_Cv(h, y, R):
    """Mínimos cuadrados de R = Cv * 2 sqrt(h y). Devuelve Cv."""
    xs = [2 * math.sqrt(hi * yi) for hi, yi in zip(h, y)]
    num = sum(x * r for x, r in zip(xs, R))
    den = sum(x * x for x in xs)
    return num / den
