$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$voices = Join-Path $root "voices"
New-Item -ItemType Directory -Force -Path $voices | Out-Null

$base = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts/high/"
$names = @("en_US-libritts-high.onnx", "en_US-libritts-high.onnx.json")
foreach ($name in $names) {
    $dest = Join-Path $voices $name
    $minimum = if ($name.EndsWith(".onnx")) { 100MB } else { 1000 }
    if ((Test-Path $dest) -and (Get-Item $dest).Length -ge $minimum) {
        Write-Host "Already downloaded: $name"
        continue
    }
    $temporary = "$dest.part"
    try {
        Write-Host "Downloading $name (one-time setup)..."
        Invoke-WebRequest -Uri ($base + $name) -OutFile $temporary -MaximumRedirection 8 -UseBasicParsing
        if ((Get-Item $temporary).Length -lt $minimum) {
            throw "Downloaded file is unexpectedly small: $name"
        }
        Move-Item -Path $temporary -Destination $dest -Force
    } finally {
        Remove-Item -Path $temporary -Force -ErrorAction SilentlyContinue
    }
}
$configPath = Join-Path $voices "en_US-libritts-high.onnx.json"
$config = Get-Content -Raw -Path $configPath | ConvertFrom-Json
if (-not $config) { throw "Voice config is invalid" }
Write-Host "Offline voice files are ready."
Write-Host "Data license: CC BY 4.0; credit LibriTTS and its contributors when used."
