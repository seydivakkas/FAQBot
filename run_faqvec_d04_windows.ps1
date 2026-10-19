# FAQVec-TR D04 - Windows/RTX, yalnız kendi özgün Türkçe veri kümesi.
# Modeller yalnız -DownloadModels geçildiğinde ilk kez ağdan indirilir.
# Eğitim ve benchmark başlatma kullanıcı tarafından açık switch gerektirir.
param(
    [switch]$InstallDependencies,
    [switch]$DownloadModels,
    [switch]$Train,
    [switch]$Benchmark,
    [switch]$IncludeAiNegatives
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    throw "Python sanal ortamı yok. Önce setup_windows.bat çalıştırın."
}
function PythonOrFail {
    param([string[]]$Arguments)
    & $py @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Komut başarısız (exit $LASTEXITCODE): python $($Arguments -join ' ')"
    }
}
Write-Host "D04: OWNED/CC0 dış veri KULLANILMAZ. İnsan etiketi yok; ticari kabul HOLD." -ForegroundColor Cyan
PythonOrFail @("-m","scripts.faqvec_d03_ai_review","--check-only")
if ($InstallDependencies) {
    # Yüklü PyTorch korunur; kullanıcı uygun CUDA sürümünü ayrıca kurabilir.
    PythonOrFail @("-m","pip","install","sentence-transformers>=4.1,<5","transformers>=4.48,<5",
        "huggingface-hub>=0.33,<1","datasets>=3.2,<4","accelerate>=1.3,<2",
        "psutil>=5.9,<8","hf-xet>=1,<2")
}
if ($DownloadModels) {
    foreach ($name in @("e5-base","minilm","bge-m3")) {
        $directory = switch ($name) {
            "e5-base" { "models\e5-base-original" }
            "minilm" { "models\minilm-original" }
            "bge-m3" { "models\bge-m3-original" }
        }
        $meta = Join-Path $directory "faqvec_backbone_origin.json"
        if (Test-Path $meta) {
            Write-Host "Mevcut model korundu: $name. Hash ve revizyon kaydı: $meta"
        } else {
            PythonOrFail @("-m","scripts.download_faqvec_model_weights",
                "--model",$name,"--confirm-download")
        }
    }
}
# Üçüncü taraf API çağrısı olmadan, yalnız yerel ağırlık.
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:WANDB_DISABLED = "true"
$trained = "models\faqvec-tr-ai-research"
if ($Train) {
    if (-not (Test-Path "models\e5-base-original\faqvec_backbone_origin.json")) {
        throw "Önce -DownloadModels ile E5-base MODEL ağırlıklarını indirin."
    }
    if (Test-Path (Join-Path $trained "model\faqvec_v2_manifest.json")) {
        throw "Model zaten mevcut; önceki modeli koruyun, yeni çıkış yolu seçin."
    }
    $argsTrain = @("-m","scripts.train_faqvec_v2",
        "--ai-owned-research","--backbone","models/e5-base-original",
        "--epochs","2","--batch-size","2","--gradient-accumulation","4",
        "--output",$trained)
    if ($IncludeAiNegatives) {
        $argsTrain += "--include-ai-negatives"
    }
    PythonOrFail $argsTrain
}
if ($Benchmark) {
    foreach ($file in @(
       "models\e5-base-original\faqvec_backbone_origin.json",
       "models\minilm-original\faqvec_backbone_origin.json",
       "models\bge-m3-original\faqvec_backbone_origin.json",
       (Join-Path $trained "model\faqvec_v2_manifest.json")
    )) {
        if (-not (Test-Path $file)) { throw "Ölçüm yapılamıyor, model yok: $file" }
    }
    New-Item -ItemType Directory -Path "reports\faqvec_d04" -Force | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $output = "reports\faqvec_d04\karsilastirma_$stamp.json"
    PythonOrFail @("-m","scripts.faqvec_d04_real_benchmark",
        "--ai-owned-research","--model","e5-base=models/e5-base-original",
        "--model","faqvec-tr=models/faqvec-tr-ai-research/model",
        "--model","minilm=models/minilm-original",
        "--model","bge-m3=models/bge-m3-original",
        "--latency-samples","12","--output",$output)
    Write-Host "Gerçek ölçüm JSON: $output" -ForegroundColor Green
}
if (-not ($Train -or $Benchmark -or $DownloadModels -or $InstallDependencies)) {
    Write-Host "Yalnız özgün veri doğrulandı. Seçenekler: -InstallDependencies -DownloadModels -Train -Benchmark"
}
Write-Host "Bağımsız müşteri testi ve ticari ürün onayı: HOLD." -ForegroundColor Yellow
