@echo off
setlocal enabledelayedexpansion

echo ========================================
echo ASD Manufacturing Dashboard Service Installer
echo ========================================
echo.

:: Check admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Run this script as Administrator
    pause
    exit /b 1
)
echo [OK] Running as Administrator

:: Paths
set "INSTALL_DIR=C:\Users\admin\PycharmProjects\odoo18"
set "ODOO_BIN=%INSTALL_DIR%\odoo\odoo-bin"
set "ODOO_CONF=%INSTALL_DIR%\conf\autoliv.conf"
set "ODOO_LOG=%INSTALL_DIR%\odoo.log"
set "PYTHON_EXE=%INSTALL_DIR%\.venv\Scripts\python.exe"
set "NSSM_DIR=C:\nssm"
set "SERVICE_NAME=ASD Manufacturing Dashboard"

echo.
echo [CHECK] Verifying Odoo installation...
if not exist "%ODOO_BIN%" (
    echo [ERROR] Missing odoo-bin at %ODOO_BIN%
    pause
    exit /b 1
)
if not exist "%ODOO_CONF%" (
    echo [ERROR] Missing config at %ODOO_CONF%
    pause
    exit /b 1
)
echo [OK] Odoo paths verified

echo.
echo [CHECK] Verifying Python...
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found at %PYTHON_EXE%
    pause
    exit /b 1
)
echo [OK] Python found

echo.
echo [CHECK] Checking NSSM...
if not exist "%NSSM_DIR%\win64\nssm.exe" (
    echo [ERROR] NSSM not installed at %NSSM_DIR%\win64\nssm.exe
    pause
    exit /b 1
)
set "NSSM_EXE=%NSSM_DIR%\win64\nssm.exe"
echo [OK] NSSM found

echo.
echo [CHECK] Checking for existing service...
sc query "%SERVICE_NAME%" >nul 2>&1
if %errorLevel% equ 0 (
    echo [INFO] Removing existing service...
    net stop "%SERVICE_NAME%" >nul 2>&1
    "%NSSM_EXE%" remove "%SERVICE_NAME%" confirm
    timeout /t 1 >nul
)

echo.
echo [INFO] Creating service...

"%NSSM_EXE%" install "%SERVICE_NAME%" "%PYTHON_EXE%" "%ODOO_BIN%" -c "%ODOO_CONF%" --logfile "%ODOO_LOG%" --log-level info

if %errorLevel% neq 0 (
    echo [ERROR] Service creation failed
    pause
    exit /b 1
)

echo [INFO] Configuring service...

"%NSSM_EXE%" set "%SERVICE_NAME%" AppDirectory "%INSTALL_DIR%"
"%NSSM_EXE%" set "%SERVICE_NAME%" Start SERVICE_AUTO_START
"%NSSM_EXE%" set "%SERVICE_NAME%" AppExit Default Restart
"%NSSM_EXE%" set "%SERVICE_NAME%" AppRestartDelay 5000
"%NSSM_EXE%" set "%SERVICE_NAME%" ObjectName LocalSystem

"%NSSM_EXE%" set "%SERVICE_NAME%" AppStdout "%INSTALL_DIR%\service_stdout.log"
"%NSSM_EXE%" set "%SERVICE_NAME%" AppStderr "%INSTALL_DIR%\service_stderr.log"

echo [OK] Service configured successfully

echo.
choice /C YN /M "Start service now?"
if %errorLevel% equ 1 (
    echo [INFO] Starting service...
    net start "%SERVICE_NAME%"
)

echo.
echo [DONE] Installation Complete!
pause
