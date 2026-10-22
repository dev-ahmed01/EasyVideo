$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
$modelDir = Join-Path $root 'models\piper'
$model = Join-Path $modelDir 'en_US-ljspeech-medium.onnx'
$config = "$model.json"
$card = Join-Path $modelDir 'MODEL_CARD.txt'

Write-Host 'EasyVideo - Free offline neural voice setup'
Write-Host 'Piper software is GPL-3.0. Voice models may have separate commercial-use requirements.'
Write-Host 'Review the voice model terms before using generated audio in business advertising:'
Write-Host 'https://huggingface.co/rhasspy/piper-voices/tree/v1.0.0/en/en_US/ljspeech/medium'
Write-Host ''
$approve = Read-Host 'Download this voice to your PC and install Piper? Type YES to continue'
if ($approve -cne 'YES') {
    Write-Host 'Cancelled without installing the voice model.'
    exit 1
}

New-Item -ItemType Directory -Path $modelDir -Force | Out-Null
Write-Host 'Installing the CPU-based Piper engine into EasyVideo venv...'
& $python -m pip install --disable-pip-version-check 'piper-tts==1.8.0'
if ($LASTEXITCODE -ne 0) { throw 'Piper installation failed' }

$remote = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ljspeech/medium/'
Write-Host 'Downloading neural English voice (~64 MB), configuration and model card...'
if (-not (Test-Path $model)) {
    Invoke-WebRequest -Uri ($remote + 'en_US-ljspeech-medium.onnx') -OutFile $model
}
$expected = '6f52a751e2349abe7a76735eb09dc1875298c77ea2342ffd2fef79ff81b87f22'
$actual = (Get-FileHash -Path $model -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) {
    Remove-Item $model -Force
    throw 'Piper model checksum mismatch. Please retry from the official model repository.'
}
Invoke-WebRequest -Uri ($remote + 'en_US-ljspeech-medium.onnx.json') -OutFile $config
Invoke-WebRequest -Uri ($remote + 'MODEL_CARD') -OutFile $card
Get-Content -Raw -Path $config | ConvertFrom-Json | Out-Null

$sample = Join-Path $modelDir 'voice_test.wav'
Write-Host 'Checking offline narration generation...'
& $python -m piper -m $model -f $sample -- 'Hello. Your EasyVideo neural voice is ready.'
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $sample)) {
    throw 'Piper did not produce a sample voice.'
}
Remove-Item $sample -Force
Write-Host 'Piper installed. EasyVideo will now choose it over the basic Windows voice.'
