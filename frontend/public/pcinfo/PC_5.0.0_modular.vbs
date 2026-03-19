'==========================================================================
'
' Version 5.0 (Modular Architecture) - Fixed for Pushgateway
' Date: 2026/03/11
' Name: PC Info Collector Modular
' Features: Modular Design + HTTP Report + Prometheus Metrics
'
'==========================================================================

On Error Resume Next

'==========================================================================
' Check and Request Administrator Privileges
'==========================================================================
Dim WshShell, objWMIService, colItems
Set WshShell = CreateObject("WScript.Shell")

' Check if running with administrator privileges
Function IsAdmin()
    On Error Resume Next
    Dim objFSO, testFile
    Set objFSO = CreateObject("Scripting.FileSystemObject")
    ' Try to create a file in system directory
    testFile = WshShell.ExpandEnvironmentStrings("%SystemRoot%\Temp\admin_test_" & Timer & ".tmp")
    Dim f
    Set f = objFSO.CreateTextFile(testFile, True)
    f.Close
    objFSO.DeleteFile testFile, True
    If Err.Number = 0 Then
        IsAdmin = True
    Else
        IsAdmin = False
        Err.Clear
    End If
End Function

'==========================================================================
' Core Configuration Constants
'==========================================================================
Const HKEY_LOCAL_MACHINE = &H80000002
Const UNINSTALL_ROOT = "Software\Microsoft\Windows\CurrentVersion\Uninstall"
Const REG_SZ = 1

'==========================================================================
' Global Variables
'==========================================================================
Dim g_fso, g_outputPath, g_colldate, g_FileDate, g_FileDateStr
Dim g_computerName, g_uuid, g_snum, g_custname
Dim g_config, g_moduleResults
Dim g_httpEnabled, g_httpEndpoint, g_httpRetryCount, g_httpFormat
Dim g_dataRetentionEnabled, g_keepDays

Set g_fso = CreateObject("Scripting.FileSystemObject")
Set g_moduleResults = CreateObject("Scripting.Dictionary")

'==========================================================================
' Main Program Entry
'==========================================================================
Sub Main()
    Call Initialize()
    Call LoadConfiguration()
    Call GetSystemInfo()
    
    ' Clean up old data files before collecting new data
    If g_dataRetentionEnabled Then
        Call CleanupOldData()
    End If
    
    Call ExecuteModules()
    
    If g_httpEnabled Then
        Call ReportToServer()
    End If
    
    Call Cleanup()
    
    WScript.Echo ""
    WScript.Echo "Script completed successfully!"
    WScript.Echo "Output directory: " & g_outputPath
End Sub

'==========================================================================
' Initialize
'==========================================================================
Sub Initialize()
    Dim strFile
    
    Set strFile = g_fso.GetFile(WScript.ScriptFullName)
    
    g_colldate = CStr(Year(Now())) & "-" & Right("0" & Month(Now()), 2) & "-" & Right("0" & Day(Now()), 2) & " " & Right("0" & Hour(Now()), 2) & ":" & Right("0" & Minute(Now()), 2) & ":" & Right("0" & Second(Now()), 2)
    g_FileDate = CStr(Year(Now())) & "-" & Right("0" & Month(Now()), 2) & "-" & Right("0" & Day(Now()), 2)
    g_FileDateStr = CStr(Year(Now())) & Right("0" & Month(Now()), 2) & Right("0" & Day(Now()), 2)
    
    g_computerName = WshShell.ExpandEnvironmentStrings("%COMPUTERNAME%")
    
    ' Output directory structure: PcInfo/20260311/
    g_outputPath = strFile.ParentFolder & "\PcInfo\" & g_FileDateStr & "\"
    If Not g_fso.FolderExists(g_outputPath) Then
        If Not g_fso.FolderExists(strFile.ParentFolder & "\PcInfo") Then
            g_fso.CreateFolder(strFile.ParentFolder & "\PcInfo")
        End If
        g_fso.CreateFolder(g_outputPath)
    End If
End Sub

'==========================================================================
' Load Configuration
'==========================================================================
Sub LoadConfiguration()
    Dim configPath, configContent
    
    configPath = g_fso.GetFile(WScript.ScriptFullName).ParentFolder & "\Conf.json"
    
    g_httpEnabled = False
    g_httpEndpoint = ""
    g_httpRetryCount = 3
    g_custname = "default"
    g_httpFormat = "json"
    g_dataRetentionEnabled = False
    g_keepDays = 30
    
    If g_fso.FileExists(configPath) Then
        configContent = ReadTextFile(configPath)
        Set g_config = ParseJSON(configContent)
        
        On Error Resume Next
        g_custname = g_config.CustInfo.id
        g_httpEnabled = g_config.HttpReport.Enabled
        g_httpEndpoint = g_config.HttpReport.Endpoint
        g_httpRetryCount = g_config.HttpReport.RetryCount
        g_httpFormat = g_config.HttpReport.Format
        g_dataRetentionEnabled = g_config.DataRetention.Enabled
        g_keepDays = g_config.DataRetention.KeepDays
        ' Load execution settings
        g_requireAdmin = g_config.Execution.RequireAdmin
        g_autoElevate = g_config.Execution.AutoElevate
        Err.Clear
    End If
End Sub

'==========================================================================
' Get System Info
'==========================================================================
Sub GetSystemInfo()
    Dim lsnum, idx, luuid
    
    Set objWMIService = GetObject("winmgmts:\\.\root\CIMV2")
    
    Set colItems = objWMIService.ExecQuery("SELECT SerialNumber FROM Win32_BIOS")
    For Each objItem In colItems
        g_snum = objItem.SerialNumber
    Next
    
    lsnum = LCase(g_snum)
    idx = InStr(lsnum, "vmware")
    If idx = 1 Then
        g_snum = Replace(g_snum, "VMware", "")
        g_snum = Replace(g_snum, "-", "")
        g_snum = Replace(g_snum, " ", "")
        If Len(g_snum) = 32 Then
            g_snum = Left(g_snum, 8) & "-" & Mid(g_snum, 9, 4) & "-" & Mid(g_snum, 13, 4) & "-" & Mid(g_snum, 17, 4) & "-" & Right(g_snum, 12)
        End If
    End If
    
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_ComputerSystemProduct")
    For Each objItem In colItems
        g_uuid = objItem.UUID
    Next
    
    luuid = LCase(g_uuid)
    idx = InStr(luuid, "vmware")
    If idx = 1 Then
        g_uuid = Replace(g_uuid, "VMware", "")
        g_uuid = Replace(g_uuid, "-", "")
        g_uuid = Replace(g_uuid, " ", "")
        If Len(g_uuid) = 32 Then
            g_uuid = Left(g_uuid, 8) & "-" & Mid(g_uuid, 9, 4) & "-" & Mid(g_uuid, 13, 4) & "-" & Mid(g_uuid, 17, 4) & "-" & Right(g_uuid, 12)
        End If
    End If
End Sub

