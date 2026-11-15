# Which network link is the live server using? Read-only: it changes nothing.
#
#   powershell -ExecutionPolicy Bypass -File scripts\link.ps1
#
# A connection stays on the adapter it was opened on, so plugging a network cable in does not move a
# running server onto it: only connections opened afterwards take the cable (Windows prefers it by itself,
# a lower route metric). So: cable in first, then replace the server (scripts\swap_server.ps1), then run
# this. Leave the Wi-Fi on: if the cable ever fails, the server opens its connections again over it.
$servers = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -match 'reco\.serve' }
if (-not $servers) { "no server running: no python process with reco.serve in its command line"; exit 1 }
$open = 0
foreach ($p in $servers) {
    $conns = Get-NetTCPConnection -OwningProcess $p.ProcessId -State Established -ErrorAction SilentlyContinue |
        Where-Object RemotePort -eq 443
    foreach ($g in ($conns | Group-Object LocalAddress)) {
        $adapter = (Get-NetIPAddress -IPAddress $g.Name -ErrorAction SilentlyContinue).InterfaceAlias
        "the server (pid {0}) has {1} connections to RawTree open through {2}" -f $p.ProcessId, $g.Count, $adapter
        $open += $g.Count
    }
}
if (-not $open) { "the server has no connection to RawTree open right now: run this again in a few seconds" }
$route = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue |
    Sort-Object { $_.RouteMetric + (Get-NetIPInterface -InterfaceIndex $_.ifIndex -AddressFamily IPv4).InterfaceMetric } |
    Select-Object -First 1
"a connection opened now would leave through {0}" -f $route.InterfaceAlias
Get-NetAdapter -Physical | Where-Object { $_.InterfaceDescription -notmatch 'Bluetooth|Virtual' } |
    ForEach-Object { "   {0}: {1}{2}" -f $_.Name, $_.Status, $(if ($_.Status -eq 'Up') { ", $($_.LinkSpeed)" } else { '' }) }
