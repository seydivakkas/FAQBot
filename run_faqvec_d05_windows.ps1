# FAQVec D05 — Windows/RTX, yalnız kendi özgün verimiz veya doğrulanmış CC0.
# Önceki D04 ağırlıkları değiştirilmez; test kümesi ve galeri sabit kalır.
param(
    [switch]$InstallDependencies,
    [switch]$DownloadModels,
    [switch]$Train,
    [switch]$Compare,
    [string]$D04Model = "models\faqvec-tr-ai-research\model",
    [string]$D05Output = "models\faqvec-tr-d05-ai-research"
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Sanal ortam eksik: önce setup_windows.bat dosyasını çalıştırın."
}
function Exec-Python {
    param([string[]]$Params)
    & $python @Params
    if ($LASTEXITCODE -ne 0) {
        throw "Python komutu başarısız (exit $LASTEXITCODE): $($Params -join ' ')"
    }
}
Write-Host "FAQVec D05 | OWNED/CC0 koşulu | ticari eğitim/yayın HOLD" -ForegroundColor Cyan
Exec-Python @("-m","scripts.faqvec_d03_ai_review","--check-only")
Exec-Python @("-m","scripts.faqvec_d05_owned_data")
Exec-Python @("-m","scripts.faqvec_d05_safety_slices")

if ($InstallDependencies) {
    Exec-Python @("-m","pip","install",
        "sentence-transformers>=4.1,<5","transformers>=4.48,<5",
        "huggingface-hub>=0.33,<1","datasets>=3.2,<4",
        "accelerate>=1.3,<2","psutil>=5.9,<8","hf-xet>=1,<2")
}
if ($DownloadModels) {
    foreach ($name in @("e5-base","minilm","bge-m3")) {
        $dest = switch ($name) {
            "e5-base" { "models\e5-base-original" }
            "minilm" { "models\minilm-original" }
            "bge-m3" { "models\bge-m3-original" }
        }
        if (Test-Path (Join-Path $dest "faqvec_backbone_origin.json")) {
            Write-Host "Kayıtlı model bulundu, yeniden indirilmedi: $name"
        } elseif (Test-Path $dest) {
            throw "Eksik model klasörü var; üzerine yazılmadı: $dest"
        } else {
            Exec-Python @("-m","scripts.download_faqvec_model_weights",
                "--model",$name,"--confirm-download")
        }
    }
}
# Ağ yalnız açık -InstallDependencies / -DownloadModels seçeneklerinde kullanılır.
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:WANDB_DISABLED = "true"
if ($Train) {
    if (-not (Test-Path "models\e5-base-original\faqvec_backbone_origin.json")) {
        throw "Yerel E5-base yok. Gerekirse açıkça -DownloadModels kullanın."
    }
    if (Test-Path $D05Output) {
        throw "Eğitilecek çıktı klasörü zaten var, eski ağırlık korunur: $D05Output"
    }
    Exec-Python @("-m","scripts.train_faqvec_v2",
        "--ai-owned-research","--d05-owned-expansion","--include-ai-negatives",
        "--backbone","models/e5-base-original","--epochs","2",
        "--batch-size","2","--gradient-accumulation","4",
        "--output",$D05Output)
}
if ($Compare) {
    $d05 = Join-Path $D05Output "model"
    $models = @{
        "e5-base" = "models\e5-base-original"
        "faqvec-d04" = $D04Model
        "faqvec-d05" = $d05
        "minilm" = "models\minilm-original"
        "bge-m3" = "models\bge-m3-original"
    }
    foreach ($name in $models.Keys) {
        if (-not (Test-Path $models[$name])) {
            throw "D05 yarışına başlanmadı; $name yerel klasörü eksik: $($models[$name])"
        }
    }
    New-Item -ItemType Directory -Path "reports\faqvec_d05" -Force | Out-Null
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $path = "reports\faqvec_d05\gercek_karsilastirma_$timestamp.json"
    Exec-Python @("-m","scripts.faqvec_d05_real_benchmark",
        "--ai-owned-research","--require-all",
        "--model","e5-base=$($models['e5-base'])",
        "--model","faqvec-d04=$($models['faqvec-d04'])",
        "--model","faqvec-d05=$($models['faqvec-d05'])",
        "--model","minilm=$($models['minilm'])",
        "--model","bge-m3=$($models['bge-m3'])",
        "--latency-samples","24","--output",$path)
    Write-Host "Karşılaştırma JSON: $path" -ForegroundColor Green
}
if (-not ($InstallDependencies -or $DownloadModels -or $Train -or $Compare)) {
    Write-Host "Yalnız özgün veri ve güvenlik dilimleri kontrol edildi."
    Write-Host "Seçenekler: -InstallDependencies -DownloadModels -Train -Compare"
}
Write-Host "Gerçek Windows GPU fiziksel kabulü ve ticari yayın: HOLD."
