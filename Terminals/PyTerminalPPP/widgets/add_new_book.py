from typing import Optional, Dict, Any

""" TEXTUAL LIBRARY """
from textual.app import ComposeResult, on
from textual.widgets import Button, Input, Label
from textual.containers import Vertical, Grid
from textual.reactive import reactive
from textual.message import Message
from textual.suggester import SuggestFromList
from textual.css.query import NoMatches

""" MY LIBRARY """
from tool.config_reader import ConfigReader
from widgets.filtered_directory_tree import FilteredDirectoryTree, FilteredTreePanel


class AddNewBook(Vertical):

    class SaveFileRequest(Message):
        """Evento personalizzato per richiesta salvataggio file."""
        def __init__(self, book_data: Dict[str, Any]):
            self.book_data = book_data
            super().__init__()

    _authors: list[str] = []
    _tags: list[str] = []

    book_data: reactive[Optional[Dict[str, Any]]] = reactive(None)

    def __init__(self, id) -> None:
        super().__init__(id=id)

        self._config = ConfigReader()
        self._new_file_path = None

        self.tree_panel = FilteredTreePanel(
            label_text="Seleziona un file:",
            tree_path=str(ConfigReader.MAIN_UPLOAD_DIR),
            id="add-newbook-tree")

    @property
    def authors(self) -> list[str]:
        return self._authors

    @authors.setter
    def authors(self, new_authors: list[str]) -> None:
        self._authors = new_authors
        # Aggiorna il suggeritore quando la lista cambia
        try:
            author_input = self.query_one("#author", Input)
            if self._authors:
                author_input.suggester = SuggestFromList(self._authors, case_sensitive=False)
            else:
                author_input.suggester = None # Nessun suggeritore se la lista è vuota
        except NoMatches:
            # Il widget potrebbe non essere ancora montato, va bene
            pass


    # !! AGGIUNGI PROPERTY SETTER PER TAGS !!
    @property
    def tags(self) -> list[str]:
        return self._tags

    @tags.setter
    def tags(self, new_tags: list[str]) -> None:
        self._tags = new_tags
        # Aggiorna il suggeritore quando la lista cambia
        try:
            tags_input = self.query_one("#tags", Input)
            if self._tags:
                tags_input.suggester = SuggestFromList(self._tags, case_sensitive=False)
            else:
                tags_input.suggester = None
        except NoMatches:
            pass

    def compose(self) -> ComposeResult:

        yield self.tree_panel
        with Grid(id="grid_container"):
            yield Label("Autore:", classes="center-label")
            # yield Input(placeholder="Author...", suggester=SuggestFromList(self.authors, case_sensitive=False), id="author")
            yield Input(placeholder="Author...", id="author")
            yield Label("Titolo:", classes="center-label")
            yield Input(id="title", placeholder="Titolo...")
            yield Label("Tags:", classes="center-label")
            yield Input(placeholder="Tags...", id="tags")
            # yield Input(placeholder="Tags (comma-separated)", suggester=SuggestFromList(self.tags, case_sensitive=False), id="tags")
            yield Button("❌ Annulla",
                                id="btn_cancel",
                                variant="error",
                                disabled=False)
            yield Button("➕ Aggiungi",
                                id="btn_save",
                                variant="success",
                                disabled=True)


    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes to enable/disable the save button."""
        author = self.query_one("#author", Input).value.strip()
        title = self.query_one("#title", Input).value.strip()

        if author and title and self._new_file_path is not None:
            self.query_one("#btn_save", Button).disabled = False
        else:
            self.query_one("#btn_save", Button).disabled = True


    def on_directory_tree_file_selected(self, event: FilteredDirectoryTree.FileSelected) -> None:
        if event.path.is_file():
            self._new_file_path = {
                "full_path": event.path,                # Percorso completo (Path object)
                "filename": event.path.name,           # Nome del file (str)
                "stem": event.path.stem,               # Nome senza estensione
                "extension": event.path.suffix         # Estensione (con punto, es. ".txt")
            }

            self.notify(f"Selected file: {event.path.name}", severity="info")

            author = self.query_one("#author", Input).value.strip()
            title = self.query_one("#title", Input).value.strip()

            if author and title:
                self.query_one("#btn_save", Button).disabled = False
            else:
                self.query_one("#btn_save", Button).disabled = True

        else:
            self._new_file_path = None
            self.query_one("#btn_save", Button).disabled = True


    def _clear_inputs(self) -> None:
        """Pulisce i campi di input e resetta lo stato."""
        try:
            self.query_one("#author", Input).value = ""
            self.query_one("#title", Input).value = ""
            self.query_one("#tags", Input).value = ""
            self.query_one("#btn_save", Button).disabled = True
            # Potrebbe essere necessario resettare anche la selezione dell'albero
            self.tree_panel.clear_selection() # Assumendo che esista un metodo del genere
            self._new_file_path = None
        except NoMatches:
            # In caso i widget non siano più disponibili per qualche motivo
            pass


    @on(Button.Pressed, "#btn_cancel")
    def handle_cancel_button(self) -> None:
        self._clear_inputs() 


    @on(Button.Pressed, "#btn_save")
    def handle_save_button(self) -> None:
        if not hasattr(self, '_new_file_path') and not isinstance(self._new_file_path, dict) and not self._new_file_path:
            return

        author = self.query_one("#author", Input).value.strip()
        title = self.query_one("#title", Input).value.strip()
        tags = self.query_one("#tags", Input).value.split(",")

        if not author:
            self.notify("Author is required!", severity="error")
            return

        if not title:
            self.notify("Title is required!", severity="error")
            return

        book_data = {
            "author": author,
            "title": title,
            "tags": tags,
            "fileinfo": self._new_file_path
        }

        self.post_message(self.SaveFileRequest(book_data))
        self._clear_inputs()
