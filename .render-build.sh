#!/usr/bin/env bash

# نصب Python 3.11
apt-get update
apt-get install -y python3.11 python3.11-venv python3.11-dev

# ساخت venv با 3.11
python3.11 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
