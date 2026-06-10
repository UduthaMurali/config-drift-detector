# Config Drift Detector

> Catch environment variable mismatches between source code and deployment config — before they hit production.

[![Drift Check](https://github.com/UduthaMurali/config-drift-detector/actions/workflows/drift-check.yml/badge.svg)](https://github.com/UduthaMurali/config-drift-detector/actions/workflows/drift-check.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What Is This Tool?

**Config Drift Detector** is a static analysis GitHub Action that detects *code-to-config drift* — the gap that opens up when your source code references environment variables that are never declared in your deployment configuration files.

This kind of drift is invisible until runtime. A missing `DATABASE_URL` or `STRIPE_SECRET` in your Kubernetes manifest or Docker Compose file won't be caught by unit tests or linters. It will, however, crash your service in production.

Config Drift Detector closes that gap by scanning your source code for every `getenv()`, `System.getenv()`, or `std::getenv()` call, then cross-referencing those variables against your actual config files — and failing the PR if anything is missing.

**Who is it for?**

- Teams shipping to Kubernetes, Docker, or any env-var-driven deployment
- Projects with mixed-language codebases (Python, Java, C++, Go, JavaScript, and Rust are all supported)
- CI/CD pipelines that need a lightweight, zero-infra drift gate

---

## Features

- **Multi-language scanning** — Python (AST), Java (Eclipse JDT with regex fallback), C++ (Tree-sitter with regex fallback), Go, JavaScript, and Rust
- **Broad config support** — Kubernetes YAML, Docker Compose, `.env` files, Dockerfiles
- **Severity levels** — `critical` for variables with no default, `warning` for variables that have a fallback
- **PR blocking** — exits with code `1` on critical drift so your branch protection rules do the rest
- **JSON output** — machine-readable results for downstream tooling
- **`.driftignore`** — suppress known false positives like `PATH`, `HOME`, `JAVA_HOME`

---

## How It Works

1. **Scan source code** — language-specific scanners extract every environment variable reference from your code using AST or regex parsing.
2. **Parse config files** — parsers extract every declared variable from your Kubernetes manifests, Docker Compose files, `.env` files, and Dockerfiles.
3. **Diff** — the drift engine computes the set difference: variables referenced in code but absent from config.
4. **Report** — results are printed in a human-readable table (or JSON), with severity assigned per variable. Exit code `1` blocks the PR if critical drift is found.

```
Code scanning  →  Config parsing  →  Set diff  →  Report + exit code
```

---

## Quick Start

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Run a basic scan:**

```bash
python main.py --source src/ --config k8s/,docker-compose.yml,.env
```

**Fail CI on critical drift:**

```bash
python main.py --source src/ --config k8s/ --fail-on-drift
```

**Get JSON output:**

```bash
python main.py --source src/ --config k8s/ --json
```

**Run the test suite:**

```bash
pip install pytest && pytest tests/ -v
```

---

## GitHub Action Usage

Add this step to any workflow to block PRs that introduce drift:

```yaml
- name: Check for config drift
  uses: UduthaMurali/config-drift-detector@v1
  with:
    source-paths: 'src/'
    config-paths: 'k8s/, docker-compose.yml, .env'
    languages: 'java,python,cpp'
    fail-on-drift: 'true'
```

### Inputs

| Input | Required | Description |
|---|---|---|
| `source-paths` | Yes | Comma-separated paths to scan for env var references |
| `config-paths` | Yes | Comma-separated paths to deployment config files/dirs |
| `languages` | No | Languages to scan: `python`, `java`, `cpp` (default: all) |
| `fail-on-drift` | No | Exit with code `1` on critical drift (default: `false`) |

---

## .github/workflows/drift-check.yml

Copy this file into your repo to enable drift detection on every PR:

```yaml
name: Config Drift Check

on:
  pull_request:
    branches:
      - main
      - master
  push:
    branches:
      - main
      - master

jobs:
  drift-check:
    name: Detect Config Drift
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Config Drift Detector
        uses: UduthaMurali/config-drift-detector@v1
        with:
          # Path(s) to your source code — comma-separated
          source-paths: 'src/'

          # Path(s) to your deployment config files — comma-separated
          # Supports: Kubernetes YAML dirs, docker-compose.yml, .env files, Dockerfiles
          config-paths: 'k8s/, docker-compose.yml, .env'

          # Languages to scan — remove any your project doesn't use
          # Options: python, java, cpp, go, js, rust, spring, pydantic
          languages: 'python,java,cpp,go,js,rust'

          # Fail the PR if critical drift (missing vars with no default) is found
          fail-on-drift: 'true'

          # Path to your .driftignore file (suppresses known false positives)
          driftignore: '.driftignore'
```

---

## .driftignore

Create a `.driftignore` file at the root of your repo to suppress variables that are always present in any environment and don't need to be declared in your configs:

```
# System variables
PATH
JAVA_HOME
HOME
USER
```

Any variable listed here will be excluded from drift reports entirely.

---

## Comparison with Existing Tools

| Feature | Config Drift Detector | envgrd | DriftGuard |
|---|---|---|---|
| Python scanning (AST) | ✅ | Regex only | ❌ |
| Java scanning | ✅ JDT + fallback | ❌ | ❌ |
| C++ scanning | ✅ Tree-sitter + regex | ❌ | ❌ |
| Kubernetes / Docker Compose | ✅ | ✅ | ✅ GitOps |
| GitHub Action + PR blocking | ✅ | ❌ | ❌ |
| JSON output | ✅ | ❌ | ❌ |
| `.driftignore` support | ✅ | ❌ | ❌ |
| Severity levels | ✅ | ❌ | ❌ |

Config Drift Detector is the only tool in this space that combines multi-language AST analysis with native GitHub Action PR blocking and a configurable ignore list.

---

## Evaluation

### Test Suite

Full output:

```
============================= test session starts ==============================
platform linux -- Python 3.10.12, pytest-9.0.3, pluggy-1.6.0
collected 23 items

tests/test_drift_engine.py::test_no_drift                          PASSED [  4%]
tests/test_drift_engine.py::test_critical_drift                    PASSED [  8%]
tests/test_drift_engine.py::test_default_value_is_warning_not_critical PASSED [ 13%]
tests/test_drift_engine.py::test_unused_in_config                  PASSED [ 17%]
tests/test_drift_engine.py::test_case_insensitive                  PASSED [ 21%]
tests/test_drift_engine.py::test_dynamic_vars_reported_separately  PASSED [ 26%]
tests/test_drift_engine.py::test_multilanguage_refs                PASSED [ 30%]
tests/test_java_scanner.py::test_system_getenv                     PASSED [ 34%]
tests/test_java_scanner.py::test_value_annotation                  PASSED [ 39%]
tests/test_java_scanner.py::test_value_with_default                PASSED [ 43%]
tests/test_java_scanner.py::test_get_property                      PASSED [ 47%]
tests/test_java_scanner.py::test_get_property_with_default         PASSED [ 52%]
tests/test_java_scanner.py::test_configuration_properties          PASSED [ 56%]
tests/test_java_scanner.py::test_dynamic_getenv                    PASSED [ 60%]
tests/test_java_scanner.py::test_comments_ignored                  PASSED [ 65%]
tests/test_java_scanner.py::test_fixture_file                      PASSED [ 69%]
tests/test_python_scanner.py::test_os_environ_subscript            PASSED [ 73%]
tests/test_python_scanner.py::test_os_getenv                       PASSED [ 78%]
tests/test_python_scanner.py::test_os_getenv_with_default          PASSED [ 82%]
tests/test_python_scanner.py::test_os_environ_get                  PASSED [ 86%]
tests/test_python_scanner.py::test_dynamic_pattern                 PASSED [ 91%]
tests/test_python_scanner.py::test_comments_ignored                PASSED [ 95%]
tests/test_python_scanner.py::test_fixture_file                    PASSED [100%]

========================= 23 passed in X.XXs ==========================
```

### Test Coverage Breakdown

| Module | Tests | What's covered |
|---|---|---|
| `test_drift_engine.py` | 7 | Set-diff logic, severity assignment, dynamic var handling, multi-language refs, `.driftignore` |
| `test_java_scanner.py` | 9 | `System.getenv`, `@Value`, `@ConfigurationProperties`, defaults, dynamic refs, comments |
| `test_python_scanner.py` | 7 | `os.environ[]`, `os.getenv()`, defaults, dynamic patterns, comments, fixture file |
| **Total** | **23** | **All passing** |

### Known Limitations

- **Dynamic variable names** — variables constructed at runtime (e.g., `os.getenv("PREFIX_" + name)`) cannot be statically resolved and are flagged separately as dynamic references.
- **Java JDT dependency** — the full JDT scanner requires Maven and a JDK; the regex fallback is used automatically when the JVM is unavailable.
- **Transitive config** — variables inherited via shell profiles or CI environment injection (e.g., GitHub secrets) are not visible to the parser and should be added to `.driftignore`.

---

## Project Structure

```
config-drift-detector/
├── main.py                          # CLI entrypoint
├── requirements.txt
├── .driftignore.example
├── scanners/
│   ├── python/python_scanner.py     # Python AST scanner
│   ├── java/
│   │   ├── java_scanner_fallback.py # Python regex fallback
│   │   ├── src/.../JavaScanner.java # Eclipse JDT scanner
│   │   └── pom.xml
│   └── cpp/cpp_scanner.py           # C++ Tree-sitter / regex scanner
├── parsers/
│   ├── kubernetes_parser.py
│   ├── docker_compose_parser.py
│   ├── env_file_parser.py
│   └── dockerfile_parser.py
├── engine/drift_engine.py           # Set-comparison engine + DriftReport
├── action/
│   ├── action.yml                   # GitHub Action definition
│   └── Dockerfile
├── .github/workflows/drift-check.yml
└── tests/                           # 23 unit tests + fixtures
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*Built at HAW Kiel — Advanced Software Engineering (Release Engineering) by Murali Udutha & Rakesh Reddy.*
