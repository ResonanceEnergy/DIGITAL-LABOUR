#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Digital Labour CPU Maximizer - PowerShell Edition
    Launches multiple processes for maximum CPU utilization

.DESCRIPTION
    This script launches multiple Digital Labour processes in parallel
    to maximize CPU usage and processing throughput.

.PARAMETER Processes
    Number of parallel processes to launch (default: CPU core count)

.PARAMETER Duration
    How long to run the maximization (in minutes, default: 10)

.PARAMETER Mode
    Processing mode: 'maximize', 'balanced', or 'conservative'

.EXAMPLE
    .\cpu_maximizer.ps1 -Processes 8 -Duration 30 -Mode maximize

.NOTES
    Requires PowerShell 7+ for optimal performance
#>

param(
    [int]$Processes = $env:NUMBER_OF_PROCESSORS,
    [int]$Duration = 10,
    [ValidateSet('maximize', 'balanced', 'conservative')]
    [string]$Mode = 'balanced'
)

# Configuration based on mode
$Config = switch ($Mode) {
    'maximize' {
        @{
            Priority = 'High'
            Affinity = 'All'
            BatchSize = $Processes
            DelayBetweenBatches = 0
        }
    }
    'balanced' {
        @{
            Priority = 'AboveNormal'
            Affinity = 'All'
            BatchSize = [math]::Max(1, $Processes / 2)
            DelayBetweenBatches = 1
        }
    }
    'conservative' {
        @{
            Priority = 'Normal'
            Affinity = 'Half'
            BatchSize = [math]::Max(1, $Processes / 4)
            DelayBetweenBatches = 2
        }
    }
}

Write-Host "🔥 Digital Labour CPU Maximizer - PowerShell Edition" -ForegroundColor Red
Write-Host "=" * 60 -ForegroundColor Yellow
Write-Host "Processes: $Processes" -ForegroundColor Cyan
Write-Host "Duration: $Duration minutes" -ForegroundColor Cyan
Write-Host "Mode: $Mode" -ForegroundColor Cyan
Write-Host "Configuration: $($Config | ConvertTo-Json -Compress)" -ForegroundColor Gray
Write-Host ""

# Get script directory
$ScriptDir = Split-Path -Parent $PSCommandPath
$RootDir = Split-Path -Parent $ScriptDir

# Define processes to run
$ProcessConfigs = @(
    @{
        Name = "CPU Maximizer"
        Command = "python"
        Arguments = "$RootDir\cpu_maximizer.py"
        WorkingDirectory = $RootDir
    },
    @{
        Name = "Parallel Orchestrator"
        Command = "python"
        Arguments = "$RootDir\parallel_orchestrator.py"
        WorkingDirectory = $RootDir
    },
    @{
        Name = "Portfolio Intel"
        Command = "python"
        Arguments = "$RootDir\ResonanceEnergy_DIGITAL LABOUR\agents\parallel_portfolio_intel.py"
        WorkingDirectory = "$RootDir\ResonanceEnergy_DIGITAL LABOUR"
    },
    @{
        Name = "AAC Engine"
        Command = "python"
        Arguments = "$RootDir\repos\AAC\aac_engine.py"
        WorkingDirectory = "$RootDir\repos\AAC"
    },
    @{
        Name = "NCL Classifier"
        Command = "python"
        Arguments = "$RootDir\ncl_second_brain\engine\classifier.py"
        WorkingDirectory = "$RootDir\ncl_second_brain"
    },
    @{
        Name = "Daily Brief"
        Command = "python"
        Arguments = "$RootDir\agents\daily_brief.py"
        WorkingDirectory = $RootDir
    }
)

