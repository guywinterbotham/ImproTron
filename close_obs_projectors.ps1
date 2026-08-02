$type = Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    public delegate bool EnumThreadDelegate(IntPtr hwnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumThreadWindows(int dwThreadId, EnumThreadDelegate lpfn, IntPtr lParam);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, uint Msg, int wParam, int lParam);
}
"@ -PassThru

Get-Process obs64 | ForEach-Object {
    foreach ($thread in $_.Threads) {
        [Win32]::EnumThreadWindows($thread.Id, {
            param($hwnd, $lparam)
            $sb = New-Object System.Text.StringBuilder 256
            [Win32]::GetWindowText($hwnd, $sb, 256) | Out-Null
            if ($sb.ToString() -like "Projector*") {
                [Win32]::PostMessage($hwnd, 0x0010, 0, 0) # WM_CLOSE
            }
            return $true
        }, [IntPtr]::Zero) | Out-Null
    }
}