'==========================================================================
' Execute Modules
'==========================================================================
Sub ExecuteModules()
    Dim moduleConfig
    Dim modules, i
    
    modules = Array("Systeminfo", "Hardware", "MEMinfo", "Diskinfo", "Softwareinfo", "Netinfo", "Hotfixinfo", "Processinfo", "Userinfo", "Environment", "Startupinfo")
    
    On Error Resume Next
    If IsObject(g_config) And IsObject(g_config.Modules) Then
        Set moduleConfig = g_config.Modules
    Else
        Set moduleConfig = Nothing
    End If
    Err.Clear
    
    For i = 0 To UBound(modules)
        Call RunModule(modules(i), moduleConfig)
    Next
End Sub

'==========================================================================
' Run Module
'==========================================================================
Sub RunModule(moduleName, moduleConfig)
    Dim enabled
    
    enabled = True
    On Error Resume Next
    If IsObject(moduleConfig) Then
        Select Case moduleName
            Case "Systeminfo": enabled = moduleConfig.Systeminfo
            Case "Hardware": enabled = moduleConfig.Hardware
            Case "MEMinfo": enabled = moduleConfig.MEMinfo
            Case "Diskinfo": enabled = moduleConfig.Diskinfo
            Case "Softwareinfo": enabled = moduleConfig.Softwareinfo
            Case "Netinfo": enabled = moduleConfig.Netinfo
            Case "Hotfixinfo": enabled = moduleConfig.Hotfixinfo
            Case "Processinfo": enabled = moduleConfig.Processinfo
            Case "Userinfo": enabled = moduleConfig.Userinfo
            Case "Environment": enabled = moduleConfig.Environment
            Case "Startupinfo": enabled = moduleConfig.Startupinfo
        End Select
    End If
    Err.Clear
    
    If Not enabled Then
        WScript.Echo "Module " & moduleName & " is disabled."
        Exit Sub
    End If
    
    WScript.Echo "Running module: " & moduleName
    
    Select Case moduleName
        Case "Systeminfo": Call Module_Systeminfo()
        Case "Hardware": Call Module_Hardware()
        Case "MEMinfo": Call Module_MEMinfo()
        Case "Diskinfo": Call Module_Diskinfo()
        Case "Softwareinfo": Call Module_Softwareinfo()
        Case "Netinfo": Call Module_Netinfo()
        Case "Hotfixinfo": Call Module_Hotfixinfo()
        Case "Processinfo": Call Module_Processinfo()
        Case "Userinfo": Call Module_Userinfo()
        Case "Environment": Call Module_Environment()
        Case "Startupinfo": Call Module_Startupinfo()
    End Select
End Sub

