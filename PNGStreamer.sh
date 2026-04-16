#!/bin/bash

if [ ! -d ".venv" ]; then
    echo "venv not found, creating..."
    python3 -m venv .venv
    echo "venv created!"
else
    echo "venv found, continue..."
fi

REQUIRED_VER=3.13
CURRENT_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

if [ "$(printf '%s\n' "$REQUIRED_VER" "$CURRENT_VER" | sort -V | head -n1)" = "$REQUIRED_VER" ]; then
    echo "Version $CURRENT_VER found"
else
    echo "Version $CURRENT_VER to old, needed >= $REQUIRED_VER"
    exit
fi

echo "Programm started!"

.venv/bin/python3 -m pip install --upgrade pip
.venv/bin/pip3 install -r app/requirements.txt
.venv/bin/python3 main.py