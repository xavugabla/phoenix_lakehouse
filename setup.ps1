# Lakehouse Core Setup Script
# Creates virtual environment and installs dependencies

Write-Host "Setting up Lakehouse Core development environment..." -ForegroundColor Green

# Check Python version
$pythonVersion = python --version 2>&1
Write-Host "Python version: $pythonVersion" -ForegroundColor Cyan

# Create virtual environment
if (Test-Path ".venv") {
    Write-Host "Virtual environment already exists. Removing old one..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force .venv
}

Write-Host "Creating virtual environment..." -ForegroundColor Cyan
python -m venv .venv

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Install package in editable mode
Write-Host "Installing lakehouse-core package..." -ForegroundColor Cyan
pip install -e .

# Install development dependencies (optional)
$installDev = Read-Host "Install development dependencies? (y/n)"
if ($installDev -eq "y" -or $installDev -eq "Y") {
    Write-Host "Installing development dependencies..." -ForegroundColor Cyan
    pip install -e ".[dev]"
}

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "To activate the virtual environment in the future, run:" -ForegroundColor Yellow
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "`nTo verify installation:" -ForegroundColor Yellow
Write-Host "  python -c 'from lakehouse_core import get_lakehouse_config; print(get_lakehouse_config())'" -ForegroundColor White

