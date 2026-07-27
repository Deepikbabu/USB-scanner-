rule USB_EICAR_Test
{
    meta:
        description = "EICAR antivirus test string"
        severity = 10
        category = "test"
    strings:
        $eicar = "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    condition:
        $eicar
}

rule USB_PowerShell_Dropper
{
    meta:
        description = "Suspicious PowerShell execution pattern"
        severity = 8
        category = "script"
    strings:
        $ps1 = /powershell(\.exe)?\s+(-w\s+hidden|-enc|-nop|-ep\s+bypass)/ nocase
        $iex = /Invoke-Expression|IEX\s*\(/ nocase
    condition:
        any of them
}

rule USB_Command_Dropper
{
    meta:
        description = "Suspicious command-line execution pattern"
        severity = 7
        category = "script"
    strings:
        $cmd = /cmd(\.exe)?\s+\/c/ nocase
        $curl = /curl\s+.*\|\s*(bash|sh|python)/ nocase
    condition:
        any of them
}

rule USB_Autorun_Config
{
    meta:
        description = "Autorun configuration with open directive"
        severity = 6
        category = "autorun"
    strings:
        $autorun = "autorun.inf" nocase
        $open = /open\s*=\s*/ nocase
    condition:
        all of them
}
