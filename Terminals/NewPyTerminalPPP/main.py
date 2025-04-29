# --- START OF FILE main.py ---

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Header, Footer
from textual.reactive import var
from textual import work

from pathlib import Path
from tinydb import TinyDB

from screens.add_book import AddBookScreen

LIBRARY_DIR = Path.home() / "OneDrive//MyDBTiny"

if "//" in str(LIBRARY_DIR):
    print(f"Attenzione: il percorso '{LIBRARY_DIR}' contiene '//'. Si consiglia di usare Path.home() / 'OneDrive' / 'MyDBTiny'")

LIBRARY_FILE = LIBRARY_DIR / "library.json"


class TerminalApp(App):
    BINDINGS = [
        ("ctrl+r", "sort_table", "Ordina Tabella"),
        ("ctrl+a", "add_book", "Aggiungi Libro"),
        ("ctrl+s", "save_data", "Salva Dati"),
        ("ctrl+q", "quit", "Esci")
    ]

    CSS = """
    Screen {
        /* Layout generale se necessario */
    }

    Header {
        dock: top;
        height: 1; /* Header fisso a 1 riga */
    }

    Footer {
        dock: bottom;
        height: 1; /* Footer fisso a 1 riga */
    }

    DataTable {
        width: 100%;
        height: 1fr; /* Occupa lo spazio rimanente */
        border: round $accent;
        margin-top: 1;
        margin-bottom: 1;
    }

    DataTable > .datatable--cursor {
        background: $accent-darken-1;
        color: $text;
    }

    DataTable > .datatable--header {
        text-style: bold;
    }
    """

    sort_column_key: var[str | None] = var(None)
    sort_reverse: var[bool] = var(False)

    def __init__(self):
        super().__init__()
        self.db = self.init_db()

    def init_db(self) -> TinyDB:
        """Inizializza il database TinyDB."""
        try:
            if not LIBRARY_DIR.exists():
                self.notify(f"Creo la directory: {LIBRARY_DIR}", title="Info Database")
                LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
            self.notify(f"Database aperto: {LIBRARY_FILE}", title="Info Database")
            # ensure_ascii=False è importante per caratteri speciali/accentati
            return TinyDB(LIBRARY_FILE, encoding='utf-8', indent=4, ensure_ascii=False)
        except Exception as e:
            self.notify(f"Errore critico nell'inizializzazione del DB:\n{e}", severity="error", timeout=10)
            self.exit(f"Errore DB: {e}") # Esce dall'app se il DB non può essere aperto

    def compose(self) -> ComposeResult:
        """Crea la tabella con i dati della libreria."""
        yield Header()
        yield DataTable(id="books-table")
        yield Footer()

    def on_mount(self) -> None:
        """Configura la tabella al montaggio."""
        table = self.query_one("#books-table", DataTable)
        table.cursor_type = "row"
        # Definisci le colonne con le loro chiavi (usate per l'ordinamento)
        table.add_column("Aggiunto", key="Aggiunto")
        table.add_column("Autore", key="Autore")
        table.add_column("Titolo", key="Titolo")
        table.add_column("Tags", key="Tags")
        self.populate_table()

    def populate_table(self) -> None:
        """Popola la tabella con i dati dalla TinyDB."""
        table = self.query_one("#books-table", DataTable)
        current_cursor_row = table.cursor_row

        table.clear()

        try:
            all_books = self.db.all()
        except Exception as e:
            self.notify(f"Errore durante la lettura dal DB: {e}", severity="error")
            all_books = [] # Continua con una lista vuota

        if not all_books:
            self.notify("Nessun libro nel database.", severity="warning")
            return

        for book in all_books:
            doc_id = book.doc_id
            try:
                # Prepara i dati per la riga, gestendo valori mancanti
                added_full = book.get("added", "N/D")
                added_display = added_full.split("T")[0] if isinstance(added_full, str) and "T" in added_full else str(added_full)

                tags_data = book.get("tags", [])
                if isinstance(tags_data, list):
                    tags_display = ", ".join(tags_data)
                elif isinstance(tags_data, str):
                    tags_display = tags_data
                else:
                    tags_display = "N/D"

                row_data = (
                    added_display,
                    book.get("author", "N/D"),
                    book.get("title", "N/D"),
                    tags_display,
                )
                # Aggiunge la riga usando la chiave del documento TinyDB
                table.add_row(*row_data, key=str(doc_id))

            except Exception as e:
                self.notify(f"Errore nel processare libro ID {doc_id}: {e}", severity="error")
                try:
                    table.add_row("Errore", str(doc_id), str(e), "", key=f"error_{doc_id}")
                except Exception as add_err:
                     self.notify(f"Impossibile aggiungere riga di errore: {add_err}", severity="error")


        # Ri-applica l'ordinamento corrente se presente
        if self.sort_column_key and self.sort_column_key in table.columns:
             try:
                 table.sort(self.sort_column_key, reverse=self.sort_reverse, refresh=False)
             except Exception as e:
                 self.notify(f"Errore ri-applicando ordinamento post-popolamento: {e}", severity="warning")
                 self.sort_column_key = None
                 self.sort_reverse = False

        # Ripristina la posizione del cursore se possibile
        if current_cursor_row < table.row_count:
            table.move_cursor(row=current_cursor_row, animate=False)
        elif table.row_count > 0:
             table.move_cursor(row=0, animate=False) # Vai alla prima riga se esiste

        table.refresh() # Aggiorna la visualizzazione della tabella


    def action_sort_table(self) -> None:
        """Ordina la tabella per colonna selezionata, alternando la direzione."""
        table = self.query_one("#books-table", DataTable)
        if table.row_count == 0:
            self.notify("La tabella è vuota, impossibile ordinare.", severity="warning")
            return

        try:
            # Get the current cursor column INDEX
            col_idx = table.cursor_column
            if col_idx is None:
                 self.notify("Nessuna colonna selezionata (cursore non posizionato?).", severity="warning")
                 return

            # --- FIX START ---
            # Get the list of column KEYS in display order
            column_keys = list(table.columns.keys())

            # Check if the index is valid for the list of keys
            if not (0 <= col_idx < len(column_keys)):
                self.notify(f"Errore interno: Indice colonna cursore ({col_idx}) non valido per le chiavi {column_keys}.", severity="error")
                return

            # Get the KEY of the column at the cursor index
            column_key_to_sort = column_keys[col_idx]
            # --- FIX END ---


            # Determina la direzione
            if self.sort_column_key == column_key_to_sort:
                # If sorting the same column again, reverse the direction
                self.sort_reverse = not self.sort_reverse
            else:
                # If sorting a new column, start with ascending
                self.sort_column_key = column_key_to_sort
                self.sort_reverse = False

            # Esegui l'ordinamento
            self.notify(f"Ordino per '{self.sort_column_key}' ({'Discendente' if self.sort_reverse else 'Ascendente'})...")
            # The sort method uses the COLUMN KEY you provided in add_column
            table.sort(self.sort_column_key, reverse=self.sort_reverse)

        # Keep existing error handling
        except IndexError:
             # This specific IndexError might be less likely now with the bounds check,
             # but keep it for safety or other potential index issues.
             self.notify(f"Errore: Indice di colonna ({col_idx}) fuori dai limiti.", severity="error")
        except Exception as e:
             self.notify(f"Errore imprevisto durante l'ordinamento: {e}", severity="error")
             # Optionally log the full traceback for debugging
             # import traceback
             # self.notify(f"Traceback: {traceback.format_exc()}", severity="error", timeout=15)

    @work(exclusive=True, group="ui_tasks") 
    async def action_add_book(self) -> None:
        """Mostra la finestra modale per aggiungere un nuovo libro."""
        # Usa la classe AddBookScreen importata
        new_book_data = await self.push_screen_wait(AddBookScreen())
        if new_book_data:
            try:
                self.db.insert(new_book_data)
                self.notify("Libro aggiunto con successo!", severity="information", title="Successo")
                # Ricarica e riapplica l'ordinamento corrente
                self.call_from_thread(self.populate_table)
            except Exception as e:
                 self.notify(f"Errore durante l'inserimento nel DB: {e}", severity="error")

    def action_save_data(self) -> None:
        """Forza il salvataggio dei dati su disco (TinyDB di solito lo fa automaticamente)."""
        try:
            current_data = {str(doc.doc_id): doc for doc in self.db.all()}
            self.db.storage.write({"_default": current_data})
            self.notify("Salvataggio forzato completato.", severity="information", title="Database")
        except Exception as e:
            self.notify(f"Errore durante il salvataggio forzato: {e}", severity="error")


if __name__ == "__main__":
    # Considera di usare il percorso corretto per OneDrive
    # LIBRARY_DIR = Path.home() / "OneDrive" / "MyDBTiny"
    app = TerminalApp()
    app.run()

# --- END OF FILE main.py ---