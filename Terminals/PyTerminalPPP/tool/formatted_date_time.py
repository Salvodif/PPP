from datetime import datetime, timezone

class FormattedDateTime:
    """
    Fornisce metodi di classe per ottenere stringhe di data/ora
    formattate come "YYYY-MM-DD HH:MM".
    """

    # Definiamo il formato desiderato come costante di classe per coerenza
    _TARGET_FORMAT = "%Y-%m-%d %H:%M"

    @classmethod
    def now(cls) -> str:
        """
        Restituisce la data e l'ora correnti (in UTC)
        come stringa formattata "YYYY-MM-DD HH:MM".
        """
        # Ottieni l'ora corrente in UTC (scelta consigliata per evitare ambiguità)
        current_utc_time = datetime.now(timezone.utc)
        # Formatta secondo lo standard richiesto
        return current_utc_time.strftime(cls._TARGET_FORMAT)

    @classmethod
    def fromisoformat(cls, iso_string: str) -> str:
        """
        Converte una stringa in formato ISO 8601 in una stringa
        formattata "YYYY-MM-DD HH:MM".

        Args:
            iso_string: La stringa in formato ISO 8601 (es. "2023-11-15T10:30:00Z").

        Returns:
            La stringa formattata.

        Raises:
            ValueError: Se la stringa di input non è in formato ISO valido.
        """
        try:
            # Parsifica la stringa ISO in un oggetto datetime
            dt_object = datetime.fromisoformat(iso_string)
            # Formatta l'oggetto datetime nel formato desiderato
            return dt_object.strftime(cls._TARGET_FORMAT)
        except ValueError as e:
            # Rilancia l'errore con un messaggio più specifico se il parsing fallisce
            raise ValueError(f"La stringa fornita non è un formato ISO 8601 valido: '{iso_string}'") from e

    @classmethod
    def from_raw(cls, raw_string: str) -> str:
        """
        Valida e formatta una stringa nel formato "YYYY-MM-DD HH:MM".
        Utile per assicurarsi che una stringa esistente rispetti il formato
        e per normalizzarla (anche se la formattazione è la stessa).

        Args:
            raw_string: La stringa da validare e formattare (es. "2024-01-01 15:00").

        Returns:
            La stringa formattata (identica all'input se valido).

        Raises:
            ValueError: Se la stringa di input non corrisponde al formato "YYYY-MM-DD HH:MM".
        """
        try:
            # Parsifica la stringa ESATTAMENTE nel formato atteso per validarla
            dt_object = datetime.strptime(raw_string, cls._TARGET_FORMAT)
            # Riformatta (garantisce che l'output sia *esattamente* quello voluto)
            # Anche se dt_object.__str__() potrebbe funzionare, strftime è esplicito.
            return dt_object.strftime(cls._TARGET_FORMAT)
        except ValueError as e:
            # Rilancia l'errore indicando il formato atteso
            raise ValueError(f"La stringa fornita '{raw_string}' non corrisponde al formato richiesto '{cls._TARGET_FORMAT}'") from e
