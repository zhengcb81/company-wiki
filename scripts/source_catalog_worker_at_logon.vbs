Option Explicit

If WScript.Arguments.Count <> 2 Then
    WScript.Quit 64
End If

Dim fileSystem
Dim shell
Dim launcherPath
Dim pythonExe
Dim projectRoot
Dim command
Dim result

Set fileSystem = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
launcherPath = fileSystem.BuildPath( _
    fileSystem.GetParentFolderName(WScript.ScriptFullName), _
    "source_catalog_worker_at_logon.ps1" _
)
pythonExe = WScript.Arguments(0)
projectRoot = WScript.Arguments(1)

If Not fileSystem.FileExists(launcherPath) Then
    WScript.Quit 2
End If

command = "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File " _
    & QuoteArgument(launcherPath) _
    & " -PythonExe " & QuoteArgument(pythonExe) _
    & " -ProjectRoot " & QuoteArgument(projectRoot)

On Error Resume Next
result = shell.Run(command, 0, False)
If Err.Number <> 0 Then
    WScript.Quit 1
End If
On Error GoTo 0
WScript.Quit result

Function QuoteArgument(value)
    If InStr(value, Chr(34)) > 0 Then
        WScript.Quit 65
    End If
    QuoteArgument = Chr(34) & value & Chr(34)
End Function
