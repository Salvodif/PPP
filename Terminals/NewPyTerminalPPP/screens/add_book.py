# --- START OF FILE add_book_screen.py ---

from textual.app import ComposeResult
from textual.widgets import Input, Label, Button
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
import datetime

class AddBookScreen(ModalScreen[dict | None]):
    """Schermata modale per aggiungere un nuovo libro."""

    CSS = """
    AddBookScreen {
        align: center middle;
    }

    #add-book-container {
        width: auto;
        height: auto;
        max-width: 80%;
        max-height: 80%;
        background: $panel;
        padding: 2 4;
        border: thick $accent;
    }

    #add-book-container > Label {
        margin-bottom: 1;
        text-style: bold;
    }

    #add-book-container > Input {
        margin-bottom: 1;
    }

    #add-book-buttons {
        /* Usiamo VerticalScroll per coerenza, ma potrebbe essere Horizontal */
        /* Se si usa Horizontal, cambiare in align-horizontal: right; */
        /* Con VerticalScroll, l'allineamento è gestito dal container padre */
        width: 100%;
        height: auto;
        margin-top: 1;
        align: right middle; /* Allinea i bottoni a destra */
    }

    #add-book-buttons > Button {
        margin-left: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="add-book-container"):
            yield Label("Aggiungi Nuovo Libro")
            yield Input(placeholder="Autore", id="author-input")
            yield Input(placeholder="Titolo", id="title-input")
            yield Input(placeholder="Tags (separati da virgola)", id="tags-input")
            # Usiamo un contenitore per i bottoni per allinearli
            with VerticalScroll(id="add-book-buttons"):
                yield Button("Aggiungi", variant="primary", id="add-button")
                yield Button("Annulla", id="cancel-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-button":
            author = self.query_one("#author-input", Input).value
            title = self.query_one("#title-input", Input).value
            tags_str = self.query_one("#tags-input", Input).value

            if not author or not title:
                self.app.notify("Autore e Titolo sono obbligatori!", severity="error", title="Errore Input")
                return

            # Processa i tag: rimuovi spazi extra e splitta per virgola
            tags_list = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

            new_book_data = {
                "author": author,
                "title": title,
                "tags": tags_list,
                "added": datetime.datetime.now().isoformat() # Aggiunge data e ora correnti in formato ISO
            }
            self.dismiss(new_book_data) # Chiude la modale e restituisce i dati
        elif event.button.id == "cancel-button":
            self.dismiss(None) # Chiude la modale senza restituire dati

# --- END OF FILE add_book_screen.py ---