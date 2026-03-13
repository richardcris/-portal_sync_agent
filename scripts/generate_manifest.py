import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python scripts/generate_manifest.py <version> <download_url> [notes] [setup_sha256]")
        return 1

    version = sys.argv[1].strip()
    download_url = sys.argv[2].strip()
    notes = sys.argv[3].strip() if len(sys.argv) >= 4 else "Atualizacao automatica publicada."
    setup_sha256 = sys.argv[4].strip().lower() if len(sys.argv) >= 5 else ""

    dist_dir = Path("dist")
    dist_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "latest_version": version,
        "download_url": download_url,
        "notes": notes,
    }

    if setup_sha256:
        payload["setup_sha256"] = setup_sha256

    manifest_path = dist_dir / "manifest.json"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Manifest generated at {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
