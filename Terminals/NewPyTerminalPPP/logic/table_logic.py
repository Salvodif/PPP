from __future__ import annotations # Per permettere il type hint 'LibraryApp' senza import circolare
import os
from pathlib import Path
import traceback
from typing import TYPE_CHECKING # Per il type hinting condizionale

from textual.widgets import DataTable, Label
from tinydb import TinyDB

from normalize import normalize_author_for_path # Assicurati che normalize.py sia accessibile

from textual.widgets import DataTable


# Importa LibraryApp solo per il type checking per evitare import circolari
if TYPE_CHECKING:
    from main import LibraryApp

def populate_library_table(app: LibraryApp, table: DataTable):
    """
    Carica i dati dal database TinyDB e popola la DataTable.

    Args:
        app: L'istanza dell'applicazione LibraryApp.
        table: L'istanza della DataTable da popolare.
    """
    db_path = app.db_path # Ottieni il percorso db dall'app
    library_base_path = app.library_base_path # Ottieni il percorso base dall'app

    # --- Definisci Colonne ---
    # (Potresti anche passare le definizioni delle colonne come argomento se vuoi più flessibilità)
    table.add_column("Added", key="added", width=12)
    table.add_column("Author", key="author", width=25)
    table.add_column("Title", key="title", width=40)
    table.add_column("Filename", key="filename", width=30)
    table.add_column("Tags", key="tags", width=25)
    table.add_column("Status", key="status", width=8)

    # --- Logica di Caricamento e Popolamento ---
    try:
        if not os.path.exists(db_path):
             app.notify(f"Error: Database file not found at '{db_path}'", title="File Not Found", severity="error", timeout=10)
             table.visible = False # Nascondi la tabella
             app.query_one("#table-container").mount(Label("Database file not found.")) # Mostra messaggio
             return # Esce dalla funzione se il file non esiste

        db = TinyDB(db_path)
        library_data = db.table('_default').storage.read() # Leggi i dati grezzi

        if not library_data or '_default' not in library_data:
            app.notify("Error: Database seems empty or missing '_default' table.", title="Load Error", severity="warning", timeout=10)
            table.visible = False
            app.query_one("#table-container").mount(Label("Database empty or invalid structure."))
            return

        default_table_data = library_data['_default']

        # Ordina per ID (chiavi numeriche) per un ordine consistente
        sorted_ids = sorted(default_table_data.keys(), key=lambda x: int(x) if x.isdigit() else float('inf'))

        # --- Popola Tabella ---
        for doc_id_str in sorted_ids:
            doc = default_table_data.get(doc_id_str)

            if doc:
                is_row_invalid = False
                status_icon = ""

                # Estrai dati, gestendo chiavi mancanti
                author = doc.get("author", "N/A")
                title = doc.get("title", "N/A")
                tags_list = doc.get("tags", [])
                tags = ", ".join(tags_list) if tags_list else ""
                added_raw = doc.get("added", "")
                filename = doc.get("filename")

                try:
                    added = added_raw.split('T')[0] if added_raw and 'T' in added_raw else added_raw
                except:
                    added = added_raw # Fallback

                # --- Logica di Validazione ---
                filename_display = "N/A"
                if not filename:
                    is_row_invalid = True
                    filename_display = "N/A (Missing)"
                else:
                    filename_display = filename
                    if not author:
                        is_row_invalid = True
                    else:
                        normalized_author = normalize_author_for_path(author)
                        expected_file_path = library_base_path / normalized_author / filename
                        if not expected_file_path.exists():
                            is_row_invalid = True
                            # filename_display = f"{filename} (Not Found)" # Opzionale

                if is_row_invalid:
                    status_icon = "[red]X[/red]"

                row_data_items = [
                    str(added),
                    str(author),
                    str(title),
                    str(filename_display),
                    str(tags),
                ]

                if is_row_invalid:
                    styled_row_data = [f"[b]{item}[/b]" for item in row_data_items]
                    styled_row_data.append(status_icon)
                    table.add_row(*styled_row_data, key=doc_id_str)
                else:
                    row_data_items.append(status_icon)
                    table.add_row(*row_data_items, key=doc_id_str)
            else:
                print(f"Warning: Could not retrieve document for ID {doc_id_str}")

    except FileNotFoundError as e:
         # Dovrebbe essere già gestito sopra, ma per sicurezza
         app.notify(f"Error loading database: {e}", title="Error", severity="error", timeout=10)
         table.visible = False
         if not app.query("#table-container Label"): # Evita di aggiungere più messaggi
             app.query_one("#table-container").mount(Label("Error loading database."))

    except Exception as e:
        # Cattura altri errori potenziali
        traceback.print_exc() # Stampa traceback per debug
        app.notify(f"An unexpected error occurred: {e}", title="Critical Error", severity="error", timeout=15)
        table.visible = False
        if not app.query("#table-container Label"): # Evita di aggiungere più messaggi
             app.query_one("#table-container").mount(Label("An unexpected error occurred during loading."))


def handle_table_sort(app: LibraryApp) -> None:
    """
    Gestisce la logica di ordinamento della DataTable nell'applicazione.

    Args:
        app: L'istanza dell'applicazione LibraryApp.
    """
    try:
        table = app.query_one(DataTable) # Accedi alla tabella tramite l'app
        if not table.row_count:
            app.notify("Table is empty, cannot sort.", severity="warning")
            return

        column_index = table.cursor_column
        if column_index is None:
            app.notify("No column selected.", severity="warning")
            return

        columns = table.ordered_columns
        if column_index >= len(columns):
            app.notify("Invalid column index.", severity="error")
            return

        selected_column = columns[column_index]
        column_key = selected_column.key

        if column_key is None:
            app.notify(f"Column '{selected_column.label}' cannot be sorted (no key).", severity="warning")
            return

        # Determina la direzione usando lo stato dell'app
        if column_key == app.last_sort_column_key:
            # Inverti la direzione memorizzata nell'app
            app.sort_reverse = not app.sort_reverse
        else:
            # Imposta la direzione default nell'app
            app.sort_reverse = False

        # Esegui l'ordinamento sulla tabella
        table.sort(column_key, reverse=app.sort_reverse)

        # Aggiorna lo stato dell'ultimo sort nell'app
        app.last_sort_column_key = column_key

        # Notifica tramite l'app
        direction = "Descending" if app.sort_reverse else "Ascending"
        app.notify(f"Sorted by '{selected_column.label}' ({direction})")

    except Exception as e:
        traceback.print_exc()
        app.notify(f"Error during sort: {e}", title="Sort Error", severity="error")

# --- END OF FILE table_actions.py ---