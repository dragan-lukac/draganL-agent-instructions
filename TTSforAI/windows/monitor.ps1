# monitor.ps1 — Clipboard TTS Monitor with pause/resume support
# Watches the clipboard and automatically reads new text aloud.
# Useful for reading Claude's responses — just copy the text and it speaks.
#
# Global hotkeys (work regardless of focused window):
#   Ctrl+Alt+P — pause / resume
#   Ctrl+Alt+S — stop current speech
#
# Usage (from Git Bash):
#   tts-monitor       (starts in background via setup.sh alias)
#   tts-stop          (stops the background monitor)

Add-Type -AssemblyName System.Speech
Add-Type -AssemblyName System.Windows.Forms

# Win32 API for global hotkeys and message pump
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32Monitor {
    [DllImport("user32.dll")] public static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);
    [DllImport("user32.dll")] public static extern bool UnregisterHotKey(IntPtr hWnd, int id);
    [DllImport("user32.dll")] public static extern bool PeekMessage(out MSG lpMsg, IntPtr hWnd, uint wMsgFilterMin, uint wMsgFilterMax, uint wRemoveMsg);
    [StructLayout(LayoutKind.Sequential)]
    public struct MSG { public IntPtr hwnd; public uint message; public IntPtr wParam; public IntPtr lParam; public uint time; public int ptX; public int ptY; }
    public const uint WM_HOTKEY = 0x0312;
    public const uint MOD_CONTROL = 0x0002;
    public const uint MOD_ALT    = 0x0001;
    public const uint PM_REMOVE  = 0x0001;
}
"@

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer

# Prefer natural/neural voices if installed
$voices = $synth.GetInstalledVoices() | Select-Object -ExpandProperty VoiceInfo
$preferredKeywords = @("Natural", "Aria", "Jenny", "Guy", "Davis")
$selectedVoice = $null

foreach ($keyword in $preferredKeywords) {
    $selectedVoice = $voices | Where-Object { $_.Name -match $keyword } | Select-Object -First 1
    if ($selectedVoice) { break }
}

if ($selectedVoice) {
    $synth.SelectVoice($selectedVoice.Name)
    Write-Host "Voice : $($selectedVoice.Name)"
} else {
    Write-Host "Voice : (default system voice)"
}

$synth.Rate = 1

# Register global hotkeys:
#   ID 1 = Ctrl+Alt+P (pause/resume) — VK_P = 0x50
#   ID 2 = Ctrl+Alt+S (stop)         — VK_S = 0x53
$modifiers = [Win32Monitor]::MOD_CONTROL -bor [Win32Monitor]::MOD_ALT
[Win32Monitor]::RegisterHotKey([IntPtr]::Zero, 1, $modifiers, 0x50) | Out-Null
[Win32Monitor]::RegisterHotKey([IntPtr]::Zero, 2, $modifiers, 0x53) | Out-Null

Write-Host "═══════════════════════════════════════"
Write-Host "  Clipboard TTS Monitor — Running"
Write-Host "  Copy any text to hear it read aloud"
Write-Host "  Ctrl+Alt+P — pause / resume"
Write-Host "  Ctrl+Alt+S — stop"
Write-Host "  Press Ctrl+C to exit"
Write-Host "═══════════════════════════════════════"
Write-Host ""

$lastText = Get-Clipboard -ErrorAction SilentlyContinue
$paused = $false
$msg = New-Object Win32Monitor+MSG

try {
    while ($true) {
        # Check for hotkey messages
        if ([Win32Monitor]::PeekMessage([ref]$msg, [IntPtr]::Zero, 0, 0, [Win32Monitor]::PM_REMOVE)) {
            if ($msg.message -eq [Win32Monitor]::WM_HOTKEY) {
                switch ($msg.wParam.ToInt32()) {
                    1 {  # Ctrl+Alt+P — toggle pause/resume
                        if ($paused) {
                            $synth.Resume()
                            $paused = $false
                            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ▶ Resumed"
                        } else {
                            $synth.Pause()
                            $paused = $true
                            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ⏸ Paused"
                        }
                    }
                    2 {  # Ctrl+Alt+S — stop
                        $synth.SpeakAsyncCancelAll()
                        $paused = $false
                        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ⏹ Stopped"
                    }
                }
            }
        }

        Start-Sleep -Milliseconds 100

        # Check clipboard for new content
        try {
            $current = Get-Clipboard -ErrorAction SilentlyContinue
            if ($current -and $current -is [string] -and $current.Trim() -ne "" -and $current -ne $lastText) {
                $lastText = $current
                $preview = if ($current.Length -gt 70) { $current.Substring(0, 70) + "..." } else { $current }
                Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $preview"
                $synth.SpeakAsyncCancelAll()
                $paused = $false
                $synth.SpeakAsync($current) | Out-Null
            }
        } catch {
            # Ignore transient clipboard access errors
        }
    }
} finally {
    [Win32Monitor]::UnregisterHotKey([IntPtr]::Zero, 1) | Out-Null
    [Win32Monitor]::UnregisterHotKey([IntPtr]::Zero, 2) | Out-Null
}
