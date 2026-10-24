# 设置 / 查看 Windows 默认播放（或录音）设备
# 用法：
#   pwsh -NoProfile -File tools\set_default_audio.ps1 -List
#   pwsh -NoProfile -File tools\set_default_audio.ps1 -Set "CABLE Input"
#   pwsh -NoProfile -File tools\set_default_audio.ps1 -Set "CABLE Input" -Record
# 说明：从注册表读端点 ID，用 IPolicyConfig 切默认端点（只影响当前用户，不需要管理员）。
#       名称按端点描述匹配，可用 -Set 传部分名称（精确优先，其次前缀）。
param(
    [switch]$List,
    [string]$Set,
    [switch]$Record
)

$cs = @'
using System;
using System.Runtime.InteropServices;

namespace AudioCtl2 {
    [ComImport, Guid("870af99c-171d-4f9e-af0d-e63df40c2bc9")]
    public class CPolicyConfigClient { }

    [ComImport, Guid("F8679F50-850A-41CF-9C72-430F290290C8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IPolicyConfig {
        int GetMixFormat(string pszDeviceName, IntPtr ppFormat);
        int GetDeviceFormat(string pszDeviceName, bool bDefault, IntPtr ppFormat);
        int ResetDeviceFormat(string pszDeviceName);
        int SetDeviceFormat(string pszDeviceName, IntPtr pEndpointFormat, IntPtr mixFormat);
        int GetProcessingPeriod(string pszDeviceName, bool bDefault, IntPtr pmftDefaultPeriod, IntPtr pmftMinimumPeriod);
        int SetProcessingPeriod(string pszDeviceName, IntPtr pmftPeriod);
        int GetShareMode(string pszDeviceName, IntPtr pMode);
        int SetShareMode(string pszDeviceName, IntPtr mode);
        int GetPropertyValue(string pszDeviceName, int bFxStore, IntPtr pKey, IntPtr pv);
        int SetPropertyValue(string pszDeviceName, int bFxStore, IntPtr pKey, IntPtr pv);
        int SetDefaultEndpoint(string pszDeviceName, int role);
        int SetEndpointVisibility(string pszDeviceName, int bVisible);
    }

    public static class Api2 {
        public static int SetDefault(string deviceId) {
            try {
                var pc = (IPolicyConfig)new CPolicyConfigClient();
                int rc = 0;
                for (int role = 0; role < 3; role++) {
                    int r = pc.SetDefaultEndpoint(deviceId, role);
                    if (r != 0) rc = r;
                }
                return rc;
            } catch (Exception e) {
                Console.Error.WriteLine(e.Message);
                return -1;
            }
        }
    }
}
'@
Add-Type -TypeDefinition $cs -Language CSharp | Out-Null

$kind = if ($Record) { 'Capture' } else { 'Render' }
$base = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\$kind"
$prefix = if ($Record) { "{0.0.1.00000000}." } else { "{0.0.0.00000000}." }

$devs = @()
foreach ($k in Get-ChildItem $base -ErrorAction SilentlyContinue) {
    $pv = Get-ItemProperty -Path (Join-Path $k.PSPath 'Properties') -ErrorAction SilentlyContinue
    if (-not $pv) { continue }
    $name = $null
    foreach ($p in $pv.PSObject.Properties) {
        if ($p.Name -like '{a45c254e-df1c-4efd-8020-67d146a850e0}*') {
            if ($p.Value -is [string] -and $p.Value) { $name = $p.Value; break }
        }
    }
    if (-not $name) { continue }
    $guid = Split-Path $k.PSPath -Leaf
    $devs += [pscustomobject]@{ Name = $name; Id = ($prefix + $guid) }
}

if ($List) { $devs | ForEach-Object { $_.Name }; exit 0 }

if ($Set) {
    $d = $devs | Where-Object { $_.Name -eq $Set } | Select-Object -First 1
    if (-not $d) { $d = $devs | Where-Object { $_.Name -like "$Set*" } | Select-Object -First 1 }
    if (-not $d) {
        "NOT FOUND: $Set"
        $devs | ForEach-Object { "  - " + $_.Name }
        exit 1
    }
    $rc = [AudioCtl2.Api2]::SetDefault($d.Id)
    if ($rc -eq 0) { "OK -> $($d.Name)" } else { "FAIL rc=$rc"; exit 1 }
}
