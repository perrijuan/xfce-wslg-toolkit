[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$setup = Join-Path $repo 'windows/Setup-Windows.ps1'
$root = Join-Path $PSScriptRoot ('.scratch-' + [guid]::NewGuid().ToString('N'))
function Assert-True($Condition, [string]$Message) {
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}
function Invoke-Setup([hashtable]$Options) {
    $output = @(& $setup @Options)
    Assert-True ($output.Count -eq 1 -and $output[0] -is [string]) 'success emits exactly one JSON string'
    return ($output[0] | ConvertFrom-Json)
}
try {
    $focus = [IO.File]::ReadAllText((Join-Path $repo 'windows/Focus-Xfce.ps1'))
    Assert-True ($focus.Contains('StartsWith("Xfce WSL")')) 'portable Xfce WSL focus prefix'
    Assert-True ($focus.Contains('ProcessName=="msrdc"')) 'focus remains limited to msrdc'
    Write-Output 'PASS focus title and msrdc guard'
    New-Item -ItemType Directory -Path $root | Out-Null
    $profile = Join-Path $root 'test profile'
    $target = Join-Path $root 'helper files'
    $options = @{TargetDirectory=$target; UserProfilePath=$profile; Confirm=$false}
    $result = Invoke-Setup $options
    Assert-True ($result.changed -and $result.applied) 'first install is changed and applied'
    Assert-True ([IO.Path]::IsPathRooted($result.windows_helper_dir)) 'native helper path'
    Assert-True ($result.windows_helper_dir -eq $target) 'helper path matches target'
    Assert-True (Test-Path -LiteralPath $result.powershell_windows -PathType Leaf) 'native PowerShell exists'
    foreach ($name in @('clipboard-host.ps1','Focus-Xfce.ps1')) {
        Assert-True ((Get-FileHash -LiteralPath (Join-Path $target $name)).Hash -eq (Get-FileHash -LiteralPath (Join-Path $repo "windows/$name")).Hash) "exact helper copy: $name"
    }
    $ini = [IO.File]::ReadAllText((Join-Path $profile '.wslgconfig'))
    Assert-True ($ini -match '(?m)^\[system-distro-env\]\r?$') 'WSLg environment section'
    Assert-True ($ini -match '(?m)^WESTON_RDP_MONITOR_REFRESH_RATE=144\r?$') 'default target 144'
    Assert-True ($ini -notmatch '(?m)^\s*#') 'no hash INI comments'
    Write-Output 'PASS first install, helper copies, and JSON contract'
    $beforeTime = (Get-Item -LiteralPath (Join-Path $profile '.wslgconfig')).LastWriteTimeUtc
    $again = Invoke-Setup $options
    Assert-True (-not $again.changed -and -not $again.applied) 'idempotent rerun performs no writes'
    Assert-True ((Get-Item -LiteralPath (Join-Path $profile '.wslgconfig')).LastWriteTimeUtc -eq $beforeTime) 'unchanged config timestamp'
    Assert-True (@(Get-ChildItem -LiteralPath $root -Filter '*.bak-*' -Recurse).Count -eq 0) 'no unnecessary backups'
    Write-Output 'PASS idempotent rerun'
    $original = "; keep this comment`r`n[system-distro-env]`r`nCUSTOM_VALUE=unchanged`r`nWESTON_RDP_MONITOR_REFRESH_RATE=60`r`n[other-section]`r`nanswer=42`r`nWESTON_RDP_MONITOR_REFRESH_RATE=30`r`n"
    $iniPath = Join-Path $profile '.wslgconfig'
    [IO.File]::WriteAllText($iniPath, $original)
    $helperPath = Join-Path $target 'Focus-Xfce.ps1'
    [IO.File]::WriteAllText($helperPath, 'previous helper')
    $updated = Invoke-Setup $options
    Assert-True ($updated.changed -and $updated.applied) 'update applied'
    $merged = [IO.File]::ReadAllText($iniPath)
    Assert-True ($merged -eq $original.Replace('WESTON_RDP_MONITOR_REFRESH_RATE=60','WESTON_RDP_MONITOR_REFRESH_RATE=144')) 'only target INI setting changes'
    $iniBackups = @(Get-ChildItem -LiteralPath $profile -Filter '.wslgconfig.bak-*')
    Assert-True ($iniBackups.Count -eq 1) 'config backed up once'
    Assert-True ([IO.File]::ReadAllText($iniBackups[0].FullName) -eq $original) 'original config backed up'
    $helperBackups = @(Get-ChildItem -LiteralPath $target -Filter 'Focus-Xfce.ps1.bak-*')
    Assert-True ($helperBackups.Count -eq 1) 'helper backed up once'
    Assert-True ([IO.File]::ReadAllText($helperBackups[0].FullName) -eq 'previous helper') 'original helper backed up'
    Write-Output 'PASS INI preservation and backups before replacement'
    $dryRoot = Join-Path $root 'dry-run'
    $dryTarget = Join-Path $dryRoot 'helpers'
    $dryProfile = Join-Path $dryRoot 'profile'
    $dry = Invoke-Setup @{TargetDirectory=$dryTarget; UserProfilePath=$dryProfile; WhatIf=$true}
    Assert-True ($dry.changed -and -not $dry.applied) 'WhatIf reports planned but unapplied changes'
    Assert-True (-not (Test-Path -LiteralPath $dryRoot)) 'WhatIf never creates directories or files'
    $native = @(& (Join-Path $PSHOME 'powershell.exe') -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $setup -TargetDirectory $dryTarget -UserProfilePath $dryProfile -WhatIf)
    Assert-True ($LASTEXITCODE -eq 0 -and $native.Count -eq 1) 'native WhatIf stdout is JSON only'
    $nativeResult = $native[0] | ConvertFrom-Json
    Assert-True (-not $nativeResult.applied) 'native WhatIf does not apply'
    $snapshot = @(Get-ChildItem -LiteralPath $root -File -Recurse | ForEach-Object { $_.FullName + ':' + (Get-FileHash -LiteralPath $_.FullName).Hash + ':' + $_.LastWriteTimeUtc.Ticks })
    $dryExisting = Invoke-Setup @{TargetDirectory=$target; UserProfilePath=$profile; RefreshRate=90; WhatIf=$true}
    $afterSnapshot = @(Get-ChildItem -LiteralPath $root -File -Recurse | ForEach-Object { $_.FullName + ':' + (Get-FileHash -LiteralPath $_.FullName).Hash + ':' + $_.LastWriteTimeUtc.Ticks })
    Assert-True ($dryExisting.changed -and -not $dryExisting.applied) 'existing WhatIf plans update'
    Assert-True (($snapshot -join "`n") -eq ($afterSnapshot -join "`n")) 'existing WhatIf leaves files and timestamps unchanged'
    Write-Output 'PASS WhatIf no writes and native JSON-only stdout'
    foreach ($badRate in @(0,145)) {
        $failed = $false
        try { $null = & $setup -TargetDirectory $dryTarget -UserProfilePath $dryProfile -RefreshRate $badRate } catch { $failed = $true }
        Assert-True $failed "reject refresh $badRate"
        Assert-True (-not (Test-Path -LiteralPath $dryRoot)) 'invalid refresh never writes'
    }
    foreach ($rate in @(1,144)) {
        $valid = Invoke-Setup @{TargetDirectory=$target; UserProfilePath=$profile; RefreshRate=$rate; WhatIf=$true}
        Assert-True (-not $valid.applied) "accept refresh boundary $rate"
    }
    Write-Output 'PASS refresh validation 1..144'
    $fixtures = @(
        @{Before="[other]`nvalue=keep"; After="[other]`nvalue=keep`n[system-distro-env]`nWESTON_RDP_MONITOR_REFRESH_RATE=144`n"},
        @{Before="[system-distro-env]`nA=1`n[other]`nB=2`n"; After="[system-distro-env]`nA=1`nWESTON_RDP_MONITOR_REFRESH_RATE=144`n[other]`nB=2`n"},
        @{Before="[system-distro-env]"; After="[system-distro-env]`r`nWESTON_RDP_MONITOR_REFRESH_RATE=144`r`n"},
        @{Before="; comment`n[SYSTEM-DISTRO-ENV]`n  WESTON_RDP_MONITOR_REFRESH_RATE = 60 ; keep`nA=one=two`n"; After="; comment`n[SYSTEM-DISTRO-ENV]`n  WESTON_RDP_MONITOR_REFRESH_RATE = 144 ; keep`nA=one=two`n"}
    )
    foreach ($fixture in $fixtures) {
        [IO.File]::WriteAllText($iniPath, $fixture.Before)
        $null = Invoke-Setup $options
        Assert-True ([IO.File]::ReadAllText($iniPath) -ceq $fixture.After) 'INI merge edge case preserves content and newlines'
        $repeat = Invoke-Setup $options
        Assert-True (-not $repeat.changed) 'INI edge case is idempotent'
    }
    Write-Output 'PASS INI insertion, LF/no-final-newline, case, spacing, comments'
    $shortcutOptions = @{TargetDirectory=$target; UserProfilePath=$profile; CreateShortcut=$true; Distro='Example Distro'; LinuxUser='example'; LinuxLauncher='/home/example/My Apps/xfce-wsl'; Confirm=$false}
    $shortcutDry = $shortcutOptions.Clone()
    $shortcutDry.WhatIf = $true
    $dryShortcut = Invoke-Setup $shortcutDry
    Assert-True ($dryShortcut.changed -and -not $dryShortcut.applied) 'shortcut WhatIf plans only'
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $profile 'Desktop'))) 'shortcut WhatIf creates no Desktop'
    $shortcutResult = Invoke-Setup $shortcutOptions
    Assert-True $shortcutResult.applied 'shortcut install applied'
    $linkPath = Join-Path $profile 'Desktop/Xfce WSL.lnk'
    Assert-True (Test-Path -LiteralPath $linkPath -PathType Leaf) 'shortcut in isolated profile Desktop'
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($linkPath)
    Assert-True ($link.TargetPath -ieq (Join-Path $env:SystemRoot 'System32/wsl.exe')) 'shortcut targets wsl.exe directly'
    Assert-True ($link.Arguments -ceq '--distribution "Example Distro" --user "example" --exec "/home/example/My Apps/xfce-wsl"') 'explicit safely quoted distro, user, launcher'
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($link)
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell)
    $sameShortcut = Invoke-Setup $shortcutOptions
    Assert-True (-not $sameShortcut.changed) 'shortcut rerun is idempotent'
    $shortcutOptions.LinuxLauncher = '/home/example/other-launcher'
    $null = Invoke-Setup $shortcutOptions
    Assert-True (@(Get-ChildItem -LiteralPath (Split-Path $linkPath -Parent) -Filter 'Xfce WSL.lnk.bak-*').Count -eq 1) 'shortcut backup before replacement'
    Write-Output 'PASS isolated shortcut, direct wsl.exe arguments, rerun, backup'
    foreach ($badShortcut in @(
        @{CreateShortcut=$true},
        @{CreateShortcut=$true; Distro='Example'; LinuxUser='example'; LinuxLauncher='relative-launcher'},
        @{CreateShortcut=$true; Distro="Example`nInjected"; LinuxUser='example'; LinuxLauncher='/bin/true'}
    )) {
        $badShortcut.TargetDirectory = $dryTarget
        $badShortcut.UserProfilePath = $dryProfile
        $failed = $false
        try { $null = & $setup @badShortcut } catch { $failed = $true }
        Assert-True $failed 'invalid shortcut rejected before applying any files'
        Assert-True (-not (Test-Path -LiteralPath $dryRoot)) 'invalid shortcut never writes'
    }
    Write-Output 'PASS shortcut validation before writes'
    $oldLocal = $env:LOCALAPPDATA
    $oldProfile = $env:USERPROFILE
    try {
        $env:LOCALAPPDATA = Join-Path $root 'isolated local app data'
        $env:USERPROFILE = Join-Path $root 'isolated default profile'
        $defaults = Invoke-Setup @{Confirm=$false}
        Assert-True ($defaults.windows_helper_dir -eq (Join-Path $env:LOCALAPPDATA 'XfceWSLToolkit')) 'default per-user target'
        Assert-True (Test-Path -LiteralPath (Join-Path $env:USERPROFILE '.wslgconfig')) 'default current-user profile'
        Assert-True (-not (Test-Path -LiteralPath (Join-Path $env:USERPROFILE 'Desktop'))) 'no shortcut without opt-in'
    } finally {
        $env:LOCALAPPDATA = $oldLocal
        $env:USERPROFILE = $oldProfile
    }
    Write-Output 'PASS default per-user paths with isolated environment'
} finally {
    if (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force }
}
Write-Output 'All Windows integration tests passed.'
