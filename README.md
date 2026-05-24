# Config Drift Detector

> **Automated Prevention of Code-to-Config Drift in CI/CD Pipelines**  
> HAW Kiel — Advanced Software Engineering (Release Engineering)  
> Team project · 3 members · 450 hrs total

[![Drift Check](https://github.com/UduthaMurali/config-drift-detector/actions/workflows/drift-check.yml/badge.svg)](https://github.com/UduthaMurali/config-drift-detector/actions/workflows/drift-check.yml)


---

## What is Config Drift?

Config drift occurs when environment variables referenced in **source code** are not declared in **deployment configuration** files (Kubernetes, Docker Compose, `.env`, Dockerfiles). This leads to runtime crashes in production — often only discovered after deployment.

This tool performs **static multi-language analysis** to catch drift **before** code is merged.

---

## Features

- **Multi-language scanning**: Python (AST), Java (Eclipse JDT / regex fallback), C++ (Tree-sitter / regex fallback)
- **Config format support**: Kubernetes YAML, Docker Compose, `.env` files, Dockerfiles
- **Severity levels**: `critical` (no default) vs `warning` (has fallback default)
- **GitHub Action**: Blocks PRs when critical drift is detected
- **JSON output**: Machine-readable for CI pipelines
- **`.driftignore`**: Suppress known false positives (PATH, JAVA_HOME, etc.)

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
│   │   ├── java_scanner_fallback.py # Python regex fallback (no build needed)
│   │   ├── src/.../JavaScanner.java # Eclipse JDT scanner
│   │   └── pom.xml                  # Maven build
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

## Quick Start

```bash
pip install -r requirements.txt

# Basic scan
python main.py --source src/ --config k8s/,docker-compose.yml,.env

# Fail CI on critical drift
python main.py --source src/ --config k8s/ --fail-on-drift

# JSON output
python main.py --source src/ --config k8s/ --json

# Run tests
pip install pytest && pytest tests/ -v
```

---

## Demo: Detecting Drift

```bash
python main.py \
  --source tests/fixtures/python,tests/fixtures/java,tests/fixtures/cpp \
  --config tests/fixtures/configs/docker-compose.yml,tests/fixtures/configs/k8s-deployment.yaml \
  --languages python,java,cpp \
  --fail-on-drift
```

Output:

```
Config Drift Detector
==================================================
  Scanning Python...     Found 5 static + 0 dynamic references
  Scanning Java...       Found 5 static references
  Scanning C++...        Found 4 static references
  Parsing config files...  Found 8 declared variables in 2 path(s)

DRIFT DETECTED -- 4 missing variable(s)

Variable            Language  File                          Line  Severity
------------------------------------------------------------------------
SMTP_HOST           cpp       tests/fixtures/cpp/main.cpp   22    critical
STRIPE_SECRET       java      PaymentService.java            13    critical
STRIPE_WEBHOOK_URL  java      PaymentService.java            24    critical
PAYMENT_TIMEOUT     java      PaymentService.java            17    warning
```

Exit code `1` → CI fails, PR is blocked.

---

## GitHub Action Usage

```yaml
- name: Check for config drift
  uses: UduthaMurali/config-drift-detector@v1
  with:
    source-paths: 'src/'
    config-paths: 'k8s/, docker-compose.yml, .env'
    languages: 'java,python,cpp'
    fail-on-drift: 'true'
```

---

## .driftignore

```
# System variables — always present in any environment
PATH
JAVA_HOME
HOME
USER
```

---

## Comparison with Existing Tools

| Feature | This Tool | envgrd | DriftGuard |
|---|---|---|---|
| Python scanning (AST) | Yes | regex only | No |
| Java scanning | JDT + fallback | No | No |
| C++ scanning | Tree-sitter + regex | No | No |
| K8s / Docker Compose | Yes | Yes | Yes (GitOps) |
| GitHub Action + PR block | Yes | No | No |
| JSON output | Yes | No | No |
| .driftignore | Yes | No | No |

---

## Academic Context

- **Course**: Advanced Software Engineering — Release Engineering, HAW Kiel  
- **Team**: 3 members x 150 hours = 450 total project hours  
- **Novelty**: First tool combining multi-language AST analysis (Java + Python + C++) with GitHub Action PR blocking for config drift

---

## License

MIT
