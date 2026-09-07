Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\工作\ww\personal_work\study_trace"
WshShell.Run "cmd /c run-prod-daemon.bat", 0, False
