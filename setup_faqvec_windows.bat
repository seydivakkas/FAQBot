@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
title FAQBot - FAQVec-TR Yerel Model Egitimi

pushd "%~dp0"
if errorlevel 1 goto :failed
if not exist ".venv\Scripts\python.exe" (
    echo [HATA] Once setup_windows.bat dosyasini calistirin.
    goto :failed
)
echo.
echo FAQVec-TR kendi modelimiz; hazir model agirligi indirmez.
echo Egitim yalnizca depodaki kurgusal SSS verilerini kullanir.
echo Guncel musteri mesajlari egitime otomatik eklenmez.
echo.
".venv\Scripts\python.exe" -m scripts.train_faqvec_tr --epochs 30
if errorlevel 1 goto :failed
echo.
echo [BASARILI] Modeller\faqvec-tr-v0.1 model dosyalari olusturuldu.
echo FAQBot Ayarlar ^> Benzer Sorular ^> FAQVec-TR secerek kaydedin.
popd
pause
exit /b 0

:failed
echo [HATA] Yerel egitim tamamlanamadi.
popd
pause
exit /b 1
