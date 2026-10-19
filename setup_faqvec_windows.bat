@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
pushd "%~dp0"
if errorlevel 1 exit /b 1
if /I "%~1"=="--check-only" (
  if not exist "scripts\build_faqvec_original.py" exit /b 1
  echo [BASARILI] Ozgun veri hazirlama araci mevcut.
  popd
  exit /b 0
)
if not exist ".venv\Scripts\python.exe" (
  echo [HATA] Once setup_windows.bat dosyasini calistirin.
  goto :fail
)
echo [BILGI] FAQVec-TR v0.1 eski demo egitimi veri politikasiyla durduruldu.
echo [BILGI] Yalniz yeni ozgun veya teyit edilmis CC0 verileri kabul edilir.
".venv\Scripts\python.exe" -m scripts.build_faqvec_original --check-only
if errorlevel 1 goto :fail
echo [BASARILI] Taslak kontrolu tamamlandi. Model egitimi YAPILMADI.
popd
pause
exit /b 0
:fail
echo [HATA] Kaynak veri kontrolu tamamlanamadi.
popd
pause
exit /b 1
