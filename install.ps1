# SDD Global Installer for Claude Code - Windows PowerShell shim.
# All installer logic lives in install.py. This shim only finds Python >= 3.9 with the same
# order as scripts/find-python.sh (python3, then `py -3`, then python) and runs install.py with
# the same arguments, for example:
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 --yes --claude-home "D:\My Claude"
# This file is ASCII-only so Windows PowerShell 5.1 reads it correctly without a BOM.

$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'install.py'

function Find-SddPython {
    $candidates = @(
        @{ Exe = 'python3'; Pre = @() },
        @{ Exe = 'py';      Pre = @('-3') },
        @{ Exe = 'python';  Pre = @() }
    )
    foreach ($c in $candidates) {
        if (-not (Get-Command $c.Exe -CommandType Application -ErrorAction SilentlyContinue)) { continue }
        $probe = $c.Pre + @('-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)')
        try {
            & $c.Exe @probe *> $null
            if ($LASTEXITCODE -eq 0) { return $c }
        } catch { continue }
    }
    return $null
}

$py = Find-SddPython
if ($null -eq $py) {
    [Console]::Error.WriteLine('[err]   Python 3.9 or later was not found (tried: python3, py -3, python).')
    [Console]::Error.WriteLine('[err]   NOT PROTECTED: nothing was installed, including the secret-handling safeguards.')
    [Console]::Error.WriteLine('[err]   Install Python 3.9+ (https://www.python.org/downloads/windows/) and re-run.')
    exit 1
}

# Native stderr must not become a terminating error under 'Stop' (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
$pyArgs = $py.Pre + @($script) + $args
& $py.Exe @pyArgs
exit $LASTEXITCODE
