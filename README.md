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

Add this file to your repo as `.github/workflows/drift-check.yml` — change `--source` and `--config` to match your project:

```yaml
name: Config Drift Check

on:
  push:
    branches:
      - main
      - 'feature/**'
      - 'update/**'
  pull_request:
    branches:
      - main

permissions:
  contents: read
  pull-requests: write

jobs:
  drift-check:
    name: Detect Config Drift
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Config Drift Detector
        run: |
          git clone https://github.com/UduthaMurali/config-drift-detector.git .drift-tool
          pip install -r .drift-tool/requirements.txt --quiet

      - name: Run Config Drift Check
        id: drift
        run: |
          set -o pipefail
          python .drift-tool/main.py \
            --source app/\          # ← change to your source folder
            --config config/ \      # ← change to your config folder
            --languages python \    # ← change to your language(s)
            --fail-on-drift \
            --json | tee drift-report.json
        continue-on-error: true

      - name: Post drift report as PR comment
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            let report;
            try {
              report = JSON.parse(fs.readFileSync('drift-report.json', 'utf8'));
            } catch (e) {
              report = { drift_level: 'ERROR', drift_score: 0, missing_in_config: [] };
            }
            const level = report.drift_level || 'UNKNOWN';
            const score = report.drift_score || 0;
            const items = report.missing_in_config || [];
            const emoji = { NONE: '✅', LOW: '⚠️', MEDIUM: '🟠', HIGH: '🔴' }[level] || '❓';
            let body = `## ${emoji} Config Drift Report\n\n`;
            body += `**Drift Level:** \`${level}\`  |  **Drift Score:** ${score}\n\n`;
            if (items.length === 0) {
              body += `All environment variables referenced in code are declared in deployment config.\n`;
              body += `No drift detected — safe to merge! ✅\n`;
            } else {
              const critical = items.filter(i => i.severity === 'critical');
              const warnings = items.filter(i => i.severity === 'warning');
              if (critical.length > 0) {
                body += `### 🔴 Critical — ${critical.length} variable(s) have NO default value\n`;
                body += `> App will **crash or behave incorrectly** if deployed without these.\n\n`;
                body += `| Variable | File | Line | Method |\n|---|---|---|---|\n`;
                for (const item of critical) {
                  body += `| \`${item.variable}\` | \`${item.file}\` | ${item.line} | ${item.method} |\n`;
                }
                body += `\n`;
              }
              if (warnings.length > 0) {
                body += `### ⚠️ Warning — ${warnings.length} variable(s) have a default but are not declared in config\n\n`;
                body += `| Variable | File | Line | Method |\n|---|---|---|---|\n`;
                for (const item of warnings) {
                  body += `| \`${item.variable}\` | \`${item.file}\` | ${item.line} | ${item.method} |\n`;
                }
                body += `\n`;
              }
              body += `---\n**Fix:** Add the missing variables to your deployment config before merging.\n`;
            }
            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });

      - name: Block PR on critical drift
        if: steps.drift.outcome == 'failure'
        run: |
          echo "❌ CRITICAL CONFIG DRIFT DETECTED"
          echo "Add missing variables to deployment config before merging."
          exit 1
```

## Drift Score

Each missing variable is scored based on severity:

| Severity | Condition | Points |
|---|---|---|
| 🔴 Critical | No default value — app will crash | 3 pts |
| ⚠️ Warning | Has default value — silent failure | 1 pt |

**Drift levels:**

| Level | Score | Meaning |
|---|---|---|
| NONE | 0 | All vars declared — safe to deploy |
| LOW | 1–3 | Minor warnings only |
| MEDIUM | 4–9 | Mix of critical and warnings |
| HIGH | 10+ | Multiple critical vars missing |

**Example:**
- 4 critical + 1 warning = (4 × 3) + (1 × 1) = **13 → MEDIUM**
- 5 critical + 4 warnings = (5 × 3) + (4 × 1) = **19 → HIGH**

## CLI Usage

```bash
pip install -r requirements.txt
python main.py --source src/ --config k8s/,docker-compose.yml --languages python,java,go,js,rust,spring,pydantic --json
```

## Authors

Murali Udutha - Rakesh Reddy Kalamakuntla
HAW Kiel - Advanced Software Engineering - 2026
