# setup.py
# This script handles the Windows Registry integration for jedXIP.
# MUST BE RUN AS ADMINISTRATOR.
# Usage:
#   python setup.py install
#   python setup.py uninstall

import sys
import os
import winreg

def get_script_paths():
    """Finds the absolute paths for the python executable and the main script."""
    # Get the path to the python executable running this script
    python_exe = sys.executable
    
    # Get the directory where this setup.py script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct the full path to the main jedXIP.py script
    main_script_path = os.path.join(script_dir, "jedXIP.py")
    
    if not os.path.exists(main_script_path):
        raise FileNotFoundError(f"Error: jedXIP.py not found in {script_dir}")
        
    return python_exe, main_script_path

def install():
    """Installs the context menu entries in the Windows Registry."""
    print("Attempting to install context menu...")
    
    try:
        python_exe, main_script_path = get_script_paths()
        
        # The command that Windows will execute. "%1" is the placeholder for the clicked file.
        command = f'"{python_exe}" "{main_script_path}" "%1"'
        
        # 1. Define our custom file type
        key_path = r'jedXIP.Archive'
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path)
        winreg.SetValue(key, '', winreg.REG_SZ, 'jedXIP Archive')
        winreg.CloseKey(key)

        # 2. Add the "Open with jedXIP" command to our file type
        key_path = r'jedXIP.Archive\shell\openwithjedxip'
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path)
        winreg.SetValue(key, '', winreg.REG_SZ, 'Open with jedXIP')
        winreg.CloseKey(key)
        
        # 3. Set the actual command string
        key_path = r'jedXIP.Archive\shell\openwithjedxip\command'
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path)
        winreg.SetValue(key, '', winreg.REG_SZ, command)
        winreg.CloseKey(key)
        
        # 4. Associate .xip and .xar extensions with our file type
        key_path = r'.xip'
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path)
        winreg.SetValue(key, '', winreg.REG_SZ, 'jedXIP.Archive')
        winreg.CloseKey(key)
        
        key_path = r'.xar'
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path)
        winreg.SetValue(key, '', winreg.REG_SZ, 'jedXIP.Archive')
        winreg.CloseKey(key)

        print("\nSUCCESS: jedXIP context menu installed!")
        print("You can now right-click on .xip and .xar files.")
        
    except FileNotFoundError as e:
        print(e)
    except PermissionError:
        print("\nERROR: Permission denied.")
        print("Please try again by running the command prompt 'As Administrator'.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

def uninstall():
    """Removes the context menu entries from the Windows Registry."""
    print("Attempting to uninstall context menu...")
    
    try:
        # It's safer to delete keys individually rather than recursively
        keys_to_delete = [
            r'jedXIP.Archive\shell\openwithjedxip\command',
            r'jedXIP.Archive\shell\openwithjedxip',
            r'jedXIP.Archive\shell',
            r'jedXIP.Archive',
            r'.xip',
            r'.xar'
        ]
        
        for key_path in keys_to_delete:
            try:
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path)
                print(f"  - Removed key: {key_path}")
            except FileNotFoundError:
                print(f"  - Key not found (already removed): {key_path}")
                pass

        print("\nSUCCESS: jedXIP context menu uninstalled.")

    except PermissionError:
        print("\nERROR: Permission denied.")
        print("Please try again by running the command prompt 'As Administrator'.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'install':
            install()
        elif sys.argv[1] == 'uninstall':
            uninstall()
        else:
            print(f"Unknown command: '{sys.argv[1]}'")
            print("Usage: python setup.py [install|uninstall]")
    else:
        print("Please provide a command.")
        print("Usage: python setup.py [install|uninstall]")
