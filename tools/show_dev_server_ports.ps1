param(
  [switch]$OnlyConflicts
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$aiAppFolderName = -join @([char]0xC571, [char]0x0020, [char]0xC81C, [char]0xC791)
$aiAppRoot = Join-Path "C:\AI" $aiAppFolderName
$monocutRoot = Join-Path $aiAppRoot "monocut"
$monocutMobileRoot = Join-Path $aiAppRoot "monocut-mobile"

$registry = @(
  [pscustomobject]@{ App = "InvestmentResearchOS"; Role = "research-api"; Port = 8001; Root = "C:\Users\lib20\InvestmentJournalApp" },
  [pscustomobject]@{ App = "InvestmentResearchOS"; Role = "mobile-api"; Port = 8010; Root = "C:\Users\lib20\InvestmentJournalApp" },
  [pscustomobject]@{ App = "InvestmentResearchOS"; Role = "mobile-api-fallback"; Port = 8020; Root = "C:\Users\lib20\InvestmentJournalApp" },
  [pscustomobject]@{ App = "InvestmentResearchOS"; Role = "react-console"; Port = 5173; Root = "C:\Users\lib20\InvestmentJournalApp" },
  [pscustomobject]@{ App = "InvestmentResearchOS"; Role = "mobile-web"; Port = 8082; Root = "C:\Users\lib20\InvestmentJournalApp" },
  [pscustomobject]@{ App = "SportsAnalysis"; Role = "api"; Port = 8101; Root = "C:\Users\lib20\projects\sports-analysis-platform" },
  [pscustomobject]@{ App = "SportsAnalysis"; Role = "web"; Port = 8181; Root = "C:\Users\lib20\projects\sports-analysis-platform" },
  [pscustomobject]@{ App = "SportsAnalysisWorktree"; Role = "api"; Port = 8102; Root = "C:\Users\lib20\projects\sports-analysis-platform-worktree" },
  [pscustomobject]@{ App = "SportsAnalysisWorktree"; Role = "web"; Port = 8182; Root = "C:\Users\lib20\projects\sports-analysis-platform-worktree" },
  [pscustomobject]@{ App = "FamilyTranslator"; Role = "api"; Port = 8201; Root = "C:\Projects\FamilyTranslatorApp" },
  [pscustomobject]@{ App = "FamilyTranslator"; Role = "web"; Port = 8281; Root = "C:\Projects\FamilyTranslatorApp" },
  [pscustomobject]@{ App = "FamilyTranslator"; Role = "expo"; Port = 8282; Root = "C:\Projects\FamilyTranslatorApp" },
  [pscustomobject]@{ App = "FamilyNews"; Role = "api"; Port = 8301; Root = "C:\Projects\FamilyNewsApp" },
  [pscustomobject]@{ App = "FamilyNews"; Role = "web"; Port = 8381; Root = "C:\Projects\FamilyNewsApp" },
  [pscustomobject]@{ App = "FamilyNews"; Role = "expo"; Port = 8382; Root = "C:\Projects\FamilyNewsApp" },
  [pscustomobject]@{ App = "KoreaTravel"; Role = "web"; Port = 8481; Root = "C:\Projects\KoreaTravel_RN_review" },
  [pscustomobject]@{ App = "KoreaTravel"; Role = "expo"; Port = 8482; Root = "C:\Projects\KoreaTravel_RN_review" },
  [pscustomobject]@{ App = "Monocut Web"; Role = "web"; Port = 8501; Root = $monocutRoot },
  [pscustomobject]@{ App = "Monocut Mobile"; Role = "expo"; Port = 8582; Root = $monocutMobileRoot }
)

function Get-PortListeners {
  param([int]$Port)

  $listeners = @()
  $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  foreach ($connection in $connections) {
    if (-not $connection.OwningProcess -or $connection.OwningProcess -le 0) {
      continue
    }
    $listeners += [pscustomobject]@{
      Address = $connection.LocalAddress
      Port = $connection.LocalPort
      Pid = $connection.OwningProcess
    }
  }
  if ($listeners.Count -gt 0) {
    return @($listeners | Sort-Object Address, Pid -Unique)
  }

  $netstatCommand = Get-Command netstat -ErrorAction SilentlyContinue
  if ($null -eq $netstatCommand) {
    return @($listeners | Sort-Object Address, Port -Unique)
  }

  $netstatLines = & $netstatCommand.Source -ano 2>$null | Select-String -Pattern "[:.]$Port\s" | Select-String -Pattern "LISTENING"
  foreach ($line in $netstatLines) {
    $parts = ($line.Line.Trim() -split "\s+") | Where-Object { $_ }
    if ($parts.Count -lt 5) {
      continue
    }
    $localAddress = $parts[1]
    $ownerText = $parts[-1]
    if ($localAddress -notmatch "[:.]$Port$") {
      continue
    }
    $ownerProcessId = 0
    if ([int]::TryParse($ownerText, [ref]$ownerProcessId) -and $ownerProcessId -gt 0) {
      $listeners += [pscustomobject]@{
        Address = $localAddress
        Port = $Port
        Pid = $ownerProcessId
      }
    }
  }

  return @($listeners | Sort-Object Address, Port -Unique)
}

$rows = foreach ($entry in $registry) {
  $listeners = @(Get-PortListeners -Port $entry.Port)
  $pids = @($listeners | Select-Object -ExpandProperty Pid -Unique)
  $processNames = foreach ($processId in $pids) {
    try {
      $process = Get-Process -Id $processId -ErrorAction Stop
      "$processId/$($process.ProcessName)"
    } catch {
      "$processId/unknown"
    }
  }
  $conflict = $pids.Count -gt 1
  [pscustomobject]@{
    App = $entry.App
    Role = $entry.Role
    Port = $entry.Port
    Listening = ($pids.Count -gt 0)
    Conflict = $conflict
    Process = ($processNames -join ", ")
    RootExists = (Test-Path -LiteralPath $entry.Root)
    Root = $entry.Root
  }
}

if ($OnlyConflicts) {
  $rows = @($rows | Where-Object { $_.Conflict })
  if ($rows.Count -eq 0) {
    Write-Host "예약 포트 충돌 없음"
  }
}

$rows | Sort-Object Port, App | Format-Table -AutoSize

$conflicts = @($rows | Where-Object { $_.Conflict })
if ($conflicts.Count -gt 0) {
  Write-Host ""
  Write-Warning "Port conflicts detected: $($conflicts.Count). Stop duplicate processes, then restart each app on its reserved port."
  exit 2
}
