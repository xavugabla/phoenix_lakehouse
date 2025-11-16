# Simplified deployment script for the CENACE data pipeline.
#
# This script uses the declarative `prefect.yaml` file to build, push,
# and deploy all flows in a single, unified command.
#
# REQUIREMENTS:
#   - Prefect CLI installed and configured.
#   - Docker running.
#   - Logged into a Docker registry (if pushing).
#
# USAGE:
#   .\deploy.ps1
#

Write-Host "Deploying all flows from prefect.yaml..." -ForegroundColor Green

prefect deploy

Write-Host "Deployment process initiated." -ForegroundColor Green
Write-Host "Check your Prefect Cloud dashboard for deployment status." -ForegroundColor Yellow
