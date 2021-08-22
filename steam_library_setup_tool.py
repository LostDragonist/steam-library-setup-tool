'''
steam-library-setup-tool.py

Small tool to add additional library folders to Steam

Copyright (c) 2018 by LostDragonist
Distributed under the MIT License
'''
import collections
import os
import re
import tkinter as tk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import vdf
import winreg
import random

info_t = collections.namedtuple("info_t", ("key", "value"))


class SteamLibrarySetupTool(tk.Frame):

    COL_ENTRY = 0
    COL_PATH = 1
    COL_BROWSE = 2
    COL_DELETE = 3
    COL_NEW = 3
    COL_ACCEPT = 0
    COL_CANCEL = 0

    def __init__(self, master=None):
        # Initialize tkinter
        tk.Frame.__init__(self, master)

        # Try to read the registry for the location of Steam
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Valve\\Steam") as key:
                value = winreg.QueryValueEx(key, "SteamExe")
                self.steam_path = value[0].replace("/", "\\")
        except:
            self.steam_path = ''

        # Prompt user for location of steam.exe if the registry wasn't useful
        if self.steam_path == '' or not os.path.exists(self.steam_path):
            dialog = filedialog.Open(self, defaultextension='.exe', initialdir=os.path.join("C:\\", "Program Files (x86)", "Steam"),
                                     initialfile="Steam.exe", title="Select Steam.exe", filetypes=(("Steam", "Steam.exe"),))
            self.steam_path = dialog.show().replace("/", "\\")

        if self.steam_path == '':
            messagebox.showerror("Error", "Could not find Steam.exe")
            raise ValueError("Could not find steam.exe")

        # Make sure libraryfolders.vdf exists where we think it should
        self.config_library_vdf = os.path.join(os.path.split(
            self.steam_path)[0], "config", "libraryfolders.vdf")
        self.steamapps_library_vdf = os.path.join(os.path.split(
            self.steam_path)[0], "steamapps", "libraryfolders.vdf")

        # Read library info
        self.new_config = {}
        self.used_contentids = []
        self.createLibraryInfo()
        self.parseLibraryInfo()

        # Initialize GUI stuff
        self.deleteRowButtons = []
        self.browseRowButtons = []
        self.entryLabels = []
        self.entryWidgets = []

        self.entryValues = [tk.StringVar()]
        self.entryValues[0].set(self.steam_path.replace("\\\\", "\\"))
        for key in self.new_config['libraryfolders']:
            if self._isint(key):
                self.entryValues.append(tk.StringVar())
                self.entryValues[-1].set(self.new_config['libraryfolders']
                                         [key]['path'].replace("\\\\", "\\"))

        self.grid()
        self.createWidgets()

    def _isint(self, val):
        retval = None
        try:
            retval = int(val)
        except:
            pass
        return retval is not None

    def createLibraryInfo(self):
        self.new_config = dict()
        self.new_config['libraryfolders'] = dict()

    def parseLibraryInfo(self):
        if os.path.exists(self.config_library_vdf):
            info = vdf.load(open(self.config_library_vdf, 'r'))
        elif os.path.exists(self.steamapps_library_vdf):
            info = vdf.load(open(self.steamapps_library_vdf, 'r'))
        else:
            raise ValueError("Could not find a libraryfolders.vdf file.")

        root = list(info.keys())[0]
        for key in info[root]:
            if self._isint(key):
                # If the value is a dict, must be new format
                if isinstance(info[root][key], dict):
                    self.new_config['libraryfolders'][key] = info[root][key]
                    self.new_config['libraryfolders'][key]['mounted'] = '1'
                    self.used_contentids.append(
                        self.new_config['libraryfolders'][key]['contentid'])

                # Old format is just a string
                elif isinstance(info[root][key], str):
                    # Create new info for the library
                    self.new_config['libraryfolders'][key] = dict()
                    self.new_config['libraryfolders'][key]['path'] = info[root][key]
                    self.new_config['libraryfolders'][key]['label'] = ''
                    self.new_config['libraryfolders'][key]['contentid'] = ''
                    self.new_config['libraryfolders'][key]['totalsize'] = '0'
                    self.new_config['libraryfolders'][key]['mounted'] = '1'
                    self.new_config['libraryfolders'][key]['apps'] = dict()

                # WTF
                else:
                    raise ValueError("Unknown file format")

            else:
                if key.lower() == 'contentstatsid':
                    self.used_contentids.append(info[root][key])

                self.new_config['libraryfolders'][key] = info[root][key]

    def finalizeLibraryInfo(self):
        # To "finalize" the library info, we need to fill out any missing entries.
        for key in self.new_config['libraryfolders']:
            if self._isint(key):
                if self.new_config['libraryfolders'][key]['contentid'] == '':
                    # First try to find a libraryfolder.vdf in the specified path
                    library_vdf_path = os.path.join(
                        self.new_config['libraryfolders'][key]['path'], 'libraryfolder.vdf')
                    if os.path.exists(library_vdf_path):
                        info = vdf.load(open(library_vdf_path, 'r'))
                        root = list(info.keys())[0]
                        for subkey in info[root]:
                            if subkey == 'contentid':
                                self.new_config['libraryfolders'][key]['contentid'] = info[root]['contentid']
                                self.used_contentids.append(
                                    info[root]['contentid'])
                            elif subkey == 'label':
                                self.new_config['libraryfolders'][key]['label'] = info[root]['label']

                # Check again as there might not have been a libraryfolder.vdf or it didn't have a valid ContentID
                if self.new_config['libraryfolders'][key]['contentid'] == '':
                    # Create a random unused number and use that
                    candidate = None
                    while candidate is None or candidate in self.used_contentids:
                        candidate = str(random.randint(1, 10000000000))
                    self.new_config['libraryfolders'][key]['contentid'] = candidate
                    self.used_contentids.append(candidate)

    def writeLibraryInfo(self):
        # Make sure directories all exist
        for key in self.new_config['libraryfolders']:
            if self._isint(key):
                folder = os.path.join(
                    self.new_config['libraryfolders'][key]['path'], 'steamapps')
                if not os.path.exists(folder):
                    if messagebox.askyesno("Create folders?", "Do you want to create the directory \"{}\"?".format(folder)):
                        try:
                            os.makedirs(folder, exist_ok=True)
                        except:
                            messagebox.showerror(
                                "Error", "Error when creating directories")
                            raise

        # Create backups
        try:
            for f_path in [self.config_library_vdf, self.steamapps_library_vdf]:
                if not os.path.exists(f_path):
                    continue

                with open(f_path, 'r') as f_in:
                    with open(f_path + '.bak', 'w') as f_out:
                        f_out.write(f_in.read())
        except:
            if not messagebox.askyesno("Warning", "Failed to create a backup. Proceed anyways?"):
                raise

        # Write the new files
        restore_backup = False
        try:
            vdf.dump(self.new_config, open(
                self.config_library_vdf, 'w'), pretty=True)
            vdf.dump(self.new_config, open(
                self.steamapps_library_vdf, 'w'), pretty=True)
        except:
            restore_backup = True

        # Restore the backup if needed
        if restore_backup:
            messagebox.showerror(
                "Error", "Failed to write libraryfolders.vdf. Restoring backup...")
            try:
                for f_path in [self.config_library_vdf, self.steamapps_library_vdf]:
                    with open(f_path + '.bak', 'r') as f_in:
                        with open(f_path, 'w') as f_out:
                            f_out.write(f_in.read())
            except:
                messagebox.showerror(
                    "Error", "Failed to restore backup! Sorry about that.")
                raise

        # Tell the user stuff is done
        messagebox.showinfo(
            "Complete", "Steam Library Setup is done. Closing program...")
        self.quit()

    def acceptEvent(self):
        listed_libraries = []

        # Parse the new directories list
        for i, entry in enumerate(self.entryValues):
            # Skip the base Steam directory
            if i == 0:
                continue

            # Skip empty rows
            value = entry.get()
            if not value:
                continue

            listed_libraries.append(value)

        # See if any libraries need to be deleted
        something_to_delete = True
        while something_to_delete:
            for key in self.new_config['libraryfolders']:
                if self._isint(key):
                    for library in listed_libraries:
                        if self.new_config['libraryfolders'][key]['path'].lower() == library.lower():
                            break
                    else:
                        print("deleting folder: {}".format(
                            self.new_config['libraryfolders'][key]['path']))
                        del self.new_config['libraryfolders'][key]
                        break
            else:
                something_to_delete = False

        # See if there are new libraries
        for library in listed_libraries:
            new_entry = False
            for key in self.new_config['libraryfolders']:
                if self._isint(key) and self.new_config['libraryfolders'][key]['path'].lower() == library.lower():
                    break
            else:
                print("adding folder: {}".format(library))
                new_entry = True

            if new_entry:
                # Find the first index available
                new_index = 1
                while str(new_index) in self.new_config['libraryfolders']:
                    new_index += 1
                new_index = str(new_index)

                self.new_config['libraryfolders'][new_index] = dict()
                self.new_config['libraryfolders'][new_index]['path'] = library
                self.new_config['libraryfolders'][new_index]['label'] = ''
                self.new_config['libraryfolders'][new_index]['contentid'] = ''
                self.new_config['libraryfolders'][new_index]['totalsize'] = '0'
                self.new_config['libraryfolders'][new_index]['mounted'] = '1'
                self.new_config['libraryfolders'][new_index]['apps'] = dict()

        # Write the library info
        self.finalizeLibraryInfo()
        self.writeLibraryInfo()

    def cancelEvent(self):
        if messagebox.askyesno("Cancel", "Cancel all pending changes and quit?"):
            self.quit()

    def createWidgets(self):
        # Create some headers
        label_header_entry = tk.Label(self, text="Entry")
        label_header_entry.grid(row=0, column=0)
        label_header_path = tk.Label(self, text="Path")
        label_header_path.grid(row=0, column=1)

        # Create the rows for each entry
        # i+1 due to header row
        for i, entry_var in enumerate(self.entryValues):
            self.entryLabels.append(tk.Label(self, text=str(i)))
            self.entryLabels[-1].grid(row=i+1, column=0)

            # i == 0 as the base Steam directory can not be modified
            self.entryWidgets.append(tk.Entry(
                self, textvariable=entry_var, state=tk.DISABLED if i == 0 else tk.NORMAL, width=100))
            #self.entryWidgets.append( tk.Entry( self, textvariable=entry_var, state=tk.DISABLED, width=100 ) )
            self.entryWidgets[-1].grid(row=i+1, column=1)

            # i > 0 as the first row is the base Steam directory and can not be modified
            if i > 0:
                self.browseRowButtons.append(
                    tk.Button(self, text="Browse...", command=lambda row=i: self.browseRow(row)))
                self.browseRowButtons[-1].grid(row=i+1,
                                               column=SteamLibrarySetupTool.COL_BROWSE)

                self.deleteRowButtons.append(
                    tk.Button(self, text="Delete Row", command=lambda row=i: self.deleteRow(row)))
                self.deleteRowButtons[-1].grid(row=i+1,
                                               column=SteamLibrarySetupTool.COL_DELETE)

        # Create the general buttons
        self.acceptButton = tk.Button(
            self, text="Accept", command=self.acceptEvent)
        self.acceptButton.grid(row=len(
            self.entryValues)+1, column=SteamLibrarySetupTool.COL_ACCEPT, sticky=tk.N+tk.E+tk.S+tk.W)

        self.newRowButton = tk.Button(
            self, text="Add Row", command=self.addRow)
        self.newRowButton.grid(row=len(
            self.entryValues)+1, column=SteamLibrarySetupTool.COL_NEW, sticky=tk.N+tk.E+tk.S+tk.W)

        self.cancelButton = tk.Button(
            self, text="Cancel", command=self.cancelEvent)
        self.cancelButton.grid(row=len(
            self.entryValues)+2, column=SteamLibrarySetupTool.COL_CANCEL, sticky=tk.N+tk.E+tk.S+tk.W)

    def addRow(self):
        # Create a new row
        self.entryValues.append(tk.StringVar())
        i = len(self.entryValues)
        self.entryLabels.append(tk.Label(self, text=str(i-1)))
        self.entryLabels[-1].grid(row=i, column=0)

        self.entryWidgets.append(
            tk.Entry(self, textvariable=self.entryValues[-1], width=100))
        self.entryWidgets[-1].grid(row=i, column=1)

        self.browseRowButtons.append(
            tk.Button(self, text="Browse...", command=lambda row=i-1: self.browseRow(row)))
        self.browseRowButtons[-1].grid(
            row=i, column=SteamLibrarySetupTool.COL_BROWSE, sticky=tk.N+tk.E+tk.S+tk.W)

        self.deleteRowButtons.append(tk.Button(
            self, text="Delete Row", command=lambda row=i-1: self.deleteRow(row)))
        self.deleteRowButtons[-1].grid(
            row=i, column=SteamLibrarySetupTool.COL_DELETE, sticky=tk.N+tk.E+tk.S+tk.W)

        # Relocate the general buttons
        self.acceptButton.grid_remove()
        self.acceptButton.grid(
            row=i+1, column=SteamLibrarySetupTool.COL_ACCEPT, sticky=tk.N+tk.E+tk.S+tk.W)

        self.newRowButton.grid_remove()
        self.newRowButton.grid(
            row=i+1, column=SteamLibrarySetupTool.COL_NEW, sticky=tk.N+tk.E+tk.S+tk.W)

        self.cancelButton.grid_remove()
        self.cancelButton.grid(
            row=i+2, column=SteamLibrarySetupTool.COL_CANCEL, sticky=tk.N+tk.E+tk.S+tk.W)

    def deleteRow(self, row_to_delete):
        # Shift the contents from x to N
        for row in range(row_to_delete, len(self.entryValues)):
            if row+1 < len(self.entryValues):
                self.entryValues[row].set(self.entryValues[row+1].get())
        self.entryValues.pop()

        # Remove the row
        self.entryLabels[-1].grid_remove()
        self.entryLabels.pop()

        self.entryWidgets[-1].grid_remove()
        self.entryWidgets.pop()

        self.browseRowButtons[-1].grid_remove()
        self.browseRowButtons.pop()

        self.deleteRowButtons[-1].grid_remove()
        self.deleteRowButtons.pop()

        # Relocate the general buttons
        self.acceptButton.grid_remove()
        self.acceptButton.grid(
            row=row+1, column=SteamLibrarySetupTool.COL_ACCEPT, sticky=tk.N+tk.E+tk.S+tk.W)

        self.newRowButton.grid_remove()
        self.newRowButton.grid(
            row=row+1, column=SteamLibrarySetupTool.COL_NEW, sticky=tk.N+tk.E+tk.S+tk.W)

        self.cancelButton.grid_remove()
        self.cancelButton.grid(
            row=row+3, column=SteamLibrarySetupTool.COL_CANCEL, sticky=tk.N+tk.E+tk.S+tk.W)

    def browseRow(self, row):
        # Open a dialog to find a directory
        new_path = filedialog.Directory(self).show()

        # Remove "\\steamapps" if the user selected it
        if new_path.lower().endswith("\\steamapps"):
            new_path = os.path.split(new_path)[0]

        # Replace "/" with "\\" to keep things consistent
        self.entryValues[row].set(new_path.replace("/", "\\"))


app = SteamLibrarySetupTool()
app.master.title("Steam Library Setup Tool")
app.mainloop()
