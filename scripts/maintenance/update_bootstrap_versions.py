#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PYPROJECT = ROOT / "pyproject.toml"
FILES = [
    ROOT / "scripts" / "install-app.sh",
    ROOT / "scripts" / "install-app.ps1",
]
README = ROOT / "README.md"
MAIN = ROOT / "src" / "inquira" / "main.py"


def read_version() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r"^version\s*=\s*\"([^\"]+)\"", text, re.MULTILINE)
    if not m:
        raise SystemExit("Could not find version in pyproject.toml")
    return m.group(1)


def pep440_normalize(version: str) -> str:
    """Best-effort PEP 440 normalization for common prerelease forms.

    Examples:
    - 0.4.3-alpha -> 0.4.3a0
    - 0.4.3-alpha1 -> 0.4.3a1
    - 0.4.3-beta -> 0.4.3b0
    - 0.4.3-rc -> 0.4.3rc0
    - 0.4.3rc1 -> 0.4.3rc1
    """
    v = version.strip().lower()
    # Remove separators around prerelease labels to simplify parsing
    v = v.replace("_", "-")
    # Map wordy labels to short forms
    v = re.sub(r"alpha", "a", v)
    v = re.sub(r"beta", "b", v)
    v = re.sub(r"(?:preview|pre|c)", "rc", v)
    # Remove dashes between base and pre label (e.g., 1.0.0-a1 -> 1.0.0a1)
    v = re.sub(r"-(?=(?:a|b|rc)\d*$)", "", v)
    # If ends with a/b/rc with no number, append 0
    m = re.search(r"^(.*?)(a|b|rc)(?:[-\.]?)(\d*)$", v)
    if m:
        base, label, num = m.groups()
        if num == "":
            num = "0"
        return f"{base}{label}{num}"
    return version


def build_urls(version: str):
    norm = pep440_normalize(version)
    tag = f"v{norm}"
    wheel = f"inquira_ce-{norm}-py3-none-any.whl"
    url = f"https://github.com/adarsh9780/inquira-ce/releases/download/{tag}/{wheel}"
    return url


def replace_in_file(path: Path, url: str):
    text = path.read_text(encoding="utf-8")
    # Replace the default wheel occurrences in scripts
    text_new = re.sub(
        r"https://github.com/adarsh9780/inquira-ce/releases/download/[^\s'\"]+/inquira_ce-[^\s'\"]+\.whl",
        url,
        text,
    )
    # Also replace the embedded __DEFAULT_WHEEL__ in the PS1 shim template if present
    text_new = text_new.replace("__DEFAULT_WHEEL__", url)
    if text_new != text:
        path.write_text(text_new, encoding="utf-8")
        return True
    return False


def main():
    version = read_version()
    url = build_urls(version)
    norm = pep440_normalize(version)
    changed = []
    for f in FILES:
        if replace_in_file(f, url):
            changed.append(f)
    if changed:
        print("Updated default wheel URLs in:")
        for c in changed:
            print(f" - {c.relative_to(ROOT)}")
        print(f"Project version: {version}")
        print(f"Normalized (PEP 440): {norm}")
        print(f"URL: {url}")
    else:
        print("No changes needed; scripts already point to:")
        print(f"URL: {url}")

    # Update README version badge and wheel references
    if README.exists():
        readme = README.read_text(encoding="utf-8")
        readme_new = readme
        # 1) Shields version badge: replace the middle value
        readme_new = re.sub(
            r"(shields\.io/badge/Version-)([^-\?]+)(-blue\?style=for-the-badge)",
            rf"\g<1>{norm}\g<3>",
            readme_new,
        )
        # 2) Replace any wheel download URLs to the normalized new one
        readme_new = re.sub(
            r"https://github.com/adarsh9780/inquira-ce/releases/download/[^\s`]+/inquira_ce-[^\s`]+\.whl",
            url,
            readme_new,
        )
        # 3) Update human-friendly text mentioning default version like "vX.Y.Z*"
        readme_new = re.sub(
            r"(uses a released wheel by default:\s*)v[^\s\.]+[\w\.-]*",
            rf"\1v{norm}",
            readme_new,
        )
        readme_new = re.sub(
            r"(default to the\s*)v[^\s\.]+[\w\.-]*",
            rf"\1v{norm}",
            readme_new,
        )
        if readme_new != readme:
            README.write_text(readme_new, encoding="utf-8")
            print("Updated README version badge and wheel links.")

    if MAIN.exists():
        main_code = MAIN.read_text(encoding="utf-8")
        main_new = re.sub(
            r"APP_VERSION\s*=\s*\"[^\"]+\"",
            f'APP_VERSION = "{version}"',
            main_code,
        )
        if main_new != main_code:
            MAIN.write_text(main_new, encoding="utf-8")
            print("Updated src/inquira/main.py APP_VERSION.")


if __name__ == "__main__":
    main()
