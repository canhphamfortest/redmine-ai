# Manual cleanup script for old log files (PowerShell)
# Usage: .\cleanup_logs_manual.ps1 [-LogDir "path"] [-RetentionDays 30] [-DryRun]

param(
    [string]$LogDir = ".\logs",
    [int]$RetentionDays = 30,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Log Cleanup Script (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Log directory: $LogDir"
Write-Host "Retention: $RetentionDays days"
Write-Host "Dry run: $DryRun"
Write-Host "============================================" -ForegroundColor Cyan

# Calculate cutoff date
$CutoffDate = (Get-Date).AddDays(-$RetentionDays)
Write-Host "Deleting files older than: $($CutoffDate.ToString('yyyy-MM-dd'))" -ForegroundColor Yellow

# Find old log files
# Parse date from filename (e.g., backend.log.2026-02-11) instead of LastWriteTime
$OldFiles = Get-ChildItem -Path $LogDir -Recurse -File | 
    Where-Object { 
        if ($_.Name -match '\.log\.(\d{4}-\d{2}-\d{2})') {
            # Parse date from filename for time-rotated logs
            try {
                $FileDate = [DateTime]::ParseExact($Matches[1], 'yyyy-MM-dd', $null)
                return $FileDate -lt $CutoffDate
            } catch {
                # If parse fails, fall back to LastWriteTime
                return $_.LastWriteTime -lt $CutoffDate
            }
        } elseif ($_.Name -match '\.log\.\d+$') {
            # For numbered rotation files, use LastWriteTime
            return $_.LastWriteTime -lt $CutoffDate
        }
        return $false
    }

if ($OldFiles.Count -eq 0) {
    Write-Host "`nNo files to delete." -ForegroundColor Green
} else {
    $TotalSizeMB = [math]::Round(($OldFiles | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
    
    Write-Host "`nFound $($OldFiles.Count) files to delete (Total: $TotalSizeMB MB):" -ForegroundColor Yellow
    
    if ($DryRun) {
        Write-Host "`nDRY RUN - Files that would be deleted:" -ForegroundColor Magenta
        $OldFiles | Select-Object Name, LastWriteTime, @{Name="SizeMB";Expression={[math]::Round($_.Length/1MB, 2)}} | 
            Format-Table -AutoSize
    } else {
        Write-Host "`nDeleting files..." -ForegroundColor Red
        $OldFiles | ForEach-Object {
            Write-Host "  Deleting: $($_.Name)" -ForegroundColor DarkGray
            Remove-Item $_.FullName -Force
        }
        Write-Host "`nDeleted $($OldFiles.Count) files ($TotalSizeMB MB freed)" -ForegroundColor Green
    }
}

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "Current log directory size:" -ForegroundColor Cyan
$CurrentSize = (Get-ChildItem -Path $LogDir -Recurse -File | Measure-Object -Property Length -Sum).Sum
$CurrentSizeMB = [math]::Round($CurrentSize / 1MB, 2)
$CurrentSizeGB = [math]::Round($CurrentSize / 1GB, 2)
Write-Host "  $CurrentSizeMB MB ($CurrentSizeGB GB)" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
