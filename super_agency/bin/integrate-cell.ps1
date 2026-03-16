Param(
  [Parameter(Mandatory=$true)][string]$Repo,
  [string]$PythonExe = "python",
  [string]$Org = "ResonanceEnergy",
  [switch]$Clone
)
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$Agent = Join-Path $Root "agents/integrate_cell.py"
if (-not (Test-Path $Agent)) { throw "Missing: $Agent" }
$argsList = @($Agent, "--repo", $Repo, "--org", $Org)
if ($Clone) { $argsList += "--clone" }
& $PythonExe @argsList
