#Requires -Version 5.1
<#
.SYNOPSIS
  Install official Qianfan CLI in a persistent Windows environment.
.DESCRIPTION
  Follows https://aipe-dragonboat.cdn.bcebos.com/qianfan-cli/docs/guide.md
  Without switches: install and print version ONLY.
  -Login: interactive browser authorization on this machine.
  -ConnectSkills: confirm and install Qianfan Agent Skills on this machine.
  NEVER run this with private credentials in public GitHub Actions logs.
#>
[CmdletBinding()]
param(
    [switch]$Login,
    [switch]$ConnectSkills
)
$ErrorActionPreference = 'Stop'
$nodePath = Get-Command node -ErrorAction SilentlyContinue
$npmPath = Get-Command npm -ErrorAction SilentlyContinue
if (!$nodePath -or !$npmPath) {
    throw "Node.js and npm must be installed first (Node.js >=16)."
}
$nodeText = (& node --version).Trim()
if ($nodeText -notmatch '^v(\d+)\.') { throw "Unable to detect Node.js version." }
if ([int]$Matches[1] -lt 16) { throw "Node.js >=16 required; found $nodeText" }
& npm config set registry https://registry.npmjs.org/
if ($LASTEXITCODE -ne 0) { throw "npm registry setup failed" }
& npm i '@baiducloud/qianfan-cli@latest' -g
if ($LASTEXITCODE -ne 0) { throw "Qianfan CLI npm installation failed" }
& qianfan --version
if ($LASTEXITCODE -ne 0) { throw "Qianfan version check failed" }
if ($Login) {
    Write-Host "Complete the browser authorization personally. Never share a token."
    & qianfan auth login
    if ($LASTEXITCODE -ne 0) { throw "Qianfan login failed" }
    & qianfan auth status
    if ($LASTEXITCODE -ne 0) { throw "Qianfan account authorization not confirmed" }
}
if ($ConnectSkills) {
    & qianfan +connect --dry-run
    if ($LASTEXITCODE -ne 0) { throw "Qianfan Skills preview failed" }
    & qianfan +connect --yes
    if ($LASTEXITCODE -ne 0) { throw "Qianfan Skills installation failed" }
    & qianfan +connect list
    if ($LASTEXITCODE -ne 0) { throw "Qianfan Skills list failed" }
}
Write-Host "CLI installed on this persistent machine."
if (!$Login) { Write-Host "Account authorization pending: qianfan auth login" }
if (!$ConnectSkills) { Write-Host "Skills pending: qianfan +connect --dry-run ; qianfan +connect --yes" }
