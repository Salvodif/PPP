from datetime import datetime

from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Button, Label, Checkbox
from textual.markup import escape


from tools.logger import AppLogger
from models import BookManager
from widgets.bookform import BookForm

class EditScreen(Screen):
    BINDINGS = [("escape", "back", "Torna indietro")]

    def __init__(self, bookmanager: BookManager, book):
        super().__init__()
        self.bookmanager = bookmanager
        self.book = book
        self.form = BookForm(book, show_file_browser=False)
        self.read_checkbox = Checkbox("Letto?", value=bool(book.read), classes="form-checkbox")
        self.read_checkbox.tooltip = "Spunta se hai letto questo libro"
        self.logger = AppLogger.get_logger()


    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label(f"Modifica: {self.book.title}", id="edit-title-label", classes="title"),
            self.form.form_container,
            Horizontal(
                Label("Letto?", classes="form-label"),
                self.read_checkbox,
                self.form.read_input, 
                classes="form-row"
            ),
            Horizontal(
                Button("Annulla", id="cancel"),
                Button("Salva Modifiche", id="save", variant="primary", classes="button-primary"),
                classes="button-bar"
            ),
            classes="form-screen-container",
            id="edit-container"
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
        try:
            error = self.form.validate()
            if error:
                self.logger.warning(f"Validazione fallita durante modifica libro: {error}")
                self.notify(error, severity="error")
            else:
                values = self.form.get_values()
                if not self.read_checkbox.value:
                    values['read'] = None
                self.logger.info(f"Modifica libro: {self.book.uuid}")
                self.bookmanager.update_book(self.book.uuid, values)
                self.app.pop_screen()
        except Exception as e:
            self.logger.error("Errore durante la modifica di un libro", exc_info=e)
            self.notify("Errore durante il salvataggio", severity="error")

    @on(Button.Pressed, "#cancel")
    def cancel_edits(self) -> None:
        self.app.pop_screen()

    def action_back(self):
        self.app.pop_screen()