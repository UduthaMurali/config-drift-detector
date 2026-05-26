"""Unit tests for the drift detection engine."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.drift_engine import detect_drift, EnvRef, ConfigDecl


def make_ref(variable, language="python", has_default=False, is_dynamic=False):
    return EnvRef(variable=variable, file="test.py", line=1,
                  method="os.getenv", language=language,
                  has_default=has_default, is_dynamic=is_dynamic)

def make_decl(variable, source="kubernetes"):
    return ConfigDecl(variable=variable, file="k8s.yaml", source=source)


def test_no_drift():
    refs = [make_ref("DATABASE_URL"), make_ref("API_KEY")]
    decls = [make_decl("DATABASE_URL"), make_decl("API_KEY")]
    report = detect_drift(refs, decls, ["k8s.yaml"], ["python"])
    assert report.status == "CLEAN"
    assert len(report.missing_in_config) == 0


def test_critical_drift():
    refs = [make_ref("DATABASE_URL"), make_ref("STRIPE_SECRET")]
    decls = [make_decl("DATABASE_URL")]
    report = detect_drift(refs, decls, ["k8s.yaml"], ["python"])
    assert report.status == "DRIFT_DETECTED"
    assert any(d.variable == "STRIPE_SECRET" for d in report.missing_in_config)


def test_default_value_is_warning_not_critical():
    refs = [make_ref("REDIS_HOST", has_default=True)]
    decls = []
    report = detect_drift(refs, decls, [], ["python"])
    item = next((d for d in report.missing_in_config if d.variable == "REDIS_HOST"), None)
    assert item is not None
    assert item.severity == "warning"
    assert report.status == "CLEAN"  # only warnings, no critical


def test_unused_in_config():
    refs = [make_ref("DATABASE_URL")]
    decls = [make_decl("DATABASE_URL"), make_decl("LEGACY_DB_HOST")]
    report = detect_drift(refs, decls, ["k8s.yaml"], ["python"])
    assert any(d.variable == "LEGACY_DB_HOST" for d in report.unused_in_config)


def test_case_insensitive():
    refs = [make_ref("database_url")]
    decls = [make_decl("DATABASE_URL")]
    report = detect_drift(refs, decls, ["k8s.yaml"], ["python"])
    assert report.status == "CLEAN"


def test_dynamic_vars_reported_separately():
    refs = [make_ref("<dynamic>", is_dynamic=True)]
    decls = []
    report = detect_drift(refs, decls, [], ["python"])
    assert len(report.dynamic_warnings) == 1
    assert len(report.missing_in_config) == 0


def test_multilanguage_refs():
    refs = [
        make_ref("DATABASE_URL", language="python"),
        make_ref("API_KEY", language="java"),
        make_ref("SMTP_HOST", language="cpp"),
    ]
    decls = [make_decl("DATABASE_URL"), make_decl("API_KEY")]
    report = detect_drift(refs, decls, [], ["python", "java", "cpp"])
    assert any(d.variable == "SMTP_HOST" and d.language == "cpp"
               for d in report.missing_in_config)


if __name__ == "__main__":
    test_no_drift()
    test_critical_drift()
    test_default_value_is_warning_not_critical()
    test_unused_in_config()
    test_case_insensitive()
    test_dynamic_vars_reported_separately()
    test_multilanguage_refs()
    print("All drift engine tests passed!")
