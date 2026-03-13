import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/set_version.py <version>")
        return 1

    version = sys.argv[1].strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        print("Version must follow semantic format: X.Y.Z")
        return 1

    file_path = Path("sync_agent.py")
    source = file_path.read_text(encoding="utf-8")

    pattern = r'^APP_VERSION\s*=\s*"[^"]+"\s*$'
    replacement = f'APP_VERSION = "{version}"'

    updated, count = re.subn(pattern, replacement, source, count=1, flags=re.MULTILINE)
    if count != 1:
        print("Failed to update APP_VERSION in sync_agent.py")
        return 1

    file_path.write_text(updated, encoding="utf-8")
    print(f"APP_VERSION updated to {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
