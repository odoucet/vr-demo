"""Trajectoires des créatures, calculées sur le tracé et le terrain (clés lues par animatic.py).

    python pipeline/layout/creatures.py      # → pipeline/layout/creatures.json

Repère du tracé (m, x avant au départ, y gauche, z haut), cap en degrés. Retours d'Olivier (2026-10-18) :
- abysses : suit le chenal (et non plus en travers), plus vite que la barque : arrive de derrière, passe
  à ~5 m à droite de la barque à t = 70 s (dessous, la coque la cachait), file devant, s'enfonce et s'éteint (paramètre AbyssFade) dans le chenal profond ;
- troupeau : vitesse, écart et couloir propres à chaque bête ; sort de la forêt à droite par un sentier creusé dans la berge, traverse le gué l'eau au poitrail
  et remonte sur la berge gauche ; la hauteur suit le terrain (plus de traversée « dans le sol ») ;
- créature volante : passe lentement devant la lune puis continue son vol jusqu'à sortir du champ.
Une clé par seconde (interpolation linéaire dans la séquence). Déterministe.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

LAYOUT = Path(__file__).resolve().parent
sys.path.insert(0, str(LAYOUT))
from greybox_geometry import GRID_M, herd_crossing, terrain  # noqa: E402

OUT = LAYOUT / "creatures.json"
HIDDEN_Z = -60.0      # sous le terrain : créature cachée


def main():
    river = json.loads((LAYOUT / "river.json").read_text(encoding="utf-8"))
    s = river["samples"]
    st = np.array([p["t"] for p in s])
    marks = {m["id"]: m for m in river["landmarks"]}
    _, bounds, (gx, gy, d, z) = terrain(river)

    def ground(x, y):
        j = int(round((y - bounds["y0"]) / GRID_M))
        i = int(round((x - bounds["x0"]) / GRID_M))
        j, i = min(max(j, 0), z.shape[0] - 1), min(max(i, 0), z.shape[1] - 1)
        return float(z[j, i])

    def path(tau):
        """Point du chenal au temps de parcours tau (la barque y passe à tau), interpolé."""
        tau = float(np.clip(tau, st[0], st[-1]))
        k = int(np.searchsorted(st, tau))
        a, b = s[max(k - 1, 0)], s[min(k, len(s) - 1)]
        f = 0 if b["t"] == a["t"] else (tau - a["t"]) / (b["t"] - a["t"])
        return (a["x"] + f * (b["x"] - a["x"]), a["y"] + f * (b["y"] - a["y"]),
                a["heading_deg"] + f * (b["heading_deg"] - a["heading_deg"]))

    ABYSS_BREACH = False      # 23/10 (Olivier : « pas très naturel son déplacement… gardons-la sous l'eau ») ; True : affleure
    out = {"units": "m", "abysses": [], "troupeau": [], "volante": []}

    # --- Abysses : avance relative de -24 m (derrière) à +20 m (devant) entre 54 s et 84 s, puis plongée --------
    t0 = marks["abysses-passage"]["t"]
    for t in np.arange(t0 - 22, t0 + 13, 0.5):              # pas de 0,5 s : la remontée dure ~4 s
        # arrive de derrière, passe sous la barque, file devant puis s'enfonce et s'éteint en restant dans le
        # chenal profond (retour d'Olivier : elle ne doit plus « disparaître dans le sol » sous la barque)
        lead = np.interp(t, [t0 - 16, t0, t0 + 14], [-24.0, 0.0, 17.0])
        lead = lead if t >= t0 - 16 else -24.0 - (t0 - 16 - t) * 1.0
        tau = t + lead
        x, y, h = path(tau)
        # passe à ~5 m à droite de la barque (retour d'Olivier : juste dessous, on ne la voyait plus, cachée par la
        # coque) puis rejoint l'axe du chenal en filant devant ; léger serpentement
        side = -5.0 * float(np.interp(t, [t0 - 14, t0 - 6, t0 + 6, t0 + 12], [0.3, 1.0, 1.0, 0.2]))
        if ABYSS_BREACH:      # 22/10 : en remontant, la pointe d'une nageoire (7 m de large) traversait le plancher → 7 m
            side -= 2.0 * math.exp(-((t - (t0 + 3.0)) / 3.5) ** 2)
        wiggle = side + 0.8 * math.sin(t * 0.35)
        x, y = x - math.sin(math.radians(h)) * wiggle, y + math.cos(math.radians(h)) * wiggle
        bed = ground(x, y)
        # près de la surface sans l'effleurer : le dos est ~1,3 m au-dessus du centre (affleurement du 22/10) ; 23/10
        # (« laisse-la sous l'eau, pas loin de la surface ») : dos ~30 cm sous l'eau (-1,6 m ; -2,0 avant)
        depth = min(max(-1.6, bed + 1.2), -1.5)
        if t < t0 - 12:                                         # avant : sous le fond, invisible, puis remonte
            depth = np.interp(t, [t0 - 22, t0 - 12], [bed - 3.0, depth])
        if t > t0 + 4:                                          # s'enfonce doucement en s'éloignant
            depth = np.interp(t, [t0 + 4, t0 + 12], [depth, -4.5])   # éteinte (AbyssFade) avant le haut-fond
        # affleure (21/10, idée d'Olivier : « légèrement monter, dépasser la surface et replonger, qu'on la voie bien ») :
        # le dos perce la surface (~40 cm) juste après son passage sous la barque, devant à droite, puis replonge
        if ABYSS_BREACH:
            # 22/10 (« son mouvement n'est pas naturel ») : remontée plus lente et plus haute (le dos sort ~70 cm), le corps
            # se cabre en montant et pique en replongeant (tangage calculé dans animatic.py d'après la pente de la trajectoire)
            depth += 1.4 * math.exp(-((t - (t0 + 3.0)) / 3.2) ** 2)
        out["abysses"].append([round(float(t), 2), round(x, 3), round(y, 3), round(float(depth), 3), round(h, 2)])

    # --- Troupeau : sentier forêt droite → gué → forêt gauche, à 1,8 m/s, hauteur sur le terrain --------------
    hx, hy, ux, uy = herd_crossing(river)
    # 15 s plus tôt que le repère (retour d'Olivier du 19/10 : le troupeau détournait l'attention de l'arche qui suit) ;
    # même lieu de traversée, la barque en est donc plus loin (~33 m au lieu de 18)
    HERD_ADVANCE_S = 15.0
    tm = marks["troupeau-gue"]["t"] - HERD_ADVANCE_S
    heading = math.degrees(math.atan2(uy, ux))                  # vers la gauche du tracé
    hrng = np.random.default_rng(7)                             # troupeau irrégulier (retour d'Olivier)
    lag = 0.0
    for i in range(5):
        lag += 0.0 if i == 0 else float(hrng.uniform(0.9, 2.8))     # écarts inégaux entre les bêtes
        lane = float(hrng.uniform(-2.6, 2.6))
        start, speed = -34.0 - float(hrng.uniform(0, 3)), float(hrng.uniform(1.45, 2.15))
        t_start = tm + lag + start / speed                      # au milieu du gué à t ≈ 112 s (+ décalage)
        keys = []
        for k in range(int(68 / speed) + 1):
            a = start + k * speed
            x = hx + ux * a + uy * lane
            y = hy + uy * a - ux * lane
            gz = ground(x, y)
            keys.append([round(t_start + k, 2), round(x, 3), round(y, 3), round(gz + 1.2, 3), round(heading, 2)])
        out["troupeau"].append(keys)

    # --- Créature volante : arc devant la lune, puis s'éloigne en montant, cachée une fois hors du champ -----------
    cl = marks["creature-lune"]
    pc = min(s, key=lambda p: abs(p["t"] - cl["t"]))
    hc = math.radians(pc["heading_deg"])
    alt = cl["ahead_m"] * math.tan(math.radians(22))
    fx, fy, lx, ly = math.cos(hc), math.sin(hc), -math.sin(hc), math.cos(hc)
    k = cl["ahead_m"] / 300.0                                    # vitesses réglées pour 300 m : même vitesse apparente
    for t in np.arange(cl["t"] - 34, cl["t"] + 60, 1.0):
        u = (t - cl["t"]) / 20.0                                # passage lent devant la lune (retour : trop rapide)
        side = cl["side_m"] - 150.0 * k * u
        ahead = cl["ahead_m"] + 45.0 * k * max(u - 1, 0) ** 1.2  # après le passage : s'éloigne
        zz = alt + 6.0 * k * math.sin(u * 1.3) + 20.0 * k * max(u - 1, 0)
        x, y = pc["x"] + fx * ahead + lx * side, pc["y"] + fy * ahead + ly * side
        yaw = math.degrees(math.atan2(-ly * 150 + fy * (45 if u > 1 else 0), -lx * 150 + fx * (45 if u > 1 else 0)))
        out["volante"].append([round(float(t), 2), round(x, 2), round(y, 2), round(zz, 2), round(yaw, 2)])

    OUT.write_text(json.dumps(out), encoding="utf-8")
    print(f"→ {OUT.relative_to(LAYOUT.parents[1])} : abysses {len(out['abysses'])} clés, troupeau 5 × "
          f"{len(out['troupeau'][0])}, volante {len(out['volante'])}")
    a = out["abysses"]
    print("  abysses (t, z) :", [(k[0], k[3]) for k in a[::6]])
    print("  troupeau 0 (t, z) :", [(k[0], k[3]) for k in out["troupeau"][0][::6]])


if __name__ == "__main__":
    main()
