Param(
    [string]$PythonExe = "python"
)
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$Agent = Join-Path $Root "agents/portfolio_maintainer.py"
function Invoke-Py($args) {
    param([string[]]$args)
    $cmds = @($PythonExe, "py", "py -3")
    foreach ($c in $cmds) { try { & $c $args; return } catch {} }
    throw "Python not found; install Python 3 and add to PATH."
}
if (-not (Test-Path $Agent)) { throw "Missing: $Agent" }
Invoke-Py @($Agent)