"""Read-only status check for previously submitted cloud render jobs."""
import argparse
import json
from .longform import LongformError, connection
from .longform_renderer import poll_render


def main(argv=None):
    p = argparse.ArgumentParser(description="Read-only Shotstack/JSON2Video render status")
    p.add_argument("--db", required=True)
    p.add_argument("--job-id", required=True)
    args = p.parse_args(argv)
    try:
        with connection(args.db) as conn:
            output = poll_render(conn, args.job_id)
        print(json.dumps(output, ensure_ascii=False))
        return 0
    except LongformError as exc:
        p.exit(2, "BLOCKED: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
