from pathlib import Path
from typing import Iterable

from textual.app import ComposeResult
from textual.containers import Horizontal, Container
from textual.widgets import DirectoryTree, Label, Button



class FilteredDirectoryTree(DirectoryTree):

    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".epub"}

    def __init__(
        self,
        path: str | Path,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(path, name=name, id=id, classes=classes, disabled=disabled)

        self.allowed_extensions = {ext.lower() for ext in (self.ALLOWED_EXTENSIONS or set())}

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        for path in paths:
            if path.is_dir():
                yield path
            elif path.is_file():
                if self.allowed_extensions and path.suffix.lower() in self.allowed_extensions:
                    yield path
                elif not self.allowed_extensions:
                     yield path



class FilteredTreePanel(Container):
    def __init__(
        self,
        label_text: str,
        tree_path: str | Path,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)

        self.label_text = label_text
        self.tree_path = tree_path


    def compose(self) -> ComposeResult:
        """Crea e dispone i widget interni."""
        with Horizontal(id="filtered_dir_tree_container"):
            yield Label(self.label_text, id="center-label")
            yield FilteredDirectoryTree(
                    path=self.tree_path,
                    id="filtered_directory_tree")

            yield Button("🔄 Refresh", id="filtered_btn_refresh", variant="primary", disabled=False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Assicuriamoci che sia il nostro bottone (se ce ne fossero altri)
        if event.button.id == "filtered_btn_refresh":
            self.query_one("#filtered_directory_tree", FilteredDirectoryTree).refresh()