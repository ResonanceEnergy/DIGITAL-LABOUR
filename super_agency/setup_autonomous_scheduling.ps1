# Digital Labour Autonomous Operations Scheduler
# Implements scheduled task system for Windows Task Scheduler integration

# Define the scheduled tasks
$tasks = @(
    @{
        Name        = "DIGITAL LABOUR-DailyOperations"
        Description = "Daily Digital Labour operations and portfolio management"
        Command     = "powershell.exe"
        Arguments   = "-ExecutionPolicy Bypass -File `"$PSScriptRoot\autonomous_operations.ps1`""
        Schedule    = "DAILY"
        StartTime   = "06:00"
        User        = $env:USERNAME
    },
    @{
        Name        = "DIGITAL LABOUR-ConductorCycle"
        Description = "Hourly conductor agent orchestration cycle"
        Command     = "python.exe"
        Arguments   = "`"$PSScriptRoot\conductor_agent.py`""
        Schedule    = "HOURLY"
        Interval    = 1
        User        = $env:USERNAME
    },
    @{
        Name        = "DIGITAL LABOUR-OperationsMonitoring"
        Description = "Continuous operations centers monitoring"
        Command     = "python.exe"
        Arguments   = "`"$PSScriptRoot\activate_operations_centers.py`""
        Schedule    = "MINUTE"
        Interval    = 30
        User        = $env:USERNAME
    },
    @{
        Name        = "DIGITAL LABOUR-SystemHealth"
        Description = "System health monitoring and alerts"
        Command     = "python.exe"
        Arguments   = "`"$PSScriptRoot\advanced_monitoring_dashboard.py`""
        Schedule    = "HOURLY"
        Interval    = 2
        User        = $env:USERNAME
    },
    @{
        Name        = "DIGITAL LABOUR-MemoryDoctrine"
        Description = "Memory doctrine maintenance and optimization"
        Command     = "python.exe"
        Arguments   = "`"$PSScriptRoot\memory_doctrine_system.py`""
        Schedule    = "DAILY"
        StartTime   = "02:00"
        User        = $env:USERNAME
    }
)

Write-Host "🤖 Digital Labour Autonomous Scheduling System" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Yellow

# Function to create a scheduled task
function New-ScheduledTaskWrapper {
    param(
        [string]$TaskName,
        [string]$Description,
        [string]$Command,
        [string]$Arguments,
        [string]$Schedule,
        [string]$StartTime = $null,
        [int]$Interval = $null,
        [string]$User
    )

    try {
        # Remove existing task if it exists
        $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($existingTask) {
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
            Write-Host "🔄 Updated existing task: $TaskName" -ForegroundColor Yellow
        }

        # Create new scheduled task
        $action = New-ScheduledTaskAction -Execute $Command -Argument $Arguments
        $principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive

        switch ($Schedule) {
            "DAILY" {
                $trigger = New-ScheduledTaskTrigger -Daily -At $StartTime
            }
            "HOURLY" {
                $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours $Interval)
            }
            "MINUTE" {
                $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes $Interval)
            }
        }

        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        $task = New-ScheduledTask -Action $action -Principal $principal -Trigger $trigger -Settings $settings -Description $Description

        Register-ScheduledTask -TaskName $TaskName -InputObject $task -User $User

        Write-Host "✅ Created scheduled task: $TaskName" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ Failed to create task '$TaskName': $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Create scheduled tasks individually
$createdTasks = 0
$totalTasks = 5

# 1. Daily Operations
$result1 = New-ScheduledTaskWrapper -TaskName "DIGITAL LABOUR-DailyOperations" -Description "Daily Digital Labour operations and portfolio management" -Command "powershell.exe" -Arguments "-ExecutionPolicy Bypass -File `"$PSScriptRoot\autonomous_operations.ps1`"" -Schedule "DAILY" -StartTime "06:00" -User $env:USERNAME
if ($result1) { $createdTasks++ }

# 2. Conductor Cycle
$result2 = New-ScheduledTaskWrapper -TaskName "DIGITAL LABOUR-ConductorCycle" -Description "Hourly conductor agent orchestration cycle" -Command "python.exe" -Arguments "`"$PSScriptRoot\conductor_agent.py`"" -Schedule "HOURLY" -Interval 1 -User $env:USERNAME
if ($result2) { $createdTasks++ }

# 3. Operations Monitoring
$result3 = New-ScheduledTaskWrapper -TaskName "DIGITAL LABOUR-OperationsMonitoring" -Description "Continuous operations centers monitoring" -Command "python.exe" -Arguments "`"$PSScriptRoot\activate_operations_centers.py`"" -Schedule "MINUTE" -Interval 30 -User $env:USERNAME
if ($result3) { $createdTasks++ }

# 4. System Health
$result4 = New-ScheduledTaskWrapper -TaskName "DIGITAL LABOUR-SystemHealth" -Description "System health monitoring and alerts" -Command "python.exe" -Arguments "`"$PSScriptRoot\advanced_monitoring_dashboard.py`"" -Schedule "HOURLY" -Interval 2 -User $env:USERNAME
if ($result4) { $createdTasks++ }

# 5. Memory Doctrine
$result5 = New-ScheduledTaskWrapper -TaskName "DIGITAL LABOUR-MemoryDoctrine" -Description "Memory doctrine maintenance and optimization" -Command "python.exe" -Arguments "`"$PSScriptRoot\memory_doctrine_system.py`"" -Schedule "DAILY" -StartTime "02:00" -User $env:USERNAME
if ($result5) { $createdTasks++ }

# Display results
Write-Host "`n📊 Scheduling Results:" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Gray
Write-Host "✅ Tasks Created: $createdTasks/$totalTasks" -ForegroundColor Green

# List all Digital Labour tasks
Write-Host "`n📋 Active Digital Labour Scheduled Tasks:" -ForegroundColor Cyan
Get-ScheduledTask | Where-Object { $_.TaskName -like "*DIGITAL LABOUR*" } | Format-Table TaskName, State, LastRunTime, NextRunTime

Write-Host "`n🎯 Autonomous Operations System Active!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Yellow
Write-Host "The Digital Labour will now run autonomously according to the schedule above." -ForegroundColor White
Write-Host "Monitor the 'logs' directory for execution results and system status." -ForegroundColor Gray
