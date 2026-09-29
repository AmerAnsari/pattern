: << 'CMDBLOCK'
@echo off
REM Polyglot wrapper so one file works as both a Windows batch script and a
REM POSIX shell script. On Windows cmd.exe runs the batch half below, which
REM locates bash and hands off. On Unix the leading ":" is a no-op and the
REM shell falls through to the last two lines.
REM
REM The hook scripts are deliberately extensionless: Claude Code's Windows
REM detection prepends "bash" to any command containing ".sh", which would
REM double-invoke them.
REM
REM Technique borrowed from the Superpowers plugin (MIT, github.com/obra/superpowers).
REM
REM Usage: run-hook.cmd <script-name> [args...]

if "%~1"=="" (
    echo run-hook.cmd: missing script name >&2
    exit /b 1
)

set "HOOK_DIR=%~dp0"

if exist "C:\Program Files\Git\bin\bash.exe" (
    "C:\Program Files\Git\bin\bash.exe" "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)
if exist "C:\Program Files (x86)\Git\bin\bash.exe" (
    "C:\Program Files (x86)\Git\bin\bash.exe" "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

where bash >nul 2>nul
if %ERRORLEVEL% equ 0 (
    bash "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

REM No bash available. Exit quietly: losing pattern's hooks should never break
REM the user's session.
exit /b 0
CMDBLOCK

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME="$1"
shift
exec bash "${SCRIPT_DIR}/${SCRIPT_NAME}" "$@"
