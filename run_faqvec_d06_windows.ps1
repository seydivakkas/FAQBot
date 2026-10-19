# FAQVec D06 — önce kaynak mühürü, sonra isteğe bağlı yerel altılı karşılaştırma.
# Hiçbir ağırlık/veri indirme veya yeniden eğitim gerçekleştirilmez.
param(
    [switch]$Compare,
    [string]$D04Model = "models\faqvec-tr-ai-research\model",
    [string]$D05Model = "models\faqvec-tr-d05-ai-research\model"
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    throw "Python sanal ortamı bulunamadı. Önce setup_windows.bat kullanın."
}
function Invoke-LocalPython {
    param([string[]]$Arguments)
    & $py @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Yerel Python başarısız: $($Arguments -join ' ') (exit $LASTEXITCODE)"
    }
}
Write-Host "D06: sadece kendi proje özgün testlerimiz. Ticari kabul HOLD." -ForegroundColor Cyan
Invoke-LocalPython @("-m", "scripts.faqvec_d03_ai_review", "--check-only")
Invoke-LocalPython @("-m", "scripts.faqvec_d05_owned_data")
Invoke-LocalPython @("-m", "scripts.faqvec_d06_frozen_challenge")

$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
$env:WANDB_DISABLED="true"
if ($Compare) {
    $dirs = @{
        "e5-base"="models\e5-base-original"
        "faqvec-d04"=$D04Model
        "faqvec-d05"=$D05Model
        "minilm"="models\minilm-original"
        "bge-m3"="models\bge-m3-original"
    }
    foreach ($name in $dirs.Keys) {
        if (-not (Test-Path $dirs[$name])) {
            throw "D06 model karşılaştırması engellendi. Yerel ağırlık yok: $name => $($dirs[$name])"
        }
    }
    New-Item -ItemType Directory -Path "reports\faqvec_d06" -Force | Out-Null
    $filename = "reports\faqvec_d06\frozen_hard_$(Get-Date -Format yyyyMMdd-HHmmss).json"
    Invoke-LocalPython @(
        "-m","scripts.faqvec_d06_hard_benchmark",
        "--ai-owned-research","--require-all",
        "--model","e5-base=$($dirs['e5-base'])",
        "--model","faqvec-d04=$($dirs['faqvec-d04'])",
        "--model","faqvec-d05=$($dirs['faqvec-d05'])",
        "--model","minilm=$($dirs['minilm'])",
        "--model","bge-m3=$($dirs['bge-m3'])",
        "--latency-samples","24","--output",$filename
    )
    Write-Host "D06 mühürlü zor test raporu: $filename" -ForegroundColor Green
} else {
    Write-Host "Kaynak testi tamamlandı; gerçek model yarışması başlatılmadı."
    Write-Host "Bütün ağırlıklar yerelse -Compare ile yalnız çevrimdışı ölçüm yapılır."
}
Write-Host "AI etiketli zor test bağımsız gerçek müşteri doğrulaması değildir." -ForegroundColor Yellow
