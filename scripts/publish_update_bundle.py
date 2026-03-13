import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


APP_EXE = "VEXPER-SISTEMAS.exe"
SETUP_EXE = "VEXPER-SISTEMAS-Setup.exe"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_base_url(url: str) -> str:
    return url.strip().rstrip("/")


def build_manifest(version: str, base_url: str, notes: str, setup_sha256: str) -> dict:
    return {
        "latest_version": version,
        "download_url": f"{base_url}/latest/{SETUP_EXE}",
        "notes": notes,
        "setup_sha256": setup_sha256,
        "published_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def copy_artifacts(dist_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dist_dir / APP_EXE, target_dir / APP_EXE)
    shutil.copy2(dist_dir / SETUP_EXE, target_dir / SETUP_EXE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create public update bundle with manifest and binaries.")
    parser.add_argument("--version", required=True, help="Version string (example: 1.2.0)")
    parser.add_argument("--base-url", required=True, help="Public base URL where public_update folder will be hosted")
    parser.add_argument("--notes", default="Atualizacao automatica publicada.", help="Release notes")
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent.parent
    dist_dir = root_dir / "dist"

    app_exe = dist_dir / APP_EXE
    setup_exe = dist_dir / SETUP_EXE

    if not app_exe.exists() or not setup_exe.exists():
        print("Build nao encontrado. Gere os arquivos em dist antes de publicar.")
        print(f"Esperado: {app_exe}")
        print(f"Esperado: {setup_exe}")
        return 1

    public_root = root_dir / "public_update"
    latest_dir = public_root / "latest"
    version_dir = public_root / "versions" / args.version

    copy_artifacts(dist_dir, latest_dir)
    copy_artifacts(dist_dir, version_dir)

    setup_hash = sha256_file(setup_exe)

    manifest = build_manifest(
        version=args.version.strip(),
        base_url=normalize_base_url(args.base_url),
        notes=args.notes.strip(),
        setup_sha256=setup_hash,
    )

    latest_manifest = latest_dir / "manifest.json"
    version_manifest = version_dir / "manifest.json"
    latest_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    version_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    checksum_lines = [
        f"{sha256_file(dist_dir / APP_EXE)}  {APP_EXE}",
        f"{setup_hash}  {SETUP_EXE}",
    ]
    (latest_dir / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    (version_dir / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    print("Public update bundle criado com sucesso:")
    print(f"- {latest_dir}")
    print(f"- {version_dir}")
    print("URL para configurar nos agentes:")
    print(f"{normalize_base_url(args.base_url)}/latest/manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
