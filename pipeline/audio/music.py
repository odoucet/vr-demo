"""Musique ACE-Step 1.5 XL : brouillons turbo sur N seeds LM, puis rendu sft de la seed retenue.

    python pipeline/audio/music.py draft --seeds 30          # explore les seeds LM 1..30 en turbo
    python pipeline/audio/music.py render --lm-seed 17       # fige la composition 17, rendu sft
    python pipeline/audio/music.py analyze <dossier>         # refait le pré-tri d'un dossier
    python pipeline/audio/music.py compare a.flac b.flac ... # vérifie qu'une composition est conservée

Idempotent : le dossier de sortie est nommé d'après le hash de la composition (texte, métadonnées,
paramètres du LM). Relancer la même commande saute les fichiers déjà produits.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import soundfile as sf
import yaml

PIPELINE = Path(__file__).resolve().parents[1]
ROOT = PIPELINE.parent
sys.path.insert(0, str(PIPELINE))

from comfy import client  # noqa: E402
from gpu import gpu_lock  # noqa: E402

import music_analysis  # noqa: E402

CONFIG = Path(__file__).with_name("music.yaml")
WORKFLOW = "ace15_text2music.json"
OUT = ROOT / "audio" / "music" / "ace"
MANIFEST = ROOT / "assets" / "manifest.yaml"


def rel(p):
    p = Path(p).resolve()
    return p.relative_to(ROOT) if p.is_relative_to(ROOT) else p


def load_config():
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def lyrics(cfg):
    """Structure du morceau : une balise de section par beat du séquencier, sans paroles."""
    return "\n\n".join(f"[{s['tag']}]" for s in cfg["sections"])


def composition(cfg):
    """Tout ce qui détermine les codes audio du LM, hors seed."""
    return {
        "tags": cfg["style"], "lyrics": lyrics(cfg), "bpm": cfg["bpm"],
        "duration": float(cfg["end_s"] - cfg["offset_s"]), "timesignature": cfg["timesignature"],
        "language": cfg["language"], "keyscale": cfg["keyscale"], "text_encoders": cfg["text_encoders"],
        **cfg["lm"],
    }


def comp_hash(cfg):
    return hashlib.sha1(json.dumps(composition(cfg), sort_keys=True).encode()).hexdigest()[:8]


def build_prompt(cfg, stage, lm_seed, dit_seed, prefix):
    comp = composition(cfg)
    st = cfg[stage]
    wf = client.load_workflow(WORKFLOW)
    wf["1"]["inputs"]["unet_name"] = st["model"]
    wf["2"]["inputs"]["shift"] = st["shift"]
    wf["3"]["inputs"]["clip_name1"], wf["3"]["inputs"]["clip_name2"] = cfg["text_encoders"]
    wf["4"]["inputs"]["vae_name"] = cfg["vae"]
    enc = wf["5"]["inputs"]
    for k in ("tags", "lyrics", "bpm", "duration", "timesignature", "language", "keyscale",
              "cfg_scale", "temperature", "top_p", "top_k", "min_p"):
        enc[k] = comp[k]
    enc["seed"] = lm_seed
    wf["7"]["inputs"]["seconds"] = comp["duration"]
    wf["8"]["inputs"].update(seed=dit_seed, steps=st["steps"], cfg=st["cfg"])
    wf["10"]["inputs"]["filename_prefix"] = prefix
    return wf


def run_jobs(jobs):
    """jobs : liste de (prompt, destination). Tout est mis en file, puis récupéré dans l'ordre."""
    todo = [(p, d) for p, d in jobs if not d.exists()]
    if len(todo) < len(jobs):
        print(f"{len(jobs) - len(todo)} fichier(s) déjà présent(s), ignoré(s).")
    if not todo:
        return
    ids = [(client.submit(p), d) for p, d in todo]
    t0 = time.time()
    for i, (pid, dest) in enumerate(ids, 1):
        entry = client.wait(pid, timeout=7200)
        files = client.output_files(entry, "10", "audio")
        if not files:
            raise client.ComfyError(f"Aucun audio produit pour {dest.name}")
        client.download(files[0], dest)
        el = time.time() - t0
        print(f"[{i}/{len(ids)}] {rel(dest)}  ({el / i:.0f} s/fichier, reste ~{el / i * (len(ids) - i) / 60:.0f} min)")