'==========================================================================
' Module: Systeminfo
'==========================================================================
Sub Module_Systeminfo()
    Dim colItems, objItem, colBoard, board
    Dim boardManufacturer, boardProduct, boardSerial, biosVersion, biosReleaseDate
    Dim osCaption, osVersion, installDate, lastBootTime
    Dim outputFile
    Dim stream
    
    On Error Resume Next
    
    Set colBoard = objWMIService.ExecQuery("SELECT * FROM Win32_BaseBoard")
    For Each board In colBoard
        boardManufacturer = board.Manufacturer
        boardProduct = board.Product
        boardSerial = board.SerialNumber
    Next
    
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_BIOS")
    For Each objItem In colItems
        biosVersion = objItem.SMBIOSBIOSVersion
        biosReleaseDate = Left(objItem.ReleaseDate, 4) & "-" & Mid(objItem.ReleaseDate, 5, 2) & "-" & Mid(objItem.ReleaseDate, 7, 2)
    Next
    
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_OperatingSystem")
    For Each objItem In colItems
        osCaption = objItem.Caption
        osVersion = objItem.Version
        installDate = Left(objItem.InstallDate, 4) & "-" & Mid(objItem.InstallDate, 5, 2) & "-" & Mid(objItem.InstallDate, 7, 2)
        lastBootTime = Left(objItem.LastBootUpTime, 4) & "-" & Mid(objItem.LastBootUpTime, 5, 2) & "-" & Mid(objItem.LastBootUpTime, 7, 2) & " " & Mid(objItem.LastBootUpTime, 9, 2) & ":" & Mid(objItem.LastBootUpTime, 11, 2)
    Next
    
    outputFile = g_outputPath & "PcInfo-Systeminfo-" & g_computerName & "-" & g_FileDate & ".csv"
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Mode = 3
    stream.Charset = "UTF-8"
    stream.Open
    stream.WriteText "CollectionDate,UUID,ComputerName,Manufacturer,Product,SerialNumber,BIOSVersion,BIOSReleaseDate,OSCaption,OSVersion,InstallDate,LastBootTime"
    stream.WriteText vbCrLf
    stream.WriteText g_colldate & "," & g_uuid & "," & g_computerName & "," & boardManufacturer & "," & boardProduct & "," & boardSerial & "," & biosVersion & "," & biosReleaseDate & "," & osCaption & "," & osVersion & "," & installDate & "," & lastBootTime
    stream.SaveToFile outputFile, 2
    stream.Close
    Set stream = Nothing
    
    g_moduleResults.Add "Systeminfo", "{""status"":""success"",""file"":""" & outputFile & """}"
End Sub

'==========================================================================
' Module: Hardware
'==========================================================================
Sub Module_Hardware()
    Dim colItems, objItem
    Dim outputFile
    Dim stream
    
    On Error Resume Next
    
    outputFile = g_outputPath & "PcInfo-Hardware-" & g_computerName & "-" & g_FileDate & ".csv"
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Mode = 3
    stream.Charset = "UTF-8"
    stream.Open
    stream.WriteText "CollectionDate,HardwareType,HardwareName,Detail1,Detail2,Detail3,Detail4"
    stream.WriteText vbCrLf
    
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_Processor")
    For Each objItem In colItems
        stream.WriteText g_colldate & ",CPU," & objItem.Name & "," & objItem.NumberOfCores & "," & objItem.NumberOfLogicalProcessors & "," & objItem.MaxClockSpeed & ","
        stream.WriteText vbCrLf
    Next
    
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_DiskDrive")
    For Each objItem In colItems
        stream.WriteText g_colldate & ",HardDisk," & objItem.Model & "," & objItem.InterfaceType & "," & Round(objItem.Size / 1024 / 1024 / 1024, 2) & "GB," & objItem.SerialNumber & ","
        stream.WriteText vbCrLf
    Next
    
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_VideoController")
    For Each objItem In colItems
        stream.WriteText g_colldate & ",GPU," & objItem.Name & "," & Round(objItem.AdapterRAM / 1024 / 1024, 2) & "MB," & objItem.DriverVersion & ",,"
        stream.WriteText vbCrLf
    Next
    
    stream.SaveToFile outputFile, 2
    stream.Close
    Set stream = Nothing
    
    g_moduleResults.Add "Hardware", "{""status"":""success"",""file"":""" & outputFile & """}"
End Sub

'==========================================================================
' Module: MEMinfo
'==========================================================================
Sub Module_MEMinfo()
    Dim colItems, objItem
    Dim totalMemory, outputFile
    Dim stream
    
    On Error Resume Next
    
    outputFile = g_outputPath & "PcInfo-MEMinfo-" & g_computerName & "-" & g_FileDate & ".csv"
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Mode = 3
    stream.Charset = "UTF-8"
    stream.Open
    stream.WriteText "CollectionDate,CapacityGB,Speed,MemoryType"
    stream.WriteText vbCrLf
    
    totalMemory = 0
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_PhysicalMemory")
    For Each objItem In colItems
        totalMemory = totalMemory + objItem.Capacity
        stream.WriteText g_colldate & "," & Round(objItem.Capacity / 1024 / 1024 / 1024, 2) & "," & objItem.Speed & "," & objItem.MemoryType
        stream.WriteText vbCrLf
    Next
    
    stream.SaveToFile outputFile, 2
    stream.Close
    Set stream = Nothing
    
    g_moduleResults.Add "MEMinfo", "{""status"":""success"",""file"":""" & outputFile & """}"
End Sub

'==========================================================================
' Module: Diskinfo
'==========================================================================
Sub Module_Diskinfo()
    Dim colLogicalDisks, objLogicalDisk
    Dim colDiskPartitions, objPartition
    Dim colPhysicalDisks, objPhysicalDisk
    Dim outputFile
    Dim driveLetter, totalSizeGB, freeSpaceGB, freePercent
    Dim diskModel, diskInterface, physicalDiskSizeGB
    Dim partitionDeviceID, physicalDiskDeviceID
    Dim stream
    
    On Error Resume Next
    
    outputFile = g_outputPath & "PcInfo-Diskinfo-" & g_computerName & "-" & g_FileDate & ".csv"
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Mode = 3
    stream.Charset = "UTF-8"
    stream.Open
    stream.WriteText "CollectionDate,PhysicalDiskModel,InterfaceType,PhysicalDiskSizeGB,DriveLetter,TotalSizeGB,FreeSpaceGB,FreeSpacePercent"
    stream.WriteText vbCrLf
    
    Set colLogicalDisks = objWMIService.ExecQuery("SELECT * FROM Win32_LogicalDisk WHERE DriveType = 3")
    
    For Each objLogicalDisk In colLogicalDisks
        driveLetter = objLogicalDisk.DeviceID
        totalSizeGB = Round(objLogicalDisk.Size / 1024 / 1024 / 1024, 2)
        freeSpaceGB = Round(objLogicalDisk.FreeSpace / 1024 / 1024 / 1024, 2)
        
        If totalSizeGB > 0 Then
            freePercent = Round((freeSpaceGB / totalSizeGB) * 100, 2)
        Else
            freePercent = 0
        End If
        
        diskModel = ""
        diskInterface = ""
        physicalDiskSizeGB = ""
        
        Set colDiskPartitions = objWMIService.ExecQuery("ASSOCIATORS OF {Win32_LogicalDisk.DeviceID='" & driveLetter & "'} WHERE AssocClass = Win32_LogicalDiskToPartition")
        
        For Each objPartition In colDiskPartitions
            partitionDeviceID = objPartition.DeviceID
            
            Set colPhysicalDisks = objWMIService.ExecQuery("ASSOCIATORS OF {Win32_DiskPartition.DeviceID='" & partitionDeviceID & "'} WHERE AssocClass = Win32_DiskDriveToDiskPartition")
            
            For Each objPhysicalDisk In colPhysicalDisks
                diskModel = objPhysicalDisk.Model
                diskInterface = objPhysicalDisk.InterfaceType
                physicalDiskSizeGB = Round(objPhysicalDisk.Size / 1024 / 1024 / 1024, 2)
            Next
        Next
        
        stream.WriteText g_colldate & "," & diskModel & "," & diskInterface & "," & physicalDiskSizeGB & "," & driveLetter & "," & totalSizeGB & "," & freeSpaceGB & "," & freePercent & "%"
        stream.WriteText vbCrLf
    Next
    
    stream.SaveToFile outputFile, 2
    stream.Close
    Set stream = Nothing
    
    g_moduleResults.Add "Diskinfo", "{""status"":""success"",""file"":""" & outputFile & """}"
End Sub

'==========================================================================
' Module: Softwareinfo
'==========================================================================
Sub Module_Softwareinfo()
    Dim oReg, strKeyPath, arrSubKeys, strSubKey
    Dim sKeyValuesAry, iKeyTypesAry, nCnt, sValue
    Dim sDisplayName, sDisplayVersion, sPublisher, sInstallDate
    Dim outputFile
    Dim stream
    
    On Error Resume Next
    
    outputFile = g_outputPath & "PcInfo-Softwareinfo-" & g_computerName & "-" & g_FileDate & ".csv"
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Mode = 3
    stream.Charset = "UTF-8"
    stream.Open
    stream.WriteText "CollectionDate,SoftwareName,Version,Publisher,InstallDate"
    stream.WriteText vbCrLf
    
    Set oReg = GetObject("winmgmts:{impersonationLevel=impersonate}!\\.\root\default:StdRegProv")
    strKeyPath = UNINSTALL_ROOT
    oReg.EnumKey HKEY_LOCAL_MACHINE, strKeyPath, arrSubKeys
    
    For Each strSubKey In arrSubKeys
        If Left(strSubKey, 2) <> "KB" Then
            sDisplayName = ""
            sDisplayVersion = ""
            sPublisher = ""
            sInstallDate = ""
            
            oReg.EnumValues HKEY_LOCAL_MACHINE, strKeyPath & "\" & strSubKey, sKeyValuesAry, iKeyTypesAry
            If IsArray(sKeyValuesAry) Then
                For nCnt = 0 To UBound(sKeyValuesAry)
                    If LCase(sKeyValuesAry(nCnt)) = "displayname" Then
                        oReg.GetStringValue HKEY_LOCAL_MACHINE, strKeyPath & "\" & strSubKey, sKeyValuesAry(nCnt), sValue
                        If sValue <> "" Then sDisplayName = sValue
                    End If
                    If LCase(sKeyValuesAry(nCnt)) = "displayversion" Then
                        oReg.GetStringValue HKEY_LOCAL_MACHINE, strKeyPath & "\" & strSubKey, sKeyValuesAry(nCnt), sValue
                        If sValue <> "" Then sDisplayVersion = sValue
                    End If
                    If LCase(sKeyValuesAry(nCnt)) = "publisher" Then
                        oReg.GetStringValue HKEY_LOCAL_MACHINE, strKeyPath & "\" & strSubKey, sKeyValuesAry(nCnt), sValue
                        If sValue <> "" Then sPublisher = sValue
                    End If
                    If LCase(sKeyValuesAry(nCnt)) = "installdate" Then
                        oReg.GetStringValue HKEY_LOCAL_MACHINE, strKeyPath & "\" & strSubKey, sKeyValuesAry(nCnt), sValue
                        If sValue <> "" Then sInstallDate = sValue
                    End If
                Next
                
                If sDisplayName <> "" Then
                    stream.WriteText g_colldate & "," & sDisplayName & "," & sDisplayVersion & "," & sPublisher & "," & sInstallDate
                    stream.WriteText vbCrLf
                End If
            End If
        End If
    Next
    
    stream.SaveToFile outputFile, 2
    stream.Close
    Set stream = Nothing
    
    g_moduleResults.Add "Softwareinfo", "{""status"":""success"",""file"":""" & outputFile & """}"
End Sub

'==========================================================================
' Module: Netinfo
'==========================================================================
Sub Module_Netinfo()
    Dim colItems, objItem
    Dim ipAddress, gateway, dns, outputFile
    Dim stream
    
    On Error Resume Next
    
    outputFile = g_outputPath & "PcInfo-Netinfo-" & g_computerName & "-" & g_FileDate & ".csv"
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Mode = 3
    stream.Charset = "UTF-8"
    stream.Open
    stream.WriteText "CollectionDate,Description,IPAddress,MACAddress,DefaultIPGateway,DHCPEnabled"
    stream.WriteText vbCrLf
    
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_NetworkAdapterConfiguration WHERE IPEnabled=True")
    For Each objItem In colItems
        ipAddress = ""
        If Not IsNull(objItem.IPAddress) Then
            ipAddress = Join(objItem.IPAddress, ";")
        End If
        
        gateway = ""
        If Not IsNull(objItem.DefaultIPGateway) Then
            gateway = Join(objItem.DefaultIPGateway, ";")
        End If
        
        stream.WriteText g_colldate & "," & objItem.Description & "," & ipAddress & "," & objItem.MACAddress & "," & gateway & "," & objItem.DHCPEnabled
        stream.WriteText vbCrLf
    Next
    
    stream.SaveToFile outputFile, 2
    stream.Close
    Set stream = Nothing
    
    g_moduleResults.Add "Netinfo", "{""status"":""success"",""file"":""" & outputFile & """}"
End Sub

'==========================================================================
' Module: Hotfixinfo
'==========================================================================
Sub Module_Hotfixinfo()
    Dim colItems, objItem
    Dim outputFile
    Dim installDate
    Dim stream
    
    On Error Resume Next
    
    outputFile = g_outputPath & "PcInfo-Hotfixinfo-" & g_computerName & "-" & g_FileDate & ".csv"
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Mode = 3
    stream.Charset = "UTF-8"
    stream.Open
    stream.WriteText "CollectionDate,HotFixID,InstalledOn,Description"
    stream.WriteText vbCrLf
    
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_QuickFixEngineering")
    
    For Each objItem In colItems
        installDate = objItem.InstalledOn
        If Len(installDate) = 8 Then
            installDate = Left(installDate, 4) & "-" & Mid(installDate, 5, 2) & "-" & Mid(installDate, 7, 2)
        End If
        
        stream.WriteText g_colldate & "," & objItem.HotFixID & "," & installDate & "," & objItem.Description
        stream.WriteText vbCrLf
    Next
    
    stream.SaveToFile outputFile, 2
    stream.Close
    Set stream = Nothing
    
    g_moduleResults.Add "Hotfixinfo", "{""status"":""success"",""file"":""" & outputFile & """}"
End Sub

'==========================================================================
' Module: Processinfo
'==========================================================================
Sub Module_Processinfo()
    Dim colItems, objItem
    Dim outputFile
    Dim procDict, procCountDict, procName, wsMB
    Dim sortedProcs(), sortedMems(), i, a, b
    Dim tempMem, tempName
    Dim stream
    
    On Error Resume Next
    
    Set procDict = CreateObject("Scripting.Dictionary")
    Set procCountDict = CreateObject("Scripting.Dictionary")
    
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_Process")
    For Each objItem In colItems
        procName = objItem.Name
        wsMB = Round(objItem.WorkingSetSize / 1024 / 1024, 2)
        
        If procDict.Exists(procName) Then
            procDict(procName) = procDict(procName) + wsMB
            procCountDict(procName) = procCountDict(procName) + 1
        Else
            procDict.Add procName, wsMB
            procCountDict.Add procName, 1
        End If
    Next
    
    ReDim sortedProcs(procDict.Count - 1), sortedMems(procDict.Count - 1)
    i = 0
    For Each procName In procDict.Keys
        sortedProcs(i) = procName
        sortedMems(i) = procDict(procName)
        i = i + 1
    Next
    
    For a = 0 To procDict.Count - 2
        For b = a + 1 To procDict.Count - 1
            If sortedMems(a) < sortedMems(b) Then
                tempMem = sortedMems(a)
                sortedMems(a) = sortedMems(b)
                sortedMems(b) = tempMem
                tempName = sortedProcs(a)
                sortedProcs(a) = sortedProcs(b)
                sortedProcs(b) = tempName
            End If
        Next
    Next
    
    outputFile = g_outputPath & "PcInfo-Processinfo-" & g_computerName & "-" & g_FileDate & ".csv"
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Mode = 3
    stream.Charset = "UTF-8"
    stream.Open
    stream.WriteText "CollectionDate,ProcessName,ProcessCount,TotalWorkingSetSizeMB"
    stream.WriteText vbCrLf
    
    For i = 0 To procDict.Count - 1
        stream.WriteText g_colldate & "," & sortedProcs(i) & "," & procCountDict(sortedProcs(i)) & "," & sortedMems(i)
        stream.WriteText vbCrLf
    Next
    
    stream.SaveToFile outputFile, 2
    stream.Close
    Set stream = Nothing
    
    g_moduleResults.Add "Processinfo", "{""status"":""success"",""file"":""" & outputFile & """}"
End Sub

'==========================================================================
' Module: Userinfo
'==========================================================================
Sub Module_Userinfo()
    Dim colItems, objItem
    Dim outputFile
    Dim stream
    
    On Error Resume Next
    
    outputFile = g_outputPath & "PcInfo-Userinfo-" & g_computerName & "-" & g_FileDate & ".csv"
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Mode = 3
    stream.Charset = "UTF-8"
    stream.Open
    stream.WriteText "CollectionDate,UserName,Domain,SID,LocalAccount"
    stream.WriteText vbCrLf
    
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_UserAccount WHERE LocalAccount=True")
    For Each objItem In colItems
        stream.WriteText g_colldate & "," & objItem.Name & "," & objItem.Domain & "," & objItem.SID & "," & objItem.LocalAccount
        stream.WriteText vbCrLf
    Next
    
    stream.SaveToFile outputFile, 2
    stream.Close
    Set stream = Nothing
    
    g_moduleResults.Add "Userinfo", "{""status"":""success"",""file"":""" & outputFile & """}"
End Sub

'==========================================================================
' Module: Environment
'==========================================================================
Sub Module_Environment()
    Dim colItems, objItem
    Dim outputFile
    Dim stream
    
    On Error Resume Next
    
    outputFile = g_outputPath & "PcInfo-Environment-" & g_computerName & "-" & g_FileDate & ".csv"
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Mode = 3
    stream.Charset = "UTF-8"
    stream.Open
    stream.WriteText "CollectionDate,VariableName,VariableValue"
    stream.WriteText vbCrLf
    
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_Environment")
    For Each objItem In colItems
        stream.WriteText g_colldate & "," & objItem.Name & "," & objItem.VariableValue
        stream.WriteText vbCrLf
    Next
    
    stream.SaveToFile outputFile, 2
    stream.Close
    Set stream = Nothing
    
    g_moduleResults.Add "Environment", "{""status"":""success"",""file"":""" & outputFile & """}"
End Sub

'==========================================================================
' Module: Startupinfo
'==========================================================================
Sub Module_Startupinfo()
    Dim colStartupCommands, objStartupCommand
    Dim objFSO, objFolder, objFile
    Dim outputFile
    Dim stream
    Dim startupFolders, folder
    Dim exePath
    Dim disabledItems
    
    On Error Resume Next
    
    outputFile = g_outputPath & "PcInfo-Startupinfo-" & g_computerName & "-" & g_FileDate & ".csv"
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Mode = 3
    stream.Charset = "UTF-8"
    stream.Open
    stream.WriteText "CollectionDate,Name,Command,Location,User"
    stream.WriteText vbCrLf
    
    Set objFSO = CreateObject("Scripting.FileSystemObject")
    
    Set disabledItems = GetDisabledStartupItems()
    
    Set colStartupCommands = objWMIService.ExecQuery("SELECT * FROM Win32_StartupCommand")
    
    For Each objStartupCommand In colStartupCommands
        If Not disabledItems.Exists(objStartupCommand.Name) Then
            exePath = ExtractExePath(objStartupCommand.Command)
            
            If exePath <> "" Then
                If objFSO.FileExists(exePath) Then
                    stream.WriteText g_colldate & "," & EscapeCSV(objStartupCommand.Name) & "," & EscapeCSV(objStartupCommand.Command) & ",Registry," & EscapeCSV(objStartupCommand.User)
                    stream.WriteText vbCrLf
                End If
            Else
                stream.WriteText g_colldate & "," & EscapeCSV(objStartupCommand.Name) & "," & EscapeCSV(objStartupCommand.Command) & ",Registry," & EscapeCSV(objStartupCommand.User)
                stream.WriteText vbCrLf
            End If
        End If
    Next
    
    startupFolders = Array( _
        objFSO.GetSpecialFolder(2) & "\Microsoft\Windows\Start Menu\Programs\Startup", _
        objFSO.GetSpecialFolder(0) & "\Microsoft\Windows\Start Menu\Programs\Startup" _
    )
    
    For Each folder In startupFolders
        If objFSO.FolderExists(folder) Then
            Set objFolder = objFSO.GetFolder(folder)
            For Each objFile In objFolder.Files
                If Not disabledItems.Exists(objFile.Name) Then
                    If objFSO.FileExists(objFile.Path) Then
                        stream.WriteText g_colldate & "," & EscapeCSV(objFile.Name) & "," & EscapeCSV(objFile.Path) & ",StartupFolder,"
                        stream.WriteText vbCrLf
                    End If
                End If
            Next
        End If
    Next
    
    stream.SaveToFile outputFile, 2
    stream.Close
    Set stream = Nothing
    Set objFSO = Nothing
    
    g_moduleResults.Add "Startupinfo", "{""status"":""success"",""file"":""" & outputFile & """}"
End Sub

'==========================================================================
' Helper Functions
'==========================================================================
Function GetDisabledStartupItems()
    Dim disabledDict
    Dim oReg, strKeyPath, arrSubKeys, strSubKey
    Dim startupApprovedPaths, path, i
    Dim valueData, valueType
    Dim wshShell
    
    On Error Resume Next
    
    Set disabledDict = CreateObject("Scripting.Dictionary")
    Set wshShell = CreateObject("WScript.Shell")
    
    Set oReg = GetObject("winmgmts:{impersonationLevel=impersonate}!\\.\root\default:StdRegProv")
    
    startupApprovedPaths = Array( _
        "Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run", _
        "Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32", _
        "Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder" _
    )
    
    For i = 0 To UBound(startupApprovedPaths)
        CheckStartupApproved oReg, &H80000001, startupApprovedPaths(i), disabledDict
        CheckStartupApproved oReg, &H80000002, startupApprovedPaths(i), disabledDict
    Next
    
    Dim runBackupPaths
    runBackupPaths = Array( _
        "Software\Microsoft\Windows\CurrentVersion\Run-", _
        "Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run-" _
    )
    
    For i = 0 To UBound(runBackupPaths)
        CheckDisabledRunKey oReg, &H80000001, runBackupPaths(i), disabledDict
        CheckDisabledRunKey oReg, &H80000002, runBackupPaths(i), disabledDict
    Next
    
    Set GetDisabledStartupItems = disabledDict
    Set oReg = Nothing
    Set wshShell = Nothing
End Function

Sub CheckStartupApproved(oReg, hive, keyPath, disabledDict)
    Dim arrSubKeys, strSubKey
    Dim valueData, valueType
    Dim isDisabled
    
    On Error Resume Next
    
    oReg.EnumValues hive, keyPath, arrSubKeys
    If IsArray(arrSubKeys) Then
        For Each strSubKey In arrSubKeys
            oReg.GetBinaryValue hive, keyPath, strSubKey, valueData
            If Not IsNull(valueData) Then
                isDisabled = False
                If UBound(valueData) >= 3 Then
                    If valueData(0) = 3 Or valueData(0) = 1 Then
                        isDisabled = True
                    End If
                End If
                
                If isDisabled Then
                    If Not disabledDict.Exists(strSubKey) Then
                        disabledDict.Add strSubKey, True
                    End If
                End If
            End If
        Next
    End If
End Sub

Sub CheckDisabledRunKey(oReg, hive, keyPath, disabledDict)
    Dim arrSubKeys, strSubKey
    
    On Error Resume Next
    
    oReg.EnumValues hive, keyPath, arrSubKeys
    If IsArray(arrSubKeys) Then
        For Each strSubKey In arrSubKeys
            If Not disabledDict.Exists(strSubKey) Then
                disabledDict.Add strSubKey, True
            End If
        Next
    End If
End Sub

Function ExtractExePath(cmd)
    Dim path
    
    On Error Resume Next
    
    path = ""
    
    If Left(cmd, 1) = """" Then
        Dim secondQuote
        secondQuote = InStr(2, cmd, """""")
        If secondQuote > 0 Then
            path = Mid(cmd, 2, secondQuote - 2)
        End If
    Else
        Dim firstSpace
        firstSpace = InStr(cmd, " ")
        If firstSpace > 0 Then
            path = Left(cmd, firstSpace - 1)
        Else
            path = cmd
        End If
    End If
    
    If InStr(path, "%") > 0 Then
        Dim wshShell2
        Set wshShell2 = CreateObject("WScript.Shell")
        path = wshShell2.ExpandEnvironmentStrings(path)
        Set wshShell2 = Nothing
    End If
    
    ExtractExePath = path
