Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\工作\ww\personal_work\study_trace"
WshShell.Run "cmd /c start.bat", 0, False
WshShell.Run "cmd /c cloudflared tunnel run study-trace", 0, False
