@echo off
title Genome Sentinel — Molecular Docking Workspace
echo ====================================================================
echo           Genome Sentinel — Molecular Docking Server
echo ====================================================================
echo.
echo Starting local web server on http://localhost:8000...
echo Keep this window open while using the web interface!
echo.
echo Opening dashboard in your default browser...
start "" "http://localhost:8000"
echo.
python server.py
pause
