import json
from pathlib import Path
from typing import Dict, List

class ConfigManager:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Carica il file di configurazione JSON"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Errore nel caricamento del file di configurazione: {e}")

    def _save_config(self):
        """Salva le modifiche nel file di configurazione"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise RuntimeError(f"Errore nel salvataggio del file di configurazione: {e}")

    @property
    def paths(self) -> Dict[str, str]:
        """Restituisce i percorsi configurati"""
        return self.config.get('paths', {})

    def update_path(self, key: str, new_path: str):
        """
        Aggiorna un percorso specifico e salva le modifiche
        
        Args:
            key: Uno dei valori tra 'db', 'library', 'main_upload_dir', 'exiftool_path'
            new_path: Il nuovo percorso da impostare
        """
        if key not in ['db', 'library', 'main_upload_dir', 'exiftool_path']:
            raise ValueError(f"Chiave di percorso non valida: {key}")
        
        self.config['paths'][key] = str(new_path)
        self._save_config()

    def update_paths(self, new_paths: Dict[str, str]):
        """
        Aggiorna più percorsi contemporaneamente e salva le modifiche
        
        Args:
            new_paths: Dizionario con le nuove impostazioni dei percorsi
                     Esempio: {'db': 'new/path.json', 'library': 'new/library/path'}
        """
        for key, path in new_paths.items():
            if key in ['db', 'library', 'main_upload_dir', 'exiftool_path']:
                self.config['paths'][key] = str(path)
        
        self._save_config()

    # Metodi esistenti per la gestione dei tag...
    @property
    def tag_hierarchy(self) -> Dict:
        """Restituisce la gerarchia dei tag"""
        return self.config.get('tags', {}).get('hierarchy', {})

    @property
    def flat_tags(self) -> List[str]:
        """Restituisce i tag piatti (non gerarchici)"""
        return self.config.get('tags', {}).get('flat_tags', [])

    def get_tag_icon(self, tag_name: str) -> str:
        """Restituisce l'icona per un tag specifico"""
        icons = self.config.get('tag_icons', {})
        return icons.get(tag_name, icons.get('default', '📄'))

    def get_all_tags(self) -> List[str]:
        """Restituisce tutti i tag (gerarchici e piatti)"""
        tags = []

        def extract_tags(hierarchy: Dict):
            for key, value in hierarchy.items():
                tags.append(key)
                if isinstance(value, dict):
                    extract_tags(value)

        extract_tags(self.tag_hierarchy)
        tags.extend(self.flat_tags)
        return sorted(list(set(tags)))