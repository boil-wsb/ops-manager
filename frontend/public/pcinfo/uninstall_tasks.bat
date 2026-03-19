@echo off
chcp 65001 >nul
title PC Info Collector - Uninstall Scheduled Tasks

echo ==========================================
echo PC Info Collector - Uninstall Tasks
echo ==========================================
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Administrator privileges required!
    echo.
    echo Please right-click and select 'Run as administrator'
    echo.
    pause
    exit /b 1
)

echo This will remove all PC Info Collector scheduled tasks.
echo.
set /p confirm="Are you sure you want to continue? (Y/N): "

if /i not "%confirm%"=="Y" (
    echo.
    echo Operation cancelled.
    pause
    exit /b 0
)

echo.
echo Removing scheduled tasks...
echo.

:: Remove Startup Task
echo [1/3] Removing PC_Info_Collector_Startup...
schtasks /delete /tn "PC_Info_Collector_Startup" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo      Successfully removed PC_Info_Collector_Startup
) else (
    echo      Task not found or already removed
)

:: Remove Hourly Task
echo [2/3] Removing PC_Info_Collector_Hourly...
schtasks /delete /tn "PC_Info_Collector_Hourly" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo      Successfully removed PC_Info_Collector_Hourly
) else (
    echo      Task not found or already removed
)

:: Remove Manual Task
echo [3/3] Removing PC_Info_Collector_RunNow...
schtasks /delete /tn "PC_Info_Collector_RunNow" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo      Successfully removed PC_Info_Collector_RunNow
) else (
    echo      Task not found or already removed
)

echo.
echo ==========================================
echo Uninstallation Complete!
echo ==========================================
echo.

:: Verify removal
echo Verifying task removal...
schtasks /query /fo TABLE /nh | findstr /I "PC_Info_Collector" >nul 2>&1
if %errorlevel% neq 0 (
    echo All PC Info Collector tasks have been successfully removed.
) else (
    echo Warning: Some tasks may still exist. Please check Task Scheduler.
)

echo.
pause
