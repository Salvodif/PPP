from pathlib import Path

from textual.widgets import DirectoryTree, Button, Label
from textual.containers import Container, Horizontal
from textual.app import ComposeResult
from textual.message import Message

from widgets_logic.filtered_tree import FilteredDirectoryTree


class FileSelectorPanel(Container):
    """A container holding a label, a FilteredDirectoryTree, and a Refresh button."""

    # Define a custom message to bubble up when a valid file is selected
    class FileSelected(Message):
        """Custom message indicating a valid file was selected in the tree."""
        def __init__(self, path: Path) -> None:
            super().__init__()
            self.path: Path = path # Store the path of the selected file

    def __init__(
        self,
        label_text: str = "Select Source File:", # Default label
        tree_start_path: str | Path = Path.home(), # Default start path
        *,
        name: str | None = None,
        id: str | None = None, # Allow passing an ID for the container itself
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.label_text = label_text
        # Ensure start path exists, fallback to current directory
        self.tree_start_path = Path(tree_start_path)
        if not self.tree_start_path.is_dir():
            self.log.warning(f"Tree start path '{tree_start_path}' not found, defaulting to '.'")
            self.tree_start_path = Path(".")


    def compose(self) -> ComposeResult:
        """Create and arrange the internal widgets."""
        yield Label(self.label_text, classes="panel-label") # Use a class for styling
        yield FilteredDirectoryTree(
                path=self.tree_start_path,
                id="file-selector-tree" # Give the tree a specific ID
            )
        yield Horizontal( # Use Horizontal to place button nicely maybe
            Button("Refresh", id="file-selector-refresh", variant="default"),
            classes="panel-controls"
        )

    def on_mount(self) -> None:
        """Focus the tree when the panel is mounted."""
        try:
             self.query_one(FilteredDirectoryTree).focus()
        except Exception:
             self.log.error("Could not focus FilteredDirectoryTree on mount.")


    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses within this panel."""
        if event.button.id == "file-selector-refresh":
            event.stop() # Prevent further processing if needed
            try:
                tree = self.query_one(FilteredDirectoryTree)
                # Reload data at the current root
                tree.reload()
                self.log.info("Directory tree refreshed.")
            except Exception as e:
                 self.log.error(f"Failed to refresh directory tree: {e}")


    # --- WATCH for file selection events from the specific tree ---
    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected # Use the base event type
    ) -> None:
        """Called when a file node is selected/clicked in *any* DirectoryTree."""
        # Check if the event originated from *our* specific tree
        if event.control.id == "file-selector-tree":
            event.stop() # We handled it
            selected_path = event.path
            # Even though filter_paths ran, it's good practice to double-check
            # But since filter_paths *should* prevent invalid files from appearing,
            # we can be reasonably sure it's valid here.
            self.log.info(f"File selected in tree: {selected_path}")
            # Post our custom message for the parent screen/app to catch
            self.post_message(self.FileSelected(selected_path))

