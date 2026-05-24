# Config Drift Detector — GitHub Setup Script
# Run this in PowerShell from your C:\Users\mural\Desktop\ASE folder
# Usage: .\git-setup.ps1 -RepoUrl https://github.com/UduthaMurali/config-drift-detector.git

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoUrl
)

$ErrorActionPreference = "Stop"
$ProjectDir = $PSScriptRoot

Write-Host "`nConfig Drift Detector — GitHub Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# Step 1: Clean up any corrupt .git from sandbox
if (Test-Path "$ProjectDir\.git") {
    Write-Host "`n[1/5] Removing old/corrupt .git folder..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "$ProjectDir\.git"
}

# Step 2: Initialize fresh repo
Write-Host "[2/5] Initializing git repository..." -ForegroundColor Blue
Set-Location $ProjectDir
git init -b main

# Step 3: Configure user (already set globally if you have git configured)
git config user.email "uduthamuraliyadav@gmail.com"
git config user.name "Murali"

# Step 4: Stage everything
Write-Host "[3/5] Staging all files..." -ForegroundColor Blue
git add .
git status --short

# Step 5: Initial commit
Write-Host "[4/5] Creating initial commit..." -ForegroundColor Blue
git commit -m "feat: initial release — Config Drift Detector v1.0

Multi-language static analysis tool for detecting code-to-config drift.

Features:
- Python AST scanner (os.environ, os.getenv, dotenv, Django)
- Java Eclipse JDT scanner + Python regex fallback
- C++ Tree-sitter + regex scanner
- Parsers: Kubernetes, Docker Compose, .env, Dockerfile
- Drift detection engine with severity levels (critical/warning)
- GitHub Action for PR blocking
- JSON output for CI pipelines
- .driftignore support
- 23 unit tests (all passing)

HAW Kiel — Advanced Software Engineering, Release Engineering
Team project: 3 members x 150 hrs = 450 total hours"

# Step 6: Push to GitHub
Write-Host "[5/5] Pushing to GitHub..." -ForegroundColor Blue
git remote add origin $RepoUrl
git push -u origin main

Write-Host "`nDone! Your project is live at:" -ForegroundColor Green
Write-Host "  $($RepoUrl -replace '\.git$', '')" -ForegroundColor Green
Write-Host "`nGitHub Actions will trigger automatically on the next pull request." -ForegroundColor Green
