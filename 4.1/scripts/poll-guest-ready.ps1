$vb = 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
$deadline = (Get-Date).AddMinutes(50)
$user = 'labadmin'
$pass = 'REDACTED_LAB_ADMIN'
$ready = $false
while ((Get-Date) -lt $deadline) {
  $state = (& $vb showvminfo MERIDIAN-DC01 --machinereadable | Select-String '^VMState=').ToString().Split('=')[1].Trim('"')
  $ga = (& $vb guestproperty get MERIDIAN-DC01 '/VirtualBox/GuestInfo/OS/Product' 2>$null | Out-String).Trim()
  $ts = Get-Date -Format HH:mm:ss
  Write-Host "[$ts] state=$state ga=$ga"
  if ($ga -match 'Windows' -or $state -eq 'running') {
    $out = & $vb guestcontrol MERIDIAN-DC01 run --exe 'C:\Windows\System32\cmd.exe' --username $user --password $pass --wait-stdout --wait-stderr -- -c 'echo READY' 2>&1 | Out-String
    Write-Host $out
    if ($out -match 'READY') { $ready = $true; break }
    # also try Administrator
    $out2 = & $vb guestcontrol MERIDIAN-DC01 run --exe 'C:\Windows\System32\cmd.exe' --username 'Administrator' --password $pass --wait-stdout --wait-stderr -- -c 'echo READY' 2>&1 | Out-String
    if ($out2 -match 'READY') { $ready = $true; Write-Host 'READY via Administrator'; break }
  }
  Start-Sleep -Seconds 40
}
if ($ready) { 'GUEST_READY' } else { 'STILL_INSTALLING_OR_TIMEOUT' }
