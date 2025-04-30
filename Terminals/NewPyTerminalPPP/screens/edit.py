from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Button, Label

from models import BookManager
from widgets.datatablebook import DataTableBook
from widgets.bookform import BookForm


class EditScreen(Screen):
    def __init__(self, libreria: BookManager, libro):
        super().__init__()
        self.libreria = libreria
        self.libro = libro
        self.form = BookForm(libro)
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label(f"Modifica: {self.libro.title}"),
            Label("Titolo:"),
            self.form.title_input,
            Label("Autore:"),
            self.form.author_input,
            Label("Tags:"),
            self.form.tags_input,
            Label("Serie:"),
            self.form.series_input,
            Label("Numero serie:"),
            self.form.num_series_input,
            Label("Data lettura:"),
            self.form.read_input,
            Label("Descrizione:"),
            self.form.description_input,
            Horizontal(
                Button("Annulla", id="cancel"),
                self.form.save_button,
            ),
            id="edit-container"
        )
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button is self.form.save_button:
            error = self.form.validate()
            if error:
                self.notify(error, severity="error")
            else:
                self.libreria.update_libro(self.libro.uuid, self.form.get_values())
                self.app.pop_screen()
                self.app.query_one("#libri-table", DataTableBook).update_table(self.libreria.libri)