End Function

Function EscapeCSV(str)
    If IsNull(str) Then
        EscapeCSV = ""
    ElseIf InStr(str, ",") > 0 Or InStr(str, vbCr) > 0 Or InStr(str, vbLf) > 0 Or InStr(str, "") > 0 Then
        EscapeCSV = """" & Replace(str, """", """""") & """"
    Else
        EscapeCSV = str
    End If
End Function

'==========================================================================
' Cleanup Old Data
'==========================================================================
Sub CleanupOldData()
    Dim pcInfoFolder, subFolder
    Dim folderDate, cutoffDate
    Dim deletedCount
    
    On Error Resume Next
    
    deletedCount = 0
    cutoffDate = DateAdd("d", -g_keepDays, Now())
    
    WScript.Echo "Cleaning up data older than " & g_keepDays & " days..."
    
    pcInfoFolder = g_fso.GetFile(WScript.ScriptFullName).ParentFolder & "\PcInfo"
    
    If g_fso.FolderExists(pcInfoFolder) Then
        For Each subFolder In g_fso.GetFolder(pcInfoFolder).SubFolders
            If Len(subFolder.Name) = 8 Then
                On Error Resume Next
                folderDate = CDate(Left(subFolder.Name, 4) & "-" & Mid(subFolder.Name, 5, 2) & "-" & Mid(subFolder.Name, 7, 2))
                
                If Err.Number = 0 Then
                    If folderDate < cutoffDate Then
                        WScript.Echo "  Deleting old folder: " & subFolder.Name
                        g_fso.DeleteFolder subFolder.Path, True
                        deletedCount = deletedCount + 1
                    End If
                End If
                Err.Clear
            End If
        Next
    End If
    
    If deletedCount > 0 Then
        WScript.Echo "  Deleted " & deletedCount & " old data folder(s)."
    Else
        WScript.Echo "  No old data to clean up."
    End If
