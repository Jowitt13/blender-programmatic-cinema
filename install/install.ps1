<#
.SYNOPSIS
  Cross-agent installer for blender-programmatic-studio (Windows PowerShell).
.EXAMPLE
  .\install\install.ps1
  .\install\install.ps1 -Agent antigravity
  .\install\install.ps1 -Project C:\path\to\my-game-project
  .\install\install.ps1 -Uninstall
#>
param(
    [ValidateSet("all", "antigravity", "claude", "agents", "codex", "opencode", "gemini", "copilot", "cursor")]
    [string]$Agent = "all",
    [string]$Project = "",
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$SkillName = "blender-programmatic-studio"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$Targets = @()
if ($Project) {
    $Targets += (Join-Path $Project ".agents\skills\$SkillName")
} else {
    switch ($Agent) {
        "antigravity" { $Targets += (Join-Path $HOME ".gemini\config\skills\$SkillName") }
        "claude"      { $Targets += (Join-Path $HOME ".claude\skills\$SkillName") }
        { $_ -in @("agents", "codex", "opencode", "gemini", "copilot", "cursor") } {
            $Targets += (Join-Path $HOME ".agents\skills\$SkillName")
        }
        "all" {
            $Targets += (Join-Path $HOME ".gemini\config\skills\$SkillName")
            $Targets += (Join-Path $HOME ".claude\skills\$SkillName")
            $Targets += (Join-Path $HOME ".agents\skills\$SkillName")
        }
    }
}

$Items = @("SKILL.md", "README.md", "README_zh.md", "LICENSE", "CHANGELOG.md", "AGENTS.md", "CLAUDE.md", "adapters", "assets", "examples", "references", "scripts", "tests")

foreach ($Dst in $Targets) {
    $DstFull = [System.IO.Path]::GetFullPath($Dst)
    if ($DstFull.TrimEnd("\") -ieq $RepoRoot.TrimEnd("\")) {
        Write-Host "[SKIP] Destination matches source repository: $DstFull"
        continue
    }
    if ($Uninstall) {
        if (Test-Path $DstFull) {
            Remove-Item -Recurse -Force $DstFull
            Write-Host "[UNINSTALLED] $DstFull"
        } else {
            Write-Host "[NOT_FOUND] $DstFull"
        }
        continue
    }
    if (Test-Path $DstFull) {
        Remove-Item -Recurse -Force $DstFull
    }
    New-Item -ItemType Directory -Force -Path $DstFull | Out-Null
    foreach ($Item in $Items) {
        $Src = Join-Path $RepoRoot $Item
        if (Test-Path $Src) {
            Copy-Item -Recurse -Force $Src (Join-Path $DstFull $Item)
        }
    }
    Get-ChildItem -Recurse -Directory -Force $DstFull | Where-Object { $_.Name -eq "__pycache__" } | Remove-Item -Recurse -Force
    Write-Host "[INSTALLED] $DstFull"
}
