"""
juego.py - BOMBERO TORRICELLI
Un tanque de agua con varias válvulas a distintas alturas está sobre un soporte.
El fuego aparece a diferentes distancias: hay que elegir QUÉ válvula abrir y
CUÁNDO, porque el alcance del chorro depende de la altura de agua (que baja
según la Ley de Torricelli) y de la altura de la válvula respecto al suelo.

Modos:
  JUEGO        -> apagar todos los fuegos antes de quedarse sin agua.
  LABORATORIO  -> sin fuegos; se abre una válvula y se registra h(t) para
                  compararlo con el experimento real (datos/vaciado.csv).

Controles:
  Flechas arriba/abajo  elegir válvula       ESPACIO  abrir / cerrar
  1 / 2  diámetro del orificio  -/+          3 / 4    Cd  -/+
  5 / 6  diámetro del tanque    -/+          G        cambiar gravedad
  + / -  velocidad de simulación             TAB      Juego <-> Laboratorio
  R      reiniciar                           ESC      salir
"""
import csv
import json
import math
import os
import random
import sys
from datetime import datetime

import pygame

from modelo import (GRAVEDADES, ParametrosTanque, alcance, caudal,
                    h_analitica, paso_rk4, tiempo_vaciado, trayectoria_chorro,
                    velocidad_salida)

BASE = os.path.dirname(os.path.abspath(__file__))
ANCHO, ALTO = 1180, 690
PANEL_X = 800
SUELO_Y = 630
ESCALA = 850            # píxeles por metro
TANQUE_X = 60           # borde izquierdo del tanque (px)
RADIO_FUEGO = 0.022     # m: tolerancia para que el chorro "acierte"
VIDA_FUEGO = 2.0        # s de agua necesarios para apagar un fuego
VELOCIDADES = [1, 2, 4, 8, 16]
DT_SUB = 0.005          # paso de integración RK4 [s]

C_CIELO = (24, 28, 44)
C_SUELO = (58, 52, 46)
C_AGUA = (64, 160, 255)
C_TEXTO = (230, 232, 240)
C_TENUE = (140, 146, 165)
C_PANEL = (34, 38, 58)
C_ACENTO = (255, 196, 72)


def cargar_config():
    with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def cargar_mediciones():
    """Lee datos/vaciado.csv (t_s, nivel_cm) si existe, para el modo laboratorio."""
    ruta = os.path.join(BASE, "datos", "vaciado.csv")
    puntos = []
    if not os.path.exists(ruta):
        return puntos
    with open(ruta, encoding="utf-8") as f:
        filas = [l for l in f if l.strip() and not l.startswith("#")]
    for fila in csv.DictReader(filas):
        try:
            puntos.append((float(fila["t_s"]), float(fila["nivel_cm"])))
        except (ValueError, KeyError):
            pass
    return puntos


