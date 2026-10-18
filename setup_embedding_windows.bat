@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
title FAQBot - Istege Bagli Yerel Embedding Kurulumu

pushd "%~dp0"
if errorlevel 1 goto :failed
if not exist ".venv\Scripts\python.exe" (
    echo [HATA] Oncelikle setup_windows.bat dosyasini calistirin.
    goto :failed
)
echo.
echo Bu istege bagli kurulum ek Python kutuphaneleri ve acik kaynak modeli indirir.
echo Ilk kurulum icin internet gerekir. Sonraki taramalar yerel calisir.
echo Model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
echo.
".venv\Scripts\python.exe" -m pip install -r requirements-embeddings.txt
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m scripts.download_embedding_model
if errorlevel 1 goto :failed
echo.
echo [BASARILI] Model hazir. FAQBot > Ayarlar > Benzer Sorular bolumunden
echo Yerel Embedding secenegini secip Yontemi kaydedin.
popd
pause
exit /b 0

:failed
echo [HATA] Istege bagli embedding kurulumu tamamlanamadi.
popd
pause
exit /b 1