End Sub

'==========================================================================
' HTTP Report to Server
'==========================================================================
Sub ReportToServer()
    Dim http, postData, retryCount
    Dim contentType
    
    On Error Resume Next
    
    If LCase(g_httpFormat) = "prometheus" Then
        postData = BuildPrometheusMetrics()
        contentType = "text/plain"
        WScript.Echo "Reporting Prometheus metrics to: " & g_httpEndpoint
    Else
        postData = BuildReportJSON()
        contentType = "application/json"
        WScript.Echo "Reporting JSON data to: " & g_httpEndpoint
    End If
    
    retryCount = 0
    Do While retryCount < g_httpRetryCount
        Set http = CreateObject("Microsoft.XMLHTTP")
        http.Open "POST", g_httpEndpoint, False
        http.SetRequestHeader "Content-Type", contentType
        http.Send postData
        
        If http.Status = 200 Then
            WScript.Echo "Report successful!"
            Exit Sub
        Else
            WScript.Echo "Report failed (attempt " & (retryCount + 1) & "): HTTP " & http.Status
            If http.Status = 400 Then
                WScript.Echo "Response: " & Left(http.responseText, 200)
            End If
            retryCount = retryCount + 1
            WScript.Sleep 2000
        End If
        
        Set http = Nothing
    Loop
    
    WScript.Echo "Report failed after " & g_httpRetryCount & " attempts."
    Call SaveToLocalCache(postData)
