"""Print local Streamlit environment details for troubleshooting blank pages."""

from __future__ import annotations

import argparse
import importlib.metadata
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_required_streamlit_version() -> str | None:
    requirements = ROOT / "requirements.txt"
    for raw_line in requirements.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("streamlit=="):
            return line.split("==", 1)[1].strip()
    return None


def fetch(url: str) -> tuple[int, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "json2qdrant-diagnostic"})
    with urllib.request.urlopen(req, timeout=5) as response:
        body = response.read(500)
        return response.status, response.headers.get("content-type", ""), body.decode(
            "utf-8", errors="replace"
        )


def probe_streamlit_frontend(base_url: str) -> bool:
    base_url = base_url.rstrip("/")
    ok = True

    for path in ("/_stcore/health", "/"):
        url = f"{base_url}{path}"
        try:
            status, content_type, sample = fetch(url)
            print(f"probe={url} status={status} content_type={content_type}")
            print(f"probe_sample={sample[:120]!r}")
        except (OSError, urllib.error.URLError) as exc:
            print(f"probe={url} error={exc}")
            ok = False

    try:
        _, _, html = fetch(f"{base_url}/")
    except (OSError, urllib.error.URLError):
        return False

    script_paths = re.findall(r'<script[^>]+src="([^"]+\.js)"', html)
    if not script_paths:
        print("probe_static_js=not_found")
        return False

    first_script = script_paths[0]
    if first_script.startswith("http://") or first_script.startswith("https://"):
        script_url = first_script
    else:
        script_url = f"{base_url}{first_script}"

    try:
        status, content_type, sample = fetch(script_url)
        print(f"probe_static_js={script_url} status={status} content_type={content_type}")
        print(f"probe_static_js_sample={sample[:120]!r}")
        if "javascript" not in content_type.lower() and "text/plain" not in content_type.lower():
            print("status=frontend_asset_unexpected_content_type")
            ok = False
    except (OSError, urllib.error.URLError) as exc:
        print(f"probe_static_js={script_url} error={exc}")
        ok = False

    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--probe-url",
        help="Optional running Streamlit URL to probe, for example http://127.0.0.1:8501",
    )
    args = parser.parse_args()

    required = read_required_streamlit_version()
    installed = importlib.metadata.version("streamlit")
    config_path = ROOT / ".streamlit" / "config.toml"

    print(f"python_executable={sys.executable}")
    print(f"python_version={sys.version.split()[0]}")
    print(f"project_root={ROOT}")
    print(f"required_streamlit={required or 'not pinned'}")
    print(f"installed_streamlit={installed}")
    print(f"streamlit_config={config_path}")
    print(f"streamlit_config_exists={config_path.exists()}")

    status_ok = True
    if required and installed != required:
        print("status=version_mismatch")
        print(
            "action=Run: python -m pip install --force-reinstall "
            f'"streamlit=={required}"'
        )
        status_ok = False

    if args.probe_url:
        status_ok = probe_streamlit_frontend(args.probe_url) and status_ok

    if status_ok:
        print("status=ok")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