class Juego:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Bombero Torricelli - Diseño y Control de Modelos")
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        self.reloj = pygame.time.Clock()
        self.f_titulo = pygame.font.SysFont("arial", 24, bold=True)
        self.f_grande = pygame.font.SysFont("arial", 40, bold=True)
        self.f = pygame.font.SysFont("consolas", 15)
        self.f_peq = pygame.font.SysFont("consolas", 12)

        self.cfg = cargar_config()
        self.p = ParametrosTanque(
            D_tanque=self.cfg["D_tanque_cm"] / 100,
            d_orificio=self.cfg["d_orificio_mm"] / 1000,
            Cd=self.cfg["Cd"],
            Cv=self.cfg["Cv"],
        )
        self.i_grav = 0
        self.soporte = self.cfg["altura_soporte_cm"] / 100
        self.alto_tanque = self.cfg["altura_tanque_cm"] / 100
        self.nivel0 = self.cfg["nivel_inicial_cm"] / 100
        self.valvulas = [v / 100 for v in self.cfg["valvulas_cm"]]
        self.mediciones = cargar_mediciones()
        self.modo = "JUEGO"
        self.i_vel = 0
        self.reiniciar()

    # ------------------------------------------------------------ estado
    def reiniciar(self):
        self.nivel = self.nivel0
        self.t = 0.0
        self.log = []
        self.t_ult_log = -1.0
        self.estado = "jugando"
        self.guardado = False
        if self.modo == "LABORATORIO":
            self.sel = self.cfg["valvula_experimento"]
            self.abierta = True
            self.fuegos = []
            self.t_apertura = 0.0
        else:
            self.sel = len(self.valvulas) - 1
            self.abierta = False
            self.fuegos = self.generar_fuegos(4)
        self.registrar(forzar=True)

    def generar_fuegos(self, n):
        fuegos = []
        intentos = 0
        while len(fuegos) < n and intentos < 500:
            intentos += 1
            utiles = [z for z in self.valvulas if self.nivel0 - z > 0.03]
            z = random.choice(utiles)
            h = random.uniform(0.25, 0.9) * (self.nivel0 - z)
            x = alcance(h, self.soporte + z, self.p)
            if all(abs(x - f["x"]) > 0.07 for f in fuegos) and x > 0.08:
                fuegos.append({"x": x, "vida": VIDA_FUEGO})
        return sorted(fuegos, key=lambda f: f["x"])

    @property
    def z_sel(self):
        return self.valvulas[self.sel]

    @property
    def carga(self):
        """Carga h sobre la válvula seleccionada [m]."""
        return max(self.nivel - self.z_sel, 0.0)

    # ------------------------------------------------------------ física
    def actualizar(self, dt_real):
        if self.estado != "jugando":
            return
        dt = dt_real * VELOCIDADES[self.i_vel]
        pasos = max(1, int(dt / DT_SUB))
        sub = dt / pasos
        for _ in range(pasos):
            if self.abierta and self.carga > 0:
                h_nueva = paso_rk4(self.carga, sub, self.p)
                self.nivel = self.z_sel + h_nueva
                impacto = alcance(self.carga, self.soporte + self.z_sel, self.p)
                for f in self.fuegos:
                    if f["vida"] > 0 and abs(impacto - f["x"]) < RADIO_FUEGO:
                        f["vida"] -= sub
            self.t += sub
            self.registrar()
        self.revisar_fin()

    def registrar(self, forzar=False):
        if forzar or self.t - self.t_ult_log >= 0.5:
            self.t_ult_log = self.t
            h = self.carga
            self.log.append({
                "t_s": round(self.t, 3),
                "nivel_cm": round(self.nivel * 100, 3),
                "valvula": self.sel,
                "abierta": int(self.abierta),
                "carga_cm": round(h * 100, 3),
                "v_ms": round(velocidad_salida(h, self.p) if self.abierta else 0, 4),
                "Q_mL_s": round(caudal(h, self.p) * 1e6 if self.abierta else 0, 3),
                "alcance_cm": round(alcance(h, self.soporte + self.z_sel, self.p) * 100
                                    if self.abierta else 0, 3),
                "Cd": self.p.Cd, "d_mm": round(self.p.d_orificio * 1000, 2),
                "D_cm": round(self.p.D_tanque * 100, 2), "g": self.p.g,
            })

    def revisar_fin(self):
        if self.modo == "JUEGO":
            if all(f["vida"] <= 0 for f in self.fuegos):
                self.estado = "ganaste"
            elif self.nivel <= min(self.valvulas) + 0.0005:
                self.estado = "sin agua"
        elif self.carga <= 0.0005:
            self.estado = "vaciado"
        if self.estado != "jugando":
            self.guardar_log()

    def guardar_log(self):
        if self.guardado or len(self.log) < 2:
            return
        os.makedirs(os.path.join(BASE, "resultados"), exist_ok=True)
        sello = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = os.path.join(BASE, "resultados", f"partida_{self.modo.lower()}_{sello}.csv")
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(self.log[0].keys()))
            w.writeheader()
            w.writerows(self.log)
        self.guardado = True
        print("Partida guardada en", ruta)

    # ----------------------------------------------------------- entrada
    def tecla(self, k):
        p = self.p
        if k == pygame.K_UP:
            self.sel = min(self.sel + 1, len(self.valvulas) - 1)
        elif k == pygame.K_DOWN:
            self.sel = max(self.sel - 1, 0)
        elif k == pygame.K_SPACE and self.estado == "jugando":
            self.abierta = not self.abierta
        elif k == pygame.K_1:
            p.d_orificio = max(0.001, p.d_orificio - 0.0005)
        elif k == pygame.K_2:
            p.d_orificio = min(0.02, p.d_orificio + 0.0005)
        elif k == pygame.K_3:
            p.Cd = max(0.30, round(p.Cd - 0.01, 2))
        elif k == pygame.K_4:
            p.Cd = min(1.00, round(p.Cd + 0.01, 2))
        elif k == pygame.K_5:
            p.D_tanque = max(0.04, p.D_tanque - 0.005)
        elif k == pygame.K_6:
            p.D_tanque = min(0.20, p.D_tanque + 0.005)
        elif k == pygame.K_g:
            self.i_grav = (self.i_grav + 1) % len(GRAVEDADES)
            p.g = GRAVEDADES[self.i_grav][1]
        elif k in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
            self.i_vel = min(self.i_vel + 1, len(VELOCIDADES) - 1)
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.i_vel = max(self.i_vel - 1, 0)
        elif k == pygame.K_TAB:
            self.guardar_log()
            self.modo = "LABORATORIO" if self.modo == "JUEGO" else "JUEGO"
            self.reiniciar()
        elif k == pygame.K_r:
            self.guardar_log()
            self.reiniciar()
        self.registrar(forzar=True)

    # ----------------------------------------------------------- dibujo
    def sx(self, x_m):
        return int(self.borde_tanque() + x_m * ESCALA)

    def sy(self, y_m):
        return int(SUELO_Y - y_m * ESCALA)

    def borde_tanque(self):
        return TANQUE_X + self.p.D_tanque * ESCALA

    def texto(self, s, x, y, fuente=None, color=C_TEXTO):
        img = (fuente or self.f).render(s, True, color)
        self.pantalla.blit(img, (x, y))
        return img.get_height()

    def dibujar_escena(self):
        sc = self.pantalla
        sc.fill(C_CIELO)
        pygame.draw.rect(sc, C_SUELO, (0, SUELO_Y, PANEL_X, ALTO - SUELO_Y))
        # regla horizontal en el suelo (cada 10 cm desde la pared del tanque)
        for i in range(0, 80, 5):
            x = self.sx(i / 100)
            if x > PANEL_X - 5:
                break
            alto = 10 if i % 10 == 0 else 5
            pygame.draw.line(sc, C_TENUE, (x, SUELO_Y), (x, SUELO_Y + alto))
            if i % 10 == 0:
                self.texto(f"{i}", x - 6, SUELO_Y + 12, self.f_peq, C_TENUE)
        self.texto("cm desde la pared", self.sx(0), SUELO_Y + 32, self.f_peq, C_TENUE)

        # soporte
        ancho = int(self.p.D_tanque * ESCALA)
        pygame.draw.rect(sc, (90, 80, 70),
                         (TANQUE_X + 6, self.sy(self.soporte), ancho - 12,
                          SUELO_Y - self.sy(self.soporte)))
        # agua y tanque
        y_fondo = self.sy(self.soporte)
        y_agua = self.sy(self.soporte + self.nivel)
        pygame.draw.rect(sc, C_AGUA, (TANQUE_X, y_agua, ancho, y_fondo - y_agua))
        pygame.draw.rect(sc, C_TEXTO,
                         (TANQUE_X, self.sy(self.soporte + self.alto_tanque),
                          ancho, int(self.alto_tanque * ESCALA)), 2)
        # regla vertical del tanque
        for cm in range(0, int(self.alto_tanque * 100) + 1, 3):
            y = self.sy(self.soporte + cm / 100)
            pygame.draw.line(sc, C_TENUE, (TANQUE_X - 8, y), (TANQUE_X, y))
            self.texto(f"{cm}", TANQUE_X - 30, y - 6, self.f_peq, C_TENUE)

        # válvulas
        for i, z in enumerate(self.valvulas):
            pos = (int(self.borde_tanque()), self.sy(self.soporte + z))
            color = C_TENUE
            if i == self.sel:
                color = C_AGUA if self.abierta else C_ACENTO
                pygame.draw.circle(sc, color, pos, 9, 2)
            pygame.draw.circle(sc, color, pos, 5)

        # chorro
        if self.abierta and self.carga > 0:
            y0 = self.soporte + self.z_sel
            pts = trayectoria_chorro(self.carga, y0, self.p, 50)
            ancho_chorro = max(2, int(self.p.d_orificio * ESCALA))
            pp = [(self.sx(x), self.sy(y)) for x, y in pts]
            if len(pp) > 1:
                pygame.draw.lines(sc, C_AGUA, False, pp, ancho_chorro)
            xi = pp[-1][0]
            for _ in range(6):
                pygame.draw.circle(sc, (150, 210, 255),
                                   (xi + random.randint(-8, 8), SUELO_Y - random.randint(0, 6)), 2)

        # fuegos
        for f in self.fuegos:
            x = self.sx(f["x"])
            if f["vida"] > 0:
                s = 0.4 + 0.6 * f["vida"] / VIDA_FUEGO
                for c, esc in (((255, 90, 30), 1.0), ((255, 170, 40), 0.65), ((255, 240, 120), 0.35)):
                    h = int(46 * s * esc * random.uniform(0.85, 1.15))
                    w = int(16 * s * esc)
                    pygame.draw.polygon(sc, c, [(x - w, SUELO_Y), (x + w, SUELO_Y), (x, SUELO_Y - h)])
                pygame.draw.line(sc, (255, 255, 255, 60),
                                 (self.sx(f["x"] - RADIO_FUEGO), SUELO_Y + 2),
                                 (self.sx(f["x"] + RADIO_FUEGO), SUELO_Y + 2), 1)
            else:
                pygame.draw.circle(sc, (110, 110, 120), (x, SUELO_Y - 10), 7)
                self.texto("OK", x - 8, SUELO_Y - 34, self.f_peq, (120, 230, 140))

    def dibujar_panel(self):
        sc = self.pantalla
        pygame.draw.rect(sc, C_PANEL, (PANEL_X, 0, ANCHO - PANEL_X, ALTO))
        x, y = PANEL_X + 16, 12
        y += self.texto("BOMBERO TORRICELLI", x, y, self.f_titulo, C_ACENTO) + 2
        y += self.texto(f"Modo: {self.modo}   (TAB para cambiar)", x, y, self.f_peq, C_TENUE) + 10

        p, h = self.p, self.carga
        y_or = self.soporte + self.z_sel
        lineas = [
            ("PARÁMETROS DEL MODELO", C_ACENTO),
            (f"[1/2] d orificio   = {p.d_orificio*1000:5.1f} mm", C_TEXTO),
            (f"[3/4] Cd           = {p.Cd:5.2f}", C_TEXTO),
            (f"[5/6] D tanque     = {p.D_tanque*100:5.1f} cm", C_TEXTO),
            (f"[G]   gravedad     = {p.g:5.2f} m/s² ({GRAVEDADES[self.i_grav][0]})", C_TEXTO),
            (f"[+/-] velocidad    = x{VELOCIDADES[self.i_vel]}", C_TEXTO),
            ("", C_TEXTO),
            ("VARIABLES EN TIEMPO REAL", C_ACENTO),
            (f"t                  = {self.t:7.1f} s", C_TEXTO),
            (f"nivel del agua     = {self.nivel*100:6.2f} cm", C_TEXTO),
            (f"válvula {self.sel+1} (z={self.z_sel*100:.0f} cm) {'ABIERTA' if self.abierta else 'cerrada'}",
             C_AGUA if self.abierta else C_TEXTO),
            (f"carga h            = {h*100:6.2f} cm", C_TEXTO),
            (f"v = Cv·√(2gh)      = {velocidad_salida(h, p):6.3f} m/s", C_TEXTO),
            (f"Q = Cd·a·√(2gh)    = {caudal(h, p)*1e6:6.2f} mL/s", C_TEXTO),
            (f"R = 2Cv·√(h·y)     = {alcance(h, y_or, p)*100:6.2f} cm", C_TEXTO),
            (f"t vaciado (teór.)  = {tiempo_vaciado(h, p):6.1f} s", C_TEXTO),
        ]
        for s, c in lineas:
            y += self.texto(s, x, y, self.f, c) + 3

        self.dibujar_grafico(x, y + 10, ANCHO - PANEL_X - 32, 170)
        ayuda = "↑↓ válvula  ESPACIO abrir/cerrar  R reiniciar"
        self.texto(ayuda, x, ALTO - 22, self.f_peq, C_TENUE)

    def dibujar_grafico(self, x, y, w, h):
        sc = self.pantalla
        pygame.draw.rect(sc, (22, 25, 40), (x, y, w, h))
        pygame.draw.rect(sc, C_TENUE, (x, y, w, h), 1)
        self.texto("nivel (cm) vs t (s)", x + 6, y + 4, self.f_peq, C_TENUE)

        t_max = max(self.t, 10.0)
        curva_teo = []
        if self.modo == "LABORATORIO":
            h0 = self.nivel0 - self.z_sel
            t_max = max(t_max, tiempo_vaciado(h0, self.p) * 1.05)
            for i in range(61):
                ti = t_max * i / 60
                curva_teo.append((ti, (self.z_sel + h_analitica(ti, h0, self.p)) * 100))
            if self.mediciones:
                t_max = max(t_max, max(t for t, _ in self.mediciones))
        n_max = self.alto_tanque * 100

        def px(t, n):
            return (x + int(w * t / t_max), y + h - int(h * n / n_max))

        if len(curva_teo) > 1:
            pygame.draw.lines(sc, C_ACENTO, False, [px(*c) for c in curva_teo], 1)
        datos = [(r["t_s"], r["nivel_cm"]) for r in self.log]
        if len(datos) > 1:
            pygame.draw.lines(sc, C_AGUA, False, [px(*d) for d in datos], 2)
        if self.modo == "LABORATORIO":
            for t, n in self.mediciones:
                if t <= t_max:
                    pygame.draw.circle(sc, (255, 110, 110), px(t, n), 3)
            leyenda = [("simulación RK4", C_AGUA), ("analítica", C_ACENTO),
                       ("medición real" if self.mediciones else "sin datos/vaciado.csv", (255, 110, 110))]
            for i, (s, c) in enumerate(leyenda):
                self.texto(s, x + w - 150, y + 4 + 14 * i, self.f_peq, c)
        self.texto(f"{t_max:.0f} s", x + w - 40, y + h - 16, self.f_peq, C_TENUE)

    def dibujar_mensaje(self):
        if self.estado == "jugando":
            return
        textos = {
            "ganaste": ("¡INCENDIO CONTROLADO!", (120, 230, 140)),
            "sin agua": ("SIN AGUA... los fuegos ganaron", (255, 110, 110)),
            "vaciado": ("VACIADO COMPLETO", C_ACENTO),
        }
        s, c = textos[self.estado]
        caja = pygame.Surface((PANEL_X - 120, 110), pygame.SRCALPHA)
        caja.fill((0, 0, 0, 170))
        self.pantalla.blit(caja, (60, 40))
        self.texto(s, 80, 52, self.f_grande, c)
        detalle = f"t = {self.t:.1f} s   agua restante: {self.nivel*100:.1f} cm   (R para reiniciar)"
        self.texto(detalle, 82, 108, self.f, C_TEXTO)

    # ------------------------------------------------------------- bucle
    def ejecutar(self):
        while True:
            dt = self.reloj.tick(60) / 1000
            for e in pygame.event.get():
                if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                    self.guardar_log()
                    pygame.quit()
                    sys.exit()
                if e.type == pygame.KEYDOWN:
                    self.tecla(e.key)
            self.actualizar(dt)
            self.dibujar_escena()
            self.dibujar_panel()
            self.dibujar_mensaje()
            pygame.display.flip()


if __name__ == "__main__":
    Juego().ejecutar()
