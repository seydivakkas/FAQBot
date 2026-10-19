@echo off
setlocal
chcp 65001 >nul
pushd "%~dp0"
if errorlevel 1 exit /b 1
if /I "%~1"=="--check-only" (
  if not exist "docs\VERI_KAYNAGI_KESIN_POLITIKA.md" exit /b 1
  if not exist "scripts\faqvec_d02_review.py" exit /b 1
  if not exist "scripts\faqvec_d02_acceptance.py" exit /b 1
  echo [BASARILI] D02 arşiv kayıtları ve veri politikası mevcut.
  popd
  exit /b 0
)
echo.
echo [BILGI] D02 üçüncü taraf dataset indirmesi kullanici karariyla DURDURULDU.
echo Bu betik harici veri indirmez, islemez veya model egitmez.
echo [BILGI] Yeni incelemeler yalnizca kendi üretilen veya dogrulanmis CC0 verilerle yapilabilir.
echo Arsiv komut referanslari: faqvec_d02_review prepare ve faqvec_d02_acceptance.
popd
pause
exit /b 0
