@echo off
cd /d %~dp0
echo === Installazione Juta Analisi Movimento ===
echo.
py -3.12 -m venv .venv 2>nul || python -m venv .venv
if not exist .venv\Scripts\activate.bat (
  echo ERRORE: Python non trovato. Installa Python 3.12 da python.org
  echo e spunta "Add python.exe to PATH" durante l'installazione.
  pause
  exit /b
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo === Autotest del motore ===
python prova_motore.py
echo.
echo Installazione finita. Ora fai doppio clic su avvia.bat
pause
