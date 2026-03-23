'==========================================================================
'
' Update Manager for PC Info Collector
' Version: 1.0.0
' Date: 2026/03/23
' Features: Check for updates, download and install from remote server
'
'==========================================================================

On Error Resume Next

'==========================================================================
' Global Variables
'==========================================================================
Dim WshShell, g_fso, g_scriptDir, g_config
Dim g_updateServer, g_updatePort, g_currentVersion
Dim g_tempDir, g_backupDir

Set WshShell = CreateObject("WScript.Shell")
Set g_fso = CreateObject("Scripting.FileSystemObject")
g_scriptDir = g_fso.GetFile(WScript.ScriptFullName).ParentFolder
g_currentVersion = "5.0.0"
g_tempDir = g_scriptDir & "\UpdateTemp"
g_backupDir = g_scriptDir & "\UpdateBackup"

'==========================================================================
' Main Entry Point
'==========================================================================
Sub Main()
    WScript.Echo "=========================================="
    WScript.Echo "PC Info Collector - Update Manager"
    WScript.Echo "=========================================="
    WScript.Echo ""
    
    ' Load configuration
    If Not LoadConfiguration() Then
        WScript.Echo "[ERROR] Failed to load configuration!"
        WScript.Quit 1
    End If
    
    ' Check if update server is configured
    If g_updateServer = "" Then
        WScript.Echo "[ERROR] Update server not configured!"
        WScript.Echo "Please configure UpdateServer in Conf.json"
        WScript.Quit 1
    End If
    
    WScript.Echo "Current Version: " & g_currentVersion
    WScript.Echo "Update Server: " & g_updateServer & ":" & g_updatePort
    WScript.Echo ""
    
    ' Check for updates
    Dim updateInfo
    Set updateInfo = CheckForUpdate()
    
    If updateInfo Is Nothing Then
        WScript.Echo "[ERROR] Failed to check for updates!"
        WScript.Echo "Please check your network connection and server configuration."
        WScript.Quit 1
    End If
    
    If updateInfo.NewVersion = "" Then
        WScript.Echo "No update information available from server."
        WScript.Quit 0
    End If
    
    WScript.Echo "Server Version: " & updateInfo.NewVersion
    WScript.Echo ""
    
    ' Compare versions
    If CompareVersion(g_currentVersion, updateInfo.NewVersion) >= 0 Then
        WScript.Echo "[OK] You are running the latest version!"
        WScript.Echo ""
        WScript.Echo "No update needed."
        WScript.Quit 0
    End If
    
    WScript.Echo "[INFO] A new version is available!"
    WScript.Echo ""
    WScript.Echo "Update Details:"
    WScript.Echo "  Version: " & updateInfo.NewVersion
    If updateInfo.ReleaseNotes <> "" Then
        WScript.Echo "  Release Notes: " & updateInfo.ReleaseNotes
    End If
    WScript.Echo ""
    
    ' Ask for confirmation
    Dim userInput
    WScript.StdOut.Write "Do you want to proceed with the update? (Y/N): "
    userInput = WScript.StdIn.ReadLine()
    
    If LCase(Trim(userInput)) <> "y" Then
        WScript.Echo ""
        WScript.Echo "Update cancelled by user."
        WScript.Quit 0
    End If
    
    WScript.Echo ""
    WScript.Echo "Starting update process..."
    WScript.Echo ""
    
    ' Perform update
    If PerformUpdate(updateInfo) Then
        WScript.Echo ""
        WScript.Echo "=========================================="
        WScript.Echo "Update completed successfully!"
        WScript.Echo "=========================================="
        WScript.Echo ""
        WScript.Echo "New version: " & updateInfo.NewVersion
        WScript.Echo ""
        WScript.Echo "Please restart PC Info Collector to use the new version."
    Else
        WScript.Echo ""
        WScript.Echo "=========================================="
        WScript.Echo "[ERROR] Update failed!"
        WScript.Echo "=========================================="
        WScript.Echo ""
        WScript.Echo "Your original files have been preserved."
        WScript.Echo "Please check the error messages above."
        WScript.Quit 1
    End If
End Sub

