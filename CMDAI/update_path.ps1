$targetPath = $PSScriptRoot
$path = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($path -notlike "*$targetPath*") {
    [Environment]::SetEnvironmentVariable('Path', $path + ';' + $targetPath, 'User')
    Write-Host "Dodano $targetPath do PATH"
} else {
    Write-Host "$targetPath juz jest w PATH"
}