End Sub

'==========================================================================
' Build Report JSON
'==========================================================================
Function BuildReportJSON()
    Dim json, key
    
    json = "{"
    json = json & """computerName"":""" & g_computerName & ""","
    json = json & """uuid"":""" & g_uuid & ""","
    json = json & """serialNumber"":""" & g_snum & ""","
    json = json & """collectionDate"":""" & g_colldate & ""","
    json = json & """customerName"":""" & g_custname & ""","
    json = json & """modules"":["
    
    Dim first
    first = True
    For Each key In g_moduleResults.Keys
        If Not first Then
            json = json & ","
        End If
        first = False
        json = json & g_moduleResults(key)
    Next
    
    json = json & "]}"
    
    BuildReportJSON = json
End Function

'==========================================================================
' Build Prometheus Metrics
'==========================================================================
Function BuildPrometheusMetrics()
    Dim metrics, nl
    Dim totalMemoryGB, freeMemoryGB
    Dim totalDiskGB, freeDiskGB
    Dim cpuUsage, memoryUsagePercent, diskUsagePercent
    Dim cpuCount, memoryCount, diskCount
    Dim softwareCount, processCount, userCount
    Dim startupCount, hotfixCount
    Dim key, moduleResult
    Dim colDisks, objDisk
    Dim colItems, objItem
    Dim oReg, strKeyPath, arrSubKeys
    Dim ipAddress, biosReleaseDate, installDate, osVersion, osCaption
    Dim objFSO, disabledItems, exePath
    Dim startupFolders, folder, objFolder, objFile
    
    On Error Resume Next
    nl = vbLf
    metrics = ""
    
    Set objFSO = CreateObject("Scripting.FileSystemObject")
    
    ' Get IP Address from first enabled network adapter
    ipAddress = ""
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_NetworkAdapterConfiguration WHERE IPEnabled=True")
    For Each objItem In colItems
        If Not IsNull(objItem.IPAddress) Then
            ipAddress = objItem.IPAddress(0)
            Exit For
        End If
    Next
    
    ' Get BIOS Release Date and OS Version
    biosReleaseDate = ""
    osVersion = ""
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_BIOS")
    For Each objItem In colItems
        biosReleaseDate = Left(objItem.ReleaseDate, 4) & "-" & Mid(objItem.ReleaseDate, 5, 2) & "-" & Mid(objItem.ReleaseDate, 7, 2)
        Exit For
    Next
    
    ' Get OS Install Date, OS Version and OS Caption
    installDate = ""
    osCaption = ""
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_OperatingSystem")
    For Each objItem In colItems
        installDate = Left(objItem.InstallDate, 4) & "-" & Mid(objItem.InstallDate, 5, 2) & "-" & Mid(objItem.InstallDate, 7, 2)
        osVersion = objItem.Version
        osCaption = objItem.Caption
        Exit For
    Next
    
    metrics = metrics & "# HELP pc_info Basic system info" & nl
    metrics = metrics & "# TYPE pc_info gauge" & nl
    metrics = metrics & "pc_info{hostname=""" & g_computerName & """,uuid=""" & g_uuid & """,serial=""" & g_snum & """,customer=""" & g_custname & """,ipAddress=""" & ipAddress & """,biosReleaseDate=""" & biosReleaseDate & """,installDate=""" & installDate & """,osVersion=""" & osVersion & """,osCaption=""" & osCaption & """} 1" & nl
    
    ' CPU
    metrics = metrics & nl & "# HELP pc_cpu_usage_percent CPU usage percentage" & nl
    metrics = metrics & "# TYPE pc_cpu_usage_percent gauge" & nl
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_PerfFormattedData_PerfOS_Processor WHERE Name='_Total'")
    For Each objItem In colItems
        cpuUsage = objItem.PercentProcessorTime
        metrics = metrics & "pc_cpu_usage_percent{hostname=""" & g_computerName & """} " & cpuUsage & nl
    Next
    
    metrics = metrics & nl & "# HELP pc_cpu_cores_total Total CPU cores" & nl
    metrics = metrics & "# TYPE pc_cpu_cores_total gauge" & nl
    cpuCount = 0
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_Processor")
    For Each objItem In colItems
        cpuCount = cpuCount + objItem.NumberOfCores
    Next
    metrics = metrics & "pc_cpu_cores_total{hostname=""" & g_computerName & """} " & cpuCount & nl
    
    metrics = metrics & nl & "# HELP pc_cpu_logical_processors Total logical processors" & nl
    metrics = metrics & "# TYPE pc_cpu_logical_processors gauge" & nl
    cpuCount = 0
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_Processor")
    For Each objItem In colItems
        cpuCount = cpuCount + objItem.NumberOfLogicalProcessors
    Next
    metrics = metrics & "pc_cpu_logical_processors{hostname=""" & g_computerName & """} " & cpuCount & nl
    
    ' Memory
    metrics = metrics & nl & "# HELP pc_memory_total_bytes Total physical memory in bytes" & nl
    metrics = metrics & "# TYPE pc_memory_total_bytes gauge" & nl
    metrics = metrics & nl & "# HELP pc_memory_free_bytes Free physical memory in bytes" & nl
    metrics = metrics & "# TYPE pc_memory_free_bytes gauge" & nl
    metrics = metrics & nl & "# HELP pc_memory_used_bytes Used physical memory in bytes" & nl
    metrics = metrics & "# TYPE pc_memory_used_bytes gauge" & nl
    metrics = metrics & nl & "# HELP pc_memory_usage_percent Memory usage percentage" & nl
    metrics = metrics & "# TYPE pc_memory_usage_percent gauge" & nl
    metrics = metrics & nl & "# HELP pc_memory_modules_total Total memory modules" & nl
    metrics = metrics & "# TYPE pc_memory_modules_total gauge" & nl
    
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_OperatingSystem")
    For Each objItem In colItems
        totalMemoryGB = objItem.TotalVisibleMemorySize * 1024
        freeMemoryGB = objItem.FreePhysicalMemory * 1024
        memoryUsagePercent = Round(((objItem.TotalVisibleMemorySize - objItem.FreePhysicalMemory) / objItem.TotalVisibleMemorySize) * 100, 2)
        
        metrics = metrics & "pc_memory_total_bytes{hostname=""" & g_computerName & """} " & totalMemoryGB & nl
        metrics = metrics & "pc_memory_free_bytes{hostname=""" & g_computerName & """} " & freeMemoryGB & nl
        metrics = metrics & "pc_memory_used_bytes{hostname=""" & g_computerName & """} " & (totalMemoryGB - freeMemoryGB) & nl
        metrics = metrics & "pc_memory_usage_percent{hostname=""" & g_computerName & """} " & memoryUsagePercent & nl
    Next
    
    memoryCount = 0
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_PhysicalMemory")
    For Each objItem In colItems
        memoryCount = memoryCount + 1
    Next
    metrics = metrics & "pc_memory_modules_total{hostname=""" & g_computerName & """} " & memoryCount & nl
    
    ' Disk
    metrics = metrics & nl & "# HELP pc_disk_total_bytes Total disk size in bytes" & nl
    metrics = metrics & "# TYPE pc_disk_total_bytes gauge" & nl
    metrics = metrics & nl & "# HELP pc_disk_free_bytes Free disk space in bytes" & nl
    metrics = metrics & "# TYPE pc_disk_free_bytes gauge" & nl
    metrics = metrics & nl & "# HELP pc_disk_used_bytes Used disk space in bytes" & nl
    metrics = metrics & "# TYPE pc_disk_used_bytes gauge" & nl
    metrics = metrics & nl & "# HELP pc_disk_usage_percent Disk usage percentage" & nl
    metrics = metrics & "# TYPE pc_disk_usage_percent gauge" & nl
    
    Set colDisks = objWMIService.ExecQuery("SELECT * FROM Win32_LogicalDisk WHERE DriveType=3")
    For Each objDisk In colDisks
        If Not IsNull(objDisk.Size) And Not IsNull(objDisk.FreeSpace) Then
            totalDiskGB = objDisk.Size
            freeDiskGB = objDisk.FreeSpace
            diskUsagePercent = Round(((totalDiskGB - freeDiskGB) / totalDiskGB) * 100, 2)
            
            metrics = metrics & "pc_disk_total_bytes{hostname=""" & g_computerName & """,drive=""" & objDisk.DeviceID & """} " & totalDiskGB & nl
            metrics = metrics & "pc_disk_free_bytes{hostname=""" & g_computerName & """,drive=""" & objDisk.DeviceID & """} " & freeDiskGB & nl
            metrics = metrics & "pc_disk_used_bytes{hostname=""" & g_computerName & """,drive=""" & objDisk.DeviceID & """} " & (totalDiskGB - freeDiskGB) & nl
            metrics = metrics & "pc_disk_usage_percent{hostname=""" & g_computerName & """,drive=""" & objDisk.DeviceID & """} " & diskUsagePercent & nl
        End If
    Next
    
    metrics = metrics & nl & "# HELP pc_physical_disks_total Total physical disks" & nl
    metrics = metrics & "# TYPE pc_physical_disks_total gauge" & nl
    diskCount = 0
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_DiskDrive")
    For Each objItem In colItems
        diskCount = diskCount + 1
    Next
    metrics = metrics & "pc_physical_disks_total{hostname=""" & g_computerName & """} " & diskCount & nl
    
    ' Software
    metrics = metrics & nl & "# HELP pc_software_installed_total Total installed software count" & nl
    metrics = metrics & "# TYPE pc_software_installed_total gauge" & nl
    softwareCount = 0
    Set oReg = GetObject("winmgmts:{impersonationLevel=impersonate}!\\.\root\default:StdRegProv")
    strKeyPath = "Software\Microsoft\Windows\CurrentVersion\Uninstall"
    oReg.EnumKey &H80000002, strKeyPath, arrSubKeys
    If IsArray(arrSubKeys) Then
        softwareCount = UBound(arrSubKeys) + 1
    End If
    metrics = metrics & "pc_software_installed_total{hostname=""" & g_computerName & """} " & softwareCount & nl
    
    ' Process
    metrics = metrics & nl & "# HELP pc_processes_total Total running processes" & nl
    metrics = metrics & "# TYPE pc_processes_total gauge" & nl
    processCount = 0
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_Process")
    For Each objItem In colItems
        processCount = processCount + 1
    Next
    metrics = metrics & "pc_processes_total{hostname=""" & g_computerName & """} " & processCount & nl
    
    ' User
    metrics = metrics & nl & "# HELP pc_local_users_total Total local users" & nl
    metrics = metrics & "# TYPE pc_local_users_total gauge" & nl
    userCount = 0
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_UserAccount WHERE LocalAccount=True")
    For Each objItem In colItems
        userCount = userCount + 1
    Next
    metrics = metrics & "pc_local_users_total{hostname=""" & g_computerName & """} " & userCount & nl
    
    ' Startup - Count only enabled startup items with existing executables (same logic as CSV)
    metrics = metrics & nl & "# HELP pc_startup_items_total Total startup items" & nl
    metrics = metrics & "# TYPE pc_startup_items_total gauge" & nl
    startupCount = 0
    Set disabledItems = GetDisabledStartupItems()
    
    ' Count registry startup items
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_StartupCommand")
    For Each objItem In colItems
        If Not disabledItems.Exists(objItem.Name) Then
            exePath = ExtractExePath(objItem.Command)
            If exePath <> "" Then
                If objFSO.FileExists(exePath) Then
                    startupCount = startupCount + 1
                End If
            Else
                startupCount = startupCount + 1
            End If
        End If
    Next
    
    ' Count startup folder items
    startupFolders = Array( _
        objFSO.GetSpecialFolder(2) & "\Microsoft\Windows\Start Menu\Programs\Startup", _
        objFSO.GetSpecialFolder(0) & "\Microsoft\Windows\Start Menu\Programs\Startup" _
    )
    
    For Each folder In startupFolders
        If objFSO.FolderExists(folder) Then
            Set objFolder = objFSO.GetFolder(folder)
            For Each objFile In objFolder.Files
                If Not disabledItems.Exists(objFile.Name) Then
                    If objFSO.FileExists(objFile.Path) Then
                        startupCount = startupCount + 1
                    End If
                End If
            Next
        End If
    Next
    
    metrics = metrics & "pc_startup_items_total{hostname=""" & g_computerName & """} " & startupCount & nl
    
    ' Hotfix
    metrics = metrics & nl & "# HELP pc_hotfixes_total Total installed hotfixes" & nl
    metrics = metrics & "# TYPE pc_hotfixes_total gauge" & nl
    hotfixCount = 0
    Set colItems = objWMIService.ExecQuery("SELECT * FROM Win32_QuickFixEngineering")
    For Each objItem In colItems
        hotfixCount = hotfixCount + 1
    Next
    metrics = metrics & "pc_hotfixes_total{hostname=""" & g_computerName & """} " & hotfixCount & nl
    
    ' Module status
    metrics = metrics & nl & "# HELP pc_module_status Module execution status (1=success, 0=failed)" & nl
    metrics = metrics & "# TYPE pc_module_status gauge" & nl
    For Each key In g_moduleResults.Keys
        moduleResult = g_moduleResults(key)
        If InStr(moduleResult, """status"":""success""") > 0 Then
            metrics = metrics & "pc_module_status{hostname=""" & g_computerName & """,module=""" & key & """} 1" & nl
        Else
            metrics = metrics & "pc_module_status{hostname=""" & g_computerName & """,module=""" & key & """} 0" & nl
        End If
    Next
    
    ' Timestamp
    metrics = metrics & nl & "# HELP pc_collection_timestamp Collection timestamp (Unix)" & nl
    metrics = metrics & "# TYPE pc_collection_timestamp gauge" & nl
    metrics = metrics & "pc_collection_timestamp{hostname=""" & g_computerName & """} " & DateDiff("s", "1970-01-01 00:00:00", Now()) & nl
    
    BuildPrometheusMetrics = metrics
End Function

'==========================================================================
' Save to Local Cache
'==========================================================================
Sub SaveToLocalCache(data)
    Dim cacheFile
    Dim stream
    Dim ext
    
    If LCase(g_httpFormat) = "prometheus" Then
        ext = ".txt"
    Else
        ext = ".json"
    End If
    
    cacheFile = g_outputPath & "report_cache_" & g_FileDateStr & ext
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Mode = 3
    stream.Charset = "UTF-8"
    stream.Open
    stream.WriteText data
    stream.SaveToFile cacheFile, 2
    stream.Close
    Set stream = Nothing
    
    WScript.Echo "Data saved to local cache: " & cacheFile
End Sub

'==========================================================================
' Cleanup
'==========================================================================
Sub Cleanup()
    Set g_fso = Nothing
    Set g_moduleResults = Nothing
    Set WshShell = Nothing
    Set objWMIService = Nothing
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
' Entry Point - Check permissions before running Main
'==========================================================================
Dim g_requireAdmin, g_autoElevate
g_requireAdmin = False  ' Default: don't require admin
g_autoElevate = False   ' Default: don't auto elevate

' Load configuration first to get execution settings
Dim tempFSO, tempFile, configPath, configContent
Set tempFSO = CreateObject("Scripting.FileSystemObject")
configPath = tempFSO.GetFile(WScript.ScriptFullName).ParentFolder & "\Conf.json"

If tempFSO.FileExists(configPath) Then
    configContent = ReadTextFile(configPath)
    Dim tempConfig
    Set tempConfig = ParseJSON(configContent)
    On Error Resume Next
    g_requireAdmin = tempConfig.Execution.RequireAdmin
    g_autoElevate = tempConfig.Execution.AutoElevate
    Err.Clear
End If
Set tempFSO = Nothing

' Check admin status and handle according to configuration
If Not IsAdmin() Then
    If g_autoElevate Or g_requireAdmin Then
        ' Auto-elevate if configured (either AutoElevate=true or RequireAdmin=true)
        WScript.Echo "Administrator privileges required."
        WScript.Echo "Requesting elevation..."
        
        Dim scriptPath, args, i
        scriptPath = WScript.ScriptFullName
        args = ""
        For i = 0 To WScript.Arguments.Count - 1
            args = args & " """ & WScript.Arguments(i) & """"
        Next
        
        Dim objShell, cmdArgs
        Set objShell = CreateObject("Shell.Application")
        cmdArgs = "/k cd /d """ & Left(scriptPath, InStrRev(scriptPath, "\")) & """ && cscript.exe //NoLogo """ & scriptPath & """" & args
        objShell.ShellExecute "cmd.exe", cmdArgs, "", "runas", 1
        Set objShell = Nothing
        
        WScript.Sleep 1000
        WScript.Quit
    Else
        ' Continue without admin (default behavior)
        WScript.Echo "Running without administrator privileges."
        WScript.Echo "Some features may be limited."
        WScript.Echo ""
    End If
Else
    WScript.Echo "Running with administrator privileges."
    WScript.Echo ""
End If

Call Main()
