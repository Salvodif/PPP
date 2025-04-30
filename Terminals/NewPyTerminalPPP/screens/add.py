from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Button, Label
from widgets.bookform import BookForm
from models import BookManager, Book


class AddScreen(Screen):
    def __init__(self, libreria: BookManager):
        super().__init__()
        self.libreria = libreria
        self.form = BookForm()
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Aggiungi nuovo libro"),
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
            id="add-container"
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
                from uuid import uuid4
                from datetime import datetime
                values = self.form.get_values()
                libro = Book(
                    uuid=str(uuid4()),
                    author=values['author'],
                    title=values['title'],
                    added=datetime.now(),
                    tags=values['tags'],
                    series=values['series'],
                    num_series=values['num_series'],
                    read=values['read'],
                    description=values['description']
                )
                self.libreria.add_libro(Book)
                self.app.pop_screen()
                self.app.query_one("#libri-table", DataTableBook).update_table(self.libreria.libri)