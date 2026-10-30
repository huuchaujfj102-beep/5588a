"""Offline-safe adapters for third-party video engines. No paid API or GPU calls."""
import argparse
import ipaddress
import json
import os
import pathlib
import subprocess
import urllib.parse

PROJECTS = {
    "kinocut": {"upstream": "https://github.com/KyaniteLabs/kinocut", "license": "Apache-2.0", "mode": "local-cli"},
    "moneyprinterturbo": {"upstream": "https://github.com/harry0703/MoneyPrinterTurbo", "license": "MIT", "mode": "external-local-service"},
    "comfyui": {"upstream": "https://github.com/Comfy-Org/ComfyUI", "license": "GPL-3.0", "mode": "external-local-service"},
    "wan2.2": {"upstream": "https://github.com/Wan-Video/Wan2.2", "license": "Apache-2.0", "mode": "model-not-installed"}
}

def validate_local_endpoint(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Only plain HTTP localhost endpoints are permitted")
    host = parsed.hostname
    if host != "localhost":
        try:
            if not ipaddress.ip_address(host).is_loopback:
                raise ValueError("Remote endpoints are disabled; no paid APIs")
        except ValueError as exc:
            raise ValueError("Only localhost/loopback is permitted") from exc
    if parsed.port is None:
        raise ValueError("Explicit local port required")
    return parsed.geturl().rstrip("/")

def validate_comfy_workflow(obj):
    if not isinstance(obj, dict) or not obj:
        raise ValueError("ComfyUI API workflow must be a non-empty node map")
    for node_id, node in obj.items():
        if not str(node_id).isdigit() or not isinstance(node, dict):
            raise ValueError("Invalid node ID or node payload")
        if not isinstance(node.get("class_type"), str) or not isinstance(node.get("inputs"), dict):
            raise ValueError("Missing class_type or inputs")
    return True

def build_comfy_request(workflow):
    validate_comfy_workflow(workflow)
    return {"prompt": workflow}

def moneyprinter_health_url(base_url):
    return validate_local_endpoint(base_url) + "/docs"

def kinocut_doctor():
    return subprocess.run(["kino", "doctor", "--json"], check=False, capture_output=True, text=True, timeout=90)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["manifest", "validate-comfy", "validate-local", "kinocut-doctor"])
    parser.add_argument("--file")
    parser.add_argument("--url")
    args = parser.parse_args()
    if args.action == "manifest":
        print(json.dumps(PROJECTS, indent=2))
    elif args.action == "validate-comfy":
        if not args.file:
            parser.error("--file required")
        path = pathlib.Path(args.file)
        if path.stat().st_size > 2_000_000:
            raise ValueError("Workflow JSON too large")
        print(json.dumps(build_comfy_request(json.loads(path.read_text(encoding="utf-8")))))
    elif args.action == "validate-local":
        print(validate_local_endpoint(args.url))
    else:
        result = kinocut_doctor()
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        raise SystemExit(result.returncode)

if __name__ == "__main__":
    main()
