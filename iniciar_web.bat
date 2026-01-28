@echo off
REM Script para iniciar a versão WEB com Streamlit

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ========================================
    echo ERRO: Python nao foi encontrado!
    echo ========================================
    echo.
    echo Por favor, instale Python em:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM Verifica se Streamlit está instalado
pip show streamlit >nul 2>&1
if errorlevel 1 (
    echo Instalando Streamlit...
    pip install streamlit
)

REM Inicia o app
echo.
echo Iniciando interface web...
echo.
echo Abra o navegador e acesse: http://localhost:8501
echo.
streamlit run app_streamlit.py --logger.level=error
