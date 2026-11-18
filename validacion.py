"""
validacion.py - Compara el modelo (y el juego) con las mediciones reales.

Entradas (en la carpeta datos/):
  vaciado.csv  -> columnas: t_s, nivel_cm         (nivel medido desde el fondo)
  alcance.csv  -> columnas: nivel_cm, valvula, alcance_cm   (opcional)
  y el último resultados/partida_laboratorio_*.csv que genere el juego (opcional)

Salidas (en resultados/):
  fig1_vaciado.png, fig2_linealizacion.png, fig3_alcance.png, resumen_validacion.txt

Uso:
  python validacion.py          # usa tus datos reales
  python validacion.py --demo   # genera datos SINTÉTICOS solo para probar el script
"""
import argparse
import csv
import glob
import json
import math
import os
import random
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from modelo import ParametrosTanque, ajustar_Cd, ajustar_Cv, alcance, h_analitica

BASE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(BASE, "resultados")


def leer_csv(ruta):
    with open(ruta, encoding="utf-8") as f:
        filas = [l for l in f if l.strip() and not l.startswith("#")]
    return list(csv.DictReader(filas))


def crear_demo(cfg, carpeta):
    """Datos inventados con ruido para probar el flujo. NO usar en el informe."""
    os.makedirs(carpeta, exist_ok=True)
    p = ParametrosTanque(cfg["D_tanque_cm"] / 100, cfg["d_orificio_mm"] / 1000, Cd=0.66, Cv=0.94)
    z = cfg["valvulas_cm"][cfg["valvula_experimento"]] / 100
    h0 = cfg["nivel_inicial_cm"] / 100 - z
    with open(os.path.join(carpeta, "vaciado.csv"), "w", newline="", encoding="utf-8") as f:
        f.write("# DATOS SINTETICOS DE PRUEBA - reemplazar por mediciones reales\n")
        w = csv.writer(f)
        w.writerow(["t_s", "nivel_cm"])
        t = 0.0
        while True:
            h = h_analitica(t, h0, p)
            n = (z + h) * 100 + random.gauss(0, 0.25)
            w.writerow([round(t, 1), round(n, 1)])
            if h <= 0:
                break
            t += 10
    with open(os.path.join(carpeta, "alcance.csv"), "w", newline="", encoding="utf-8") as f:
        f.write("# DATOS SINTETICOS DE PRUEBA - reemplazar por mediciones reales\n")
        w = csv.writer(f)
        w.writerow(["nivel_cm", "valvula", "alcance_cm"])
        for iv, zc in enumerate(cfg["valvulas_cm"]):
            for nivel in range(int(cfg["nivel_inicial_cm"]), int(zc) + 2, -3):
                h = (nivel - zc) / 100
                y = (cfg["altura_soporte_cm"] + zc) / 100
                r = alcance(h, y, p) * 100 + random.gauss(0, 0.8)
                w.writerow([nivel, iv, round(r, 1)])


