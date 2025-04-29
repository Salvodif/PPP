import os
import argparse

from pathlib import Path
import sys
import traceback

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Label
from textual.containers import Container
from textual.reactive import var

from logic.table_logic import populate_library_table, handle_table_sort
from logic.config_manager_logic import ConfigManagerLogic
from screens.add_book import AddBookScreen
from screens.config_manager import ConfigManager



class LibraryApp(App):
    """A Textual app to display the TinyDB library."""

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("ctrl+r", "sort_table", "Sort by Column"),
        ("ctrl+a", "add_book", "Add New Book"),
        ("ctrl+s", "open_settings", "Settings")
    ]


    config_manager: ConfigManagerLogic
    last_sort_column_key: str | None = None # Chiave dell'ultima colonna ordinata
    sort_reverse: bool = False


    def __init__(self, config_manager: ConfigManagerLogic, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_manager = config_manager

    @property
    def db_path(self) -> str | None:
        return self.config_manager.db_path

    @property
    def library_base_path(self) -> Path | None:
         return self.config_manager.library_path


    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container(id="table-container"):
            yield DataTable(id="library-table", zebra_stripes=True, show_cursor=True, show_header=True, cursor_type="row")
        yield Footer()


    def on_mount(self) -> None:
        """Called when the app is mounted."""
        db_file_path = self.db_path
        if db_file_path:
             self.title = f"Library Viewer - {Path(db_file_path).name}"
        else:
             self.title = "Library Viewer - Error: DB Path not configured"
             self.notify("Critical Error: Database path not found in configuration.", severity="error", timeout=10)
             # Prevent table loading if path is missing
             return

        self.refresh_library_table() # Load data initially




    def refresh_library_table(self) -> None:
        """Clears and re-populates the library table using config paths."""
        # --- Ensure paths are available ---
        db_p = self.db_path
        lib_p = self.library_base_path
        if not db_p or not lib_p:
             self.notify("Error: Cannot refresh table. DB path or Library path missing in config.", severity="error", timeout=10)
             # Optionally hide table / show message
             try:
                 table = self.query_one(DataTable)
                 table.clear()
                 table.visible = False
                 if not self.query("#table-container Label"):
                     self.query_one("#table-container").mount(Label("Configuration path error."))
             except Exception: pass
             return
        # ---------------------------------

        try:
            table = self.query_one(DataTable)
            table.clear() # Clear existing rows before repopulating
            # Clear any previous error messages if they exist
            for label in self.query("#table-container Label"):
                label.remove()
            table.visible = True # Ensure table is visible
            populate_library_table(self, table) # Call the existing loader

            # Restore sort order if previously sorted
            if self.last_sort_column_key:
                # Use a slight delay if needed, but often direct call works
                # self.set_timer(0.1, lambda: table.sort(self.last_sort_column_key, reverse=self.sort_reverse))
                # Direct call might be fine after data is loaded
                 try:
                    table.sort(self.last_sort_column_key, reverse=self.sort_reverse)
                 except Exception as sort_e:
                    print(f"Error re-applying sort: {sort_e}") # Log error, don't crash
                    self.notify(f"Could not re-apply sort: {sort_e}", severity="warning")

        except Exception as e:
            traceback.print_exc()
            self.notify(f"Error refreshing table: {e}", title="Refresh Error", severity="error")
            try:
                # Attempt to hide table and show message on error during refresh
                table = self.query_one(DataTable)
                table.visible = False
                if not self.query("#table-container Label"): # Avoid duplicates
                    self.query_one("#table-container").mount(Label(f"Error loading data: {e}"))
            except Exception: # If table query fails etc.
                 pass # Avoid nested error handling issues


    def action_sort_table(self) -> None:
        handle_table_sort(self)


    def action_add_book(self) -> None:
        """Pushes the AddBookScreen, passing config paths."""
        db_p = self.db_path
        lib_p = self.library_base_path
        if not db_p or not lib_p:
            self.notify("Error: Cannot add book. DB or Library path missing in config.", severity="error")
            return

        # Pass paths from config manager to the AddBookScreen
        add_screen = AddBookScreen(db_path=db_p, library_base_path=lib_p)

        def handle_add_result(result: dict | None) -> None:
            if result and result.get("success"):
                self.notify(result.get("message", "Book added!"), title="Success", timeout=8)
                self.refresh_library_table()
            # Errors are handled within AddBookScreen or logic function

        self.push_screen(add_screen, handle_add_result)

    # --- Action to open settings ---
    def action_open_settings(self) -> None:
        """Pushes the SettingsScreen."""
        settings_screen = ConfigManager(config_manager=self.config_manager)

        # Define callback to handle saving
        def handle_settings_save(new_paths: dict | None) -> None:
            if new_paths: # If data was returned (Save clicked)
                try:
                    self.config_manager.update_paths(new_paths)
                    save_ok = self.config_manager.save_config()
                    if save_ok:
                        self.notify("Settings saved successfully.", title="Settings Saved")
                        # Update title and potentially refresh if db path changed
                        db_file_path = self.db_path
                        if db_file_path:
                           self.title = f"Library Viewer - {Path(db_file_path).name}"
                        else:
                            self.title = "Library Viewer - Error: DB Path not configured"
                        # Consider refreshing the table if paths changed
                        # Especially if db_path or library_path changed
                        self.refresh_library_table()
                    else:
                        self.notify("Error saving settings to config.json.", title="Save Error", severity="error")

                except Exception as e:
                     traceback.print_exc()
                     self.notify(f"Failed to save settings: {e}", title="Save Error", severity="error")
            # If new_paths is None, Cancel was clicked

        self.push_screen(settings_screen, handle_settings_save)


    CSS = """
    Screen {
        align: center middle;
    }

    Container {
        width: 100%; /* Adjust width as needed */
        height: 100%;
    }

    DataTable {
        width: 100%;
        height: 100%;
    }

    AddBookScreen {
        align: center middle;
    }

    #add-form {
        /* Keep existing form styles */
        width: 80%;
        max-width: 80; /* Might need more width for DirectoryTree */
        /* min-height: 20; */ /* Ensure minimum height */
        height: auto; /* Allow vertical expansion */
        border: thick $accent;
        padding: 1 2;
        background: $panel;
        margin-top: 1;
    }

    /* Style the DirectoryTree */
    #file-tree {
        height: 10;
        border: thick $accent;
        margin-bottom: 1;
    }

    /* Style the selected file display */
    #selected-file-display {
        height: auto; /* Allow wrapping */
        margin-bottom: 1; /* Space before author input */
        /* border: round $accent 50%; */ /* Optional border */
        padding: 0 1;
    }
    #selected-file-display:focus {
         border: none; /* Avoid focus border on static text */
    }

    #add-form Input {
        margin-bottom: 1;
    }

    #buttons-container {
        margin-top: 1;
        align: center middle;
        width: 100%;
    }

    #buttons-container Button {
         margin: 0 1;
    }

    #add-form Label.label {
        margin-top: 1;
        margin-bottom: 0;
    }

    #status-message {
        margin-top: 1; /* Reduced margin */
        text-align: center;
        width: 100%;
        height: auto;
        /* border: thin $accent 50%; */ /* Keep it less prominent */
        padding: 0 1;
        /* Consider using text-opacity */
        /* text-opacity: 0.8; */
    }

    #status-message.success {
        color: $success;
    }

    #status-message.error {
        color: $error;
    }

    FileSelectorPanel {
        padding: 1;
        height: auto; /* Or set a specific height */
        min-height: 15; /* Ensure it's not too small */
        width: 100%;
    }

    FileSelectorPanel > .panel-label {
        margin-bottom: 1;
    }

    FileSelectorPanel > FilteredDirectoryTree {
        /* Give the tree a flexible height within the panel */
        /* Or a fixed height like height: 10; */
        height: 1fr;
        margin-bottom: 1;
        border: solid $accent 50%;
    }

    FileSelectorPanel > .panel-controls {
        height: auto;
        align: right middle; /* Align button to the right */
    }

    FileSelectorPanel > .panel-controls > Button {
        margin-left: 1;
        width: auto; /* Let button size itself */
        min-width: 12; /* Ensure minimum width */
    }
    """

# --- Main Execution ---
if __name__ == "__main__":
    # --- Load Configuration First ---
    CONFIG_FILE = "config.json"
    config_manager = ConfigManagerLogic(CONFIG_FILE)
    if not config_manager: # Check if config loaded successfully
        print(f"Failed to load configuration from '{CONFIG_FILE}'. Exiting.")
        sys.exit(1) # Exit if config is essential and failed to load

    # --- Get DB path from config for initial check ---
    db_path_from_config = config_manager.db_path
    if not db_path_from_config:
        print(f"Error: Database path ('paths.db') not found in '{CONFIG_FILE}'.")
        sys.exit(1)
    if not os.path.exists(db_path_from_config):
        print(f"Error: Database file specified in config not found at '{db_path_from_config}'")
        print("Please check the 'paths.db' setting in config.json.")
        # Decide if you want to exit or let the app show an error
        # sys.exit(1) # Optional: exit immediately

    app = LibraryApp(config_manager=config_manager)
    app.run()

