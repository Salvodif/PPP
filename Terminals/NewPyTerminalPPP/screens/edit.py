from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import Header, Footer, Button, Label, Checkbox
from datetime import datetime

from models import BookManager
from widgets.bookform import BookForm


class EditScreen(Screen):
    def __init__(self, bookmanager: BookManager, book):
        super().__init__()
        self.bookmanager = bookmanager
        self.book = book
        self.form = BookForm(book, show_file_browser=False)
        # Aggiungi uno stato per la checkbox
        self.read_checkbox = Checkbox("Letto?", value=bool(book.read), classes="form-checkbox")
        self.read_checkbox.tooltip = "Spunta se hai letto questo libro"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Vertical(
                Label(f"Modifica: {self.book.title}", id="title-label"),
                # Utilizza il form_container di BookForm invece di ricreare manualmente i campi
                self.form.form_container,
                # Aggiungi la checkbox per "Letto" e il campo data lettura
                Horizontal(
                    Label("Data lettura:", classes="form-label"),
                    self.read_checkbox,
                    self.form.read_input, 
                    classes="form-row"
                ),
                # Pulsanti
                Horizontal(
                    Button("Annulla", id="cancel"),
                    Button("Salva Modifiche", id="save", variant="primary"),
                    id="buttons-container"
                ),
                id="edit-container"
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        self._update_read_field()

    @on(Checkbox.Changed)
    def handle_checkbox_change(self, event: Checkbox.Changed) -> None:
        self._update_read_field()

    def _update_read_field(self) -> None:
        """Aggiorna il campo read in base allo stato della checkbox"""
        if self.read_checkbox.value:
            if not self.form.read_input.value:
                today = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.form.read_input.value = today
            self.form.read_input.disabled = False
        else:
            self.form.read_input.value = ""
            self.form.read_input.disabled = True

    @on(Button.Pressed, "#save")
    def save_changes(self) -> None:
        error = self.form.validate()
        if error:
            self.notify(error, severity="error")
        else:
            values = self.form.get_values()
            if not self.read_checkbox.value:
                values['read'] = None
            self.bookmanager.update_book(self.book.uuid, values)
            self.app.pop_screen()

    @on(Button.Pressed, "#cancel")
    def cancel_edits(self) -> None:
        self.app.pop_screen()
