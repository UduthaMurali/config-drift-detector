# Config Drift Detector

> **Detect code-to-config drift before it reaches production.**

A cross-artifact static analysis tool and GitHub Action that scans source code for environment variable references, compares them against deployment configuration (Kubernetes YAML, Docker Compose, `.env`), and blocks the Pull Request if variables are missing.

## Comparison with Existing Tools

| Feature | **Config Drift Detector** | envgrd | SonarQube | KubeLinter |
|---|---|---|---|---|
| Python scanning (AST) | Yes | Yes (Tree-Sitter AST) | Yes | No |
| Java scanning | JDT + regex fallback | Yes (Tree-Sitter AST) | Yes | No |
| Go scanning | Yes | Yes (Tree-Sitter AST) | No | No |
| JavaScript / TypeScript | Yes | Yes (Tree-Sitter AST) | Yes | No |
| Rust scanning | Yes | Yes (Tree-Sitter AST) | No | No |
| C / C++ scanning | Yes (regex + wrappers) | Yes (Tree-Sitter AST) | Yes | No |
| Spring Boot adapter (${VAR} in properties/YAML) | Yes | No | No | No |
| Pydantic BaseSettings adapter | Yes | No | No | No |
| SECTION__KEY env-injection (Gitea, ASP.NET Core) | Yes | No | No | No |
| Reads Kubernetes YAML | Yes | No (.env only) | No | Yes |
| Reads Docker Compose | Yes | No (.env only) | No | No |
| Cross-artifact drift detection | Yes | No | No | No |
| GitHub Action + PR block | Yes | No | No | No |
| JSON output | Yes | No | Yes | Yes |
| .driftignore support | Yes | No | No | No |
| Precision / Recall (seeded eval) | 100% / 100% | - | 0% | 0% |

> **Note on envgrd:** [envgrd](https://github.com/njenia/envgrd) uses Tree-Sitter AST across six languages - a solid approach. Its key limitation: validates against `.env` files only (no Kubernetes/Compose support), no CI/CD integration, and no framework adapters for Spring Boot or Pydantic. On our K8s/Compose drift benchmark it scores 0%.

## Supported Languages and Adapters

### Language Scanners

| Language | Method | Patterns |
|---|---|---|
| Python | AST (ast module) | os.getenv(), os.environ.get(), os.environ[] |
| Java | Eclipse JDT JAR + regex fallback | System.getenv(), environment.getProperty() |
| Go | Regex | os.Getenv(), os.LookupEnv(), os.ExpandEnv() |
| JavaScript / TypeScript | Regex | process.env.KEY, import.meta.env.KEY (Vite) |
| Rust | Regex | env::var(), env!(), option_env!(), env::vars() |
| C / C++ | Regex | getenv(), std::getenv(), curl_getenv() and wrappers |

### Framework Adapters

| Adapter | Enable with | What it detects |
|---|---|---|
| Spring Boot | --languages spring | ${VAR:default} in application*.properties/.yml, @Value annotations |
| Pydantic BaseSettings | --languages pydantic | BaseSettings class fields, env_prefix, Field(env=...) aliases |
| Env-injection | --languages env_inject | GITEA__section__KEY, ASPNETCORE__Key, Database__ConnStr patterns |

## Evaluation Results

Seeded evaluation (10 drift cases per repo):

| Repository | Language | LOC | Precision | Recall | Avg Time |
|---|---|---|---|---|---|
| microblog (Grinberg) | Python | 1,843 | 100.0% | 100.0% | 0.07 s |
| Netflix Conductor | Java | 60,911 | 100.0% | 100.0% | 0.16 s |

Cross-language validation on real open-source projects:

| Project | Language | Static Refs | Drift Found |
|---|---|---|---|
| Outline | TypeScript | 50 | Yes |
| Gitea | Go | 46 | Yes |
| Alacritty | Rust | 19 | Yes |
| curl | C/C++ | 81 | Yes |
| Spring PetClinic | Java/Spring (adapter) | 9 | Yes - 6 cases |
| FastAPI template | Python/Pydantic (adapter) | 25 | Yes - 5 cases |

## Quick Start

```yaml
# .github/workflows/drift-check.yml
name: Config Drift Check
on: [pull_request]
jobs:
  drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: UduthaMurali/config-drift-detector@v1
        with:
          source-paths: 'src/'
          config-paths: 'k8s/,docker-compose.yml,.env'
          languages: 'python,java,go,js,rust,spring,pydantic'
```

## CLI Usage

```bash
pip install -r requirements.txt
python main.py --source src/ --config k8s/,docker-compose.yml --languages python,java,go,js,rust,spring,pydantic --json
```

## Authors

Murali Udutha - Rakesh Reddy Kalamakuntla
HAW Kiel - Advanced Software Engineering - 2026
