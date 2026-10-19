@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
pushd "%~dp0"
if errorlevel 1 exit /b 1
if /I "%~1"=="--check-only" (
  if not exist "scripts\build_faqvec_original.py" exit /b 1
  if not exist "scripts\train_faqvec_v2.py" exit /b 1
  if not exist "seed\faqvec_tr_ozgun_taslak_v01.json" exit /b 1
  echo [BASARILI] Ozgun veri ve E5 altyapisi mevcut.
  popd
  exit /b 0
)
if not exist ".venv\Scripts\python.exe" (
  echo [HATA] Once setup_windows.bat dosyasini calistirin.
  goto :fail
)
echo [BILGI] FAQVec-TR v0.2: Eski 110 SSS demo egitimi iptal edildi.
echo [BILGI] Yeni ozgun veri paketi insan ve veri hakki kabulunu bekliyor.
".venv\Scripts\python.exe" -m scripts.build_faqvec_original --check-only
if errorlevel 1 goto :fail
echo [BILGI] E5 egitimi veya model indirmesi OTOMATIK yapilmadi.
echo [BILGI] Yalniz insan onayli OWNED/CC0 manifestinden egitim acilabilir.
popd
pause
exit /b 0
:fail
echo [HATA] FAQVec veri kontrolu tamamlanamadi.
popd
pause
exit /b 1
