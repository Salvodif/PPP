from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Button, Label, DirectoryTree
from textual import work

from models import BookManager
from widgets.bookform import BookForm


class AddScreen(Screen):
    BINDINGS = [("escape", "back", "Torna indietro")]

    def __init__(self, bookmanager: BookManager, start_directory: str = "."):
        super().__init__()
        self.bookmanager = bookmanager
        self.form = BookForm(start_directory=start_directory)
        self.start_directory = start_directory

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Aggiungi nuovo libro", classes="title"),
            self.form.compose_form(),
            Horizontal(
                Button("Annulla", id="cancel"),
                self.form.save_button,
            ),
            id="add-container"
        )
        yield Footer()

    def on_mount(self):
        """Focus sul tree dopo il mount"""
        self.query_one("#file-browser").focus()

    def action_back(self):
        self.app.pop_screen()