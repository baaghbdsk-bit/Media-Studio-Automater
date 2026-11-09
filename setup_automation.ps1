[CmdletBinding(SupportsShouldProcess = $true)]
param()

$ErrorActionPreference = "Stop"

$projectDir = $PSScriptRoot
$daemonScript = Join-Path $projectDir "src\automation_daemon.py"
$localVenvPython = Join-Path $projectDir "venv\Scripts\python.exe"
$siblingVenvPython = "E:\X-Post-Automater\venv\Scripts\python.exe"
if (Test-Path -LiteralPath $localVenvPython -PathType Leaf) {
    $pythonPath = $localVenvPython
} elseif (Test-Path -LiteralPath $siblingVenvPython -PathType Leaf) {
    $pythonPath = $siblingVenvPython
} else {
    $python = Get-Command python.exe -ErrorAction Stop
    $pythonPath = $python.Source
}

if (-not (Test-Path -LiteralPath $daemonScript -PathType Leaf)) {
    throw "Automation daemon not found: $daemonScript"
}

& $pythonPath -c "import schedule" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "The selected Python environment is missing the 'schedule' package. Install dependencies with: `"$pythonPath`" -m pip install -r `"$projectDir\requirements.txt`""
}

$principal = New-ScheduledTaskPrincipal `
    -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$tasks = @(
    @{
        Name = "Media Studio - Reels Shorts"
        Time = "17:15"
        Action = "schedule-reels-shorts"
        Description = "Generate and publish the daily YouTube Shorts and Instagram Reels broadcast."
    },
    @{
        Name = "Media Studio - Reels Shorts 2"
        Time = "19:15"
        Action = "schedule-reels-shorts"
        Description = "Generate and publish the second daily YouTube Shorts and Instagram Reels broadcast."
    },
    @{
        Name = "Media Studio - Explainer"
        Time = "21:15"
        Action = "schedule-explainer"
        Description = "Run the alternate-day long-form explainer workflow."
    }
)

foreach ($task in $tasks) {
    $time = [TimeSpan]::ParseExact($task.Time, "hh\:mm", [Globalization.CultureInfo]::InvariantCulture)
    $triggerTime = [datetime]::Today.Add($time)
    $trigger = New-ScheduledTaskTrigger -Daily -At $triggerTime
    $action = New-ScheduledTaskAction `
        -Execute $pythonPath `
        -Argument ('"{0}" {1}' -f $daemonScript, $task.Action) `
        -WorkingDirectory $projectDir

    if ($PSCmdlet.ShouldProcess($task.Name, "Register daily task at $($task.Time)")) {
        Register-ScheduledTask `
            -TaskName $task.Name `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -Principal $principal `
            -Description $task.Description `
            -Force | Out-Null
        Write-Host "[OK] $($task.Name) at $($task.Time) (local time)"
    }
}

if (-not $WhatIfPreference) {
    Write-Host "Tasks run as $($principal.UserId) and write run details to output\automation.log."
    Write-Host "Keep the Windows account signed in. Wake-from-sleep depends on Windows power settings."
}
