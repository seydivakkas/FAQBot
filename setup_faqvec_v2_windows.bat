@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
title FAQBot - FAQVec-TR v0.2 MIT E5 Yerel Ince Ayar

pushd "%~dp0"
if errorlevel 1 exit /b 1

if /I "%~1"=="--check-only" (
  if not exist "scripts\train_faqvec_v2.py" exit /b 1
  if not exist "scripts\fetch_faqvec_v2_backbone.py" exit /b 1
  if not exist "requirements-faqvec-v2.txt" exit /b 1
  echo [BASARILI] FAQVec-TR v0.2 Windows betik kaynaklari yerinde.
  popd
  exit /b 0
)

if not exist ".venv\Scripts\python.exe" (
  echo [HATA] Once setup_windows.bat dosyasini calistirin.
  goto :failed
)

echo.
echo FAQVec-TR v0.2 deneme kurulumu (ticari kabul HOLD).
echo Bu komut MIT E5-base modelini ~1 GB seviyesinde BIR KEZ indirebilir.
echo Egitim, kurgusal FAQBot SSS verileriyle yapilacak, gercek kullanici verisi olmayacak.
echo Internet ilk model ve kutuphane indirmelerinde gerekir; sonraki inference offline.
echo.
choice /C EH /M "Devam etmek icin E, iptal etmek icin H"
if errorlevel 2 (
  popd
  exit /b 0
)

".venv\Scripts\python.exe" -m pip install -r requirements-faqvec-v2.txt
if errorlevel 1 goto :failed

if not exist "models\e5-base-original\faqvec_backbone_origin.json" (
  ".venv\Scripts\python.exe" -m scripts.fetch_faqvec_v2_backbone --output "models\e5-base-original"
  if errorlevel 1 goto :failed
)

if exist "models\faqvec-tr-v0.2-e5\model\faqvec_v2_manifest.json" (
  echo [BILGI] Mevcut model korunuyor; otomatik uzerine yazilmadi.
) else (
  ".venv\Scripts\python.exe" -m scripts.train_faqvec_v2 --demo --epochs 2 --batch-size 2 --gradient-accumulation 8 --output "models\faqvec-tr-v0.2-e5"
  if errorlevel 1 goto :failed
)

".venv\Scripts\python.exe" -m scripts.benchmark_faqvec_v2 --demo --model "e5-base=models\e5-base-original" --model "faqvec-v2=models\faqvec-tr-v0.2-e5\model" --output "reports\faqvec_v2_demo_benchmark.json"
if errorlevel 1 goto :failed
echo.
echo [BASARILI] E5 tabanli deneme modeli ve benchmark raporu hazir.
echo Ayarlar / Benzer Sorular / FAQVec-TR v0.2 secin.
echo Kullanim haklari ve bagimsiz kalite testi tamamlanmadan ticari dagitim yapmayin.
popd
pause
exit /b 0

:failed
echo [HATA] FAQVec-TR v0.2 kurulum/egitimi tamamlanamadi.
popd
pause
exit /b 1