function Start-MaximizedProcess {
    param(
        [string]$Name,
        [string]$Command,
        [string]$Arguments,
        [string]$WorkingDirectory
    )

    try {
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = $Command
        $startInfo.Arguments = $Arguments
        $startInfo.WorkingDirectory = $WorkingDirectory
        $startInfo.UseShellExecute = $false
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $startInfo.CreateNoWindow = $true

        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $startInfo

        # Set process priority
        $process.Start() | Out-Null

        if ($process.Id -and $process.HasExited -eq $false) {
            $process.PriorityClass = $Config.Priority

            # Set CPU affinity if specified
            if ($Config.Affinity -eq 'Half') {
                $cpuCount = [Environment]::ProcessorCount
                $affinity = [math]::Pow(2, $cpuCount / 2) - 1
                $process.ProcessorAffinity = [IntPtr]$affinity
            }

            Write-Host "✅ Started $Name (PID: $($process.Id))" -ForegroundColor Green
            return $process
        } else {
            Write-Host "❌ Failed to start $Name" -ForegroundColor Red
            return $null
        }
    }
    catch {
        Write-Host "❌ Error starting $Name: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

function Stop-ProcessGracefully {
    param([System.Diagnostics.Process]$Process, [string]$Name)

    if ($Process -and !$Process.HasExited) {
        try {
            $Process.Kill($true)
            $Process.WaitForExit(5000)
            Write-Host "🛑 Stopped $Name (PID: $($Process.Id))" -ForegroundColor Yellow
        }
        catch {
            Write-Host "⚠️  Failed to stop $Name gracefully" -ForegroundColor Yellow
        }
    }
}

# Main execution
$RunningProcesses = @()
$StartTime = Get-Date
$EndTime = $StartTime.AddMinutes($Duration)

Write-Host "🚀 Launching processes..." -ForegroundColor Green

# Launch processes in batches
$BatchNumber = 1
$TotalLaunched = 0

while ((Get-Date) -lt $EndTime -and $TotalLaunched -lt ($Processes * 2)) {
    Write-Host "`n📦 Batch $BatchNumber (Target: $($Config.BatchSize) processes)" -ForegroundColor Blue

    $BatchProcesses = @()
    $LaunchedInBatch = 0

    foreach ($config in $ProcessConfigs) {
        if ($LaunchedInBatch -ge $Config.BatchSize) { break }

        # Check if we already have this process type running
        $existing = $RunningProcesses | Where-Object { $_.Name -eq $config.Name -and !$_.Process.HasExited }
        if ($existing) { continue }

        $process = Start-MaximizedProcess @config
        if ($process) {
            $BatchProcesses += @{ Name = $config.Name; Process = $process }
            $LaunchedInBatch++
            $TotalLaunched++
        }

        # Small delay between process starts
        Start-Sleep -Milliseconds 500
    }

    $RunningProcesses += $BatchProcesses

    # Clean up finished processes
    $RunningProcesses = $RunningProcesses | Where-Object { !$_.Process.HasExited }

    Write-Host "📊 Running processes: $($RunningProcesses.Count)" -ForegroundColor Cyan

    # Wait before next batch
    if ($Config.DelayBetweenBatches -gt 0) {
        Write-Host "⏳ Waiting $($Config.DelayBetweenBatches)s before next batch..." -ForegroundColor Gray
        Start-Sleep -Seconds $Config.DelayBetweenBatches
    }

    $BatchNumber++
}

# Monitor processes during runtime
Write-Host "`n📊 Monitoring phase..." -ForegroundColor Blue

while ((Get-Date) -lt $EndTime) {
    $remaining = $EndTime - (Get-Date)
    Write-Host "⏰ Time remaining: $($remaining.TotalMinutes.ToString("F1")) minutes" -ForegroundColor Cyan

    # Check process health
    $healthy = 0
    $crashed = 0

    foreach ($procInfo in $RunningProcesses) {
        if ($procInfo.Process.HasExited) {
            $crashed++
            Write-Host "💥 $($procInfo.Name) crashed (Exit code: $($procInfo.Process.ExitCode))" -ForegroundColor Red
        } else {
            $healthy++
        }
    }

    Write-Host "💚 Healthy processes: $healthy, Crashed: $crashed" -ForegroundColor Gray

    # Restart crashed processes if in maximize mode
    if ($Mode -eq 'maximize' -and $crashed -gt 0) {
        Write-Host "🔄 Restarting crashed processes..." -ForegroundColor Yellow
        foreach ($config in $ProcessConfigs) {
            $existing = $RunningProcesses | Where-Object { $_.Name -eq $config.Name -and !$_.Process.HasExited }
            if (!$existing) {
                $process = Start-MaximizedProcess @config
                if ($process) {
                    $RunningProcesses += @{ Name = $config.Name; Process = $process }
                }
            }
        }
    }

    Start-Sleep -Seconds 30
}

# Cleanup
Write-Host "`n🧹 Cleaning up processes..." -ForegroundColor Yellow

foreach ($procInfo in $RunningProcesses) {
    Stop-ProcessGracefully -Process $procInfo.Process -Name $procInfo.Name
}

$TotalRuntime = (Get-Date) - $StartTime

# Final statistics
Write-Host "`n📊 Final Statistics:" -ForegroundColor Green
Write-Host "   Total Runtime: $($TotalRuntime.TotalMinutes.ToString("F1")) minutes" -ForegroundColor White
Write-Host "   Processes Launched: $TotalLaunched" -ForegroundColor White
Write-Host "   Final Running Count: $($RunningProcesses.Count)" -ForegroundColor White
Write-Host "   CPU Cores Utilized: $Processes" -ForegroundColor White
Write-Host "   Mode: $Mode" -ForegroundColor White

Write-Host "`n🎯 CPU maximization complete!" -ForegroundColor Green