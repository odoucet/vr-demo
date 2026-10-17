"""Ambiances et bruitages Freesound : recherche de candidats, puis choix tracé dans le manifeste.

    python pipeline/audio/freesound.py search                 # tous les besoins de sounds.yaml
    python pipeline/audio/freesound.py search amb-clapotis    # un seul besoin
    python pipeline/audio/freesound.py pick amb-clapotis 673969

search : télécharge l'aperçu HQ des meilleurs candidats (licence filtrée) dans audio/sfx/candidates/<id>/
et écrit audio/sfx/candidates/README.md (liste à écouter, liens vers Freesound).
pick : copie le candidat retenu dans audio/sfx/<id>.ogg et ajoute l'entrée au manifeste (auteur, licence,
lien). L'aperçu (OGG ~192 kb/s) suffit au prototypage ; l'original sans perte demandera une connexion OAuth.
Clé API : ~/.config/barque/freesound.env (FREESOUND_API_KEY), hors dépôt.
"""
import argparse
import json
import os
import shutil
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).with_name("sounds.yaml")
CANDIDATES = ROOT / "audio" / "sfx" / "candidates"
CHOSEN = ROOT / "audio" / "sfx"
MANIFEST = ROOT / "assets" / "manifest.yaml"
API = "https://freesound.org/apiv2"
SECRETS = Path.home() / ".config" / "barque" / "freesound.env"
LICENSES = {"cc0": '"Creative Commons 0"', "ccby": '"Attribution"'}
FIELDS = "id,name,username,license,duration,previews,avg_rating,num_downloads,url,tags"


def api_key():
    if os.environ.get("FREESOUND_API_KEY"):
        return os.environ["FREESOUND_API_KEY"]
    for line in SECRETS.read_text(encoding="utf-8").splitlines():
        if line.startswith("FREESOUND_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"FREESOUND_API_KEY introuvable ({SECRETS})")


def search(need, n, max_duration, key):
    """Tri par pertinence (le tri par note fait remonter des sons hors sujet), puis on écarte les sons
    jamais notés et peu téléchargés, signe d'enregistrements non éprouvés."""
    allowed = need.get("licence", "cc0").split("+")
    lic = " OR ".join(LICENSES[a] for a in allowed)
    params = {"query": need["query"],
              "filter": f"license:({lic}) duration:[{need['min_duration']} TO {need.get('max_duration', max_duration)}]",
              "sort": "score", "fields": FIELDS, "page_size": n * 4, "token": key}
    r = requests.get(f"{API}/search/text/", params=params, timeout=30)
    r.raise_for_status()
    results = r.json()["results"]
    proven = [x for x in results if x["avg_rating"] >= 3.5 or x["num_downloads"] >= 200]
    return (proven or results)[:n]


def cmd_search(args):
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    key = api_key()
    needs = [s for s in cfg["sounds"] if not args.ids or s["id"] in args.ids]
    index = {}
    index_file = CANDIDATES / "candidates.json"
    if index_file.exists():
        index = json.loads(index_file.read_text(encoding="utf-8"))
    for need in needs:
        results = search(need, cfg["candidates"], cfg.get("max_duration", 300), key)
        folder = CANDIDATES / need["id"]
        folder.mkdir(parents=True, exist_ok=True)
        entries = []
        for r in results:
            dest = folder / f"{r['id']}.ogg"
            if not dest.exists():
                audio = requests.get(r["previews"]["preview-hq-ogg"], timeout=120)
                audio.raise_for_status()
                dest.write_bytes(audio.content)
            entries.append({k: r[k] for k in ("id", "name", "username", "license", "duration", "avg_rating", "num_downloads", "url")}
                           | {"file": str(dest.relative_to(ROOT))})
        index[need["id"]] = {"query": need["query"], "beats": need["beats"], "candidates": entries}
        print(f"{need['id']:20s} {len(entries)} candidat(s)")
        time.sleep(0.5)  # politesse envers l'API
    index_file.write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")
    write_report(index)


def write_report(index):
    lines = ["# Candidats Freesound à écouter", "",
             "Choisir un son : `python pipeline/audio/freesound.py pick <besoin> <id Freesound>`", ""]
    for nid, info in index.items():
        lines += [f"## {nid} — {', '.join(info['beats'])}", f"Recherche : « {info['query']} »", "",
                  "| Fichier | Titre | Auteur | Durée | Note | Licence |", "|---|---|---|---|---|---|"]
        for c in info["candidates"]:
            rel = Path(c["file"]).relative_to("audio/sfx/candidates")
            lic = "CC0" if "zero" in c["license"] or "/0/" in c["license"] else "CC-BY"
            lines.append(f"| [{c['id']}.ogg]({rel}) | [{c['name']}]({c['url']}) | {c['username']} | "
                         f"{c['duration']:.0f} s | {c['avg_rating']:.1f} | {lic} |")
        lines.append("")
    (CANDIDATES / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Liste : {(CANDIDATES / 'README.md').relative_to(ROOT)}")


def cmd_pick(args):
    index = json.loads((CANDIDATES / "candidates.json").read_text(encoding="utf-8"))
    cand = next((c for c in index.get(args.need, {}).get("candidates", []) if c["id"] == args.freesound_id), None)
    if cand is None:
        raise SystemExit(f"{args.freesound_id} n'est pas un candidat de {args.need} (relancer search ?)")
    dest = CHOSEN / f"{args.need}.ogg"
    shutil.copyfile(ROOT / cand["file"], dest)
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {"assets": []}
    entry = {"id": f"sfx/{args.need}", "type": "sound", "file": str(dest.relative_to(ROOT)),
             "source": f"Freesound #{cand['id']} « {cand['name']} » par {cand['username']}", "url": cand["url"],
             "licence": cand["license"], "credit": f"{cand['name']} by {cand['username']} (freesound.org)",
             "format": "aperçu OGG ~192 kb/s (original à récupérer via OAuth pour le master)",
             "beats": index[args.need]["beats"], "script": f"pipeline/audio/freesound.py pick {args.need} {cand['id']}"}
    data["assets"] = [a for a in data["assets"] if a.get("id") != entry["id"]] + [entry]
    MANIFEST.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
    print(f"{dest.relative_to(ROOT)} ← {entry['source']} ({cand['license']})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("search")
    p.add_argument("ids", nargs="*")
    p.set_defaults(func=cmd_search)
    p = sub.add_parser("pick")
    p.add_argument("need")
    p.add_argument("freesound_id", type=int)
    p.set_defaults(func=cmd_pick)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
