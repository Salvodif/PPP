
import traceback
from typing import TYPE_CHECKING, Dict

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Input, Button, Label, Static,
    TabbedContent, TabPane, TextArea, DataTable
)
from textual.containers import Vertical, Horizontal 
from textual.message import Message



# Import ConfigManager only for type hinting to avoid circular imports
if TYPE_CHECKING:
    from logic.config_manager_logic import ConfigManager


class ConfigManager(Screen):
    """Screen for editing application path settings."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel"),
        ("ctrl+s", "save_settings", "Save"),
    ]


    # --- Custom Message for Icon Selection ---
    class IconSelected(Message):
        def __init__(self, tag: str, icon: str) -> None:
            super().__init__()
            self.tag = tag
            self.icon = icon



    # Pass the config manager instance when creating the screen
    def __init__(self, config_manager: 'ConfigManager', *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.config_manager = config_manager



    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        # Use TabbedContent to organize settings
        with TabbedContent(id="config-tabs"):
            # --- Paths Pane ---
            with TabPane("Paths", id="tab-paths"):
                with VerticalScroll(id="settings-form-paths"): # Scrollable container
                    yield Label("Database File (.json):", classes="label")
                    yield Input(id="input-db", placeholder="Path to library.json")
                    yield Label("Library Base Directory:", classes="label")
                    yield Input(id="input-library", placeholder="Directory containing author folders")
                    yield Label("Default Upload Directory:", classes="label")
                    yield Input(id="input-upload", placeholder="Directory to browse for new files")
                    yield Label("ExifTool Executable Path:", classes="label")
                    yield Input(id="input-exiftool", placeholder="Path to exiftool.exe (optional)")

            # --- Flat Tags Pane ---
            with TabPane("Flat Tags", id="tab-flat-tags"):
                 with VerticalScroll(id="settings-form-flat-tags"):
                    yield Label("Edit Flat Tags (one tag per line):", classes="label")
                    yield TextArea(id="textarea-flat-tags", language="text", theme="vscode_dark") # Simple text area

            # --- Tag Icons Pane ---
            with TabPane("Tag Icons", id="tab-tag-icons"):
                 # Layout: Table on top, editing controls below
                 yield DataTable(id="table-tag-icons")
                 with Horizontal(id="icon-edit-controls"): # Horizontal layout for inputs/buttons
                     with Vertical(id="icon-inputs"):
                         yield Input(id="input-icon-tag", placeholder="Tag Name")
                         yield Input(id="input-icon-value", placeholder="Icon (e.g., ⭐)")
                     with Vertical(id="icon-buttons"):
                         yield Button("Add/Update", id="btn-icon-add-update", variant="success")
                         yield Button("Delete Sel.", id="btn-icon-delete", variant="error")
                 yield Static(id="icon-status", classes="status-inline") # Feedback for icon ops


        yield Static(id="settings-status", classes="status") # General status/feedback at bottom
        yield Footer()



    def on_mount(self) -> None:
        """Populate widgets with current config values when screen is mounted."""
        # --- Populate Paths ---
        self.query_one("#input-db", Input).value = self.config_manager.db_path or ""
        lib_path = self.config_manager.library_path
        self.query_one("#input-library", Input).value = str(lib_path) if lib_path else ""
        upl_path = self.config_manager.upload_dir
        self.query_one("#input-upload", Input).value = str(upl_path) if upl_path else ""
        exif_path = self.config_manager.exiftool_path
        self.query_one("#input-exiftool", Input).value = exif_path or ""

        # --- Populate Flat Tags ---
        flat_tags_text = "\n".join(self.config_manager.flat_tags)
        self.query_one("#textarea-flat-tags", TextArea).text = flat_tags_text

        # --- Populate Tag Icons ---
        self.populate_icon_table()

        # Focus first input on the default tab
        self.set_timer(0.1, lambda: self.query_one("#input-db", Input).focus())


    def populate_icon_table(self) -> None:
        """Clears and repopulates the tag icon DataTable."""
        table = self.query_one("#table-tag-icons", DataTable)
        table.clear() # Clear previous rows and columns if any
        if not table.columns: # Add columns only if they don't exist
            table.add_column("Tag", key="tag", width=30)
            table.add_column("Icon", key="icon", width=10)
            table.cursor_type = "row" # Ensure row cursor

        # Sort icons by tag name for consistent order, excluding 'default' for now
        sorted_icons = sorted(
            [(tag, icon) for tag, icon in self.config_manager.tag_icons.items() if tag != "default"],
            key=lambda item: item[0]
        )
        # Add the default icon at the end (or beginning if preferred)
        default_icon = self.config_manager.tag_icons.get("default", "📄")
        sorted_icons.append(("default", default_icon))

        for tag, icon in sorted_icons:
            # Use tag name as row key for easy lookup
            table.add_row(tag, icon, key=tag)


    def clear_status(self, status_id: str = "settings-status") -> None:
        """Clears a specific status message."""
        try:
            status_widget = self.query_one(f"#{status_id}", Static)
            status_widget.update("")
            status_widget.remove_class("success", "error")
        except Exception:
            pass # Ignore if widget not found

    def show_status(self, message: str, success: bool = True, status_id: str = "settings-status", clear_after: float = 5.0) -> None:
        """Displays a status message on a specific widget."""
        try:
            status_widget = self.query_one(f"#{status_id}", Static)
            status_widget.update(message)
            status_widget.set_class(success, "success")
            status_widget.set_class(not success, "error")
            if clear_after > 0:
                self.set_timer(clear_after, lambda: self.clear_status(status_id))
        except Exception:
             print(f"Status Error: Could not find status widget #{status_id}")

    # --- Icon Table Interaction ---
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """When a row in the icon table is selected, populate the input fields."""
        if event.control.id == "table-tag-icons":
            row_key = event.row_key.value
            if row_key:
                try:
                    # Get data directly from the config using the key
                    icon = self.config_manager.tag_icons.get(row_key, "")
                    self.query_one("#input-icon-tag", Input).value = row_key
                    self.query_one("#input-icon-value", Input).value = icon
                    self.clear_status("icon-status")
                    # Post custom message (optional, could be used by other widgets)
                    self.post_message(self.IconSelected(row_key, icon))
                except Exception as e:
                     self.show_status(f"Error loading icon data: {e}", success=False, status_id="icon-status")

    # --- Icon Button Actions ---
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses for icons AND main save/cancel."""
        button_id = event.button.id
        self.clear_status("settings-status") # Clear main status
        self.clear_status("icon-status")   # Clear icon status

        if button_id == "btn-icon-add-update":
            tag_input = self.query_one("#input-icon-tag", Input)
            icon_input = self.query_one("#input-icon-value", Input)
            tag = tag_input.value.strip()
            icon = icon_input.value.strip()

            if not tag:
                self.show_status("Tag name cannot be empty.", success=False, status_id="icon-status")
                await self.app.bell()
                tag_input.focus()
                return
            if not icon:
                 self.show_status("Icon value cannot be empty.", success=False, status_id="icon-status")
                 await self.app.bell()
                 icon_input.focus()
                 return

            # Update the internal config data directly (will be saved on Ctrl+S/Save)
            current_icons = self.config_manager.tag_icons # Get mutable dict
            action = "updated" if tag in current_icons else "added"
            current_icons[tag] = icon
            self.config_manager.update_tag_icons(current_icons) # Ensure 'default' exists etc.

            # Refresh table and clear inputs
            self.populate_icon_table()
            tag_input.value = ""
            icon_input.value = ""
            tag_input.focus()
            self.show_status(f"Icon for '{tag}' {action}.", success=True, status_id="icon-status")

        elif button_id == "btn-icon-delete":
            table = self.query_one("#table-tag-icons", DataTable)
            if table.cursor_row is None:
                 self.show_status("Select an icon row to delete.", success=False, status_id="icon-status")
                 await self.app.bell()
                 return

            row_key = table.get_row_key(table.cursor_row)
            if not row_key:
                 self.show_status("Cannot delete row without key.", success=False, status_id="icon-status")
                 return

            tag_to_delete = row_key

            if tag_to_delete == "default":
                self.show_status("Cannot delete the 'default' icon.", success=False, status_id="icon-status")
                await self.app.bell()
                return

            current_icons = self.config_manager.tag_icons
            if tag_to_delete in current_icons:
                del current_icons[tag_to_delete]
                self.config_manager.update_tag_icons(current_icons) # Save updated dict
                self.populate_icon_table()
                self.query_one("#input-icon-tag", Input).value = ""
                self.query_one("#input-icon-value", Input).value = ""
                self.show_status(f"Icon for '{tag_to_delete}' deleted.", success=True, status_id="icon-status")
            else:
                 self.show_status(f"Tag '{tag_to_delete}' not found.", success=False, status_id="icon-status")

        elif button_id == "button-cancel": # Main cancel button (though Escape works too)
            self.dismiss(False) # Dismiss indicating no save



    # --- Save Action (Ctrl+S or triggered internally) ---
    def action_save_settings(self) -> None:
        """Gathers all data, updates config manager, and dismisses."""
        self.clear_status()
        self.clear_status("icon-status")

        try:
            # 1. Gather Paths
            new_paths: Dict[str, str] = {
                "db": self.query_one("#input-db", Input).value.strip(),
                "library": self.query_one("#input-library", Input).value.strip(),
                "main_upload_dir": self.query_one("#input-upload", Input).value.strip(),
                "exiftool_path": self.query_one("#input-exiftool", Input).value.strip(),
            }
            if not new_paths["db"] or not new_paths["library"]:
                self.show_status("Error: Database Path and Library Path cannot be empty.", success=False)
                self.query_one(TabbedContent).active = "tab-paths" # Switch to paths tab
                self.query_one("#input-db").focus()
                return # Don't proceed

            # 2. Gather Flat Tags
            flat_tags_text = self.query_one("#textarea-flat-tags", TextArea).text
            new_flat_tags = [line.strip() for line in flat_tags_text.splitlines() if line.strip()]

            # 3. Gather Tag Icons (already updated in self.config_manager.tag_icons by add/delete actions)
            # No need to re-read from table, trust the internal state
            new_tag_icons = self.config_manager.tag_icons

            # 4. Update ConfigManager instance (this doesn't save to file yet)
            self.config_manager.update_paths(new_paths)
            self.config_manager.update_flat_tags(new_flat_tags)
            self.config_manager.update_tag_icons(new_tag_icons) # Ensure consistency

            # 5. Dismiss the screen returning True to signal success
            self.dismiss(True)

        except Exception as e:
            traceback.print_exc()
            self.show_status(f"Error preparing settings: {e}", success=False)




    # async def on_button_pressed(self, event: Button.Pressed) -> None:
    #     """Handle button presses."""
    #     if event.button.id == "button-save":
    #         await self._save_changes()
    #     elif event.button.id == "button-cancel":
    #         self.dismiss(None) # Dismiss without returning data

    # async def _save_changes(self) -> None:
    #     """Gathers data, validates (basic), and dismisses with new paths."""
    #     self.clear_status()
    #     new_paths: Dict[str, str] = {
    #         "db": self.query_one("#input-db", Input).value.strip(),
    #         "library": self.query_one("#input-library", Input).value.strip(),
    #         "main_upload_dir": self.query_one("#input-upload", Input).value.strip(),
    #         "exiftool_path": self.query_one("#input-exiftool", Input).value.strip(),
    #     }

    #     # Basic validation: Ensure required paths are not empty
    #     if not new_paths["db"] or not new_paths["library"]:
    #         self.show_status("Error: Database Path and Library Path cannot be empty.", success=False)
    #         await self.app.bell()
    #         return

    #     # More validation could be added here (e.g., check if paths look valid)

    #     # Dismiss the screen, returning the dictionary of new paths
    #     # The main app's callback will handle the actual saving
    #     self.dismiss(new_paths)


    DEFAULT_CSS = """
    ConfigManager {
        /* align: center middle; */ /* Let TabbedContent handle layout */
    }

    TabbedContent {
        height: 100%; /* Fill available space */
    }
    TabPane {
        /* Padding within each tab */
        padding: 1 2;
    }

    /* Style for the vertical scroll containers within tabs */
    #settings-form-paths, #settings-form-flat-tags {
         height: 100%;
    }

    /* Paths tab styling */
    #settings-form-paths Input { margin-bottom: 1; }
    #settings-form-paths Label.label { margin-top: 1; margin-bottom: 0; }

    /* Flat Tags tab styling */
    #textarea-flat-tags {
        width: 100%;
        height: 80%; /* Adjust height as needed */
        border: thick $accent;
        margin-top: 1;
    }

    /* Tag Icons tab styling */
    #tab-tag-icons {
        /* Use grid or vertical layout for table + controls */
         grid-size: 2;
         grid-gutter: 1 2;
         grid-columns: 1fr; /* One column */
         grid-rows: 1fr auto; /* Table takes available space, controls fixed */
         height: 100%;
    }
    #table-tag-icons {
        width: 100%;
        /* height: 1fr; Let grid handle height */
        border: thick $accent;
        margin-bottom: 1; /* Space between table and controls */
    }
    #icon-edit-controls {
        width: 100%;
        height: auto; /* Adjust height based on content */
        align-vertical: bottom;
        align-horizontal: left;
         background: $panel-darken-1;
    }
    #icon-inputs {
        width: 1fr; /* Take available width */
        margin-right: 2; /* Space between inputs and buttons */
    }
    #icon-inputs Input {
         margin-bottom: 0; /* Inputs close together */
    }
    #icon-buttons {
         width: auto; /* Fit buttons */
         height: 100%;
         align: center middle;
    }
     #icon-buttons Button {
         width: 100%;
         margin-bottom: 0;
    }
    #icon-status { /* Inline status for icons */
         width: 100%;
         height: 1;
         margin-top: 1;
         text-align: center;
    }


    /* General status at the bottom */
    #settings-status {
        dock: bottom;
        width: 100%;
        height: 1;
        text-align: center;
        color: $text;
        background: $panel-lighten-1; /* Make it stand out slightly */
    }
    #settings-status.success { color: $success; }
    #settings-status.error { color: $error; }
    """