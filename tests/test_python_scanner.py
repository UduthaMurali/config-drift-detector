"""Unit tests for the Python AST scanner."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scanners.python.python_scanner import scan_file, scan_directory


def test_os_environ_subscript(tmp_path):
    f = tmp_path / "app.py"
    f.write_text('import os\ndb = os.environ["DATABASE_URL"]\n')
    refs = scan_file(str(f))
    assert any(r.variable == "DATABASE_URL" for r in refs)


def test_os_getenv(tmp_path):
    f = tmp_path / "app.py"
    f.write_text('import os\nkey = os.getenv("API_KEY")\n')
    refs = scan_file(str(f))
    assert any(r.variable == "API_KEY" for r in refs)


def test_os_getenv_with_default(tmp_path):
    f = tmp_path / "app.py"
    f.write_text('import os\nhost = os.getenv("REDIS_HOST", "localhost")\n')
    refs = scan_file(str(f))
    r = next((r for r in refs if r.variable == "REDIS_HOST"), None)
    assert r is not None
    assert r.has_default is True


def test_os_environ_get(tmp_path):
    f = tmp_path / "app.py"
    f.write_text('import os\nlvl = os.environ.get("LOG_LEVEL", "INFO")\n')
    refs = scan_file(str(f))
    assert any(r.variable == "LOG_LEVEL" for r in refs)


def test_dynamic_pattern(tmp_path):
    f = tmp_path / "app.py"
    f.write_text('import os\nkey = os.getenv(some_var)\n')
    refs = scan_file(str(f))
    assert any(r.is_dynamic for r in refs)


def test_comments_ignored(tmp_path):
    f = tmp_path / "app.py"
    f.write_text('import os\n# db = os.environ["COMMENTED_OUT"]\n')
    refs = scan_file(str(f))
    assert not any(r.variable == "COMMENTED_OUT" for r in refs)


def test_fixture_file():
    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "python", "app.py")
    if not os.path.exists(fixture):
        return
    refs = scan_file(fixture)
    var_names = {r.variable for r in refs if not r.is_dynamic}
    assert "DATABASE_URL" in var_names
    assert "API_KEY" in var_names
    assert "STRIPE_SECRET" in var_names


if __name__ == "__main__":
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        test_os_environ_subscript(tmp_path)
        test_os_getenv(tmp_path)
        test_os_getenv_with_default(tmp_path)
        test_os_environ_get(tmp_path)
        test_dynamic_pattern(tmp_path)
        test_comments_ignored(tmp_path)
        test_fixture_file()
    print("All Python scanner tests passed!")
