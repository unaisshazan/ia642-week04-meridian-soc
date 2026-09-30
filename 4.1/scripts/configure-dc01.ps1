# Lab 4.1 â€” configure MERIDIAN-DC01 after Windows install (run via guestcontrol)
$ErrorActionPreference = 'Stop'
Start-Transcript -Path 'C:\Windows\Temp\meridian-configure.log' -Force

# Disable firewall for lab isolation
netsh advfirewall set allprofiles state off | Out-Null

# Pick internal-network NIC (not the NAT default gateway adapter)
$adapters = @(Get-NetAdapter | Where-Object { $_.Status -ne 'Disabled' } | Sort-Object ifIndex)
Write-Output "Adapters: $($adapters.Name -join ', ')"

$natIf = $null
$labIf = $null
foreach ($a in $adapters) {
  $gw = Get-NetRoute -InterfaceIndex $a.ifIndex -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue
  if ($gw) { $natIf = $a } else { if (-not $labIf) { $labIf = $a } }
}
if (-not $labIf -and $adapters.Count -ge 2) { $labIf = $adapters[-1] }
if (-not $labIf) { $labIf = $adapters[0] }

Write-Output "Lab adapter: $($labIf.Name) ifIndex=$($labIf.ifIndex)"

Get-NetIPAddress -InterfaceIndex $labIf.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
  Where-Object { $_.IPAddress -ne '127.0.0.1' } |
  ForEach-Object {
    Remove-NetIPAddress -InterfaceIndex $_.InterfaceIndex -IPAddress $_.IPAddress -Confirm:$false -ErrorAction SilentlyContinue
  }
Get-NetRoute -InterfaceIndex $labIf.ifIndex -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue |
  Remove-NetRoute -Confirm:$false -ErrorAction SilentlyContinue

New-NetIPAddress -InterfaceIndex $labIf.ifIndex -IPAddress 10.77.0.10 -PrefixLength 24 -ErrorAction Stop
Set-DnsClientServerAddress -InterfaceIndex $labIf.ifIndex -ServerAddresses 127.0.0.1

$needReboot = $false
if ($env:COMPUTERNAME -ne 'MERIDIAN-DC01') {
  Rename-Computer -NewName 'MERIDIAN-DC01' -Force
  $needReboot = $true
}

# Install AD DS role
Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools | Out-Null

$safeMode = ConvertTo-SecureString 'REDACTED_DSRM' -AsPlainText -Force
# Domain Admin password already set on local Administrator / labadmin via unattended

if ($needReboot) {
  # Rename requires reboot before forest promote on some builds; promote after reboot via scheduled task
  $promote = @'
$ErrorActionPreference = "Stop"
Start-Transcript -Path "C:\Windows\Temp\meridian-promote.log" -Force
$sm = ConvertTo-SecureString "REDACTED_DSRM" -AsPlainText -Force
Install-ADDSForest `
  -DomainName "meridian.local" `
  -DomainNetbiosName "MERIDIAN" `
  -SafeModeAdministratorPassword $sm `
  -InstallDns `
  -CreateDnsDelegation:$false `
  -DatabasePath "C:\Windows\NTDS" `
  -LogPath "C:\Windows\NTDS" `
  -SysvolPath "C:\Windows\SYSVOL" `
  -NoRebootOnCompletion:$false `
  -Force
'@
  Set-Content -Path 'C:\Windows\Temp\promote-forest.ps1' -Value $promote -Encoding ASCII
  schtasks /Create /TN MeridianPromote /SC ONSTART /RU SYSTEM /RL HIGHEST /TR "powershell.exe -ExecutionPolicy Bypass -File C:\Windows\Temp\promote-forest.ps1" /F | Out-Null
  Write-Output 'CONFIGURED_REBOOT_THEN_PROMOTE'
  Stop-Transcript
  Restart-Computer -Force
} else {
  Install-ADDSForest `
    -DomainName 'meridian.local' `
    -DomainNetbiosName 'MERIDIAN' `
    -SafeModeAdministratorPassword $safeMode `
    -InstallDns `
    -CreateDnsDelegation:$false `
    -DatabasePath 'C:\Windows\NTDS' `
    -LogPath 'C:\Windows\NTDS' `
    -SysvolPath 'C:\Windows\SYSVOL' `
    -NoRebootOnCompletion:$false `
    -Force
  Write-Output 'PROMOTE_STARTED'
  Stop-Transcript
}