def errores(real, modelo):
    real, modelo = np.asarray(real), np.asarray(modelo)
    e = modelo - real
    rmse = float(np.sqrt(np.mean(e ** 2)))
    mae = float(np.mean(np.abs(e)))
    emax = float(np.max(np.abs(e)))
    return rmse, mae, emax


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap =argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="usar datos sintéticos de prueba")
    args = ap.parse_args()

    with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    carpeta = os.path.join(BASE, "datos")
    etiqueta = ""
    if args.demo:
        carpeta = os.path.join(BASE, "datos", "demo")
        crear_demo(cfg, carpeta)
        etiqueta = "  [DATOS DEMO SINTÉTICOS]"
        print("ATENCIÓN: usando datos sintéticos de prueba (datos/demo). No son mediciones reales.")

    ruta_vac = os.path.join(carpeta, "vaciado.csv")
    if not os.path.exists(ruta_vac):
        print(f"No existe {ruta_vac}. Copia datos/plantilla_vaciado.csv como vaciado.csv "
              "y llénalo con tus mediciones (o prueba con --demo).")
        return
    os.makedirs(RES, exist_ok=True)

    p = ParametrosTanque(cfg["D_tanque_cm"] / 100, cfg["d_orificio_mm"] / 1000,
                         Cd=cfg["Cd"], Cv=cfg["Cv"])
    z = cfg["valvulas_cm"][cfg["valvula_experimento"]] / 100

    filas = leer_csv(ruta_vac)
    t = np.array([float(r["t_s"]) for r in filas])
    nivel = np.array([float(r["nivel_cm"]) for r in filas]) / 100
    h = np.clip(nivel - z, 0, None)
    h0 = h[0]

    # ---- ajuste de Cd con la linealización sqrt(h) vs t
    # Se excluyen los puntos con carga < 0.5 cm y los posteriores al vaciado:
    # ahí sqrt(h) amplifica el error de lectura de la regla.
    i_vacio = int(np.argmax(h <= 0.002)) if (h <= 0.002).any() else len(h)
    m_fit = (h > 0.005) & (np.arange(len(h)) < i_vacio)
    Cd_aj, b0, r2 = ajustar_Cd(t[m_fit], h[m_fit], p)
    p_aj = ParametrosTanque(p.D_tanque, p.d_orificio, Cd=Cd_aj, Cv=p.Cv)

    h_teo = np.array([h_analitica(ti, h0, p) for ti in t])
    h_fit = np.array([h_analitica(ti, h0, p_aj) for ti in t])
    m = h > 0.002  # solo puntos con agua sobre el orificio
    e_teo = errores(h[m] * 100, h_teo[m] * 100)
    e_fit = errores(h[m] * 100, h_fit[m] * 100)

    t_vac_teo = math.sqrt(h0) / p.k
    t_vac_fit = b0 / p_aj.k
    vacios = t[h <= 0.002]
    t_vac_med = float(vacios[0]) if len(vacios) else float("nan")

    # ---- datos del juego (modo laboratorio)
    juego = None
    logs = sorted(glob.glob(os.path.join(RES, "partida_laboratorio_*.csv")))
    if logs:
        lj = leer_csv(logs[-1])
        tj = np.array([float(r["t_s"]) for r in lj])
        nj = np.array([float(r["nivel_cm"]) for r in lj])
        nj_interp = np.interp(t, tj, nj)
        juego = (tj, nj, errores(nivel[m] * 100, nj_interp[m]), os.path.basename(logs[-1]))

    # ---- figura 1: h(t)
    tt = np.linspace(0, max(t.max(), t_vac_teo) * 1.05, 300)
    plt.figure(figsize=(9, 5.5))
    plt.plot(t, nivel * 100, "o", color="crimson", label="Medición real")
    plt.plot(tt, [(z + h_analitica(x, h0, p)) * 100 for x in tt], "--", color="orange",
             label=f"Modelo teórico (Cd = {p.Cd:.2f})")
    plt.plot(tt, [(z + h_analitica(x, h0, p_aj)) * 100 for x in tt], "-", color="seagreen",
             label=f"Modelo ajustado (Cd = {Cd_aj:.3f})")
    if juego:
        plt.plot(juego[0], juego[1], "-", color="royalblue", alpha=.7, lw=2,
                 label="Juego (modo laboratorio, RK4)")
    plt.axhline(z * 100, color="gray", lw=.8, ls=":")
    plt.xlabel("Tiempo (s)")
    plt.ylabel("Nivel del agua desde el fondo (cm)")
    plt.title("Vaciado del tanque: realidad vs modelo" + etiqueta)
    plt.grid(alpha=.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(RES, "fig1_vaciado.png"), dpi=140)
    plt.close()

    # ---- figura 2: linealización
    plt.figure(figsize=(8, 5))
    plt.plot(t[m], np.sqrt(h[m]), "o", color="crimson", label="√h medido")
    plt.plot(tt, np.clip(b0 - p_aj.k * tt, 0, None), "-", color="seagreen",
             label=f"Recta ajustada  R² = {r2:.4f}")
    plt.xlabel("Tiempo (s)")
    plt.ylabel("√h  (√m)")
    plt.title("Linealización de Torricelli: √h = √h₀ − k·t" + etiqueta)
    plt.grid(alpha=.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(RES, "fig2_linealizacion.png"), dpi=140)
    plt.close()

    # ---- alcance del chorro
    txt_alc = "  (no hay datos/alcance.csv)"
    ruta_alc = os.path.join(carpeta, "alcance.csv")
    if os.path.exists(ruta_alc):
        fa = leer_csv(ruta_alc)
        iv = [int(r["valvula"]) for r in fa]
        za = np.array([cfg["valvulas_cm"][i] / 100 for i in iv])
        ha = np.array([float(r["nivel_cm"]) for r in fa]) / 100 - za
        ya = cfg["altura_soporte_cm"] / 100 + za
        Ra = np.array([float(r["alcance_cm"]) for r in fa]) / 100
        Cv_aj = ajustar_Cv(ha, ya, Ra)
        R_teo = np.array([alcance(a, b, p) for a, b in zip(ha, ya)])
        R_fit = 2 * Cv_aj * np.sqrt(ha * ya)
        ea_teo, ea_fit = errores(Ra * 100, R_teo * 100), errores(Ra * 100, R_fit * 100)
        txt_alc = (f"  Cv teórico = {p.Cv:.2f}  -> RMSE = {ea_teo[0]:.2f} cm, error máx = {ea_teo[2]:.2f} cm\n"
                   f"  Cv ajustado = {Cv_aj:.3f} -> RMSE = {ea_fit[0]:.2f} cm, error máx = {ea_fit[2]:.2f} cm")

        plt.figure(figsize=(8, 5))
        colores = plt.cm.viridis(np.linspace(0, .85, len(cfg["valvulas_cm"])))
        for i, zc in enumerate(cfg["valvulas_cm"]):
            sel = np.array(iv) == i
            if not sel.any():
                continue
            hh = np.linspace(0, cfg["nivel_inicial_cm"] / 100 - zc / 100, 100)
            y = cfg["altura_soporte_cm"] / 100 + zc / 100
            plt.plot(ha[sel] * 100, Ra[sel] * 100, "o", color=colores[i])
            plt.plot(hh * 100, [alcance(x, y, p) * 100 for x in hh], "-", color=colores[i],
                     label=f"Válvula {i+1} (z = {zc:.0f} cm)")
        plt.xlabel("Carga h sobre el orificio (cm)")
        plt.ylabel("Alcance del chorro (cm)")
        plt.title("Alcance: puntos = medición, líneas = R = 2·Cv·√(h·y)" + etiqueta)
        plt.grid(alpha=.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(RES, "fig3_alcance.png"), dpi=140)
        plt.close()

    # ---- resumen
    txt_juego = "  (no hay partida de laboratorio guardada; juega en modo LABORATORIO hasta vaciar)"
    if juego:
        txt_juego = (f"  Archivo: {juego[3]}\n"
                     f"  RMSE juego vs real = {juego[2][0]:.2f} cm, error máx = {juego[2][2]:.2f} cm")
    resumen = f"""RESUMEN DE VALIDACIÓN{etiqueta}
=====================================================
Tanque: D = {cfg['D_tanque_cm']} cm | orificio d = {cfg['d_orificio_mm']} mm | válvula a z = {z*100:.1f} cm
Carga inicial h0 = {h0*100:.2f} cm   ({len(t)} mediciones)

VACIADO h(t)
  Cd teórico  = {p.Cd:.3f} -> RMSE = {e_teo[0]:.2f} cm | MAE = {e_teo[1]:.2f} cm | error máx = {e_teo[2]:.2f} cm
  Cd ajustado = {Cd_aj:.3f} -> RMSE = {e_fit[0]:.2f} cm | MAE = {e_fit[1]:.2f} cm | error máx = {e_fit[2]:.2f} cm
  R² de la linealización √h vs t = {r2:.4f}
  Tiempo de vaciado: medido = {t_vac_med:.1f} s | teórico = {t_vac_teo:.1f} s | ajustado = {t_vac_fit:.1f} s
  Error del tiempo teórico = {100*(t_vac_teo - t_vac_med)/t_vac_med:+.1f} %

JUEGO vs REALIDAD
{txt_juego}

ALCANCE DEL CHORRO
{txt_alc}
"""
    with open(os.path.join(RES, "resumen_validacion.txt"), "w", encoding="utf-8") as f:
        f.write(resumen)
    print(resumen)
    print("Gráficos guardados en", RES)


if __name__ == "__main__":
    main()
