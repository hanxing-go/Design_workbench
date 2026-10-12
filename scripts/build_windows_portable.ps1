param([switch]$SkipChecks)
$ErrorActionPreference = 'Stop'
if (-not $IsWindows -and $env:OS -ne 'Windows_NT') { throw 'Build this bundle on Windows x64.' }
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    function Invoke-Checked {
        param([string]$Program, [string[]]$Arguments)
        & $Program @Arguments
        if ($LASTEXITCODE -ne 0) { throw "$Program failed with exit code $LASTEXITCODE" }
    }
    Invoke-Checked uv @('sync', '--locked', '--python', '3.12', '--extra', 'gui', '--group', 'packaging')
    Invoke-Checked npm.cmd @('ci', '--prefix', 'frontend')
    if (-not $SkipChecks) {
        Invoke-Checked uv @('run', '--no-sync', 'ruff', 'check', '.')
        Invoke-Checked uv @('run', '--no-sync', 'ruff', 'format', '--check', '.')
        Invoke-Checked uv @('run', '--no-sync', 'mypy')
        Invoke-Checked uv @('run', '--no-sync', 'pytest', '-m', 'not e2e and not resources', '-q')
        Invoke-Checked npm.cmd @('run', 'check', '--prefix', 'frontend')
    }
    Invoke-Checked npm.cmd @('run', 'build', '--prefix', 'frontend')
    Invoke-Checked uv @('run', '--no-sync', 'pyinstaller', '--noconfirm', '--clean', 'packaging/windows/workbench.spec')
    $bundle = Join-Path $projectRoot 'dist/DesignWorkbench'
    Copy-Item -LiteralPath 'packaging/windows/GET_STARTED.txt' -Destination $bundle
    Copy-Item -LiteralPath 'LICENSE' -Destination (Join-Path $bundle 'LICENSE.txt')
    Copy-Item -LiteralPath 'docs/WINDOWS_PORTABLE.md' -Destination $bundle
    Invoke-Checked uv @('run', '--no-sync', 'python', 'scripts/portable_smoke.py', $bundle)
    $version = (& uv run --no-sync python -c 'from design_workbench import __version__; print(__version__)').Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Failed to read version' }
    $archive = Join-Path $projectRoot "dist/DesignWorkbench-$version-windows-x64.zip"
    Compress-Archive -Path $bundle -DestinationPath $archive -Force
    (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLower() + '  ' + (Split-Path -Leaf $archive) |
        Set-Content -LiteralPath "$archive.sha256" -Encoding ascii
    Write-Output "Portable release: $archive"
} finally {
    Pop-Location
}
