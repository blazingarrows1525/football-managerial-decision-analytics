"""Repository hygiene: no secrets, no machine-specific paths, no source data, thin entry point, no causal claims."""
from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CODE = [p for d in ("src", "pages", "scripts") for p in (ROOT / d).rglob("*.py")] + [ROOT / "app.py"]
SECRET_PATTERNS = [r"api[_-]?key\s*=\s*['\"][A-Za-z0-9_\-]{12,}", r"\bsk-[A-Za-z0-9]{20,}", r"\bghp_[A-Za-z0-9]{20,}",
                   r"password\s*=\s*['\"][^'\"]{4,}", r"BEGIN (RSA|OPENSSH) PRIVATE KEY"]
LOCAL_PATH = re.compile(r"([A-Za-z]:\\\\?Users\\|/home/[a-z]|/Users/[A-Za-z])")


def _tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    return out.stdout.split("\n") if out.returncode == 0 else []


def test_no_secrets_or_machine_paths_in_code():
    for p in CODE:
        text = p.read_text(encoding="utf-8")
        for pat in SECRET_PATTERNS:
            assert not re.search(pat, text, flags=re.I), f"possible secret in {p.relative_to(ROOT)}"
        assert not LOCAL_PATH.search(text), f"machine-specific path in {p.relative_to(ROOT)}"
        assert "st.secrets" not in text, "the public data path must not need secrets"


def test_source_data_is_ignored_and_not_tracked():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for rule in ("data/raw/", "data/processed/", ".streamlit/secrets.toml"):
        assert rule in ignore
    tracked = _tracked()
    if not tracked:
        pytest.skip("not a git checkout")
    bad = [f for f in tracked if f.startswith(("data/raw/", "data/processed/", "data/interim/"))
           or f.endswith((".parquet", "secrets.toml"))]
    assert not bad, f"source data or secrets are tracked: {bad[:5]}"


def test_entry_point_is_thin():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    assert not [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.For, ast.While))]
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert "pandas" not in imported and "numpy" not in imported, "no data work in the entry point"


def test_pages_use_the_shared_package_only():
    for p in sorted((ROOT / "pages").glob("*.py")):
        text = p.read_text(encoding="utf-8")
        assert "from src." in text
        assert "read_json" not in text and "requests.get" not in text and "open(" not in text, \
            f"{p.name} must not do its own data loading"
        assert "layout.start(" in text and "layout.footer()" in text, f"{p.name} must use the shared page chrome"


def test_no_package_import_cycles():
    """Every module of the shared package imports on its own (catches circular imports)."""
    mods = [".".join(p.relative_to(ROOT).with_suffix("").parts) for p in (ROOT / "src").rglob("*.py")
            if p.name != "__init__.py" and "dashboard" not in p.parts]
    code = "import importlib,sys\nfor m in sys.argv[1:]:\n    importlib.import_module(m)\nprint('ok')"
    out = subprocess.run(["python", "-c", code, *mods], cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0 and "ok" in out.stdout, out.stderr[-800:]


def test_user_facing_text_avoids_unsupported_causal_language():
    banned = [r"\bcaused\b", r"\bproved\b", r"made the team win", r"the best substitution", r"\boptimal XI\b(?! )"]
    files = list((ROOT / "pages").glob("*.py")) + [ROOT / "src" / "reporting" / "insight_cards.py",
                                                   ROOT / "src" / "visualization" / "catalogue.py"]
    for p in files:
        text = p.read_text(encoding="utf-8")
        for pat in banned[:4]:
            assert not re.search(pat, text, flags=re.I), f"{pat} in {p.name}"


def test_live_claims_are_only_denials():
    for p in list((ROOT / "pages").glob("*.py")) + list((ROOT / "src" / "dashboard").glob("*.py")):
        for line in p.read_text(encoding="utf-8").split("\n"):
            if re.search(r"\blive\b|real-time", line, flags=re.I) and "import" not in line:
                assert re.search(r"not|nothing|no |never|live widget|live kernel", line, flags=re.I), \
                    f"{p.name}: '{line.strip()[:90]}' presents the data as live"
