from textual.screen import ModalScreen
from textual.containers import Grid
from textual.widgets import Button, Label
from tinydb import Query

class YesOrNo(ModalScreen):
    CSS_PATH="mymodal.tcss"

    def __init__(self, db, uuid, title, name = None, id = None, classes = None):       
        super().__init__(name, id, classes)

        self._db = db
        self._uuid = uuid
        self._title = title

    def compose(self):
        yield Grid(
            Label(f"Are you sure you want to delete {self._title}?", id="question"),
            Button("Yes", variant="primary", id="yes"),
            Button("No", variant="error", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(False)
            return

        try:
            Book = Query()
            # Verifica prima se il libro esiste
            if not self._db.contains(Book.uuid == self._uuid):
                self.notify(f"❌ Il libro {self._title} non è stato trovato nel db", severity="error")
            else:
                removed = self._db.remove(Book.uuid == self._uuid)
                self.notify(f"✅ Rimosso {removed} libro/i con UUID {self._uuid}")

            self.dismiss(True)
            return

        except Exception as e:
            return f"❌ Errore durante l'eliminazione: {str(e)}"