'==========================================================================
' Load Configuration
'==========================================================================
Function LoadConfiguration()
    Dim configPath, configContent
    
    On Error Resume Next
    LoadConfiguration = False
    
    g_updateServer = ""
    g_updatePort = "8080"
    
    configPath = g_scriptDir & "\Conf.json"
    
    If Not g_fso.FileExists(configPath) Then
        WScript.Echo "[ERROR] Configuration file not found: " & configPath
        Exit Function
    End If
    
    configContent = ReadTextFile(configPath)
    Set g_config = ParseJSON(configContent)
    
    If Err.Number <> 0 Then
        WScript.Echo "[ERROR] Failed to parse configuration file!"
        Err.Clear
        Exit Function
    End If
    
    On Error Resume Next
    If IsObject(g_config.UpdateServer) Then
        g_updateServer = g_config.UpdateServer.Host
        g_updatePort = g_config.UpdateServer.Port
        If g_updatePort = "" Then g_updatePort = "8080"
    End If
    Err.Clear
    
    LoadConfiguration = True
End Function

'==========================================================================
' Check For Update
'==========================================================================
Function CheckForUpdate()
    Dim http, url, response
    Dim updateInfo
    
    On Error Resume Next
    Set CheckForUpdate = Nothing
    
    url = "http://" & g_updateServer & ":" & g_updatePort & "/api/version"
    
    WScript.Echo "Checking for updates..."
    WScript.Echo "  URL: " & url
    
    Set http = CreateObject("Microsoft.XMLHTTP")
    http.Open "GET", url, False
    http.SetRequestHeader "Content-Type", "application/json"
    http.Send
    
    If http.Status <> 200 Then
        WScript.Echo "[ERROR] Server returned HTTP " & http.Status
        Set http = Nothing
        Exit Function
    End If
    
    response = http.responseText
    Set http = Nothing
    
    ' Parse version info
    Set updateInfo = CreateObject("Scripting.Dictionary")
    
    ' Try to parse JSON response
    Dim jsonObj
    Set jsonObj = ParseJSON(response)
    
    If Err.Number <> 0 Then
        WScript.Echo "[ERROR] Failed to parse server response!"
        Err.Clear
        Exit Function
    End If
    
    On Error Resume Next
    updateInfo.Add "NewVersion", jsonObj.version
    updateInfo.Add "ReleaseNotes", jsonObj.releaseNotes
    updateInfo.Add "DownloadUrl", jsonObj.downloadUrl
    updateInfo.Add "Files", jsonObj.files
    Err.Clear
    
    If updateInfo("NewVersion") = "" Then
        updateInfo("NewVersion") = ""
    End If
    
    Set CheckForUpdate = updateInfo
End Function

'==========================================================================
' Compare Versions
' Returns: -1 if v1 < v2, 0 if v1 = v2, 1 if v1 > v2
'==========================================================================
Function CompareVersion(v1, v2)
    Dim parts1, parts2, i, maxParts
    
    parts1 = Split(v1, ".")
    parts2 = Split(v2, ".")
    
    maxParts = UBound(parts1)
    If UBound(parts2) > maxParts Then maxParts = UBound(parts2)
    
    For i = 0 To maxParts
        Dim n1, n2
        n1 = 0
        n2 = 0
        
        If i <= UBound(parts1) Then
            On Error Resume Next
            n1 = CInt(parts1(i))
            Err.Clear
        End If
        
        If i <= UBound(parts2) Then
            On Error Resume Next
            n2 = CInt(parts2(i))
            Err.Clear
        End If
        
        If n1 < n2 Then
            CompareVersion = -1
            Exit Function
        ElseIf n1 > n2 Then
            CompareVersion = 1
            Exit Function
        End If
    Next
    
    CompareVersion = 0
End Function

