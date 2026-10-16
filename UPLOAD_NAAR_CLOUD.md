# ==============================================================================
# STAY4OS - CLOUD UPLOAD SCRIPT
# Voer dit uit na authenticatie
# ==============================================================================

## OPTIE 1: Google Drive (aanbevolen - makkelijkst)
# Download en installeer: https://www.google.com/drive/download/
# Of gebruik rclone: https://rclone.org/drive/

# Met rclone (na installatie en config):
# rclone config
#   -> New remote -> drive -> Google Drive
#   -> Volg instructies voor OAuth

# Daarna:
# rclone copy K:\stay4\STAY4OS_RELEASE_v1.0\01_FACTORY_ZIP gdrive:Stay4OS/
# rclone copy K:\stay4\STAY4OS_RELEASE_v1.0\03_BACKUPS gdrive:Stay4OS/

## OPTIE 2: Google Cloud Storage (meer controle)
# Download: https://cloud.google.com/sdk/docs/install
# gcloud auth login
# gcloud config set project JOUW_PROJECT_ID
# gsutil mb gs://stay4os-releases/
# gsutil cp K:\stay4\STAY4OS_RELEASE_v1.0\01_FACTORY_ZIP\stay4os_tegu-bp41_factory.zip gs://stay4os-releases/

## OPTIE 3: GitHub Release (max 2GB - past NIET voor 3GB zip)
# Ga naar: https://github.com/hetnieuwebeginbv-glitch/stay4s-platform/releases
# -> Draft new release -> Upload zip (maar 3GB > 2GB limiet, dus NIET mogelijk)

## OPTIE 4: WeTransfer / Filemail (tijdelijk, 30 dagen)
# Ga naar: https://wetransfer.com
# Upload: stay4os_tegu-bp41_factory.zip
# Deel link

# ==============================================================================
# HUIDIGE STATUS
# ==============================================================================

Write-Host "=== STAY4OS BESTANDEN ===" -ForegroundColor Green
Write-Host ""

Write-Host "LOKAAL (K:\stay4\STAY4OS_RELEASE_v1.0\):" -ForegroundColor Yellow
Get-ChildItem K:\stay4\STAY4OS_RELEASE_v1.0 -Recurse | 
    Select-Object @{N='Locatie';E={$_.FullName.Replace('K:\stay4\STAY4OS_RELEASE_v1.0\','')}}, 
                  @{N='Grootte';E={if($_.Length -gt 1MB){"$([math]::Round($_.Length/1MB,1)) MB"}else{"$([math]::Round($_.Length/1KB,1)) KB"}}} |
    Format-Table

Write-Host ""
Write-Host "GITHUB (https://github.com/hetnieuwebeginbv-glitch/stay4s-platform):" -ForegroundColor Yellow
Write-Host "- README.md"
Write-Host "- 02_RAPPORTEN/ (alle .md bestanden)"
Write-Host "- 04_LOGS/ (build logs)"
Write-Host "- 05_FLASH/ (instructies)"
Write-Host "- .gitignore, GROTE_BESTANDEN.md"
Write-Host ""
Write-Host "NIET op GitHub (te groot):" -ForegroundColor Red
Write-Host "- 01_FACTORY_ZIP/stay4os_tegu-bp41_factory.zip (3.0 GB)"
Write-Host "- 03_BACKUPS/stay4os_tegu_device_config.tar.gz (54 MB)"
