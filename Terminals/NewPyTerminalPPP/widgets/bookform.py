from textual.widgets import Input, Button, TextArea
from datetime import datetime

class BookForm:
    def __init__(self, libro=None):
        self.libro = libro
        self.title_input = Input(placeholder="Titolo", value=libro.title if libro else "")
        self.author_input = Input(placeholder="Autore", value=libro.author if libro else "")
        self.tags_input = Input(placeholder="Tags (separati da virgola)", 
                               value=", ".join(libro.tags) if libro else "")
        self.series_input = Input(placeholder="Serie", value=libro.series if libro and libro.series else "")
        self.num_series_input = Input(placeholder="Numero serie", 
                                    value=str(libro.num_series) if libro and libro.num_series else "")
        self.read_input = Input(placeholder="Data lettura (YYYY-MM-DD)", 
                              value=libro.read if libro and libro.read else "")
        self.description_input = TextArea(libro.description if libro and libro.description else "", 
                                        language="markdown")
        self.save_button = Button("Salva", variant="primary")
    
    def get_values(self):
        return {
            'title': self.title_input.value,
            'author': self.author_input.value,
            'tags': [tag.strip() for tag in self.tags_input.value.split(",") if tag.strip()],
            'series': self.series_input.value if self.series_input.value else None,
            'num_series': float(self.num_series_input.value) if self.num_series_input.value else None,
            'read': self.read_input.value if self.read_input.value else None,
            'description': self.description_input.text if self.description_input.text else None
        }
    
    def validate(self):
        if not self.title_input.value:
            return "Il titolo è obbligatorio"
        if not self.author_input.value:
            return "L'autore è obbligatorio"
        if self.read_input.value:
            try:
                datetime.strptime(self.read_input.value, "%Y-%m-%d")
            except ValueError:
                return "Formato data lettura non valido (usare YYYY-MM-DD)"
        return None