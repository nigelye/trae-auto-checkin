' TRAE 签到隐藏运行脚本
' 用于定时任务，不显示命令行窗口
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 获取脚本所在目录
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' 切换到脚本目录并运行Python脚本
WshShell.CurrentDirectory = scriptDir
WshShell.Run "python """ & scriptDir & "\trae_checkin.py""", 0, False
