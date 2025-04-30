import os
import shutil
import subprocess
import sys
import json
import uuid
import logging

from tinydb import TinyDB
from pathlib import Path
from pathvalidate import ValidationError, validate_filename

""" Textual library """
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Container
from textual.logging import TextualHandler
from textual.reactive import reactive
from textual.widgets import DataTable, Button, Input, Tree, Footer
from textual.widgets import TabbedContent, TabPane

""" My modules """
from tool.config_reader import ConfigReader
from tool.formatted_date_time import FormattedDateTime
""" My widgets """
from widgets.add_new_book import AddNewBook
from widgets.book_details import BookDetails
from widgets.config_editor import ConfigEditor

""" My Screens """
from screens.modal_yes_no import YesOrNo



# Aggiungi questo prima di avviare l'app
logging.basicConfig(
    level=logging.INFO,
    handlers=[TextualHandler()],
    force=True
)

class BookManagerApp(App):
    def __init__(self) -> None:
        super().__init__()

        try:
            db = ConfigReader().DB
            tinydb_path = Path(f"{db}")

            self._db = TinyDB(f"{tinydb_path}", encoding='utf-8')
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            self.log.error(f"❌Database {tinydb_path} corrotto o illeggibile: {e}. Creazione/uso di un nuovo database.")
        except FileNotFoundError:
             self.log.error(f"❌Percorso database non trovato: {db}. Controlla config.yaml.")
             self.exit("Errore critico: Percorso DB non valido.")
        except Exception as e:
            self.log.error(f"❌Errore imprevisto durante l'inizializzazione del DB: {e}")
            self.exit(f"Errore critico DB: {e}")

        # self._tags_tree = Tree("📁Tags", id="tags_tree")

        self._cache_books = []
        self._uuid_to_book = {}
        self._current_uuid = None
        self._selected_row = None
        self._all_tags: list[str] = []
        self._all_authors: list[str] = []


    def compose(self) -> ComposeResult:
        with Container(classes="datatable-container"):
            with Horizontal():
                # yield self._tags_tree
                with TabbedContent(id="main_tabs", initial="list"):
                    with TabPane("Book List", id="list"):
                        yield self._build_book_table_container()
                    with TabPane("Details", id="details_pane"):
                        yield BookDetails(id="book_details", db=self._db)
                    with TabPane("Add Book", id="add_new_book_pane"):
                        yield AddNewBook(id="add_new_book")
                    with TabPane("Config", id="config_pane"):
                        yield ConfigEditor(id="config_editor")

        with Horizontal(classes="button-row"):
            yield Button("Delete Book", id="btndelete", variant="error")
            yield Button("Refresh", id="btnrefresh", variant="default")
            yield Button("Open File", id="btnopen_file", variant="default")
            yield Input(placeholder="Search...", id="search_input")

        yield Footer()

    def _build_book_table_container(self) -> Container:
        return Container(
            DataTable(
                id="book_table", 
                cursor_type="row",
                show_cursor=True, 
                show_header=True, 
                zebra_stripes=True
            ),
            classes="table-container"
        )


    def on_mount(self) -> None:
        self.theme = "nord"

        self._table = self.query_one("#book_table", DataTable)
        self._table.add_columns("Added", "Title", "Author", "Tags")
        self._table.focus()

        self._update_table([])


    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if event.tab.id == "--content-tab-add_new_book_pane":
            addnewbook = self.query_one(AddNewBook)
            addnewbook.authors = self._all_authors
            addnewbook.tags = self._all_tags
            return

        if event.tab.id == "--content-tab-details_pane":
            active_tab_content = self.query_one(TabbedContent)

            if not self._current_uuid:
                self.notify("Select a book first", severity="warning")
                active_tab_content.active = "list" # Torna alla lista
                return

            book = self._uuid_to_book.get(self._current_uuid)
            if not book:
                self.notify("Book not found", severity="error")
                active_tab_content.active = "list"
                return

            details = self.query_one(BookDetails)
            details.book_data = book


    # def _build_tags_tree(self):
    #     self._tags_tree.clear()
    #     root_node = self._tags_tree.root
    #     self._all_tags = []

    #     # Aggiungi tag gerarchici
    #     for parent_tag in ConfigReader.get_parent_tags():
    #         parent_label = ConfigReader.get_tag_display_name(parent_tag)
    #         parent_node = root_node.add(parent_label, data=parent_tag)
    #         self._all_tags.append(parent_tag)

    #         for child_tag in ConfigReader.get_child_tags(parent_tag):
    #             child_label = ConfigReader.get_tag_display_name(child_tag)
    #             parent_node.add(child_label, data=child_tag)
    #             self._all_tags.append(child_tag)

    #     # Aggiungi tag piatti
    #     for flat_tag in ConfigReader.FLAT_TAGS:
    #         flat_label = ConfigReader.get_tag_display_name(flat_tag)
    #         root_node.add(flat_label, data=flat_tag)
    #         self._all_tags.append(flat_tag)

    #     # Espandi tutto e aggiorna
    #     root_node.expand_all()
    #     self._all_tags = sorted(list(set(self._all_tags)))
    #     # Forza il refresh del widget
    #     self._tags_tree.refresh()


    def _open_file(self):
        if not self._current_uuid:
            self.notify("No book selected", severity="warning")
            return

        book = self._uuid_to_book.get(self._current_uuid)
        if not book:
            self.notify("Selected book data not found", severity="error")
            return

        # Usa la property LIBRARY letta da Config
        library_path = Path(ConfigReader.LIBRARY)
        author = book.get('author', 'Unknown Author')
        filename = book.get('filename')

        if not filename:
             self.notify("Filename missing for this book", severity="error")
             return

        try:
            filepath = (library_path / author / filename).resolve()

            # Verifica aggiuntiva che il percorso risolto sia ancora dentro LIBRARY
            if not str(filepath).startswith(str(library_path.resolve())):
                 self.notify("❌ Invalid file path (outside library)", severity="error")
                 return

            if not filepath.is_file(): # Usa is_file() invece di exists()
                self.notify(f"❌ File not found: {filepath.name}", severity="error")
                return

            # Apri il file
            self.notify(f"🚀 Opening {filepath.name}...") # Feedback utente
            if os.name == 'nt': # Windows
                os.startfile(filepath)
            elif sys.platform == 'darwin': # macOS
                 os.system(f'open "{filepath}"')
            else: # Linux/Altri Unix
                os.system(f'xdg-open "{filepath}"')

        except OSError as e:
             self.notify(f"❌ OS Error opening file: {e}", severity="error")
        except Exception as e:
            # Log più dettagliato per il debug
            self.log.error(f"Unexpected error opening file '{filepath}': {e}")
            self.notify(f"❌ Unexpected error opening file", severity="error")


    def _update_table(self, books_to_display=None) -> None:
        """Aggiorna la tabella e l'albero dei tag se necessario."""
        try:
            # 1. Aggiorna cache se necessario
            # Se books_to_display non è fornito O se la cache è vuota, ricarica dal DB
            if books_to_display is None or not self._cache_books:
                self.log.info("Refreshing book cache from database...")
                try:
                    self._cache_books = sorted(self._db.all(), key=lambda x: x.get("added", ""), reverse=True)
                    self._uuid_to_book = {book["uuid"]: book for book in self._cache_books}
                    self.log.info(f"Cache updated with {len(self._cache_books)} books.")
                except Exception as db_err:
                    self.notify(f"❌Error reading database: {db_err}", severity="error")
                    self._cache_books = [] # Svuota cache in caso di errore
                    self._uuid_to_book = {}

            if books_to_display is None or len(books_to_display) == 0:
                 books_to_display = self._cache_books

            # 2. Ricostruisci l'albero dei tag solo se è vuoto (la prima volta o dopo un clear)
            # if not self._tags_tree.root.children:
            #     self.log.info("Building tags tree...")
            #     self._build_tags_tree() # Ora usa la nuova logica

            # 3. Aggiorna lista autori (basata sulla cache completa)
            if not self._all_authors:
                self._all_authors = sorted(list(set(
                    book["author"] for book in self._cache_books
                    if book.get("author") # Assicura che la chiave esista e non sia vuota/None
                )))

            if not self._all_tags or books_to_display is None: # Ricalcola se forzato o vuoto
                all_tags_flat = set()
                for book in self._cache_books:
                    for tag in book.get("tags", []):
                        all_tags_flat.add(tag)
                self._all_tags = sorted(list(all_tags_flat))

            # 4. Popola la tabella con i libri da visualizzare (filtrati o tutti)
            self._table.clear()
            if not books_to_display:
                 self.log.warning("No books to display in the table.")
                 self._table.add_row("---", "No books found", "---", "---")
                 return # Esce se non ci sono libri

            self.log.info(f"Populating table with {len(books_to_display)} books.")
            rows = []
            for book in books_to_display:
                try:
                    added_formatted = "N/A"
                    if added_ts := book.get("added"):
                         try:
                             added_formatted = FormattedDateTime.fromisoformat(added_ts)
                         except (ValueError, TypeError):
                             self.log.warning(f"Invalid date format for book {book.get('uuid', 'N/A')}: {added_ts}")
                except Exception as date_err:
                     self.log.error(f"❌Error processing date for book {book.get('uuid', 'N/A')}: {date_err}")
                     added_formatted = "Error"

                title = book.get("title", "No Title")
                author = book.get("author", "Unknown Author")
                tags_list = book.get("tags", [])
                tags_display = ", ".join(tags_list) if tags_list else "No Tags"

                # Limita lunghezza per display
                title_display = title[:77] + "..." if len(title) > 80 else title
                author_display = author[:27] + "..." if len(author) > 30 else author

                rows.append((
                    added_formatted,
                    title_display,
                    author_display,
                    tags_display,
                ))

            # keys = [book["uuid"] for book in books_to_display]

            for i, book in enumerate(books_to_display):
                row_data = rows[i]  # Get the pre-formatted row data
                key = book["uuid"] # Get the key for this book
                # Add the row using add_row, unpacking the data and providing the key
                self._table.add_row(*row_data, key=key)

        except Exception as e:
            self.log.error(f"Critical error during table update: {e}", exc_info=True)
            self.notify(f"Error updating table: {e}", severity="error")


    def _run_search(self, search_term: str):
        """Filtra i libri nella cache basandosi sul termine di ricerca."""
        search_term_lower = search_term.lower()
        self.log.info(f"Running search for: '{search_term}'")

        # Filtra sulla cache, non ricaricare dal DB qui
        results = [
            book for book in self._cache_books
            if (search_term_lower in book.get("title", "").lower() or
                search_term_lower in book.get("author", "").lower() or
                # Cerca nei tag (assumendo siano nomi puliti nel DB)
                any(search_term_lower in tag.lower() for tag in book.get("tags", [])))
        ]
        self.log.info(f"Search found {len(results)} results.")
        # Aggiorna la tabella solo con i risultati
        self._update_table(results)


    def _filter_on_tags(self, tag_to_filter: str):
        tag_lower = tag_to_filter.lower()
        self.log.info(f"Filtering books by tag: '{tag_to_filter}'")

        results = [
            book for book in self._cache_books
            if tag_lower in [t.lower() for t in book.get("tags", [])]
        ]
        self.log.info(f"Filter found {len(results)} books with tag '{tag_to_filter}'.")
        self._update_table(results)



    @on(Button.Pressed, "#btndelete")
    def handle_delete(self, event: Button.Pressed) -> None:
        if not self._current_uuid:
            self.notify("❌Select a book to delete first.", severity="warning")
            return

        book = self._uuid_to_book.get(self._current_uuid)
        if not book:
            self.notify("❌Cannot find data for the selected book.", severity="error")
            return

        # Assumi che YesOrNo accetti una callback `on_confirm` o simile
        # che viene chiamata con True/False
        # self.push_screen(YesOrNo(self._db, self._current_uuid, book["title"], on_confirm=refresh_after_delete))

        # Se YesOrNo non ha callback, aggiorna sempre dopo la chiusura (meno ideale)
        self.push_screen(YesOrNo(self._db, self._current_uuid, book["title"]))
        # TODO: Idealmente YesOrNo dovrebbe emettere un messaggio o chiamare una callback
        # per aggiornare la tabella *solo* se la cancellazione avviene.
        # Per ora, aggiorniamo comunque al ritorno:
        self.call_after_refresh(lambda: self._update_table([]))


    @on(Button.Pressed, "#btnrefresh")
    def handle_refresh(self, event: Button.Pressed) -> None:
        self.notify("🔄 Refreshing data...")
        self._update_table([]) # Forza ricaricamento completo da DB


    @on(Button.Pressed, "#btnopen_file")
    def handle_open_file(self, event: Button.Pressed) -> None:
        self._open_file() # Chiama il metodo helper


    @on(BookDetails.OpenFileRequest)
    def handle_open_file_request(self, event: BookDetails.OpenFileRequest) -> None:
        """Gestisce la richiesta di apertura file dal pannello dettagli."""
        # Trova l'UUID corrispondente ai dati ricevuti
        found_uuid = None
        for uuid, book in self._uuid_to_book.items():
            # Confronta usando un identificatore univoco se possibile (es. uuid)
            if book.get("uuid") == event.book_data.get("uuid"):
                 found_uuid = uuid
                 break
        # Se non trovi per uuid, prova un confronto più lasco (meno affidabile)
        if not found_uuid:
             for uuid, book in self._uuid_to_book.items():
                  if book == event.book_data:
                       found_uuid = uuid
                       break

        if found_uuid:
            self._current_uuid = found_uuid # Imposta l'UUID corrente
            self._open_file() # Chiama l'apertura file
        else:
            self.notify("❌Could not match book details to open file.", severity="error")


    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Gestisce la ricerca dall'input."""
        search_value = event.value.strip()
        if len(search_value) >= 3: # Minimo 3 caratteri per la ricerca
            self._run_search(search_value)
        elif not search_value: # Se l'input è vuoto, mostra tutto
            self.notify("Showing all books.")
            self._update_table([]) # Mostra tutti i libri dalla cache


    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """ Aggiorna l'UUID corrente e i dettagli quando una riga è selezionata """
        if event.row_key.value is not None:
            self._current_uuid = event.row_key.value
            # Aggiorna i dettagli *solo se* il tab dei dettagli è attivo
            active_tab_pane_id = self.query_one(TabbedContent).active
            if active_tab_pane_id == "details_pane":
                 book = self._uuid_to_book.get(self._current_uuid)
                 if book:
                     details = self.query_one(BookDetails)
                     details.book_data = book
                 else:
                     self.log.warning(f"No book data found for highlighted UUID: {self._current_uuid}")
        else:
            self._current_uuid = None

    @on(AddNewBook.SaveFileRequest)
    def handle_open_file_request(self, event: AddNewBook.SaveFileRequest) -> None:
        """ Gestisce la richiesta di salvataggio nuovo libro """
        new_book_data = event.book_data
        tags = event.book_data.get("tags", [])

        fileinfo = new_book_data.get("fileinfo")
        author = new_book_data.get("author")
        author_path = Path(f"{ConfigReader.LIBRARY}/{author}")
        stem = fileinfo.get("stem") # non usato al momento
        ext = fileinfo.get("extension")
        title = new_book_data.get("title")

        src_file = fileinfo.get("full_path")

        new_file_name = f"{title} - {author}{ext}"
        new_file_path = Path(f"{ConfigReader.LIBRARY}/{author}/{new_file_name}")
        tags_list = sorted([t.strip() for t in tags if t.strip()])

        try:
            validate_filename(new_file_name, platform="universal")
        except ValidationError as e:
            self.notify(f"Invalid characters in {new_file_path} for filename/directory: {e}", severity="error")
            return

        try:
            # Create directory if not exists
            author_path.mkdir(parents=True, exist_ok=True)

            # Check if file already exists to prevent accidental overwrite
            if new_file_path.exists():
                self.notify(f"File '{new_file_name}' already exists in '{author}' directory. Please rename or choose a different title.", severity="error")
                return

            shutil.copy2(src_file, new_file_path)
            self.log.info(f"File copied to: {new_file_path}")

            # Write metadata using exiftool
            try:
                keywords_str = ",".join(tags)

                exiftool_cmd = [
                    str(Path(ConfigReader.EXIFTOOL_PATH)),
                    "-charset", "utf8", # Use UTF-8 for metadata
                    f"-Title={title}",
                    f"-Author={author}",
                    f"-Keywords={keywords_str}", # Pass the string here
                    "-overwrite_original", # Overwrite the copied file
                    str(new_file_path) # Pass path as string
                ]
                self.log.info(f"Running exiftool: {' '.join(exiftool_cmd)}") # Log the command
                # Capture output for better error reporting
                result = subprocess.run(exiftool_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
                self.log.info(f"Exiftool output: {result.stdout}")
                if result.stderr:
                     self.log.warning(f"Exiftool stderr: {result.stderr}") # Log warnings

            except FileNotFoundError:
                 self.notify(f"❌ Exiftool not found at: {ConfigReader.EXIFTOOL_PATH}. Metadata not written.", severity="error")
                 # Decide if you want to proceed without metadata or stop
            except subprocess.CalledProcessError as e:
                self.log.error(f"Exiftool failed: {e.stderr}")
                self.notify(f"❌ Error writing metadata with exiftool: {e.stderr[:200]}...", severity="error")
                # Decide if you want to proceed or stop
            except Exception as exif_err: # Catch other potential errors
                self.log.error(f"Unexpected error during exiftool execution: {exif_err}", exc_info=True)
                self.notify(f"❌ Unexpected error writing metadata: {exif_err}", severity="warning") # Warn but maybe proceed

            # Prepare data for database insertion
            book_data = {
                "uuid": str(uuid.uuid4()),
                "author": author,
                "title": title,
                "added": FormattedDateTime.now(),
                "tags": tags_list, # Save the CLEAN list of tags
                "filename": new_file_name, # Save the new filename
                "other_formats": [], # Default fields
                "series": "",
                "num_series": None, # Use None instead of 1.0 if no series
                "desc": "",
                "read": ""
            }

            # Insert into database
            self._db.insert(book_data)
            self.log.info(f"Book data inserted into DB for UUID: {book_data['uuid']}")

            self.notify("✅ Book added successfully!", severity="information")

            self._cache_books = []  # Clear cache to force reload
            self._update_table([])
            # self.query_one(TabbedContent).active = "list"

        except OSError as e:
             # Handle file system errors (permissions, disk full etc.)
             self.log.error(f"File system error during save: {e}", exc_info=True)
             self.notify(f"❌ File system error: {e}", severity="error")
        except Exception as e:
             # Catch-all for unexpected errors during the save process
             self.log.error(f"Unexpected error saving book file: {e}", exc_info=True)
             self.notify(f"❌ Unexpected error saving book: {e}", severity="error")


    @on(Tree.NodeSelected)
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """ Gestisce la selezione di un nodo nell'albero dei tag """
        clean_tag_name = event.node.data

        if clean_tag_name and isinstance(clean_tag_name, str):
            self._filter_on_tags(clean_tag_name)

            search_input = self.query_one("#search_input", Input)
            if search_input.value:
                 search_input.value = ""
                 self.notify(f"Filtered by tag: {clean_tag_name}", title="Filter Active")
        else:
            self.log.info("Root node or node without data selected, showing all.")
            # self._update_table([]) # O non fare nulla
            pass # Non fare nulla se non c'è un tag valido

    CSS = """
BookManagerApp {
    .datatable-container {
        content-align: center middle;
        padding: 0 0;
    }

    #tags_tree {
        width: 15%;
        padding: 1 1;
    }
}

    /* anche se usato in main la button-row torna utile in altri posti */
.button-row {
    align-horizontal: center;
    align-vertical: top;
    height: 5;
    padding: 0 0;

    #search_input {
        width: 50%;
    }
}

.hidden {
    display: none;
}

.center-label {
    content-align: right middle;
    background: $primary-background;
    height: 3;
    width: 1fr;
}

Grid {
    border: solid $primary;
    padding: 2 4;
    height: auto;
    grid-size: 2;
    grid-columns: auto 1fr;
    width: 80%;

    Label {
        padding: 1;
    }

    Input {
        width: 70%;
    }

    TextArea {
        padding: 1;
        width: 70%;
        height: 3fr;
    }
}

#filtered_dir_tree_container {
    width: 80%;
    align: center middle;
}
"""