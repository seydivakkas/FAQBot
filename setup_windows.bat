@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
rem Python ciktisi Windows CI konsolunda cp1252 olabilecegi icin UTF-8 zorla.
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
title FAQBot - Windows Kurulum ve Calistirma

set "REPO_URL=https://github.com/seydivakkas/FAQBot.git"
set "PROJECTS=%USERPROFILE%\Projects"
set "PROJECT=%PROJECTS%\FAQBot"
set "PYTHON=%PROJECT%\.venv\Scripts\python.exe"
set "PUSHED=0"
set "CHECK_ONLY=0"
if /I "%~1"=="--check-only" set "CHECK_ONLY=1"

echo.
echo ==========================================
echo    FAQBot - Windows otomatik kurulum
echo ==========================================
echo.

where git >nul 2>&1
if errorlevel 1 (
    echo [HATA] Git bulunamadi. Git for Windows kurup tekrar deneyin.
    goto :failed
)

if not exist "%PROJECTS%" (
    mkdir "%PROJECTS%"
    if errorlevel 1 goto :failed
)

if exist "%PROJECT%" (
    if not exist "%PROJECT%\.git" (
        echo [HATA] %PROJECT% mevcut ancak Git deposu degil.
        echo Bu klasoru silmeyin. Elle kontrol edin.
        goto :failed
    )
) else (
    echo [1/6] Proje GitHub'dan indiriliyor...
    git clone "%REPO_URL%" "%PROJECT%"
    if errorlevel 1 goto :failed
)

pushd "%PROJECT%"
if errorlevel 1 goto :failed
set "PUSHED=1"

echo [2/6] Mevcut proje guncelleniyor...
git pull --ff-only
if errorlevel 1 (
    echo [HATA] git pull basarisiz. Yerel degisiklikleri kontrol edin.
    goto :failed
)

echo [3/6] Python 3.12 kontrol ediliyor...
py -3.12 --version
if errorlevel 1 (
    echo [HATA] Python 3.12 ve Windows py launcher gerekli.
    echo https://www.python.org/downloads/
    goto :failed
)

if not exist "%PYTHON%" (
    echo Sanal ortam olusturuluyor...
    py -3.12 -m venv ".venv"
    if errorlevel 1 goto :failed
)

echo [4/6] Python kutuphaneleri kuruluyor...
"%PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo [5/6] SQLite SSS veritabani hazirlaniyor...
"%PYTHON%" -m app.database
if errorlevel 1 goto :failed

echo [6/6] Otomatik testler calistiriliyor...
"%PYTHON%" -m pytest -v
if errorlevel 1 (
    echo [HATA] Testler basarisiz. Hata ciktilarini inceleyin.
    goto :failed
)

if "%CHECK_ONLY%"=="1" (
    echo.
    echo [BASARILI] Kurulum ve test kontrolu tamamlandi.
    goto :done
)

echo.
echo ==========================================
echo  FAQBot kurulumu tamamlandi!
echo  Sohbet: http://127.0.0.1:8000/app
echo  API:    http://127.0.0.1:8000/docs
echo  Sorular: Sohbet ekraninda Soruyu Gor
echo  Sunucuyu kapatmak icin: CTRL + C
echo ==========================================
echo.

rem Tarayiciyi yalnizca /health cevap verdikten sonra ac.
rem Asil Uvicorn bu pencerede calisir ve CTRL+C ile kapanir.
start "" /B powershell.exe -NoProfile -NonInteractive -Command "$url='http://127.0.0.1:8000/health'; for($i=0;$i -lt 60;$i++){try{$r=Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2; if($r.StatusCode -eq 200){Start-Process 'http://127.0.0.1:8000/app'; break}}catch{}; Start-Sleep -Seconds 1}"

"%PYTHON%" -m uvicorn app.main:app --app-dir . --reload
if errorlevel 1 (
    echo.
    echo [BILGI] Sunucu sonlandi veya CTRL+C ile kapatildi.
)
goto :done

:failed
echo.
echo [HATA] FAQBot kurulumu tamamlanamadi.
echo Yukaridaki hatayi inceleyin. Proje dosyalari silinmedi.
if "%PUSHED%"=="1" popd
if "%CHECK_ONLY%"=="0" pause
exit /b 1

:done
if "%PUSHED%"=="1" popd
endlocal
exit /b 0
