from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container
from textual.widgets import Header, Footer, DataTable

from widgets.datatablebook import DataTableBook

from models import BookManager
from screens.add import AddScreen
from screens.edit import EditScreen

class MainScreen(Screen):
    BINDINGS = [
        ("e", "edit_book", "Modifica"),
        ("ctrl+a", "add_book", "Aggiungi"),
        ("ctrl+r", "reverse_sort", "Inverti ordine"),
    ]

    def __init__(self, library: BookManager):
        super().__init__()
        self.library = library
        self.sort_reverse = False
        self.sort_field = "added"
        self.theme = "nord"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            DataTableBook(id="books-table"),
            id="main-container"
        )
        yield Footer()

    def on_mount(self):
        self.update_table()

    def update_table(self):
        self.library.sort_books(self.sort_field, self.sort_reverse)
        table = self.query_one("#books-table", DataTableBook)
        table.update_table(self.library.get_all_books())

    def action_edit_book(self):
        table = self.query_one("#books-table", DataTableBook)

        book_uuid = table.current_uuid

        b = self.library.get_book(book_uuid)
        
        if b:
            self.app.push_screen(EditScreen(self.library, b))


    def action_add_book(self):
        self.app.push_screen(AddScreen(self.library))


    def action_reverse_sort(self):
        table = self.query_one("#books-table", DataTableBook)

        column_mapping = {
            0: "added",
            1: "author",
            2: "title",
            3: "read",
            4: "tags"
        }

        # Ottieni la colonna corrente del cursore
        current_col = table.current_column
        
        # Se il cursore è su una colonna valida, usa quella per l'ordinamento
        if current_col is not None and current_col in column_mapping:
            self.sort_field = column_mapping[current_col]

        # Inverti l'ordine
        self.sort_reverse = not self.sort_reverse

        # Ordina e aggiorna la tabella
        sorted_books = self.library.sort_books(self.sort_field, self.sort_reverse)
        table.update_table(sorted_books)


    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key.value is not None:
            self._current_uuid = event.row_key.value


    def on_data_table_header_selected(self, event):
        # Aggiorna il campo di ordinamento quando si clicca su un header
        column_mapping = {
            0: "added",
            1: "author",
            2: "title",
            3: "read",
            4: "tags"
        }

        self.sort_field = column_mapping.get(event.column_index, "added")
        self.sort_reverse = False  # Resetta l'ordinamento a crescente
        self.update_table()