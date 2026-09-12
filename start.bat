@echo off
title Nimora Bill System
color 1F
echo.
echo ============================================
echo    NIMORA - Bill System
echo    Your Tech Era Begins
echo ============================================
echo.
echo  Installing requirements...
pip install -r requirements.txt
echo.
echo  Starting server...
echo  Open: http://localhost:5000
echo  Login: admin / admin123
echo.
start http://localhost:5000
python app.py
pause