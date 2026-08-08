#!/bin/bash
export PATH="/usr/bin:/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "/Users/nachoinmobiliario/leadqueue" || exit 1
/usr/bin/python3 ingest.py
