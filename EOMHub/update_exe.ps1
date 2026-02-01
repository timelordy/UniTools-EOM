# Kill EOMHub process and copy new EXE
Write-Host "Stopping EOMHub processes..."
Get-Process -Name "EOMHub" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

$source = "C:\Users\anton\EOMTemplateTools\EOMHub\dist\EOMHub.exe"
$dest = "C:\Users\anton\AppData\Roaming\pyRevit\Extensions\EOMTemplateTools.extension\bin\EOMHub.exe"

Write-Host "Copying $source to $dest..."
Copy-Item -Path $source -Destination $dest -Force

$item = Get-Item $dest
Write-Host "Done! File size: $($item.Length) bytes, Last modified: $($item.LastWriteTime)"
