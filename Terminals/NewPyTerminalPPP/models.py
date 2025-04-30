import tinydb
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Union

@dataclass
class Book:
    uuid: str
    author: str
    title: str
    added: datetime
    tags: List[str] = field(default_factory=list)
    filename: str = ""
    other_formats: List[str] = field(default_factory=list)
    series: Optional[str] = None
    num_series: Optional[float] = None
    description: Optional[str] = None
    read: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Book':
        try:
            # Prova prima con il formato completo (con secondi e timezone)
            added = datetime.strptime(data['added'], "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            # Se fallisce, prova con il formato senza secondi
            added = datetime.strptime(data['added'], "%Y-%m-%dT%H:%M%z")

        return cls(
            uuid=data['uuid'],
            author=data['author'],
            title=data['title'],
            added=added,
            tags=data.get('tags', []),
            filename=data.get('filename', ''),
            other_formats=data.get('other_formats', []),
            series=data.get('series'),
            num_series=data.get('num_series'),
            description=data.get('description'),
            read=data.get('read')
        )
    
    def to_dict(self) -> Dict:
        return {
            'uuid': self.uuid,
            'author': self.author,
            'title': self.title,
            'added': self.added.isoformat(),
            'tags': self.tags,
            'filename': self.filename,
            'other_formats': self.other_formats,
            'series': self.series,
            'num_series': self.num_series,
            'description': self.description,
            'read': self.read
        }

    @property
    def formatted_date(self) -> str:
        """Restituisce la data nel formato Y-m-d H:M per l'interfaccia"""
        return self.added.strftime("%Y-%m-%d %H:%M")

    @classmethod
    def parse_ui_date(cls, date_str: str) -> datetime:
        """Converte dal formato dell'interfaccia (Y-m-d H:M) a datetime"""
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M").replace(tzinfo=datetime.now().astimezone().tzinfo)


####### BookManager
# Gestisce l'interazione con il database TinyDB per i libri
class BookManager:
    def __init__(self, file_path: str):
        self.db = tinydb.TinyDB(file_path)
        self.books_table = self.db.table('books')
        self._cache = None
        self._dirty = True 


    def _ensure_cache(self):
        """Carica la cache se è obsoleta o non esiste"""
        if self._dirty or self._cache is None:
            self._cache = {book['uuid']: Book.from_dict(book) 
                          for book in self.books_table.all()}
            self._dirty = False

    def add_book(self, book: Book):
        """Aggiunge un libro al database e invalida la cache"""
        self.books_table.insert(book.to_dict())
        self._dirty = True

    def update_book(self, uuid: str, new_data: Dict):
        """Aggiorna un libro esistente e invalida la cache"""
        q = tinydb.Query()
        if 'added' in new_data and isinstance(new_data['added'], str):
            new_data['added'] = datetime.strptime(
                new_data['added'], "%Y-%m-%dT%H:%M:%S%z").isoformat()

        self.books_table.update(new_data, q.uuid == uuid)
        self._dirty = True

    def remove_book(self, uuid: str):
        """Rimuove un libro dal database e invalida la cache"""
        BookQuery = tinydb.Query()
        self.books_table.remove(BookQuery.uuid == uuid)
        self._dirty = True

    def get_book(self, uuid: str) -> Optional[Book]:
        """Ottiene un libro specifico per UUID dalla cache"""
        self._ensure_cache()
        return self._cache.get(uuid)

    def get_all_books(self) -> List[Book]:
        """Ottiene tutti i libri dalla cache"""
        self._ensure_cache()
        return list(self._cache.values())

    def search_books(self, query: Union[tinydb.Query, Dict]) -> List[Book]:
        """
        Cerca libri nel database.
        Se la query è complessa, bypassa la cache e interroga direttamente il DB.
        Per query semplici, usa la cache filtrata.
        """
        # Se la query è un dict semplice, filtra la cache
        if isinstance(query, dict):
            self._ensure_cache()
            return [book for book in self._cache.values() 
                   if all(getattr(book, k) == v for k, v in query.items())]

        # Per query complesse di TinyDB, interroga direttamente il database
        results = self.books_table.search(query)
        return [Book.from_dict(book) for book in results]


    def sort_books(self, field: str, reverse: bool = False) -> List[Book]:
        """Ordina i libri per un campo specifico utilizzando la cache"""
        books = self.get_all_books()

        if not books:
            return []

        if field == 'added':
            books.sort(key=lambda x: x.added, reverse=reverse)
        elif hasattr(books[0], field):
            books.sort(key=lambda x: str(getattr(x, field) or ''), reverse=reverse)

        return books  # Restituisce la lista ordinata


    def close(self):
        """Chiude la connessione al database e pulisce la cache"""
        self.db.close()
        self._cache = None
        self._dirty = True