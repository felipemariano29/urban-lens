@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d C:\Users\lucas.neto\Documents\IAcomp\urban-lens

if not exist ".env" (
    echo [ERRO] Arquivo .env nao encontrado.
    exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    set "%%A=%%B"
)

set "ACTOR=lucas.neto"

call :run_month 03 d57aca10-3109-422f-8a17-692cc071d55c
call :run_month 04 2f741b65-3598-43fa-b8c4-031bad624348
call :run_month 05 c81da001-3011-4f28-a2e4-bc10a89ad07a
call :run_month 06 a49e92bd-eef4-4a58-bb97-4254156ea9bb
call :run_month 07 aaf81a53-e6b2-463e-bb08-89cd4d3fc602
call :run_month 08 a1d3c1a5-b05e-4a5a-bdbf-c3753cb89645
call :run_month 09 ec2d5610-9304-4243-9a2b-ea6a573c3059
call :run_month 10 ff4bb688-8bd9-4a60-9df6-77ecb9808a1f
call :run_month 11 0d6f3e74-b36e-4b0a-ab70-2ce5ca6b6e6f
call :run_month 12 9ff4aa81-5957-4337-b360-4d7953957c11

echo.
echo ==========================================
echo Regeracao Gold concluida com sucesso.
echo ==========================================
pause
exit /b 0

:run_month
set "MONTH=%~1"
set "SILVER_ID=%~2"

echo.
echo ==========================================
echo Regerando Gold para 2024-%MONTH%
echo ==========================================
echo SILVER_ID=%SILVER_ID%

python pipelines\silver_to_gold.py --silver-object-key "silver/police_uk/crimes_standardized/year=2024/month=%MONTH%/part-000.parquet" --silver-dataset-version-id "%SILVER_ID%" --actor %ACTOR%
if errorlevel 1 (
    echo [ERRO] Falha no silver_to_gold de 2024-%MONTH%
    exit /b 1
)

exit /b 0