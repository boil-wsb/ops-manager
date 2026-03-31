@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title PC Info Collector v5.0.0

echo ==========================================
echo PC Info Collector v5.0.0
echo ==========================================
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Not running as Administrator.
    echo Some features may be limited.
    echo.
    echo To run as Administrator, right-click and select 'Run as administrator'
    echo.
    timeout /t 3 /nobreak >nul
)

:: Get script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: Check if Conf.json exists
if not exist "Conf.json" (
    echo [ERROR] Conf.json not found!
    echo Please ensure the configuration file exists.
    pause
    exit /b 1
)

:: Check if VBS script exists
if not exist "PC_5.0.0_modular.vbs" (
    echo [ERROR] PC_5.0.0_modular.vbs not found!
    echo Please ensure the script file exists.
    pause
    exit /b 1
)

:: Menu
echo Please select an option:
echo   [1] Run PC Info Collector now
echo   [2] Install to C:\Program Files\PCInfoCollector ^(requires Admin^)
echo   [3] Uninstall scheduled tasks ^(requires Admin^)
echo   [4] Check task status
echo   [5] View current configuration
echo   [6] Check for updates
echo   [0] Exit
echo.
set /p choice="Enter your choice (0-6): "

if "%choice%"=="1" goto RUN_NOW
if "%choice%"=="2" goto INSTALL_TO_PROGRAMFILES
if "%choice%"=="3" goto UNINSTALL_TASKS
if "%choice%"=="4" goto CHECK_STATUS
if "%choice%"=="5" goto VIEW_CONFIG
if "%choice%"=="6" goto CHECK_UPDATE
if "%choice%"=="0" goto EXIT

echo Invalid choice!
timeout /t 2 /nobreak >nul
goto EXIT

:RUN_NOW
echo.
echo Starting PC Info Collector...
echo.
cscript //NoLogo "PC_5.0.0_modular.vbs"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Script execution failed!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Execution completed successfully!
echo ==========================================
timeout /t 3 /nobreak >nul
goto EXIT

:INSTALL_TO_PROGRAMFILES
echo.
echo Installing to C:\Program Files\PCInfoCollector...

:: Check if running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Administrator privileges required!
    echo Please right-click and select 'Run as administrator'
    echo.
    pause
    goto EXIT
)

:: Check if CustInfo.id is still the default value "boil"
powershell -Command "try { $config = Get-Content 'Conf.json' -Raw | ConvertFrom-Json; if ($config.CustInfo.id -eq 'boil') { exit 1 } else { exit 0 } } catch { exit 1 }"
if %errorlevel% equ 1 (
    echo.
    echo [WARNING] CustInfo.id is still set to the default value 'boil'.
    echo Please enter a new customer ID to continue.
    echo.
    set /p newCustId="Enter customer ID: "

    if "!newCustId!"=="" (
        echo [ERROR] Customer ID cannot be empty!
        pause
        goto EXIT
    )

    :: Update Conf.json with the new customer ID
    powershell -NoProfile -Command "$config = Get-Content 'Conf.json' -Raw | ConvertFrom-Json; $config.CustInfo.id = '!newCustId!'; $json = $config | ConvertTo-Json -Depth 10; [System.IO.File]::WriteAllText('Conf.json', $json, [System.Text.Encoding]::UTF8)"
    set updateResult=!errorlevel!

    if !updateResult! neq 0 (
        echo [ERROR] Failed to update configuration file!
        pause
        goto EXIT
    )

    echo Customer ID has been updated to: !newCustId!
    echo.
)

set "InstallPath=%ProgramFiles%\PCInfoCollector"

:: Clean up old installation
if exist "%InstallPath%" (
    echo Cleaning up old installation...
    schtasks /delete /tn "PCInfoCollector_Startup" /f >nul 2>&1
    schtasks /delete /tn "PCInfoCollector_Hourly" /f >nul 2>&1
    schtasks /delete /tn "PC_Info_Collector_Startup" /f >nul 2>&1
    schtasks /delete /tn "PC_Info_Collector_Hourly" /f >nul 2>&1
    rmdir /s /q "%InstallPath%" >nul 2>&1
)

echo Creating installation directory...
mkdir "%InstallPath%" >nul 2>&1

echo Copying files...
copy /y "%SCRIPT_DIR%\PC_5.0.0_modular.vbs" "%InstallPath%\" >nul
copy /y "%SCRIPT_DIR%\Conf.json" "%InstallPath%\" >nul
copy /y "%SCRIPT_DIR%\PC_Info_Collector.bat" "%InstallPath%\" >nul
if exist "%SCRIPT_DIR%\Update_Manager.vbs" (
    copy /y "%SCRIPT_DIR%\Update_Manager.vbs" "%InstallPath%\" >nul
)

