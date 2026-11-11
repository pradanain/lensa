"""Run the built local portal without changing the census database."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app/src"))
os.environ.setdefault("OTEL_SDK_DISABLED", "true")


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description="SE2026 Bulungan local portal")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(
        "se2026.web.main:create_app",
        factory=True,
        host="127.0.0.1",
        port=args.port,
        access_log=False,
        proxy_headers=False,
    )


if __name__ == "__main__":
    main()
