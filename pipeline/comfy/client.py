"""Client minimal de l'API HTTP de ComfyUI local (soumission, attente, téléchargement)."""
import copy
import json
import os
import time
import uuid
from pathlib import Path

import requests

COMFY_URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
WORKFLOWS = Path(__file__).parent / "workflows"
CLIENT_ID = f"vr-demo-{uuid.uuid4().hex[:8]}"


class ComfyError(RuntimeError):
    pass


def load_workflow(name):
    """Charge un workflow au format API depuis pipeline/comfy/workflows/ (copie modifiable)."""
    return copy.deepcopy(json.loads((WORKFLOWS / name).read_text(encoding="utf-8")))


def strip_meta(prompt):
    return {nid: {k: v for k, v in node.items() if k != "_meta"} for nid, node in prompt.items()}


def submit(prompt):
    r = requests.post(f"{COMFY_URL}/prompt", json={"prompt": strip_meta(prompt), "client_id": CLIENT_ID}, timeout=30)
    if r.status_code != 200:
        raise ComfyError(f"/prompt a refusé le workflow ({r.status_code}) : {r.text[:2000]}")
    body = r.json()
    if body.get("node_errors"):
        # ComfyUI exécute quand même les sorties valides : on annule pour ne pas produire un résultat partiel.
        requests.post(f"{COMFY_URL}/queue", json={"delete": [body["prompt_id"]]}, timeout=30)
        raise ComfyError(f"Erreurs de validation : {json.dumps(body['node_errors'])[:2000]}")
    return body["prompt_id"]


def wait(prompt_id, timeout=3600, poll=2.0):
    """Attend la fin d'un prompt et renvoie son entrée d'historique."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=30)
        r.raise_for_status()
        entry = r.json().get(prompt_id)
        if entry:
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                errors = [m for m in status.get("messages", []) if m[0] == "execution_error"]
                raise ComfyError(f"Échec du prompt {prompt_id} : {json.dumps(errors)[:2000]}")
            if status.get("completed"):
                return entry
        time.sleep(poll)
    raise ComfyError(f"Délai dépassé pour le prompt {prompt_id}")


def output_files(entry, node_id, kind):
    """Fichiers produits par un nœud de sortie (kind : 'images', 'audio', ...)."""
    return entry.get("outputs", {}).get(str(node_id), {}).get(kind, [])


def download(fileinfo, dest):
    params = {k: fileinfo[k] for k in ("filename", "subfolder", "type")}
    r = requests.get(f"{COMFY_URL}/view", params=params, timeout=300)
    r.raise_for_status()
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return dest


def free(unload_models=True, free_memory=True):
    """Libère la VRAM de ComfyUI (à faire avant un rendu UE ou un bake)."""
    requests.post(f"{COMFY_URL}/free", json={"unload_models": unload_models, "free_memory": free_memory}, timeout=30)


def upload_image(path, subfolder="barque"):
    """Envoie une image dans le dossier input de ComfyUI ; renvoie le nom à passer à LoadImage."""
    path = Path(path)
    with path.open("rb") as f:
        r = requests.post(f"{COMFY_URL}/upload/image", files={"image": (path.name, f)},
                          data={"subfolder": subfolder, "overwrite": "true"}, timeout=120)
    r.raise_for_status()
    info = r.json()
    return f"{info['subfolder']}/{info['name']}" if info.get("subfolder") else info["name"]