if not exist "%InstallPath%\PC_5.0.0_modular.vbs" (
    echo [ERROR] Failed to copy files!
    pause
    goto EXIT
)

echo Done

:: Read schedule interval from Conf.json
set "IntervalMinutes=10"
powershell -NoProfile -Command "try { $config = Get-Content 'Conf.json' -Raw | ConvertFrom-Json; if ($config.Schedule.IntervalMinutes) { exit 0 } else { exit 1 } } catch { exit 1 }"
if %errorlevel% equ 0 (
    for /f "delims=" %%i in ('powershell -NoProfile -Command "(Get-Content 'Conf.json' -Raw | ConvertFrom-Json).Schedule.IntervalMinutes"') do set "IntervalMinutes=%%i"
)

:: Determine schedule type based on interval
set "ScheduleType=MINUTE"
set "ScheduleModifier="
if %IntervalMinutes% geq 60 (
    set /a "Hours=%IntervalMinutes% / 60"
    if %IntervalMinutes% equ 60 (
        set "ScheduleType=HOURLY"
        set "ScheduleModifier="
    ) else (
        set "ScheduleType=HOURLY"
        set "ScheduleModifier=/mo %Hours%"
    )
) else (
    set "ScheduleModifier=/mo %IntervalMinutes%"
)

echo Schedule interval: %IntervalMinutes% minutes ^(%ScheduleType% %ScheduleModifier%^)

echo Creating scheduled tasks...

set "VbsPath=%InstallPath%\PC_5.0.0_modular.vbs"

:: Delete old tasks
schtasks /delete /tn "PCInfoCollector_Startup" /f >nul 2>&1
schtasks /delete /tn "PCInfoCollector_Hourly" /f >nul 2>&1
schtasks /delete /tn "PCInfoCollector_Scheduled" /f >nul 2>&1
schtasks /delete /tn "PC_Info_Collector_Startup" /f >nul 2>&1
schtasks /delete /tn "PC_Info_Collector_Hourly" /f >nul 2>&1

:: Create startup task - use wscript.exe to run hidden
schtasks /create /tn "PCInfoCollector_Startup" /tr "wscript.exe //B \"!VbsPath!\"" /sc ONSTART /rl HIGHEST /f >nul 2>&1
echo   Created: PCInfoCollector_Startup ^(Run at startup^)

:: Create scheduled task with configurable interval
schtasks /create /tn "PCInfoCollector_Scheduled" /tr "wscript.exe //B \"!VbsPath!\"" /sc %ScheduleType% %ScheduleModifier% /rl HIGHEST /f >nul 2>&1
echo   Created: PCInfoCollector_Scheduled ^(Run every %IntervalMinutes% minutes^)

:: Create uninstall script
(
echo @echo off
echo title PC Info Collector - Uninstall
echo color 0C
echo echo ========================================
echo echo PC Info Collector - Uninstall
echo echo ========================================
echo echo.
echo schtasks /delete /tn "PCInfoCollector_Startup" /f ^>nul 2^>^&1
echo schtasks /delete /tn "PCInfoCollector_Hourly" /f ^>nul 2^>^&1
echo rmdir /s /q "%%ProgramFiles%%\PCInfoCollector" ^>nul 2^>^&1
echo echo Uninstall complete
echo pause
) > "%InstallPath%\Uninstall.bat"

echo.
echo ==========================================
echo Installation complete!
echo ==========================================
echo.
echo Features:
echo   1. Run at startup - Collect info when system starts
echo   2. Run on schedule - Collect and report info at configured interval
echo.
echo Install path: %InstallPath%
echo Config file: %InstallPath%\Conf.json
echo Uninstall: %InstallPath%\Uninstall.bat
echo.
echo Current schedule interval: %IntervalMinutes% minutes
echo.
echo Run installed version: "%InstallPath%\PC_Info_Collector.bat"
echo.

pause
goto EXIT

:RUN_INSTALLED
echo.
set "InstallPath=%ProgramFiles%\PCInfoCollector"

if not exist "%InstallPath%\PC_5.0.0_modular.vbs" (
    echo [ERROR] Installed version not found!
    echo Please run option 2 to install first.
    pause
    goto EXIT
)

echo Running installed version from: %InstallPath%
echo.
cscript //NoLogo "%InstallPath%\PC_5.0.0_modular.vbs"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Script execution failed!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Execution completed successfully!
echo ==========================================
timeout /t 3 /nobreak >nul
goto EXIT

