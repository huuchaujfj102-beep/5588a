"""Rights-aware, capabilities-first open-model routing. Catalog is not deployment proof."""
import json
from pathlib import Path


class RoutingError(ValueError):
    pass


def catalog():
    path = Path(__file__).with_name("model_catalog.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["id"]: item for item in data["models"]}


def route(stage, candidates, commercial=True):
    """Only accept explicit, reviewed model IDs; fail closed rather than silent fallback."""
    registered = catalog()
    if not isinstance(candidates, list):
        raise RoutingError(stage + " providers must be a list")
    viable = []
    for item in candidates:
        if not isinstance(item, dict) or item.get("kind") != "comfyui":
            raise RoutingError("Only explicit ComfyUI providers supported for media")
        ident = item.get("model_id", "")
        if ident not in registered:
            raise RoutingError("Provider has unknown/unregistered model_id; no guessing weights")
        spec = registered[ident]
        if stage not in spec["stages"]:
            raise RoutingError("Model " + ident + " does not support stage " + stage)
        policy = spec["license_policy"]
        if commercial and policy == "noncommercial":
            raise RoutingError("Noncommercial checkpoint blocked for commercial project: " + ident)
        if policy == "review" and not item.get("license_checked", False):
            raise RoutingError("Checkpoint legal/license approval missing: " + ident)
        if not item.get("graph") or not item.get("patches"):
            raise RoutingError("ComfyUI API graph / verified patch mapping missing: " + ident)
        viable.append(item)
    return sorted(viable, key=lambda x: (int(x.get("priority", 100)), x.get("model_id", "")))


def preflight(config):
    for stage in ("image", "video", "audio"):
        if config.get(stage):
            route(stage, config[stage], commercial=config.get("commercial", True))
    mode = config.get("audio_mode", "separate")
    if mode not in ("embedded", "separate"):
        raise RoutingError("audio_mode must be embedded or separate")
    if mode == "embedded" and not config.get("video"):
        raise RoutingError("Embedded audio requires a live video provider")
    if mode == "embedded" and config.get("video"):
        for candidate in config["video"]:
            if not candidate.get("supports_embedded_audio", False):
                raise RoutingError("All embedded-audio video candidates must be verified as AV models")
    if config.get("frame_bridge", False):
        if not config.get("image") or not all(
            any(p.get("from") == "reference_image_upload" for p in v.get("patches", []))
            for v in config["image"]):
            raise RoutingError("Frame bridge needs an image graph with mapped reference_image_upload")
    return True
