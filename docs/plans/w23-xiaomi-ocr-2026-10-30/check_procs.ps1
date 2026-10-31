Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ForEach-Object {
  "PID=" + $_.ProcessId + " WS_MB=" + [math]::Round($_.WorkingSetSize/1MB) + " CMD=" + ($_.CommandLine -replace '\s+',' ').Substring(0, [Math]::Min(160, $_.CommandLine.Length))
}
"---memwatch ps1 output---"
Get-Content "C:\Users\郑曾波\AppData\Local\Temp\zcode-bash-kh84Aw\session_915e1ed686a55c8a77bbbba375a1bc0f\call_0623db2bba2e4ad09807eb80-stdout.log" -ErrorAction SilentlyContinue
