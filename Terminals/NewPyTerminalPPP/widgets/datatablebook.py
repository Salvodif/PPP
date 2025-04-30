from typing import Optional
from textual.widgets import DataTable


class DataTableBook(DataTable):
    def on_mount(self):
        self.add_column("Aggiunto", width=10)
        self.add_column("Autore", width=20)
        self.add_column("Titolo", width=70)
        self.add_column("Letto", width=5)
        self.add_column("Tags", width=20)
        self.cursor_type = "row"
        self._current_uuid = 0
    
    def update_table(self, books):
        self.clear()

        for b in books:
            read_date = ""
            if len(b.read) > 0:
                read_date = "X"
            else:
                read_date = "—"

            added_date = b.added.strftime("%Y-%m-%d")
            tags = ", ".join(b.tags)
            self.add_row(
                added_date,
                b.author,
                b.title,
                read_date,
                tags,
                key=b.uuid
            )

    @property
    def current_column(self) -> Optional[int]:
        """Restituisce l'indice della colonna corrente del cursore"""
        if self.cursor_row is not None and self.cursor_column is not None:
            return self.cursor_column
        return None


    @property
    def current_uuid(self):
        return self._current_uuid


    @property
    def last_clicked_column(self):
        return self._last_clicked_column


    @property
    def current_uuid(self):
        return self._current_uuid