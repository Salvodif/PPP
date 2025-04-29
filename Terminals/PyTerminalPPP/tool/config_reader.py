import os
import json # Importa la libreria json integrata
from typing import Dict, List, Any # Aggiunto Any per una maggiore flessibilità nei tipi

# Rimuovi 'import yaml' se non serve più per altro

class ConfigReader:
    _instance = None
    _loaded = False

    # Il percorso ora punta a config.json di default
    CONFIGPATH: str = os.path.join(os.path.dirname(__file__), "config.json")

    # Valori di default (rimangono gli stessi)
    DB: str = ""
    LIBRARY: str = ""
    MAIN_UPLOAD_DIR: str = ""
    EXIFTOOL_PATH: str = ""
    TAGS_HIERARCHY: Dict[str, Any] = {} # Usa Any per gestire sotto-dizionari annidati
    TAGS_ICONS: Dict[str, str] = {}
    FLAT_TAGS: List[str] = []
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".epub"}
    TAG_ICONS: Dict[str, str] = {} # Mappa icone (era duplicato, ora è corretto)


    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # cls._loaded = False # Non serve resettare qui, viene fatto in _load_config
            cls._load_config() # Carica subito alla prima istanziazione
        return cls._instance

    @classmethod
    def _load_config(cls):
        # Evita ricaricamenti multipli se non necessario
        # (Potrebbe essere utile un metodo reload() esplicito se vuoi ricaricare a runtime)
        if cls._loaded:
            return

        # Usa il percorso definito nella classe
        json_path = cls.CONFIGPATH

        if not os.path.exists(json_path):
            print(f"⚠️ Attenzione: File di configurazione '{json_path}' non trovato. Verranno usati i valori di default.")
            cls._loaded = True # Considera caricato anche se il file non c'è, per evitare tentativi ripetuti
            return

        try:
            # Apri e leggi il file JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                # Usa json.load per parsare il file
                config_data = json.load(f) or {}

            # Carica i percorsi usando .get con i valori di default della classe
            paths = config_data.get('paths', {})
            cls.DB = paths.get('db', cls.DB)
            cls.LIBRARY = paths.get('library', cls.LIBRARY)
            cls.MAIN_UPLOAD_DIR = paths.get('main_upload_dir', cls.MAIN_UPLOAD_DIR)
            cls.EXIFTOOL_PATH = paths.get('exiftool_path', cls.EXIFTOOL_PATH)

            # Carica i tag (gerarchia e piatti)
            tags_section = config_data.get('tags', {})
            cls.TAGS_HIERARCHY = tags_section.get('hierarchy', cls.TAGS_HIERARCHY)
            cls.FLAT_TAGS = tags_section.get('flat_tags', cls.FLAT_TAGS)

            # Carica le icone dei tag
            cls.TAG_ICONS = config_data.get('tag_icons', cls.TAG_ICONS)

            cls._loaded = True
            print(f"✅ Configurazione caricata da '{json_path}'.")

        # Gestisci errori specifici del JSON
        except json.JSONDecodeError as e:
            print(f"❌ Errore di parsing JSON in {json_path}: {e}")
            cls._loaded = False # Fallito il caricamento
        except Exception as e:
            print(f"❌ Errore generico nel caricamento di {json_path}: {e}")
            cls._loaded = False # Fallito il caricamento

    # --- Metodi esistenti (rimangono invariati nel funzionamento) ---

    @classmethod
    def get_icon_for_tag(cls, tag_name: str) -> str:
        """Restituisce l'icona per un dato nome di tag."""
        # Assicurati che la configurazione sia caricata
        if not cls._loaded: cls._load_config()
        return cls.TAG_ICONS.get(tag_name, cls.TAG_ICONS.get("default", "")) # Aggiunto fallback a icona 'default'

    @classmethod
    def get_tag_display_name(cls, tag_name: str) -> str:
        """Restituisce il nome del tag formattato con l'icona (se presente)."""
        # Assicurati che la configurazione sia caricata
        if not cls._loaded: cls._load_config()
        icon = cls.get_icon_for_tag(tag_name)
        return f"{icon} {tag_name}".strip()

    @classmethod
    def get_all_tags(cls) -> List[str]:
        """Restituisce una lista piatta di tutti i tag definiti (gerarchici e piatti)."""
        if not cls._loaded: cls._load_config()
        all_tags_set = set(cls.FLAT_TAGS)

        def extract_nested_tags(hierarchy: Dict[str, Any]):
            for parent, children in hierarchy.items():
                all_tags_set.add(parent)
                if isinstance(children, dict): # Se i figli sono un altro dizionario
                    extract_nested_tags(children)
                elif isinstance(children, list): # Se i figli sono una lista (improbabile nella tua struttura, ma per sicurezza)
                    all_tags_set.update(children)

        extract_nested_tags(cls.TAGS_HIERARCHY)
        return sorted(list(all_tags_set)) # Ritorna lista ordinata

    @classmethod
    def get_parent_tags(cls) -> List[str]:
        """Restituisce la lista dei tag padre principali (nomi puliti)."""
        if not cls._loaded: cls._load_config()
        return list(cls.TAGS_HIERARCHY.keys())

    @classmethod
    def get_child_tags(cls, parent_tag: str) -> List[str]:
        """Restituisce la lista dei tag figli diretti per un genitore."""
        if not cls._loaded: cls._load_config()
        children = cls.TAGS_HIERARCHY.get(parent_tag, {})
        if isinstance(children, dict):
             # Se i figli sono un dizionario, restituisci le sue chiavi (che sono i sotto-tag)
             return list(children.keys())
        elif isinstance(children, list):
             # Se (improbabilmente) i figli fossero una lista, restituiscila
             return children
        else:
            # Se il genitore non esiste o non ha figli strutturati, ritorna lista vuota
            return []
