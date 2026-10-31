$ErrorActionPreference = 'Continue'
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
$proc = Get-CimInstance Win32_Processor | Select-Object -First 1
"TotalRAM_GB=" + [math]::Round($cs.TotalPhysicalMemory/1GB,2)
"FreeRAM_GB=" + [math]::Round(($os.FreePhysicalMemory*1KB)/1GB,2)
"CommitLimit_GB=" + [math]::Round(($os.TotalVirtualMemorySize*1KB)/1GB,2)
"CommitFree_GB=" + [math]::Round(($os.FreeVirtualMemory*1KB)/1GB,2)
"CPU=" + $proc.Name.Trim()
"Cores=" + $proc.NumberOfCores + " Logical=" + $proc.NumberOfLogicalProcessors
"---disks---"
Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
  "Disk " + $_.DeviceID + " Free_GB=" + [math]::Round($_.FreeSpace/1GB,1) + " Size_GB=" + [math]::Round($_.Size/1GB,1)
}
"---gpu---"
Get-CimInstance Win32_VideoController | ForEach-Object {
  "GPU " + $_.Name + " DriverVersion=" + $_.DriverVersion
}
"---nvidia-smi---"
$nsmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nsmi) { "nvidia-smi FOUND " + $nsmi.Source } else { "nvidia-smi NOT FOUND" }
"---ollama---"
$ol = Get-Command ollama -ErrorAction SilentlyContinue
if ($ol) { "ollama FOUND " + $ol.Source } else { "ollama NOT FOUND" }
