"""Conversion d'un workflow ComfyUI au format interface (templates, fichiers sauvés depuis l'UI)
vers le format API attendu par /prompt.

    python pipeline/comfy/ui2api.py template.json sortie_api.json

Les correspondances widgets → entrées viennent de /object_info du serveur en cours d'exécution :
le résultat correspond donc à la version de ComfyUI installée. Gère les widgets convertis en
entrées, les seeds avec « control_after_generate », les combos dynamiques (entrées « parent.enfant »),
les nœuds Reroute, PrimitiveNode (côté interface) et les nœuds contournés (bypass).
"""
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comfy.client import COMFY_URL  # noqa: E402

CONTROL_VALUES = {"fixed", "randomize", "increment", "decrement"}
FRONTEND_ONLY = {"Note", "MarkdownNote", "Reroute", "PrimitiveNode"}
MUTED, BYPASSED = 2, 4


def object_info():
    r = requests.get(f"{COMFY_URL}/object_info", timeout=60)
    r.raise_for_status()
    return r.json()


def _defs(spec):
    for section in ("required", "optional"):
        yield from spec.get(section, {}).items()


def _consume(defs, values, sockets, out, prefix=""):
    """Affecte les valeurs de widgets (dans l'ordre) aux entrées widget de `defs`."""
    for name, spec in defs:
        full = prefix + name
        if full in sockets and not sockets[full].get("widget"):
            continue  # vraie entrée de type lien : pas de widget
        if not values:
            return
        typ, opts = spec[0], (spec[1] if len(spec) > 1 else {})
        value = values.pop(0)
        if typ in ("INT", "FLOAT") and isinstance(value, str):
            try:
                value = int(value) if typ == "INT" else float(value)
            except ValueError:
                pass
        out[full] = value
        if values and isinstance(values[0], str) and values[0] in CONTROL_VALUES and (
                opts.get("control_after_generate") or name in ("seed", "noise_seed") or typ == "INT"):
            values.pop(0)
        if typ == "COMFY_DYNAMICCOMBO_V3":
            option = next((o for o in opts["options"] if o["key"] == value), None)
            if option:
                _consume(list(_defs(option["inputs"])), values, sockets, out, prefix=full + ".")


def convert(ui, info=None):
    info = info or object_info()
    nodes = {n["id"]: n for n in ui["nodes"]}
    links = {lk[0]: lk for lk in ui["links"]}  # id, from_node, from_slot, to_node, to_slot, type

    def source(link_id):
        """Remonte un lien à travers Reroute / nœuds contournés ; renvoie [id, slot] ou ('value', v)."""
        _, src, slot, *_ = links[link_id]
        node = nodes[src]
        if node["type"] == "Reroute" or node.get("mode") == BYPASSED:
            ins = [i for i in node.get("inputs", []) if i.get("link") is not None]
            match = next((i for i in ins if i.get("type") == links[link_id][5]), ins[0] if ins else None)
            return source(match["link"]) if match else None
        if node["type"] == "PrimitiveNode":
            return ("value", node["widgets_values"][0])
        return [str(src), slot]

    api = {}
    for nid, node in nodes.items():
        if node["type"] in FRONTEND_ONLY or node.get("mode") in (MUTED, BYPASSED):
            continue
        if node["type"] not in info:
            raise KeyError(f"Nœud {nid} : type {node['type']} absent du serveur (nœud personnalisé manquant ?)")
        sockets = {i["name"]: i for i in node.get("inputs", [])}
        inputs = {}
        _consume(list(_defs(info[node["type"]]["input"])), list(node.get("widgets_values") or []), sockets, inputs)
        # Entrées ajoutées au nœud après la sauvegarde du template : valeur par défaut du serveur.
        for name, spec in info[node["type"]]["input"].get("required", {}).items():
            opts = spec[1] if len(spec) > 1 else {}
            if name not in inputs and name not in sockets and "default" in opts:
                inputs[name] = opts["default"]
        for name, sock in sockets.items():
            if sock.get("link") is None:
                continue
            src = source(sock["link"])
            if src is None:
                continue
            inputs[name] = src[1] if isinstance(src, tuple) else src
        api[str(nid)] = {"class_type": node["type"], "inputs": inputs,
                         "_meta": {"title": node.get("title") or node["type"]}}

    # Élague les nœuds dont plus rien ne dépend et qui ne sont pas des sorties.
    used = {v[0] for n in api.values() for v in n["inputs"].values() if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str)}
    outputs = {k for k, n in api.items() if info[n["class_type"]].get("output_node")}
    keep, stack = set(), list(outputs)
    while stack:
        k = stack.pop()
        if k in keep or k not in api:
            continue
        keep.add(k)
        stack += [v[0] for v in api[k]["inputs"].values() if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str)]
    return {k: v for k, v in api.items() if k in keep or k in used and k in keep}


if __name__ == "__main__":
    ui = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    api = convert(ui)
    Path(sys.argv[2]).write_text(json.dumps(api, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(api)} nœuds écrits dans {sys.argv[2]}")
