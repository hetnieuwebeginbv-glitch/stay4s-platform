#!/bin/bash
# Stay4S Scam-Check deploy — draai op de Pi (of via ssh ... bash -s)
# Vereist: bestanden al gescpied naar /tmp/scam_deploy/ (scam_api.py, scam.html, unit, model/)
set -x
sudo mkdir -p /opt/stay4s/scam /opt/stay4s/models/scam-v2
sudo cp /tmp/scam_deploy/scam_api.py /tmp/scam_deploy/scam.html /opt/stay4s/scam/
sudo cp -r /tmp/scam_deploy/model/. /opt/stay4s/models/scam-v2/
sudo chown -R Miesdevries:Miesdevries /opt/stay4s/scam /opt/stay4s/models/scam-v2
if [ ! -d /opt/stay4s/scam/venv ]; then
  python3 -m venv /opt/stay4s/scam/venv
  /opt/stay4s/scam/venv/bin/pip install --upgrade pip
  /opt/stay4s/scam/venv/bin/pip install fastapi "uvicorn[standard]" pydantic \
    transformers==4.46.3 --extra-index-url https://download.pytorch.org/whl/cpu torch
fi
sudo cp /tmp/scam_deploy/stay4s-scam-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now stay4s-scam-api
sleep 8
curl -s http://localhost:8100/health
curl -s -X POST http://localhost:8100/check -H "Content-Type: application/json" \
  -d '{"text":"Hoi mam mijn telefoon is kapot, maak even 850 euro over naar deze rekening, het moet vandaag"}'
echo "SCAM_DEPLOY_KLAAR"
