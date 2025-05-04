from pathlib import Path
import tinydb
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from formvalidators import FormValidators
from filesystem import FileSystemHandler

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
        added_str = data['added']
        
        # Rimuovi i microsecondi dalla stringa se presenti
        if '.' in added_str and 'Z' not in added_str and '+' not in added_str and '-' not in added_str:
            added_str = added_str.split('.')[0]
        
        try:
            # Prova a parsare con timezone se presente
            if '+' in added_str or added_str.endswith('Z'):
                added = datetime.fromisoformat(added_str)
            else:
                # Altrimenti parsare senza timezone e aggiungerlo
                try:
                    added = datetime.strptime(added_str, "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    added = datetime.strptime(added_str, "%Y-%m-%dT%H:%M")
                added = added.replace(tzinfo=datetime.now().astimezone().tzinfo)
        except ValueError as e:
            # Fallback alla data corrente in caso di errori
            added = datetime.now().astimezone()
            print(f"Errore nel parsing della data '{added_str}': {e}. Usata data corrente.")

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
            'added': self.added.isoformat(timespec='seconds'),  # Force no microseconds
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


class TagsManager:
    def __init__(self, file_path: str):
        self.db = tinydb.TinyDB(file_path)
        self.tags_table = self.db.table('tags')
        self._cache = None
        self._dirty = True

    def _ensure_cache(self):
        """Carica la cache se è obsoleta o non esiste"""
        if self._dirty or self._cache is None:
            self._cache = {tag.doc_id: tag for tag in self.tags_table.all()}
            self._dirty = False

    def get_all_tags(self) -> Dict[int, Dict[str, Any]]:
        """Ottiene tutti i tag dalla cache"""
        self._ensure_cache()
        return self._cache.copy()

    def get_tag_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Ottiene un tag specifico per nome"""
        self._ensure_cache()
        for tag in self._cache.values():
            if tag['name'] == name:
                return tag
        return None

    def add_tag(self, name: str, icon: str) -> int:
        """Aggiunge un nuovo tag"""
        tag_id = self.tags_table.insert({'name': name, 'icon': icon})
        self._dirty = True
        return tag_id

    def update_tag(self, tag_id: int, new_data: Dict[str, Any]):
        """Aggiorna un tag esistente"""
        self.tags_table.update(new_data, doc_ids=[tag_id])
        self._dirty = True

    def remove_tag(self, tag_id: int):
        """Rimuove un tag"""
        self.tags_table.remove(doc_ids=[tag_id])
        self._dirty = True

    def close(self):
        """Chiude la connessione al database"""
        self.db.close()
        self._cache = None
        self._dirty = True


################################## BookManager
# Gestisce l'interazione con il database TinyDB per i libri
class BookManager:
    def __init__(self, file_path: str, library_root: str, tags_manager: TagsManager = None):
        self.db = tinydb.TinyDB(file_path)
        self.books_table = self.db.table('books')
        self._cache = None
        self._dirty = True
        self._library_root = library_root
        self.tags_manager = tags_manager


    @property
    def library_root(self) -> str:
        return self._library_root

    def _ensure_cache(self):
        """Carica la cache se è obsoleta o non esiste"""
        if self._dirty or self._cache is None:
            self._cache = {book['uuid']: Book.from_dict(book) 
                          for book in self.books_table.all()}
            self._dirty = False

    def add_book(self, book: Book):
        # Validazione nome autore
        is_valid, fs_name = FormValidators.validate_author_name(book.author)
        if not is_valid:
            raise ValueError(f"Nome autore non valido: {fs_name}")

        """Aggiunge un libro al database e invalida la cache"""
        self.books_table.insert(book.to_dict())
        self._dirty = True

    def get_book_path(self, book: Book) -> str:
        """Restituisce il percorso completo del libro"""
        if not book.filename:
            raise ValueError("Il libro non ha un filename associato")
            
        author_dir = FormValidators.author_to_fsname(book.author)
        return str(Path(self.library_root) / author_dir / book.filename)
    
    def ensure_author_directory(self, author: str) -> str:
        """Crea la directory dell'autore se non esiste"""
        author_dir = FormValidators.author_to_fsname(author)
        author_path = Path(self.library_root) / author_dir
        return FileSystemHandler.ensure_directory_exists(str(author_path))
    
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

    def search_books_by_text(self, text: str) -> List[Book]:
        """Cerca libri per testo in titolo o autore"""
        if not text:
            return self.get_all_books()
            
        self._ensure_cache()
        text_lower = text.lower()
        
        return [
            book for book in self._cache.values()
            if (book.title and text_lower in book.title.lower()) or
               (book.author and text_lower in book.author.lower())
        ]

    def sort_books(self, field: str, reverse: bool = None) -> List[Book]:
        books = self.get_all_books()

        if not books:
            return []

        # Se reverse è None, usa un valore predefinito in base al campo
        if reverse is None:
            reverse = False if field != 'added' else True

        if field == 'added':
            books.sort(key=lambda x: x.added, reverse=reverse)
        elif hasattr(books[0], field):
            books.sort(key=lambda x: str(getattr(x, field) or ''), reverse=reverse)

        return books

    def close(self):
        """Chiude la connessione al database e pulisce la cache"""
        self.db.close()
        self._cache = None
        self._dirty = True

######################################################################
#
#
#
######################################################################
class LibraryManager:
    """Contenitore per BookManager e TagsManager"""

    def __init__(self, db_path: str, library_root: str):
        self.db_path = db_path
        self.library_root = library_root
        self._book_manager = None
        self._tags_manager = None
    
    @property
    def books(self) -> BookManager:
        """Accesso al BookManager"""
        if self._book_manager is None:
            self._book_manager = BookManager(self.db_path, self.library_root)
        return self._book_manager
    
    @property
    def tags(self) -> TagsManager:
        """Accesso al TagsManager"""
        if self._tags_manager is None:
            self._tags_manager = TagsManager(self.db_path)
        return self._tags_manager
    
    def close(self):
        """Chiude tutte le connessioni"""
        if self._book_manager:
            self._book_manager.close()
        if self._tags_manager:
            self._tags_manager.close()