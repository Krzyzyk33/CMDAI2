@echo off
set PYTHONPATH=%~dp0;%PYTHONPATH%

if /I "%~1"=="CODE" (
    rem Przesuń argumenty jeśli wpisano CMDAI CODE <args>
    shift
    python -m src.main %1 %2 %3 %4 %5 %6 %7 %8 %9
) else if /I "%~1"=="code" (
    shift
    python -m src.main %1 %2 %3 %4 %5 %6 %7 %8 %9
) else (
    python -m src.main %*
)
