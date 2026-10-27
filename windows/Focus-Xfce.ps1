$ErrorActionPreference='Stop'
Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class XfceFocus {
 public delegate bool Callback(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumWindows(Callback fn,IntPtr p);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h,StringBuilder s,int n);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int cmd);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint process);
 public static IntPtr Find() {
  IntPtr found=IntPtr.Zero;
  EnumWindows((h,p)=>{var s=new StringBuilder(1024);GetWindowText(h,s,s.Capacity);uint process;GetWindowThreadProcessId(h,out process);if(IsWindowVisible(h) && s.ToString().StartsWith("Xfce WSL") && System.Diagnostics.Process.GetProcessById((int)process).ProcessName=="msrdc"){found=h;return false;}return true;},IntPtr.Zero);
  return found;
 }
}
'@
$h=[XfceFocus]::Find()
if ($h -eq [IntPtr]::Zero) {throw 'Janela Xfce nao encontrada no Windows'}
if ([XfceFocus]::IsIconic($h)) {[XfceFocus]::ShowWindow($h,9) | Out-Null}
[XfceFocus]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 200
[pscustomobject]@{focused=([XfceFocus]::GetForegroundWindow() -eq $h);window=$h.ToInt64()} | ConvertTo-Json -Compress
