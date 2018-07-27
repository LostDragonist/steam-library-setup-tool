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
import winreg

info_t = collections.namedtuple( "info_t", ( "key", "value" ) )

class SteamLibrarySetupTool( tk.Frame ):

    COL_ENTRY  = 0
    COL_PATH   = 1
    COL_BROWSE = 2
    COL_DELETE = 3
    COL_NEW    = 3
    COL_ACCEPT = 0
    COL_CANCEL = 0

    def __init__( self, master=None ):
        # Initialize tkinter
        tk.Frame.__init__( self, master )

        # Try to read the registry for the location of Steam
        try:
            with winreg.OpenKey( winreg.HKEY_CURRENT_USER, "Software\\Valve\\Steam" ) as key:
                value = winreg.QueryValueEx( key, "SteamExe" )
                self.steam_path = value[0].replace( "/", "\\" )
        except:
            self.steam_path = ''

        # Prompt user for location of steam.exe if the registry wasn't useful
        if self.steam_path == '' or not os.path.exists( self.steam_path ):
            dialog = filedialog.Open( self, defaultextension='.exe', initialdir=os.path.join( "C:\\", "Program Files (x86)", "Steam" ),
                                    initialfile="Steam.exe", title="Select Steam.exe", filetypes=(("Steam", "Steam.exe"),) )
            self.steam_path = dialog.show().replace( "/", "\\" )

        if self.steam_path == '':
            messagebox.showerror( "Error", "Could not find Steam.exe" )
            raise ValueError( "Could not find steam.exe" )

        # Make sure libraryfolders.vdf exists where we think it should
        self.library_vdf_path = os.path.join( os.path.split( self.steam_path )[ 0 ], "steamapps", "libraryfolders.vdf" )
        if not os.path.exists( self.library_vdf_path ):
            messagebox.showerror( "Error", "Could not find libraryfolders.vdf" )
            raise ValueError( "Could not find libraryfolders.vdf" )

        # Parse libraryfolders.vdf
        self.library_info = {}
        self.library_folders = []
        self.parseLibraryInfo()

        # Initialize GUI stuff
        self.deleteRowButtons = []
        self.browseRowButtons = []
        self.entryLabels = []
        self.entryWidgets = []

        self.entryValues = [ tk.StringVar() ]
        self.entryValues[ 0 ].set( self.steam_path.replace( "\\\\", "\\" ) )
        for info in self.library_folders:
            self.entryValues.append( tk.StringVar() )
            self.entryValues[ -1 ].set( info.value.replace( "\\\\", "\\" ) )

        self.grid()
        self.createWidgets()

    def parseLibraryInfo( self ):
        parent = ""
        next_parent = ""
        with open( self.library_vdf_path, 'r' ) as f:
            for line in f:
                # Match for the parent item
                match = re.match( "^\"(.*)\"$", line )
                if match:
                    next_parent = match.group( 1 )
                    continue

                # Match for opening brace
                match = re.match( "^{$", line )
                if match:
                    parent = next_parent
                    next_parent = ""
                    continue

                # Match for closing brace
                match = re.match( "^}$", line )
                if match:
                    parent = ""
                    continue

                # Match for key and value
                match = re.match( "^\\s*\"(.*)\"\\s*\"(.*)\"$", line )
                if match:
                    if parent not in self.library_info:
                        self.library_info[ parent ] = []
                    self.library_info[ parent ].append( info_t( key=match.group( 1 ), value=match.group( 2 ) ) )
                    continue

        # Find the library folders
        for info in self.library_info[ "LibraryFolders" ]:
            try:
                folder_id = int( info.key )
                self.library_folders.append( info )
            except ValueError:
                pass

        # Remove the library folders from the library info
        # They'll be added back in later
        for folder in self.library_folders:
            self.library_info[ "LibraryFolders" ].remove( folder )

    def writeLibraryInfo( self ):
        # Make sure directories all exist
        for folder in self.library_folders:
            new_folder = os.path.join( folder.value, "steamapps" )
            if not os.path.exists( new_folder ):
                if messagebox.askyesno("Create folders?", "Do you want to create the directory \"{}\"?".format( new_folder ) ):
                    try:
                        os.makedirs( new_folder, exist_ok=True )
                    except:
                        messagebox.showerror( "Error", "Error when creating directories" )
                        raise
                else:
                    messagebox.showerror( "Error", "Can not proceed without creating directories" )
                    raise ValueError( "Can not proceed without creating directories" )

        # Add the library folders back to the library info
        for i, folder in enumerate( self.library_folders ):
            self.library_info[ "LibraryFolders" ].append( info_t( key=i+1, value=folder.value.replace( "\\", "\\\\" ) ) )

        # Create a backup
        try:
            with open( self.library_vdf_path, 'r' ) as f_in:
                with open( self.library_vdf_path + '.bak', 'w' ) as f_out:
                    f_out.write( f_in.read() )
        except:
            if not messagebox.askyesno( "Warning", "Failed to create a backup.  Proceed anyways?" ):
                raise

        # Open the new file
        restore_backup = False
        try:
            with open( self.library_vdf_path, 'w' ) as f:
                for parent in self.library_info:
                    f.write( "\"{}\"\n".format( parent ) )
                    f.write( "{\n" )
                    for info in self.library_info[ parent ]:
                        f.write( "\t\"{}\"\t\t\"{}\"\n".format( info.key, info.value ) )
                    f.write( "}\n" )
        except:
            restore_backup = True

        # Restore the backup if needed
        if restore_backup:
            messagebox.showerror( "Error", "Failed to write libraryfolders.vdf.  Restoring backup..." )
            try:
                with open( self.library_vdf_path + '.bak', 'r' ) as f_in:
                    with open( self.library_vdf_path, 'w' ) as f_out:
                        f_out.write( f_in.read() )
            except:
                messagebox.showerror( "Error", "Failed to restore backup!  Sorry about that." )
                raise

        # Tell the user stuff is done
        messagebox.showinfo( "Complete", "Steam Library Setup is done.  Closing program..." )
        self.quit()

    def acceptEvent( self ):
        # Parse the new directories list
        self.library_folders = []
        for i, entry in enumerate( self.entryValues ):
            # Skip the base Steam directory
            if i == 0:
                continue

            # Skip empty rows
            value = entry.get()
            if not value:
                continue

            self.library_folders.append( info_t( key="{}".format( len( self.library_folders ) + 1 ), value=value ) )

        # Write the library info
        self.writeLibraryInfo()

    def cancelEvent( self ):
        if messagebox.askyesno( "Cancel", "Cancel all pending changes and quit?" ):
            self.quit()

    def createWidgets( self ):
        # Create some headers
        label_header_entry = tk.Label( self, text="Entry" )
        label_header_entry.grid( row=0, column=0 )
        label_header_path = tk.Label( self, text="Path" )
        label_header_path.grid( row=0, column=1 )

        # Create the rows for each entry
        # i+1 due to header row
        for i, entry_var in enumerate( self.entryValues ):
            self.entryLabels.append( tk.Label( self, text=str( i ) ) )
            self.entryLabels[ -1 ].grid( row=i+1, column=0 )

            # Github issue #1: Deleting libraries that already exist doesn't work for some reason.
            #                  The workaround for now is disabling the ability to modify or delete
            #                  those libraries.

            # i == 0 as the base Steam directory can not be modified
            #self.entryWidgets.append( tk.Entry( self, textvariable=entry_var, state=tk.DISABLED if i == 0 else tk.NORMAL, width=100 ) )
            self.entryWidgets.append( tk.Entry( self, textvariable=entry_var, state=tk.DISABLED, width=100 ) )
            self.entryWidgets[ -1 ].grid( row=i+1, column=1 )

            # i > 0 as the first row is the base Steam directory and can not be modified
            #if i > 0:
            #    self.browseRowButtons.append( tk.Button( self, text="Browse...", command=lambda row=i: self.browseRow( row ) ) )
            #    self.browseRowButtons[ -1 ].grid( row=i+1, column=SteamLibrarySetupTool.COL_BROWSE )
            #
            #    self.deleteRowButtons.append( tk.Button( self, text="Delete Row", command=lambda row=i: self.deleteRow( row ) ) )
            #    self.deleteRowButtons[ -1 ].grid( row=i+1, column=SteamLibrarySetupTool.COL_DELETE )

        # Create the general buttons
        self.acceptButton = tk.Button( self, text="Accept", command=self.acceptEvent )
        self.acceptButton.grid( row=len( self.entryValues )+1, column=SteamLibrarySetupTool.COL_ACCEPT, sticky=tk.N+tk.E+tk.S+tk.W )

        self.newRowButton = tk.Button( self, text="Add Row", command=self.addRow )
        self.newRowButton.grid( row=len( self.entryValues )+1, column=SteamLibrarySetupTool.COL_NEW, sticky=tk.N+tk.E+tk.S+tk.W )

        self.cancelButton = tk.Button( self, text="Cancel", command=self.cancelEvent )
        self.cancelButton.grid( row=len( self.entryValues )+2, column=SteamLibrarySetupTool.COL_CANCEL, sticky=tk.N+tk.E+tk.S+tk.W )

    def addRow( self ):
        # Create a new row
        self.entryValues.append( tk.StringVar() )
        i = len( self.entryValues )
        self.entryLabels.append( tk.Label( self, text=str( i-1 ) ) )
        self.entryLabels[ -1 ].grid( row=i, column=0 )

        self.entryWidgets.append( tk.Entry( self, textvariable=self.entryValues[ -1 ], width=100 ) )
        self.entryWidgets[ -1 ].grid( row=i, column=1 )

        self.browseRowButtons.append( tk.Button( self, text="Browse...", command=lambda row=i-1: self.browseRow( row ) ) )
        self.browseRowButtons[ -1 ].grid( row=i, column=SteamLibrarySetupTool.COL_BROWSE, sticky=tk.N+tk.E+tk.S+tk.W )

        self.deleteRowButtons.append( tk.Button( self, text="Delete Row", command=lambda row=i-1: self.deleteRow( row ) ) )
        self.deleteRowButtons[ -1 ].grid( row=i, column=SteamLibrarySetupTool.COL_DELETE, sticky=tk.N+tk.E+tk.S+tk.W )

        # Relocate the general buttons
        self.acceptButton.grid_remove()
        self.acceptButton.grid( row=i+1, column=SteamLibrarySetupTool.COL_ACCEPT, sticky=tk.N+tk.E+tk.S+tk.W )

        self.newRowButton.grid_remove()
        self.newRowButton.grid( row=i+1, column=SteamLibrarySetupTool.COL_NEW, sticky=tk.N+tk.E+tk.S+tk.W )

        self.cancelButton.grid_remove()
        self.cancelButton.grid( row=i+2, column=SteamLibrarySetupTool.COL_CANCEL, sticky=tk.N+tk.E+tk.S+tk.W )

    def deleteRow( self, row_to_delete ):
        # Shift the contents from x to N
        for row in range( row_to_delete, len( self.entryValues ) ):
            if row+1 < len( self.entryValues ):
                self.entryValues[ row ].set( self.entryValues[ row+1 ].get() )
        self.entryValues.pop()

        # Remove the row
        self.entryLabels[ -1 ].grid_remove()
        self.entryLabels.pop()

        self.entryWidgets[ -1 ].grid_remove()
        self.entryWidgets.pop()

        self.browseRowButtons[ -1 ].grid_remove()
        self.browseRowButtons.pop()

        self.deleteRowButtons[ -1 ].grid_remove()
        self.deleteRowButtons.pop()

        # Relocate the general buttons
        self.acceptButton.grid_remove()
        self.acceptButton.grid( row=row+1, column=SteamLibrarySetupTool.COL_ACCEPT, sticky=tk.N+tk.E+tk.S+tk.W )

        self.newRowButton.grid_remove()
        self.newRowButton.grid( row=row+1, column=SteamLibrarySetupTool.COL_NEW, sticky=tk.N+tk.E+tk.S+tk.W )

        self.cancelButton.grid_remove()
        self.cancelButton.grid( row=row+3, column=SteamLibrarySetupTool.COL_CANCEL, sticky=tk.N+tk.E+tk.S+tk.W )

    def browseRow( self, row ):
        # Open a dialog to find a directory
        new_path = filedialog.Directory( self ).show()

        # Remove "\\steamapps" if the user selected it
        if new_path.lower().endswith( "\\steamapps" ):
            new_path = os.path.split( new_path )[ 0 ]

        # Replace "/" with "\\" to keep things consistent
        self.entryValues[ row ].set( new_path.replace( "/", "\\" ) )

app = SteamLibrarySetupTool()
app.master.title( "Steam Library Setup Tool" )
app.mainloop()
