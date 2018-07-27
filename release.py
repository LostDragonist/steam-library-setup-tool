import subprocess
import os
import winreg

SCRIPT_NAME = "steam_library_setup_tool.py"

# Find the location of Python 3.6
with winreg.OpenKey( winreg.HKEY_CURRENT_USER, "Software\\Python\\PythonCore\\3.6\\InstallPath" ) as key:
    python_path = winreg.QueryValueEx( key, "" )[ 0 ]

# Find the location of pyinstaller
pyinstall_path = os.path.join( python_path, "Scripts", "pyinstaller.exe" )
if not os.path.exists( pyinstall_path ):
    raise ValueError( "pyinstaller.exe not located at \"{}\"".format( pyinstall_path ) )

# Call pyinstaller
subprocess.call( [ pyinstall_path, SCRIPT_NAME, "--noconsole", "--onefile" ] )