"""Unit tests for the Java scanner (fallback regex-based scanner)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scanners.java.java_scanner_fallback import scan_file, scan_directory


def test_system_getenv(tmp_path):
    f = tmp_path / "App.java"
    f.write_text('String db = System.getenv("DATABASE_URL");\n')
    refs = scan_file(str(f))
    assert any(r.variable == "DATABASE_URL" for r in refs)


def test_value_annotation(tmp_path):
    f = tmp_path / "App.java"
    f.write_text('@Value("${stripe.secret}")\nprivate String secret;\n')
    refs = scan_file(str(f))
    assert any(r.variable == "STRIPE_SECRET" for r in refs)


def test_value_with_default(tmp_path):
    f = tmp_path / "App.java"
    f.write_text('@Value("${server.port:8080}")\nprivate int port;\n')
    refs = scan_file(str(f))
    r = next((r for r in refs if r.variable == "SERVER_PORT"), None)
    assert r is not None
    assert r.has_default is True


def test_get_property(tmp_path):
    f = tmp_path / "App.java"
    f.write_text('String host = env.getProperty("redis.host");\n')
    refs = scan_file(str(f))
    assert any(r.variable == "REDIS_HOST" for r in refs)


def test_get_property_with_default(tmp_path):
    f = tmp_path / "App.java"
    f.write_text('String lvl = env.getProperty("log.level", "INFO");\n')
    refs = scan_file(str(f))
    r = next((r for r in refs if r.variable == "LOG_LEVEL"), None)
    assert r is not None
    assert r.has_default is True


def test_configuration_properties(tmp_path):
    f = tmp_path / "App.java"
    f.write_text('@ConfigurationProperties(prefix="app.db")\npublic class Config {}\n')
    refs = scan_file(str(f))
    assert any(r.variable == "APP_DB_*" for r in refs)


def test_dynamic_getenv(tmp_path):
    f = tmp_path / "App.java"
    f.write_text('String val = System.getenv(keyName);\n')
    refs = scan_file(str(f))
    assert any(r.is_dynamic for r in refs)


def test_comments_ignored(tmp_path):
    f = tmp_path / "App.java"
    f.write_text('// String x = System.getenv("COMMENTED_KEY");\n')
    refs = scan_file(str(f))
    assert not any(r.variable == "COMMENTED_KEY" for r in refs)


def test_fixture_file():
    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "java", "PaymentService.java")
    if not os.path.exists(fixture):
        return
    refs = scan_file(fixture)
    var_names = {r.variable for r in refs if not r.is_dynamic}
    assert "STRIPE_SECRET" in var_names
    assert "API_KEY" in var_names
    assert "DATABASE_URL" in var_names
    assert "STRIPE_WEBHOOK_URL" in var_names


if __name__ == "__main__":
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp)
        test_system_getenv(p)
        test_value_annotation(p)
        test_value_with_default(p)
        test_get_property(p)
        test_get_property_with_default(p)
        test_configuration_properties(p)
        test_dynamic_getenv(p)
        test_comments_ignored(p)
    test_fixture_file()
    print("All Java scanner tests passed!")
