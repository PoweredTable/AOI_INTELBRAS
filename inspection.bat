@ECHO OFF
SETLOCAL EnableExtensions

set EXE=pythonw.exe

FOR /F %%x IN ('tasklist /NH /FI "IMAGENAME eq %EXE%"') DO IF %%x == %EXE% goto ProcessFound

goto ProcessNotFound

:ProcessFound

echo %EXE% is running
goto END
:ProcessNotFound
start pythonw main.py
goto END
:END



