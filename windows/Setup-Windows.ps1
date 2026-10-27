# Installs per-user helpers. Does not restart WSL or request elevation.
[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='Medium')]
param(
    [string]$TargetDirectory = (Join-Path $env:LOCALAPPDATA 'XfceWSLToolkit'),
    [string]$UserProfilePath = $env:USERPROFILE,
    [ValidateRange(1,144)][int]$RefreshRate = 144,
    [switch]$CreateShortcut,
    [string]$Distro,
    [string]$LinuxUser,
    [string]$LinuxLauncher
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
Set-StrictMode -Version Latest
$TargetDirectory = [IO.Path]::GetFullPath($TargetDirectory)
$UserProfilePath = [IO.Path]::GetFullPath($UserProfilePath)
$powershell = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
$utf8 = New-Object Text.UTF8Encoding($false)

function Merge-RefreshSetting([string]$Text, [int]$Rate) {
    $newline = "`r`n"
    if ($Text.Contains("`n") -and -not $Text.Contains("`r`n")) { $newline = "`n" }
    $lines = New-Object 'System.Collections.Generic.List[string]'
    $inSection = $false
    $sectionFound = $false
    $keyFound = $false
    $insertAt = -1
    foreach ($entry in [regex]::Matches($Text, '[^\r\n]*(?:\r\n|\n|\r|$)')) {
        $line = $entry.Value
        if ($line.Length -eq 0) { continue }
        $body = $line.TrimEnd([char[]]"`r`n")
        $ending = $line.Substring($body.Length)
        if ($body -match '^\s*\[([^\]]+)\]\s*(?:;.*)?$') {
            if ($inSection -and $insertAt -lt 0) { $insertAt = $lines.Count }
            $inSection = $Matches[1] -ieq 'system-distro-env'
            if ($inSection) { $sectionFound = $true }
        } elseif ($inSection -and $body -match '^(\s*WESTON_RDP_MONITOR_REFRESH_RATE\s*=\s*)[^;]*?(\s*(?:;.*)?)$') {
            $line = $Matches[1] + $Rate + $Matches[2] + $ending
            $keyFound = $true
        }
        $lines.Add($line)
    }
    if (-not $keyFound) {
        $setting = "WESTON_RDP_MONITOR_REFRESH_RATE=$Rate$newline"
        if (-not $sectionFound) {
            if ($lines.Count -gt 0 -and -not $lines[$lines.Count-1].EndsWith("`n")) { $lines.Add($newline) }
            if ($Text.Length -eq 0) { $lines.Add("; WSLg presentation target, not guaranteed display FPS.$newline") }
            $lines.Add("[system-distro-env]$newline")
            $lines.Add($setting)
        } else {
            if ($insertAt -lt 0) { $insertAt = $lines.Count }
            if ($insertAt -gt 0 -and -not $lines[$insertAt-1].EndsWith("`n")) { $lines[$insertAt-1] += $newline }
            $lines.Insert($insertAt, $setting)
        }
    }
    return [string]::Concat($lines.ToArray())
}

$plan = New-Object 'System.Collections.Generic.List[object]'
foreach ($name in @('clipboard-host.ps1','Focus-Xfce.ps1')) {
    $source = Join-Path $PSScriptRoot $name
    $destination = Join-Path $TargetDirectory $name
    $bytes = [IO.File]::ReadAllBytes($source)
    if (-not [IO.File]::Exists($destination) -or
        (Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $destination).Hash) {
        $plan.Add(@{Path=$destination; Bytes=$bytes})
    }
}
$configPath = Join-Path $UserProfilePath '.wslgconfig'
$original = ''
if ([IO.File]::Exists($configPath)) { $original = [IO.File]::ReadAllText($configPath) }
$merged = Merge-RefreshSetting $original $RefreshRate
if ($merged -cne $original) { $plan.Add(@{Path=$configPath; Bytes=$utf8.GetBytes($merged)}) }
if ($CreateShortcut) {
    foreach ($value in @($Distro, $LinuxUser, $LinuxLauncher)) {
        if ([string]::IsNullOrWhiteSpace($value) -or $value -match '[\x00-\x1f]') {
            throw '-CreateShortcut requires nonempty -Distro, -LinuxUser, and -LinuxLauncher without control characters.'
        }
    }
    if (-not $LinuxLauncher.StartsWith('/')) { throw '-LinuxLauncher must be an absolute Linux path.' }
    function Quote-WindowsArgument([string]$Value) {
        # CommandLineToArgvW convention: double backslashes preceding quotes/end.
        $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
        $escaped = [regex]::Replace($escaped, '\\+$', '$0$0')
        return '"' + $escaped + '"'
    }
    $desktop = [Environment]::GetFolderPath('DesktopDirectory')
    if ($PSBoundParameters.ContainsKey('UserProfilePath')) { $desktop = Join-Path $UserProfilePath 'Desktop' }
    if ([string]::IsNullOrWhiteSpace($desktop)) { throw 'Cannot resolve the current user Desktop directory.' }
    $shortcutPath = Join-Path $desktop 'Xfce WSL.lnk'
    $shortcutTarget = Join-Path $env:SystemRoot 'System32/wsl.exe'
    $shortcutArgs = '--distribution ' + (Quote-WindowsArgument $Distro) + ' --user ' + (Quote-WindowsArgument $LinuxUser) + ' --exec ' + (Quote-WindowsArgument $LinuxLauncher)
    $shortcutWorkingDirectory = $UserProfilePath
    $shortcutDescription = 'Launch the Xfce WSL desktop (no automatic WSL restart)'
    $shortcutMatches = $false
    if ([IO.File]::Exists($shortcutPath)) {
        $shell = New-Object -ComObject WScript.Shell
        try {
            $link = $shell.CreateShortcut($shortcutPath)
            try {
                $shortcutMatches = $link.TargetPath -ieq $shortcutTarget -and $link.Arguments -ceq $shortcutArgs -and $link.WorkingDirectory -ieq $shortcutWorkingDirectory -and $link.Description -ceq $shortcutDescription -and $link.WindowStyle -eq 7
            } finally { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($link) }
        } finally { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell) }
    }
    if (-not $shortcutMatches) { $plan.Add(@{Path=$shortcutPath; Shortcut=$true}) }
}
$applied = $false
foreach ($change in $plan) {
    # PS5 ShouldProcess writes WhatIf text directly to the host (not stream 6).
    # Report the plan in JSON instead; never enter a write path during WhatIf.
    if ($WhatIfPreference) { continue }
    $approved = $PSCmdlet.ShouldProcess($change.Path, 'Back up if present and install file')
    if (-not $approved) { continue }
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($change.Path)) | Out-Null
    if ([IO.File]::Exists($change.Path)) {
        $backup = $change.Path + '.bak-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ') + '-' + [guid]::NewGuid().ToString('N')
        [IO.File]::Copy($change.Path, $backup, $false)
    }
    if ($change.ContainsKey('Shortcut')) {
        $shell = New-Object -ComObject WScript.Shell
        try {
            $link = $shell.CreateShortcut($change.Path)
            try {
                $link.TargetPath = $shortcutTarget
                $link.Arguments = $shortcutArgs
                $link.WorkingDirectory = $shortcutWorkingDirectory
                $link.Description = $shortcutDescription
                $link.WindowStyle = 7
                $link.Save()
            } finally { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($link) }
        } finally { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell) }
    } else {
        [IO.File]::WriteAllBytes($change.Path, $change.Bytes)
    }
    $applied = $true
}
[pscustomobject]@{
    windows_helper_dir = $TargetDirectory
    powershell_windows = $powershell
    changed = ($plan.Count -gt 0)
    applied = $applied
} | ConvertTo-Json -Compress
