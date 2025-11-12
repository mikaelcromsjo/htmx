@echo off
REM Check if an argument was provided
IF "%~1"=="" (
    echo Please provide a commit message.
    echo Usage: git-push.bat "your commit message"
    exit /b 1
)

REM Git commands
git add --all
git commit -m "%~1"
git push origin migration