param([string]$MacAddress = "58:11:22:4d:ef:8a")
$mac = $MacAddress -replace '[:-]', ''
$macBytes = [byte[]] -split ($mac -replace '..', '0x$& ')
$packet = [byte[]](, 0xFF * 6)
for ($i = 0; $i -lt 16; $i++) { $packet += $macBytes }
$client = New-Object System.Net.Sockets.UdpClient
$client.Connect(([System.Net.IPAddress]::Parse("192.168.0.255")), 9)
$client.Send($packet, $packet.Length) | Out-Null
$client.Close()
Write-Output "Magic packet enviado a $MacAddress via 192.168.0.255"