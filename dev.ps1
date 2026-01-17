 # Development helper script for Windows
 # Usage: .\dev.ps1 <command>
 
 param(
     [Parameter(Position=0)]
     [string]$Command = "help"
 )
 
 switch ($Command) {
     "install" {
         Write-Host "Installing dev dependencies..."
         pip install -r requirements-dev.txt
     }
     "lint" {
         Write-Host "Running flake8..."
         flake8 EOMTemplateTools.extension/lib/ tests/
     }
     "test" {
         Write-Host "Running pytest..."
         pytest tests/ -v
     }
     "test-cov" {
         Write-Host "Running pytest with coverage..."
         pytest tests/ --cov=EOMTemplateTools.extension/lib --cov-report=term-missing
     }
     "check" {
         Write-Host "Running lint and test..."
         flake8 EOMTemplateTools.extension/lib/ tests/
         if ($LASTEXITCODE -eq 0) {
             pytest tests/ -v
         }
     }
     "hooks" {
         Write-Host "Installing pre-commit hooks..."
         pre-commit install
     }
     "pre-commit" {
         Write-Host "Running pre-commit on all files..."
         pre-commit run --all-files
     }
     default {
         Write-Host "EOMTemplateTools Development Commands"
         Write-Host "======================================"
         Write-Host "  .\dev.ps1 install     - Install dev dependencies"
         Write-Host "  .\dev.ps1 lint        - Run flake8 linting"
         Write-Host "  .\dev.ps1 test        - Run pytest"
         Write-Host "  .\dev.ps1 test-cov    - Run pytest with coverage"
         Write-Host "  .\dev.ps1 check       - Run lint + test"
         Write-Host "  .\dev.ps1 hooks       - Install pre-commit hooks"
         Write-Host "  .\dev.ps1 pre-commit  - Run pre-commit on all files"
     }
 }
