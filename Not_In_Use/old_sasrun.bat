@echo off
REM sasrun.bat
REM   Craig Heither, last revised 02/02/10
REM
REM    This is called by various Python scripts to execute a specified SAS program.
REM    The ERRORLEVEL variable is used to flag instances when SAS issues a Warning or Error.
REM    Each script that calls this file supplies the following arguments: 
REM        %1: command to start SAS
REM        %2: SAS program name
REM        %3: directory path
REM        %4: SAS log file name
REM        %5: SAS list file name
REM #################################################

REM - Run SAS
%1 -sysin %2 -sysparm %3 -log %4 -print %5

REM - Write Error Message to SAS .LST File if SAS did not Terminate Successfully
if %ERRORLEVEL% GTR 0 echo errorlevel=%ERRORLEVEL% >>%5