def cmd_draft(args):
    cfg = load_config()
    h = comp_hash(cfg)
    out = OUT / "drafts" / h
    out.mkdir(parents=True, exist_ok=True)
    (out / "composition.json").write_text(json.dumps({"hash": h, **composition(cfg), "draft": cfg["draft"]},
                                                     indent=2, ensure_ascii=False), encoding="utf-8")
    seeds = range(args.start, args.start + args.seeds)
    jobs = [(build_prompt(cfg, "draft", s, s, f"vr-demo/music/{h}/draft"), out / f"lm{s:04d}-turbo.flac") for s in seeds]
    with gpu_lock("music.py draft (ComfyUI ACE-Step)"):
        run_jobs(jobs)
    analyze_dir(out, cfg)


def cmd_render(args):
    cfg = load_config()
    h = comp_hash(cfg)
    dit_seed = args.lm_seed if args.dit_seed is None else args.dit_seed
    dest = OUT / "render" / f"{cfg['name']}-{h}-lm{args.lm_seed:04d}-dit{dit_seed:04d}-sft.flac"
    wf = build_prompt(cfg, "render", args.lm_seed, dit_seed, f"vr-demo/music/{h}/render")
    with gpu_lock("music.py render (ComfyUI ACE-Step)"):
        run_jobs([(wf, dest)])
    wav = dest.with_suffix(".wav")
    if not wav.exists():
        data, sr = sf.read(dest)
        sf.write(wav, data, sr, subtype="PCM_24")
    update_manifest(cfg, h, args.lm_seed, dit_seed, wav)
    print(f"Rendu : {rel(wav)}")
    draft = OUT / "drafts" / h / f"lm{args.lm_seed:04d}-turbo.flac"
    if draft.exists():
        sim = music_analysis.compare([draft, dest])[0, 1]
        print(f"Similarité harmonique brouillon turbo / rendu sft : {sim:.2f} (1 = identique)")


def analyze_dir(out, cfg):
    files = sorted(Path(out).glob("*.flac"))
    if not files:
        print("Aucun fichier à analyser.")
        return
    results = [music_analysis.analyze(f, cfg) for f in files]
    ranked = music_analysis.report(results, cfg, out)
    print(f"\nPré-tri : {rel(Path(out, 'report.md'))}  ·  planche : {rel(Path(out, 'planche.png'))}")
    for r in ranked[:5]:
        print(f"  {Path(r['file']).name}  score {r['score']:.2f}  arc {r['arc']:+.2f} (ρ {r['arc_rho']:+.2f}, {r['dyn_db']:.1f} dB)  frontières ±{r['boundary_err_s']:.1f} s")


def cmd_analyze(args):
    analyze_dir(Path(args.dir), load_config())


def cmd_compare(args):
    m = music_analysis.compare(args.files)
    names = [Path(f).stem for f in args.files]
    w = max(len(n) for n in names)
    print(" " * w + "".join(f"{i:>7}" for i in range(len(names))))
    for i, n in enumerate(names):
        print(f"{n:<{w}}" + "".join(f"{v:7.2f}" for v in m[i]) + f"   [{i}]")


def update_manifest(cfg, h, lm_seed, dit_seed, wav):
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else None
    data = data or {"assets": []}
    entry = {
        "id": f"music/{cfg['name']}",
        "type": "music",
        "file": str(rel(wav)),
        "source": "ACE-Step 1.5 XL (LM 4B + DiT sft), ComfyUI local",
        "workflow": f"pipeline/comfy/workflows/{WORKFLOW}",
        "script": "pipeline/audio/music.py render --lm-seed {} --dit-seed {}".format(lm_seed, dit_seed),
        "seed": {"lm": lm_seed, "dit": dit_seed},
        "composition_hash": h,
        "prompt": cfg["style"],
        "structure": lyrics(cfg),
        "params": {k: v for k, v in composition(cfg).items() if k not in ("tags", "lyrics")} | {"render": cfg["render"]},
        "timeline_offset_s": cfg["offset_s"],
        "licence": "Généré localement ; modèles ACE-Step 1.5 sous licence Apache-2.0",
        "generated": time.strftime("%Y-%m-%d"),
    }
    data["assets"] = [a for a in data["assets"] if a.get("id") != entry["id"]] + [entry]
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("draft", help="explore des seeds LM avec le DiT turbo")
    p.add_argument("--seeds", type=int, default=30)
    p.add_argument("--start", type=int, default=1)
    p.set_defaults(func=cmd_draft)
    p = sub.add_parser("render", help="rend une seed LM retenue avec le DiT sft")
    p.add_argument("--lm-seed", type=int, required=True)
    p.add_argument("--dit-seed", type=int, help="seed du DiT (défaut : la seed LM)")
    p.set_defaults(func=cmd_render)
    p = sub.add_parser("analyze", help="pré-tri d'un dossier de brouillons")
    p.add_argument("dir")
    p.set_defaults(func=cmd_analyze)
    p = sub.add_parser("compare", help="matrice de similarité harmonique entre fichiers")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_compare)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
