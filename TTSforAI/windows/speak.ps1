# speak.ps1 — Windows TTS Reader with pause/resume support
# Reads text from stdin and speaks it aloud using Windows Speech API
#
# Global hotkeys (work regardless of focused window):
#   Ctrl+Alt+P — pause / resume
#   Ctrl+Alt+S — stop
#
# Usage (from Git Bash):
#   echo "hello world" | speak
#   cat file.txt | speak
#   some-command | speak

Add-Type -AssemblyName System.Speech

# Win32 API for global hotkeys and message pump
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
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
}

$synth.Rate = 1

# Read all text from stdin
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$text = [Console]::In.ReadToEnd().Trim()

if (-not $text) { exit }

# Register global hotkeys:
#   ID 1 = Ctrl+Alt+P (pause/resume) — VK_P = 0x50
#   ID 2 = Ctrl+Alt+S (stop)         — VK_S = 0x53
$modifiers = [Win32]::MOD_CONTROL -bor [Win32]::MOD_ALT
[Win32]::RegisterHotKey([IntPtr]::Zero, 1, $modifiers, 0x50) | Out-Null
[Win32]::RegisterHotKey([IntPtr]::Zero, 2, $modifiers, 0x53) | Out-Null

$synth.SpeakAsync($text) | Out-Null

$paused = $false
$msg = New-Object Win32+MSG

try {
    while ($synth.State -ne [System.Speech.Synthesis.SynthesizerState]::Ready) {
        if ([Win32]::PeekMessage([ref]$msg, [IntPtr]::Zero, 0, 0, [Win32]::PM_REMOVE)) {
            if ($msg.message -eq [Win32]::WM_HOTKEY) {
                switch ($msg.wParam.ToInt32()) {
                    1 {  # Ctrl+Alt+P — toggle pause/resume
                        if ($paused) {
                            $synth.Resume()
                            $paused = $false
                        } else {
                            $synth.Pause()
                            $paused = $true
                        }
                    }
                    2 {  # Ctrl+Alt+S — stop
                        $synth.SpeakAsyncCancelAll()
                    }
                }
            }
        }
        Start-Sleep -Milliseconds 50
    }
} finally {
    [Win32]::UnregisterHotKey([IntPtr]::Zero, 1) | Out-Null
    [Win32]::UnregisterHotKey([IntPtr]::Zero, 2) | Out-Null
}
