' LuaS30 IDE hidden launcher — no console window flash.
Option Explicit
Dim shell, fso, root, bat, args, i, arg
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
bat = root & "\run.bat"
If Not fso.FileExists(bat) Then
  MsgBox "LuaS30 IDE: run.bat not found next to this launcher." & vbCrLf & root, vbCritical, "LuaS30 IDE"
  WScript.Quit 1
End If
args = ""
For i = 1 To WScript.Arguments.Count - 1
  arg = WScript.Arguments(i)
  ' Strip characters that could break quoting / allow injection via shortcut args.
  arg = Replace(arg, """", "")
  arg = Replace(arg, "&", "")
  arg = Replace(arg, "|", "")
  arg = Replace(arg, ">", "")
  arg = Replace(arg, "<", "")
  If Len(args) > 0 Then args = args & " "
  args = args & """" & arg & """"
Next
shell.CurrentDirectory = root
' Ban frozen (LuaS30IDE.exe): chay thang, khong can console/pip/venv.
Dim frozen
frozen = root & "\LuaS30IDE.exe"
If fso.FileExists(frozen) Then
  shell.Run """" & frozen & """", 0, False
  WScript.Quit 0
End If
' Ban source (run.bat): lan chay dau hien console de thay tien trinh.
Dim runMode, appData, bundledOK, venvOK
runMode = 0
bundledOK = fso.FileExists(root & "\python\Lib\site-packages\PySide6\__init__.py")
appData = shell.ExpandEnvironmentStrings("%APPDATA%")
venvOK = fso.FileExists(appData & "\LuaS30IDE\venv\Lib\site-packages\PySide6\__init__.py")
If (Not bundledOK) And (Not venvOK) Then runMode = 1
shell.Run """" & bat & """ " & args, runMode, False
