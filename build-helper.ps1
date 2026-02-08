#!/usr/bin/env pwsh
<#
.SYNOPSIS
    NotebookLM2PPT Build and Release Helper Script (PowerShell)

.DESCRIPTION
    Tập lệnh PowerShell để giúp xây dựng, kiểm tra và phát hành dự án NotebookLM2PPT

.EXAMPLE
    .\build-helper.ps1 -Action test
    .\build-helper.ps1 -Action build
    .\build-helper.ps1 -Action release
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('menu', 'test', 'run', 'build', 'exe-single', 'exe-folder', 'clean', 'full', 'release')]
    [string]$Action = 'menu'
)

# Color definitions
$Colors = @{
    Success = 'Green'
    Error   = 'Red'
    Info    = 'Cyan'
    Warning = 'Yellow'
}

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor $Colors.Info
    Write-Host "  $Message" -ForegroundColor $Colors.Info
    Write-Host ("=" * 60) -ForegroundColor $Colors.Info
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host "[*] $Message" -ForegroundColor $Colors.Info
}

function Write-Success {
    param([string]$Message)
    Write-Host "[+] $Message" -ForegroundColor $Colors.Success
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "[-] $Message" -ForegroundColor $Colors.Error
}

function Show-Menu {
    Write-Header "NotebookLM2PPT - Build `& Release Helper"
    
    Write-Host ""
    Write-Host "Available commands:" -ForegroundColor $Colors.Info
    Write-Host ""
    Write-Host "  test         - Run basic checks" -ForegroundColor White
    Write-Host "  run          - Run application from source" -ForegroundColor White
    Write-Host "  build        - Build wheel + source dist" -ForegroundColor White
    Write-Host "  exe-single   - Build single-file exe (PyInstaller)" -ForegroundColor White
    Write-Host "  exe-folder   - Build folder exe (PyInstaller)" -ForegroundColor White
    Write-Host "  clean        - Clean old builds" -ForegroundColor White
    Write-Host "  full         - Clean and build (full workflow)" -ForegroundColor White
    Write-Host "  release      - Show release checklist" -ForegroundColor White
    Write-Host "  menu         - Show this menu" -ForegroundColor White
    Write-Host "  exit         - Exit" -ForegroundColor White
    Write-Host ""
    
    if ($Action -eq 'menu') {
        $choice = Read-Host "Enter command"
        if ($choice -eq 'exit') { exit 0 }
        & $PSScriptRoot\build-helper.ps1 -Action $choice
    }
}

function Test-Setup {
    Write-Header "Running basic checks"
    
    $success = $true
    
    # Check Python
    Write-Step "Checking Python installation..."
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Python: $pythonVersion"
    } else {
        Write-ErrorMsg "Python not found"
        $success = $false
    }
    
    # Check syntax
    Write-Step "Checking Python syntax..."
    Get-ChildItem notebooklm2ppt -Filter "*.py" -Recurse | ForEach-Object {
        python -m py_compile $_.FullName 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-ErrorMsg "Syntax error in $($_.Name)"
            $success = $false
        }
    }
    if ($success) {
        Write-Success "All Python files syntax OK"
    }
    
    # Check imports
    Write-Step "Checking imports..."
    python -c "import notebooklm2ppt; print('OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Imports OK"
    } else {
        Write-ErrorMsg "Import failed"
        $success = $false
    }
    
    return $success
}

function Run-Application {
    Write-Header "Running application from source"
    
    Write-Step "Activating virtual environment..."
    & venv\Scripts\Activate.ps1
    
    Write-Step "Launching main.py..."
    python main.py
}

