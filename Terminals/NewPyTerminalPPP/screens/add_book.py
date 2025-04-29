import os
from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Label, Static
from textual.containers import VerticalScroll, Container
from textual.message import Message


from widgets_view.filtered_tree import FileSelectorPanel

# Import the processing function
from actions.add_book_logic import process_add_book, ALLOWED_EXTENSIONS




class AddBookScreen(Screen):
    """Screen for adding a new book entry."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel"), # Use app.pop_screen to go back
    ]

    class FileSelected(Message):
        """Custom message to signal a valid file selection."""
        def __init__(self, path: Path) -> None:
            super().__init__()
            self.path = path

    # Pass necessary paths from the main app when creating the screen
    def __init__(self, db_path: str, library_base_path: Path, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.db_path = db_path
        self.library_base_path = library_base_path
        self.selected_file_path: Path | None = None



    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with VerticalScroll(id="add-form"):
            yield FileSelectorPanel(id="file-selector")
            yield Static("Selected file: None", id="selected-file-display", classes="label")

            yield Label("Author:", classes="label")
            yield Input(placeholder="Author Name", id="input-author")

            yield Label("Title:", classes="label")
            yield Input(placeholder="Book Title", id="input-title")

            yield Label("Tags (comma-separated):", classes="label")
            yield Input(placeholder="fiction, sci-fi, classic", id="input-tags")

            yield Container(
                 Button("Add Book", variant="primary", id="button-add"),
                 Button("Cancel", variant="default", id="button-cancel"),
                 id="buttons-container"
            )
            yield Static(id="status-message", classes="status")

        yield Footer()



    def on_mount(self) -> None:
        try:
            # Focus the panel itself, or the tree within it
            # self.query_one(FileSelectorPanel).focus()
            self.query_one("#file-selector-tree", FilteredDirectoryTree).focus()
        except Exception:
            self.log.error("Could not focus file selector on mount.")
        self.update_selected_file_display()


    def update_selected_file_display(self) -> None:
        """Updates the Static widget showing the selected file."""
        display_widget = self.query_one("#selected-file-display", Static)
        if self.selected_file_path:
            display_widget.update(f"Selected file: [b]{self.selected_file_path.name}[/b]")
        else:
            display_widget.update("Selected file: [i]None[/i]")


    def clear_status(self) -> None:
        status_widget = self.query_one("#status-message", Static)
        status_widget.update("")
        status_widget.remove_class("success", "error")

    def show_status(self, message: str, success: bool) -> None:
         status_widget = self.query_one("#status-message", Static)
         status_widget.update(message)
         status_widget.add_class("success" if success else "error")




    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        self.clear_status()
        if event.button.id == "button-add":
            if self.selected_file_path is None:
                self.show_status("Error: Please select a source file from the tree.", success=False)
                await self.app.bell()
                return

            source_path_str = str(self.selected_file_path)
            author = self.query_one("#input-author", Input).value
            title = self.query_one("#input-title", Input).value
            tags = self.query_one("#input-tags", Input).value

            if not all([author, title]):
                 self.show_status("Error: Author and Title are required.", success=False)
                 await self.app.bell()
                 return

            self.show_status("Processing...", success=True)
            await self.app.bell()

            result = process_add_book(
                source_file_path_str=source_path_str,
                author=author,
                title=title,
                tags_str=tags,
                db_path=self.db_path,
                library_base_path=self.library_base_path
            )

            self.show_status(result["message"], result["success"])

            if result["success"]:
                self.dismiss(result)
            else:
                await self.app.bell()

        elif event.button.id == "button-cancel":
            self.dismiss(None)


    def on_file_selector_panel_file_selected(
        self, event: FileSelectorPanel.FileSelected
    ) -> None:
        """Handles the custom FileSelected message from our panel."""
        event.stop() # We've handled this message
        self.selected_file_path = event.path
        self.update_selected_file_display() # Update the external Static display
        # Optional: Move focus to the next input
        try:
            self.query_one("#input-author", Input).focus()
        except Exception:
            self.log.error("Could not focus author input after file selection.")