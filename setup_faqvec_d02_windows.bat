@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
title FAQVec-TR D02 - Uzman Inceleme Hazirligi

pushd "%~dp0"
if errorlevel 1 exit /b 1
if /I "%~1"=="--check-only" (
  if not exist "scripts\faqvec_d02_review.py" exit /b 1
  if not exist "scripts\faqvec_d02_rights.py" exit /b 1
  if not exist "scripts\faqvec_d02_acceptance.py" exit /b 1
  if not exist "frontend\d02_review_offline.html" exit /b 1
  echo [BASARILI] D02 yerel inceleme dosyalari mevcut.
  popd
  exit /b 0
)
if not exist ".venv\Scripts\python.exe" (
  echo [HATA] Once setup_windows.bat dosyasini calistirin.
  goto :failure
)
set "PY=.venv\Scripts\python.exe"
set "RAW=datasets\faqvec_d01_original\ml_paraphrase_60k_labeled.jsonl"
set "REVIEW=reports\faqvec-d02"
echo.
echo D02: Veri haklari HOLD. Bu islem ticari modeli egitmez.
echo Kaynak veri ilk indirmede internet gerektirir.
echo.
if not exist "%RAW%" (
  choice /C EH /M "Orijinal veriyi bir kez indirmek icin E, iptal icin H"
  if errorlevel 2 (
    popd
    exit /b 0
  )
  "%PY%" -m pip install "huggingface-hub>=0.26,<2.0"
  if errorlevel 1 goto :failure
  "%PY%" -m scripts.fetch_faqvec_d01_original --output "datasets\faqvec_d01_original"
  if errorlevel 1 goto :failure
)
if exist "%REVIEW%\review_bundle.PRIVATE.json" (
  echo [BILGI] Var olan gorev paketi korunuyor, uzerine yazilmadi.
) else (
  "%PY%" -m scripts.faqvec_d02_review prepare --input "%RAW%" --output-dir "%REVIEW%"
  if errorlevel 1 goto :failure
)
echo.
echo [BILGI] Iki farkli uzman, ayni paketi birbirinin cevaplarini gormeden incelemeli.
echo [BILGI] Hak sahibi ve ticari dagitim izni kanitlari ayrica gerekli.
"%PY%" -m scripts.faqvec_d02_acceptance --bundle "%REVIEW%\review_bundle.PRIVATE.json" --freeze "%REVIEW%\frozen_candidate_test_ids.json" --output "%REVIEW%\ilk_kabul_durumu.json"
if errorlevel 1 echo [BILGI] Kabul raporu zaten var; onceki kanit korunuyor.
start "" "frontend\d02_review_offline.html"
echo [BASARILI] Inceleme arayuzu acildi. Ticari model egitimi HALA HOLD.
popd
pause
exit /b 0

:failure
echo [HATA] D02 hazirligi tamamlanamadi; ticari egitim engelli.
popd
pause
exit /b 1
