@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d C:\Users\lucas.neto\Documents\IAcomp\urban-lens

if not exist ".env" (
    echo [ERRO] Arquivo .env nao encontrado na raiz do projeto.
    exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    set "%%A=%%B"
)

set "YEAR=2024"
set "FORCE=metropolitan"
set "ACTOR=lucas.neto"
set "POLICE_ROOT=C:\Users\lucas.neto\Documents\Police"

echo.
echo =========================================================
echo  Garanta que o Docker Compose esteja ativo, incluindo o MLflow
echo =========================================================
echo docker compose up -d postgres minio minio-setup mlflow
echo.
pause

for %%M in (03 04 05 06 07 08 09 10 11 12) do (
    echo.
    echo ==========================================
    echo Processando %YEAR%-%%M
    echo ==========================================

    set "CSV_PATH=%POLICE_ROOT%\%YEAR%-%%M\%YEAR%-%%M-%FORCE%-street.csv"

    if not exist "!CSV_PATH!" (
        echo [ERRO] Arquivo nao encontrado: !CSV_PATH!
        exit /b 1
    )

    echo [1/4] Ingest Bronze
    python pipelines\ingest_manual.py --csv-path "!CSV_PATH!" --force-name %FORCE% --actor %ACTOR% > "%TEMP%\urban_ingest_%%M.txt" 2>&1
    if errorlevel 1 (
        type "%TEMP%\urban_ingest_%%M.txt"
        exit /b 1
    )
    type "%TEMP%\urban_ingest_%%M.txt"

    for /f "usebackq delims=" %%I in (`python -c "import ast, pathlib; d=ast.literal_eval(pathlib.Path(r'%TEMP%\urban_ingest_%%M.txt').read_text(encoding='utf-8').strip()); print(d['dataset_version_id'])"`) do (
        set "BRONZE_ID=%%I"
    )

    echo BRONZE_ID=!BRONZE_ID!

    echo [2/4] Bronze to Silver
    python pipelines\bronze_to_silver.py --bronze-object-key "bronze/data.police.uk/crimes/year=%YEAR%/month=%%M/force=%FORCE%/%YEAR%-%%M-%FORCE%-street.csv" --bronze-dataset-version-id "!BRONZE_ID!" --actor %ACTOR% > "%TEMP%\urban_silver_%%M.txt" 2>&1
    if errorlevel 1 (
        type "%TEMP%\urban_silver_%%M.txt"
        exit /b 1
    )
    type "%TEMP%\urban_silver_%%M.txt"

    for /f "usebackq delims=" %%I in (`python -c "import ast, pathlib; d=ast.literal_eval(pathlib.Path(r'%TEMP%\urban_silver_%%M.txt').read_text(encoding='utf-8').strip()); print(d['dataset_version_id'])"`) do (
        set "SILVER_ID=%%I"
    )

    echo SILVER_ID=!SILVER_ID!

    echo [3/4] Silver to Gold
    python pipelines\silver_to_gold.py --silver-object-key "silver/police_uk/crimes_standardized/year=%YEAR%/month=%%M/part-000.parquet" --silver-dataset-version-id "!SILVER_ID!" --actor %ACTOR% > "%TEMP%\urban_gold_%%M.txt" 2>&1
    if errorlevel 1 (
        type "%TEMP%\urban_gold_%%M.txt"
        exit /b 1
    )
    type "%TEMP%\urban_gold_%%M.txt"

    for /f "usebackq delims=" %%I in (`python -c "import ast, pathlib; d=ast.literal_eval(pathlib.Path(r'%TEMP%\urban_gold_%%M.txt').read_text(encoding='utf-8').strip()); print(d['forecast_training_set_dataset_version_id'])"`) do (
        set "LAST_TRAINING_ID=%%I"
    )

    for /f "usebackq delims=" %%I in (`python -c "import ast, pathlib; d=ast.literal_eval(pathlib.Path(r'%TEMP%\urban_gold_%%M.txt').read_text(encoding='utf-8').strip()); print(d['forecast_scoring_set_dataset_version_id'])"`) do (
        set "LAST_SCORING_ID=%%I"
    )

    set "LAST_MONTH=%%M"

    echo TRAINING_ID=!LAST_TRAINING_ID!
    echo SCORING_ID=!LAST_SCORING_ID!
)

echo.
echo ==========================================
echo Treinando modelo com o mes %YEAR%-%LAST_MONTH%
echo ==========================================

python pipelines\train_forecast_model.py --training-object-key "gold/ml/forecast_training_set/year=%YEAR%/month=%LAST_MONTH%/part-000.parquet" --training-dataset-version-id "%LAST_TRAINING_ID%" --scoring-object-key "gold/ml/forecast_scoring_set/year=%YEAR%/month=%LAST_MONTH%/part-000.parquet" --scoring-dataset-version-id "%LAST_SCORING_ID%" --actor %ACTOR%

if errorlevel 1 (
    echo.
    echo [ERRO] Falha no treinamento final.
    exit /b 1
)

echo.
echo ==========================================
echo Processo concluido com sucesso.
echo ==========================================
pause
