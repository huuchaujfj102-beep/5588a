import argparse
import json
from pathlib import Path

from film_audit.evidence import build_result


parser = argparse.ArgumentParser()
parser.add_argument("manifest", type=Path)
parser.add_argument("--output", type=Path, default=Path("v5.2-evidence-report.json"))
args = parser.parse_args()
result = build_result(args.manifest)
args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(result["status"] != "PASS")

