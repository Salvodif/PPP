from pathlib import Path
from typing import Optional, Dict, Any
from tinydb import Query

""" TEXTUAL LIBRARY """
from textual import on
from textual.app import ComposeResult
from textual.widgets import Static, Button, Checkbox, Label, Input, TextArea
from textual.containers import Vertical, Horizontal, Container, Grid
from textual.reactive import reactive
from textual.message import Message
from textual.css.query import NoMatches


""" MY LIBRARY """
from tool.config_reader import ConfigReader
from tool.formatted_date_time import FormattedDateTime


class BookDetails(Vertical):
    class OpenFileRequest(Message):
        """Evento personalizzato per richiesta apertura file"""
        def __init__(self, book_data: Dict[str, Any]):
            self.book_data = book_data
            super().__init__()

    book_data: reactive[Optional[Dict[str, Any]]] = reactive(None)

    def __init__(self, id: str, db: Any) -> None:
        super().__init__(id=id)
        self._db = db
        self._widgets_ready = False

    def compose(self) -> ComposeResult:
        with Grid(id="grid_container", classes="hidden"):
            yield Label("Autore:", classes="center-label")
            yield Input(id="author", placeholder="Autore...")
            yield Label("Titolo:", classes="center-label")
            yield Input(id="title", placeholder="Titolo...")
            yield Label("Aggiunto:", classes="center-label")
            yield Input(id="added", disabled=True, classes="input-width")
            yield Label("Tags: ", classes="center-label")
            yield Input(id="tags", placeholder="tag1, tag2...", classes="input-width")
            yield Label("Descrizione: ", classes="center-label")
            yield TextArea(id="description", language="markdown", show_line_numbers=False, theme="dracula", classes="input-width")
            yield Label("Letto: ", classes="center-label")
            yield Checkbox("", id="read")
            yield Button("📂 Apri File",
                                id="btn_open_file",
                                variant="primary",
                                disabled=True)
            yield Button("💾 Salva modifiche",
                                id="btn_save",
                                variant="success",
                                disabled=True)

        yield Static("⏳ Seleziona un libro per visualizzare i dettagli", id="details_placeholder")

    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        self._widgets_ready = True

        self._update_ui_from_book_data()


    def watch_book_data(self) -> None:
        """Called when the book_data reactive variable changes."""
        self.log(f"watch_book_data triggered. Widgets ready: {self._widgets_ready}")
        if self._widgets_ready:
            self._update_ui_from_book_data()


    def _update_ui_from_book_data(self) -> None:
        container = self.query_one("#grid_container")
        placeholder = self.query_one("#details_placeholder")
        book_data = self.book_data # Get the current data

        if not book_data:
            self.log("No book data, showing placeholder.")
            container.add_class("hidden")
            placeholder.remove_class("hidden")
            placeholder.update("⏳ Seleziona un libro per visualizzare i dettagli")
            # Disable buttons if no data
            try:
                self.query_one("#btn_open_file", Button).disabled = True
                self.query_one("#btn_save", Button).disabled = True
            except NoMatches:
                self.log.warning("Buttons not found when trying to disable them.")
            return

        self.log(f"Updating UI with data for book UUID: {book_data.get('uuid', 'N/A')}")
        placeholder.add_class("hidden")
        container.remove_class("hidden")

        try:
            # --- Update Input Fields ---
            self.query_one("#title", Input).value = book_data.get("title", "")
            self.query_one("#author", Input).value = book_data.get("author", "")
            self.query_one("#tags", Input).value = ", ".join(book_data.get("tags", []))

            # --- Update Added Date (Formatted) ---
            added_formatted = "N/A"
            added_raw = book_data.get("added")
            if added_raw:
                try:
                    added_formatted = FormattedDateTime.fromisoformat(added_raw)
                except (ValueError, TypeError):
                    self.log.warning(f"Invalid date format: {added_raw}")
                    added_formatted = "Data Invalida"
            self.query_one("#added", Input).value = added_formatted

            # --- Update TextArea ---
            # Use load_text for potentially large content or multi-line initialization
            description_value = book_data.get("description") # Prendi il valore (può essere None)
            description_text = description_value if description_value is not None else ""
            self.query_one("#description", TextArea).load_text(description_text)

            # --- Update Checkbox ---
            # Ensure the value from DB is treated as boolean
            read_value = book_data.get("read", "") # Default to False if missing

            if not read_value == "":
                self.query_one("#read", Checkbox).value = True

            # --- Enable Buttons ---
            # Enable 'Open File' only if there's a filename
            has_filename = bool(book_data.get("filename"))
            self.query_one("#btn_open_file", Button).disabled = not has_filename
            # Always enable 'Save' when data is loaded (or decide based on changes later)
            self.query_one("#btn_save", Button).disabled = False # Enable save button

            self.log("UI update complete.")

        except NoMatches as e:
            self.log.error(f"❌ UI element not found during update: {e}")
            placeholder.remove_class("hidden")
            container.add_class("hidden")
            placeholder.update("❌ Errore: Impossibile caricare i dettagli.")
        except Exception as e:
            self.log.error("❌ Unexpected error during UI update:") # Log full traceback
            placeholder.remove_class("hidden")
            container.add_class("hidden")
            placeholder.update(f"❌ Errore imprevisto: {e}")


    @on(Button.Pressed, "#btn_open_file")
    def handle_open_file_button(self, event: Button.Pressed) -> None: # Renamed handler
        """Gestisce il click sul pulsante Apri File"""
        if self.book_data and self.book_data.get("filename"):
            self.log(f"Posting OpenFileRequest for book UUID: {self.book_data.get('uuid')}")
            self.post_message(self.OpenFileRequest(self.book_data.copy())) # Send a copy
        else:
            self.log.warning("Open file button pressed, but no book_data or filename.")
            self.notify("❌ Nessun file associato a questo libro.", severity="warning")


    @on(Button.Pressed, "#btn_save")
    def handle_save_button(self, event: Button.Pressed) -> None: # Renamed handler
        """Gestisce il click sul pulsante Salva Modifiche"""
        if not self.book_data:
            self.notify("❌ Nessun libro selezionato da salvare.", severity="error")
            return

        uuid = self.book_data.get("uuid")
        title = self.query_one("#detail_title", Input).value
        author = self.query_one("#detail_author", Input).value
        keywords_str = ", ".join(self.query_one("#detail_tags", Input).value)
        description = self.query_one("#detail_description", TextArea).value

        read = ""
        if self.query_one("#detail_read", Checkbox).value:
            read = FormattedDateTime.now()

        filename = self.query_one("#detail_added", Input).value

        self.log("Save button pressed. Gathering data from UI.")
        try:
            updated_data = {
                "uuid": uuid,
                "title": title,
                "author": author,
                "tags": keywords_str,
                "description": description,
                "read": read,
                "filename": filename
            }

            # --- Validation (Optional but recommended) ---
            if not updated_data["title"]:
                self.notify("❌ Il titolo non può essere vuoto.", severity="error")
                return
            if not updated_data["author"]:
                self.notify("❌ L'autore non può essere vuoto.", severity="error")
                return

            # --- Database Update ---
            Record = Query()

            updated_count = self._db.update(updated_data, Record.uuid == updated_data["uuid"])

            if updated_count:
                 self.log(f"Successfully updated book UUID: {updated_data['uuid']} in DB.")
                 self.notify("✅ Modifiche salvate con successo!", title="Salvataggio")
                 # Update the internal book_data to reflect changes immediately
                 self.book_data = updated_data
                 # Optionally: Notify the main app to refresh the table row if needed
                 # (though the cache in BookManagerApp won't be updated until next refresh)
            else:
                 self.log.error(f"Failed to update book UUID: {updated_data['uuid']} in DB. Record not found?")
                 self.notify("❌ Errore: Impossibile salvare le modifiche nel database.", severity="error")


            # --- Exiftool Update (Keep your original logic if needed) ---
            # Be careful with file paths and error handling here
            author_path = Path(f"{ConfigReader.LIBRARY}/{updated_data['author']}") # Use config
            author_path.mkdir(parents=True, exist_ok=True)
            file_path = author_path / updated_data['filename']

            # if updated_data['filename'] and file_path.is_file():
            #     try:
            #         tags_str = ", ".join(updated_data["tags"]) if updated_data["tags"] else ""

            #         exiftool_cmd = [
            #             str(Path(self._config.EXIFTOOL_PATH)), # Ensure EXIFTOOL_PATH is correct in config
            #             "-charset", "utf8", # Use UTF-8 for metadata
            #             f"-Title={title}",
            #             f"-Author={author}",
            #             f"-Keywords={keywords_str}", # Pass the string here
            #             "-overwrite_original", # Overwrite the copied file
            #             str(new_file_path) # Pass path as string
            #         ]
            #         self.log.info(f"Running exiftool: {' '.join(exiftool_cmd)}") # Log the command
            #         # Capture output for better error reporting
            #         result = subprocess.run(exiftool_cmd, check=True, capture_output=True, text=True, encoding='utf-8')

            #         self.log(f"Exiftool update simulated for {file_path}") # Placeholder
            #         # self.notify("ℹ️ Metadati file aggiornati.") # Inform user
            #     except Exception as e:
            #         self.log.error("❌ Errore durante l'aggiornamento dei metadati Exiftool:")
            #         self.notify(f"⚠️ Errore aggiornamento metadati: {e}", severity="warning")
            # else:
            #     self.log.warning(f"File not found or filename missing for Exiftool update: {updated_data['filename']}")
            #     if updated_data['filename']:
            #         self.notify("⚠️ File non trovato, metadati non aggiornati.", severity="warning")


        except NoMatches as e:
            self.log.error(f"❌ UI element not found during save: {e}")
            self.notify("❌ Errore: Impossibile leggere i dati dalla UI.", severity="error")
        except Exception as e:
            self.log.error("❌ Unexpected error during save:")
            self.notify(f"❌ Errore imprevisto durante il salvataggio: {e}", severity="error")