function Build-Package {
    Write-Header "Building Python package"
    
    # Clean old builds
    Write-Step "Cleaning old builds..."
    @('build', 'dist') | ForEach-Object {
        if (Test-Path $_) {
            Remove-Item $_ -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    Get-ChildItem -Filter "*.egg-info" -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item $_.FullName -Recurse -Force
    }
    Write-Success "Cleanup complete"
    
    # Check version
    Write-Step "Checking version..."
    $versionLine = Get-Content pyproject.toml | Select-String 'version = "'
    Write-Host "  $versionLine" -ForegroundColor $Colors.Warning
    
    # Build
    Write-Step "Building package..."
    python -m build
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Build failed"
        return $false
    }
    Write-Success "Build successful"
    
    # Verify
    Write-Step "Verifying with twine..."
    python -m twine check dist/* 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Package verification failed"
        return $false
    }
    
    # Show results
    Write-Success "Generated files:"
    Get-ChildItem dist | Format-Table -AutoSize
    
    return $true
}

function Build-Exe-Single {
    Write-Header "Building single-file exe"
    
    Write-Host ""
    Write-Host "Options:" -ForegroundColor $Colors.Info
    Write-Host "  1) Basic (fast)"
    Write-Host "  2) With optimization (slower, smaller)"
    Write-Host ""
    
    $choice = Read-Host "Choose option"
    
    $args = @('--clean', '-F', '-w', '-n', 'notebooklm2ppt', 'main.py')
    $args += '--hidden-import=fitz'
    $args += '--hidden-import=pymupdf'
    $args += '--hidden-import=PyMuPDF'
    $args += '--hidden-import=spire.presentation._api'
    $args += '--hidden-import=pywin32'
    $args += '--collect-all=spire.presentation'
    $args += '--collect-all=pymupdf'
    
    if ($choice -eq '2') {
        $args += '--optimize=2'
        Write-Step "Building with optimization (this may take a while)..."
    } else {
        Write-Step "Building (basic)..."
    }
    
    python -m PyInstaller @args
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Executable created"
        $exeFile = Get-Item 'dist\notebooklm2ppt.exe' -ErrorAction SilentlyContinue
        if ($exeFile) {
            $size = $exeFile.Length / 1MB
            Write-Host "  Path: $($exeFile.FullName)" -ForegroundColor $Colors.Info
            Write-Host "  Size: $($size.ToString('F2')) MB" -ForegroundColor $Colors.Info
        }
        return $true
    } else {
        Write-ErrorMsg "Build failed"
        return $false
    }
}

function Build-Exe-Folder {
    Write-Header "Building folder exe"
    
    Write-Step "Building with PyInstaller..."
    $folderArgs = @('--clean', '-D', '-w', '-n', 'notebooklm2ppt', '--optimize=2')
    $folderArgs += '--hidden-import=fitz'
    $folderArgs += '--hidden-import=pymupdf'
    $folderArgs += '--hidden-import=PyMuPDF'
    $folderArgs += '--hidden-import=spire.presentation._api'
    $folderArgs += '--hidden-import=pywin32'
    $folderArgs += '--collect-all=spire.presentation'
    $folderArgs += '--collect-all=pymupdf'
    $folderArgs += 'main.py'
    
    python -m PyInstaller @folderArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Application folder created"
        Write-Host "  Path: dist\notebooklm2ppt\" -ForegroundColor $Colors.Info
        Write-Host "  Run: dist\notebooklm2ppt\notebooklm2ppt.exe" -ForegroundColor $Colors.Info
        return $true
    } else {
        Write-ErrorMsg "Build failed"
        return $false
    }
}

function Clean-Build {
    Write-Header "Cleaning builds"
    
    $items = @('build', 'dist', '__pycache__')
    foreach ($item in $items) {
        if (Test-Path $item) {
            Write-Step "Removing $item..."
            Remove-Item $item -Recurse -Force -ErrorAction SilentlyContinue
            Write-Success "Removed $item"
        }
    }
    
    Get-ChildItem -Filter "*.egg-info" -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Step "Removing $_..."
        Remove-Item $_.FullName -Recurse -Force
        Write-Success "Removed $_"
    }
    
    Get-ChildItem -Filter "*.pyc" -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item $_.FullName -Force
    }
    
    Write-Success "Cleanup complete"
}

function Full-Build {
    Write-Header "Full build workflow"
    
    Clean-Build
    Write-Host ""
    
    if (-not (Test-Setup)) {
        Write-ErrorMsg "Tests failed. Stopping."
        return $false
    }
    Write-Host ""
    
    if (-not (Build-Package)) {
        Write-ErrorMsg "Build failed. Stopping."
        return $false
    }
    
    Write-Success "Full build complete!"
    return $true
}

function Release-Prepare {
    Write-Header "Release Checklist"
    
    Write-Host ""
    Write-Host "Pre-release checklist:" -ForegroundColor $Colors.Warning
    Write-Host ""
    Write-Host "  [ ] Update version in pyproject.toml"
    Write-Host "  [ ] Update docs/changelog.md"
    Write-Host "  [ ] Run full build workflow"
    Write-Host "  [ ] Verify all generated files"
    Write-Host "  [ ] Create git tag: git tag -a vX.X.X -m 'Release...'"
    Write-Host "  [ ] Push tag: git push origin vX.X.X"
    Write-Host ""
    Write-Host ""
    Write-Host "Upload to PyPI:" -ForegroundColor $Colors.Warning
    Write-Host ""
    Write-Host "  1) Verify package:"
    Write-Host "     twine check dist/*"
    Write-Host ""
    Write-Host "  2) Upload to Test PyPI (optional):"
    Write-Host "     twine upload --repository testpypi dist/*"
    Write-Host ""
    Write-Host "  3) Upload to PyPI (official):"
    Write-Host "     twine upload dist/*"
    Write-Host ""
    Write-Host "  4) Create GitHub Release:"
    Write-Host "     https://github.com/mrtinhnguyen/NotebookLM2PPT/releases/new"
    Write-Host ""
}

# Execute action
switch ($Action) {
    'menu' { Show-Menu }
    'test' { Test-Setup }
    'run' { Run-Application }
    'build' { Build-Package }
    'exe-single' { Build-Exe-Single }
    'exe-folder' { Build-Exe-Folder }
    'clean' { Clean-Build }
    'full' { Full-Build }
    'release' { Release-Prepare }
    default { Show-Menu }
}

Write-Host ""