:UNINSTALL_TASKS
echo.
echo Uninstalling scheduled tasks...

:: Check if running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Administrator privileges required!
    echo Please right-click and select 'Run as administrator'
    echo.
    pause
    goto EXIT
)

:: Uninstall from Program Files
set "InstallPath=%ProgramFiles%\PCInfoCollector"
if exist "%InstallPath%" (
    echo Uninstalling from %InstallPath%...
    schtasks /delete /tn "PCInfoCollector_Startup" /f >nul 2>&1
    schtasks /delete /tn "PCInfoCollector_Scheduled" /f >nul 2>&1
    schtasks /delete /tn "PCInfoCollector_Hourly" /f >nul 2>&1
    rmdir /s /q "%InstallPath%" >nul 2>&1
    echo Done
)

:: Also uninstall from script directory
schtasks /delete /tn "PC_Info_Collector_Startup" /f >nul 2>&1
schtasks /delete /tn "PC_Info_Collector_Hourly" /f >nul 2>&1
echo Uninstall complete!

pause
goto EXIT

:CHECK_STATUS
echo.
echo Checking task status...
echo.

echo Installed version tasks ^(C:\Program Files\PCInfoCollector^):
schtasks /query /tn "PCInfoCollector_Startup" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] PCInfoCollector_Startup
) else (
    echo   [--] PCInfoCollector_Startup ^(^not configured^)
)

schtasks /query /tn "PCInfoCollector_Hourly" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] PCInfoCollector_Hourly
) else (
    echo   [--] PCInfoCollector_Hourly ^(^not configured^)
)

echo.
echo Local version tasks ^(%SCRIPT_DIR%^):
schtasks /query /tn "PC_Info_Collector_Startup" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] PC_Info_Collector_Startup
) else (
    echo   [--] PC_Info_Collector_Startup ^(^not configured^)
)

schtasks /query /tn "PC_Info_Collector_Hourly" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] PC_Info_Collector_Hourly
) else (
    echo   [--] PC_Info_Collector_Hourly ^(^not configured^)
)

echo.
pause
goto EXIT

:VIEW_CONFIG
echo.
echo ==========================================
echo Current Configuration
echo ==========================================
echo.
powershell -Command "try { $config = Get-Content 'Conf.json' -Raw | ConvertFrom-Json; Write-Host 'Customer ID: ' -NoNewline; Write-Host $config.CustInfo.id -ForegroundColor Green; Write-Host ''; Write-Host 'Schedule Interval: ' -NoNewline; Write-Host ($config.Schedule.IntervalMinutes.ToString() + ' minutes') -ForegroundColor Green; Write-Host ''; Write-Host 'Http Report: ' -NoNewline; if ($config.HttpReport.Enabled) { Write-Host 'Enabled' -ForegroundColor Green } else { Write-Host 'Disabled' -ForegroundColor Red }; Write-Host '  Endpoint: '; Write-Host $config.HttpReport.Endpoint; Write-Host '  Format: '; Write-Host $config.HttpReport.Format; Write-Host ''; Write-Host 'Update Server: ' -NoNewline; if ($config.UpdateServer.Host) { Write-Host ($config.UpdateServer.Host + ':' + $config.UpdateServer.Port) -ForegroundColor Green } else { Write-Host 'Not configured' -ForegroundColor Yellow }; Write-Host ''; Write-Host 'Modules:'; $config.Modules.PSObject.Properties | ForEach-Object { Write-Host ('  ' + $_.Name + ': ') -NoNewline; if ($_.Value) { Write-Host 'Enabled' -ForegroundColor Green } else { Write-Host 'Disabled' -ForegroundColor Red } }; Write-Host ''; Write-Host 'Data Retention: ' -NoNewline; if ($config.DataRetention.Enabled) { Write-Host ('Enabled (' + $config.DataRetention.KeepDays + ' days)') -ForegroundColor Green } else { Write-Host 'Disabled' -ForegroundColor Red } } catch { Write-Host 'Failed to read configuration file.' -ForegroundColor Red }"
echo.
pause
goto EXIT

:CHECK_UPDATE
echo.
echo ==========================================
echo Check for Updates
echo ==========================================
echo.

:: Check if Update_Manager.vbs exists
if not exist "Update_Manager.vbs" (
    echo [ERROR] Update_Manager.vbs not found!
    echo Please ensure the update manager script exists.
    pause
    goto EXIT
)

echo Starting update manager...
echo.
cscript //NoLogo "Update_Manager.vbs"

echo.
pause
goto EXIT

:EXIT
echo.
echo Goodbye!
timeout /t 1 /nobreak >nul