'==========================================================================
' Perform Update
'==========================================================================
Function PerformUpdate(updateInfo)
    Dim files, file, i
    
    On Error Resume Next
    PerformUpdate = False
    
    ' Create temp and backup directories
    PrepareDirectories()
    
    If Err.Number <> 0 Then
        WScript.Echo "[ERROR] Failed to create directories: " & Err.Description
        Err.Clear
        Exit Function
    End If
    
    ' Backup current files
    WScript.Echo "Creating backup of current files..."
    If Not BackupCurrentFiles() Then
        WScript.Echo "[ERROR] Failed to backup current files!"
        Exit Function
    End If
    WScript.Echo "  Backup created successfully."
    WScript.Echo ""
    
    ' Download new files
    WScript.Echo "Downloading new files..."
    
    On Error Resume Next
    Set files = updateInfo("Files")
    
    If Err.Number <> 0 Or files Is Nothing Then
        ' Try to download from downloadUrl
        Dim downloadUrl
        downloadUrl = updateInfo("DownloadUrl")
        
        If downloadUrl <> "" Then
            If Not DownloadFile(downloadUrl, g_tempDir & "\update.zip") Then
                WScript.Echo "[ERROR] Failed to download update package!"
                Call RestoreBackup()
                Exit Function
            End If
            
            WScript.Echo "  Downloaded update package."
            WScript.Echo "  Extracting..."
            
            If Not ExtractZip(g_tempDir & "\update.zip", g_tempDir) Then
                WScript.Echo "[ERROR] Failed to extract update package!"
                Call RestoreBackup()
                Exit Function
            End If
            
            g_fso.DeleteFile g_tempDir & "\update.zip", True
        Else
            WScript.Echo "[ERROR] No download information available!"
            Exit Function
        End If
    Else
        ' Download individual files
        For i = 0 To files.Count - 1
            file = files(i)
            WScript.Echo "  Downloading: " & file.name
            
            If Not DownloadFile(file.url, g_tempDir & "\" & file.name) Then
                WScript.Echo "[ERROR] Failed to download: " & file.name
                Call RestoreBackup()
                Exit Function
            End If
        Next
    End If
    
    WScript.Echo "  All files downloaded successfully."
    WScript.Echo ""
    
    ' Install new files
    WScript.Echo "Installing new files..."
    If Not InstallNewFiles() Then
        WScript.Echo "[ERROR] Failed to install new files!"
        Call RestoreBackup()
        Exit Function
    End If
    WScript.Echo "  Installation complete."
    WScript.Echo ""
    
    ' Cleanup
    WScript.Echo "Cleaning up..."
    Call Cleanup()
    WScript.Echo "  Cleanup complete."
    
    PerformUpdate = True
End Function

'==========================================================================
' Prepare Directories
'==========================================================================
Sub PrepareDirectories()
    ' Clean up old temp directory
    If g_fso.FolderExists(g_tempDir) Then
        g_fso.DeleteFolder g_tempDir, True
    End If
    
    ' Clean up old backup directory
    If g_fso.FolderExists(g_backupDir) Then
        g_fso.DeleteFolder g_backupDir, True
    End If
    
    ' Create new directories
    g_fso.CreateFolder g_tempDir
    g_fso.CreateFolder g_backupDir
End Sub

'==========================================================================
' Backup Current Files
'==========================================================================
Function BackupCurrentFiles()
    Dim filesToBackup, file, i
    
    On Error Resume Next
    BackupCurrentFiles = False
    
    filesToBackup = Array("PC_5.0.0_modular.vbs", "PC_Info_Collector.bat", "Conf.json")
    
    For i = 0 To UBound(filesToBackup)
        file = filesToBackup(i)
        If g_fso.FileExists(g_scriptDir & "\" & file) Then
            g_fso.CopyFile g_scriptDir & "\" & file, g_backupDir & "\" & file, True
            If Err.Number <> 0 Then
                WScript.Echo "[ERROR] Failed to backup: " & file
                Exit Function
            End If
        End If
    Next
    
    BackupCurrentFiles = True
End Function

'==========================================================================
' Restore Backup
'==========================================================================
Sub RestoreBackup()
    Dim filesToRestore, file, i
    
    On Error Resume Next
    
    WScript.Echo ""
    WScript.Echo "Restoring backup..."
    
    filesToRestore = Array("PC_5.0.0_modular.vbs", "PC_Info_Collector.bat", "Conf.json")
    
    For i = 0 To UBound(filesToRestore)
        file = filesToRestore(i)
        If g_fso.FileExists(g_backupDir & "\" & file) Then
            g_fso.CopyFile g_backupDir & "\" & file, g_scriptDir & "\" & file, True
        End If
    Next
    
    WScript.Echo "  Backup restored."
End Sub

'==========================================================================
' Download File
'==========================================================================
Function DownloadFile(url, savePath)
    Dim http, stream
    
    On Error Resume Next
    DownloadFile = False
    
    Set http = CreateObject("Microsoft.XMLHTTP")
    http.Open "GET", url, False
    http.Send
    
    If http.Status <> 200 Then
        Set http = Nothing
        Exit Function
    End If
    
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 1 ' Binary
    stream.Open
    stream.Write http.responseBody
    stream.SaveToFile savePath, 2
    stream.Close
    
    Set stream = Nothing
    Set http = Nothing
    
    If Err.Number <> 0 Then
        Err.Clear
        Exit Function
    End If
    
    DownloadFile = True
End Function

'==========================================================================
' Extract Zip File
'==========================================================================
Function ExtractZip(zipPath, extractPath)
    Dim shell, zipFolder, item
    
    On Error Resume Next
    ExtractZip = False
    
    Set shell = CreateObject("Shell.Application")
    Set zipFolder = shell.Namespace(zipPath)
    
    If zipFolder Is Nothing Then
        Exit Function
    End If
    
    shell.Namespace(extractPath).CopyHere zipFolder.Items, 16
    
    WScript.Sleep 2000
    
    Set zipFolder = Nothing
    Set shell = Nothing
    
    If Err.Number <> 0 Then
        Err.Clear
        Exit Function
    End If
    
    ExtractZip = True
End Function

'==========================================================================
' Install New Files
'==========================================================================
Function InstallNewFiles()
    Dim tempFolder, file, files
    
    On Error Resume Next
    InstallNewFiles = False
    
    Set tempFolder = g_fso.GetFolder(g_tempDir)
    Set files = tempFolder.Files
    
    For Each file In files
        ' Skip non-relevant files
        If LCase(g_fso.GetExtensionName(file.Name)) = "vbs" Or _
           LCase(g_fso.GetExtensionName(file.Name)) = "bat" Or _
           LCase(file.Name) = "conf.json" Then
            
            WScript.Echo "  Installing: " & file.Name
            
            ' Special handling for Conf.json - merge instead of replace
            If LCase(file.Name) = "conf.json" Then
                If Not MergeConfiguration(file.Path, g_scriptDir & "\Conf.json") Then
                    WScript.Echo "[WARNING] Failed to merge configuration, using new config."
                    g_fso.CopyFile file.Path, g_scriptDir & "\Conf.json", True
                End If
            Else
                g_fso.CopyFile file.Path, g_scriptDir & "\" & file.Name, True
            End If
            
            If Err.Number <> 0 Then
                WScript.Echo "[ERROR] Failed to install: " & file.Name & " - " & Err.Description
                Exit Function
            End If
        End If
    Next
    
    InstallNewFiles = True
End Function

'==========================================================================
' Merge Configuration
'==========================================================================
Function MergeConfiguration(newConfigPath, currentConfigPath)
    Dim newConfigContent, currentConfigContent
    Dim newConfig, currentConfig
    
    On Error Resume Next
    MergeConfiguration = False
    
    ' Read both configurations
    newConfigContent = ReadTextFile(newConfigPath)
    currentConfigContent = ReadTextFile(currentConfigPath)
    
    Set newConfig = ParseJSON(newConfigContent)
    Set currentConfig = ParseJSON(currentConfigContent)
    
    If Err.Number <> 0 Then
        Err.Clear
        Exit Function
    End If
    
    ' Preserve user-specific settings from current config
    On Error Resume Next
    
    ' Keep CustInfo.id
    If IsObject(currentConfig.CustInfo) And IsObject(newConfig.CustInfo) Then
        newConfig.CustInfo.id = currentConfig.CustInfo.id
    End If
    
    ' Keep HttpReport endpoint if it's customized
    If IsObject(currentConfig.HttpReport) And IsObject(newConfig.HttpReport) Then
        ' Only keep if it's different from default
        If currentConfig.HttpReport.Endpoint <> "http://192.168.23.31:9091/metrics/job/pcinfo" Then
            newConfig.HttpReport.Endpoint = currentConfig.HttpReport.Endpoint
        End If
    End If
    
    ' Keep UpdateServer settings
    If IsObject(currentConfig.UpdateServer) Then
        newConfig.UpdateServer = currentConfig.UpdateServer
    End If
    
    Err.Clear
    
    ' Save merged configuration
    Dim json
    json = ConfigToJSON(newConfig)
    
    Dim stream
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Mode = 3
    stream.Charset = "UTF-8"
    stream.Open
    stream.WriteText json
    stream.SaveToFile currentConfigPath, 2
    stream.Close
    Set stream = Nothing
    
    If Err.Number <> 0 Then
        Err.Clear
        Exit Function
    End If
    
    MergeConfiguration = True
End Function

'==========================================================================
' Configuration To JSON
'==========================================================================
Function ConfigToJSON(config)
    Dim json
    
    On Error Resume Next
    
    json = "{" & vbCrLf
    
    ' CustInfo
    json = json & "  ""CustInfo"": {" & vbCrLf
    json = json & "    ""id"": """ & config.CustInfo.id & """" & vbCrLf
    json = json & "  }," & vbCrLf
    
    ' Modules
    json = json & "  ""Modules"": {" & vbCrLf
    json = json & "    ""Systeminfo"": " & LCase(CStr(config.Modules.Systeminfo)) & "," & vbCrLf
    json = json & "    ""Hardware"": " & LCase(CStr(config.Modules.Hardware)) & "," & vbCrLf
    json = json & "    ""MEMinfo"": " & LCase(CStr(config.Modules.MEMinfo)) & "," & vbCrLf
    json = json & "    ""Diskinfo"": " & LCase(CStr(config.Modules.Diskinfo)) & "," & vbCrLf
    json = json & "    ""Softwareinfo"": " & LCase(CStr(config.Modules.Softwareinfo)) & "," & vbCrLf
    json = json & "    ""Netinfo"": " & LCase(CStr(config.Modules.Netinfo)) & "," & vbCrLf
    json = json & "    ""Hotfixinfo"": " & LCase(CStr(config.Modules.Hotfixinfo)) & "," & vbCrLf
    json = json & "    ""Processinfo"": " & LCase(CStr(config.Modules.Processinfo)) & "," & vbCrLf
    json = json & "    ""Userinfo"": " & LCase(CStr(config.Modules.Userinfo)) & "," & vbCrLf
    json = json & "    ""Environment"": " & LCase(CStr(config.Modules.Environment)) & vbCrLf
    json = json & "  }," & vbCrLf
    
    ' HttpReport
    json = json & "  ""HttpReport"": {" & vbCrLf
    json = json & "    ""Enabled"": " & LCase(CStr(config.HttpReport.Enabled)) & "," & vbCrLf
    json = json & "    ""Endpoint"": """ & config.HttpReport.Endpoint & """," & vbCrLf
    json = json & "    ""RetryCount"": " & config.HttpReport.RetryCount & "," & vbCrLf
    json = json & "    ""Timeout"": " & config.HttpReport.Timeout & "," & vbCrLf
    json = json & "    ""Format"": """ & config.HttpReport.Format & """" & vbCrLf
    json = json & "  }," & vbCrLf
    
    ' UpdateServer
    json = json & "  ""UpdateServer"": {" & vbCrLf
    json = json & "    ""Host"": """ & config.UpdateServer.Host & """," & vbCrLf
    json = json & "    ""Port"": """ & config.UpdateServer.Port & """" & vbCrLf
    json = json & "  }," & vbCrLf
    
    ' DataRetention
    json = json & "  ""DataRetention"": {" & vbCrLf
    json = json & "    ""KeepDays"": " & config.DataRetention.KeepDays & "," & vbCrLf
    json = json & "    ""Enabled"": " & LCase(CStr(config.DataRetention.Enabled)) & vbCrLf
    json = json & "  }," & vbCrLf
    
    ' Execution
    json = json & "  ""Execution"": {" & vbCrLf
    json = json & "    ""RequireAdmin"": " & LCase(CStr(config.Execution.RequireAdmin)) & "," & vbCrLf
    json = json & "    ""AutoElevate"": " & LCase(CStr(config.Execution.AutoElevate)) & vbCrLf
    json = json & "  }" & vbCrLf
    
    json = json & "}"
    
    ConfigToJSON = json
End Function

'==========================================================================
' Cleanup
'==========================================================================
Sub Cleanup()
    On Error Resume Next
    
    ' Remove temp directory
    If g_fso.FolderExists(g_tempDir) Then
        g_fso.DeleteFolder g_tempDir, True
    End If
    
    ' Optionally keep backup for rollback purposes
    ' g_fso.DeleteFolder g_backupDir, True
End Sub

'==========================================================================
' Read Text File
'==========================================================================
Function ReadTextFile(filepath)
    Dim stream
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Mode = 3
    stream.Charset = "UTF-8"
    stream.Open
    stream.LoadFromFile filepath
    ReadTextFile = stream.ReadText
    stream.Close
    Set stream = Nothing
End Function

'==========================================================================
' Parse JSON
'==========================================================================
Function ParseJSON(jsonStr)
    Dim sc, window
    Set sc = CreateObject("htmlfile")
    Set window = sc.parentWindow
    window.execScript "var json = " & jsonStr, "JScript"
    Set ParseJSON = window.json
End Function

'==========================================================================
' Entry Point
'==========================================================================
Call Main()