import streamlit as st
import pandas as pd
from tinydb import TinyDB, Query, where
from datetime import datetime
import os
import sys
import subprocess # Per aprire i file

# Importa il tuo ConfigReader
try:
    from config_reader import ConfigReader
except ImportError:
    st.error("Errore: Assicurati che il file 'config_reader.py' sia nella stessa cartella.")
    st.stop()

# --- Configurazione e Inizializzazione ---

# Carica la configurazione usando il tuo reader
# Istanzia una volta sola per leggere il file
try:
    config = ConfigReader()
    DB_PATH = config.DB # Prendi il percorso dal config
    LIBRARY_PATH = config.LIBRARY # Potrebbe servire per percorsi relativi dei PDF
except Exception as e:
    st.error(f"Errore durante la lettura della configurazione: {e}")
    st.stop()

# Verifica che il percorso DB esista
if not DB_PATH or not os.path.exists(DB_PATH):
    st.error(f"Errore: Il percorso del database specificato in config.json non è valido o il file non esiste.")
    st.error(f"Percorso cercato: {DB_PATH}")
    st.stop()

# Inizializza TinyDB
try:
    db = TinyDB(DB_PATH, encoding='utf-8')
    Book = Query()
except Exception as e:
    st.error(f"Errore nell'aprire il database TinyDB a '{DB_PATH}': {e}")
    st.stop()

# Formato data per la visualizzazione (diverso da quello ISO nel DB)
DISPLAY_DATE_FORMAT = "%d-%m-%y %H:%M"

# --- Funzioni Helper ---

def parse_iso_date(date_str: str | None) -> datetime | None:
    """Converte stringa ISO in datetime, gestendo errori e timezone offset."""
    if not date_str:
        return None
    try:
        # Rimuove timezone offset se presente (semplificazione)
        if '+' in date_str:
            date_str = date_str.split('+')[0]
        elif 'Z' in date_str:
            date_str = date_str.replace('Z', '')

        # Gestisce formati comuni con o senza microsecondi
        if 'T' in date_str:
             clean_date_str = date_str.split('.')[0] # Rimuove microsecondi per strptime
             return datetime.fromisoformat(date_str.split('.')[0]) # Prova ISO senza microsecondi
             # Alternativa se fromisoformat fallisce:
             # return datetime.strptime(clean_date_str, '%Y-%m-%dT%H:%M:%S')
        else:
             # Prova a parsare senza 'T' se presente
             return datetime.fromisoformat(date_str)

    except ValueError:
        # Prova formati alternativi comuni se ISO fallisce
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
             try:
                  return datetime.strptime(date_str.split('.')[0], fmt) # Rimuove microsecondi anche qui
             except ValueError:
                  continue
        st.warning(f"Formato data non riconosciuto: {date_str}. Ignorata per ordinamento/visualizzazione.")
        return None
    except Exception as e:
        st.error(f"Errore inatteso nel parsing data '{date_str}': {e}")
        return None


@st.cache_data(ttl=60) # Cache per 1 minuto per evitare ricariche continue
def load_data_from_db() -> pd.DataFrame:
    """Legge tutti i dati da TinyDB e li converte in DataFrame Pandas."""
    try:
        all_books_raw = db.all()
        if not all_books_raw:
            return pd.DataFrame() # Ritorna DataFrame vuoto se DB vuoto

        # Aggiungi doc_id ad ogni record prima di creare il DataFrame
        for book in all_books_raw:
            book['doc_id'] = book.doc_id

        df = pd.DataFrame(all_books_raw)

        # --- Preparazione Colonne per Visualizzazione e Ordinamento ---
        # Converte 'added' in datetime per ordinamento, gestendo errori
        df['added_dt'] = df['added'].apply(parse_iso_date)
        # Formatta 'added' per la visualizzazione
        df['Added_Display'] = df['added_dt'].dt.strftime(DISPLAY_DATE_FORMAT).fillna('')

        # Formatta 'tags' come stringa
        df['Tags_Display'] = df['tags'].apply(lambda tags: ', '.join(tags) if isinstance(tags, list) else '')

        # Seleziona e rinomina colonne per chiarezza nella visualizzazione
        # Manteniamo doc_id, uuid e filename per operazioni future
        df_display = df[['doc_id', 'uuid', 'title', 'author', 'Tags_Display', 'Added_Display', 'added_dt', 'filename']].copy()
        df_display.rename(columns={
            'title': 'Title',
            'author': 'Author',
            'Tags_Display': 'Tags',
            'Added_Display': 'Added'
        }, inplace=True)

        return df_display

    except Exception as e:
        st.error(f"Errore durante il caricamento dei dati dal DB: {e}")
        return pd.DataFrame()


def open_file(filepath: str) -> None:
    """Tenta di aprire un file usando il visualizzatore predefinito."""
    if not filepath:
        st.warning("Nessun percorso file specificato per questo libro.")
        return
    
    # Gestione percorsi relativi/assoluti
    if not os.path.isabs(filepath) and LIBRARY_PATH:
         # Se il percorso non è assoluto e abbiamo un path libreria, lo uniamo
         abs_filepath = os.path.join(LIBRARY_PATH, filepath)
         st.info(f"Tentativo di apertura percorso relativo: {abs_filepath}")
    else:
         abs_filepath = filepath
         st.info(f"Tentativo di apertura percorso assoluto: {abs_filepath}")


    if not os.path.exists(abs_filepath):
        st.error(f"File non trovato: {abs_filepath}")
        return

    try:
        if sys.platform == "win32":
            os.startfile(abs_filepath)
        elif sys.platform == "darwin":
            subprocess.call(["open", abs_filepath])
        else: # linux variants
            subprocess.call(["xdg-open", abs_filepath])
        st.success(f"Tentativo di apertura di '{os.path.basename(abs_filepath)}' inviato al sistema.")
    except FileNotFoundError:
         st.error(f"Errore: File non trovato o percorso non valido.\n{abs_filepath}")
    except Exception as e:
        st.error(f"Errore nell'aprire il file: {e}")

# --- Interfaccia Streamlit ---

st.set_page_config(layout="wide") # Usa layout largo
st.title("📚 Gestore Libreria PDF (TinyDB)")

# Carica i dati (usando la cache)
data_df = load_data_from_db()

if data_df.empty:
    st.warning("Il database è vuoto o non è stato possibile caricarlo.")
    st.stop()

# --- Filtri / Ricerca ---
st.sidebar.header("🔍 Filtri")
search_title = st.sidebar.text_input("Cerca per Titolo")
search_author = st.sidebar.text_input("Cerca per Autore")
search_tags = st.sidebar.text_input("Cerca per Tags (separati da virgola)")

filtered_df = data_df.copy() # Inizia con tutti i dati

if search_title:
    filtered_df = filtered_df[filtered_df['Title'].str.contains(search_title, case=False, na=False)]
if search_author:
    filtered_df = filtered_df[filtered_df['Author'].str.contains(search_author, case=False, na=False)]
if search_tags:
    # Cerca tutti i tag inseriti (AND)
    tags_to_search = [tag.strip().lower() for tag in search_tags.split(',') if tag.strip()]
    if tags_to_search:
        # La colonna 'Tags' è una stringa CSV, la colonna originale 'tags' in data_df era una lista
        # Ricostruiamo la ricerca sulla lista originale per correttezza
        original_tags_series = data_df.loc[filtered_df.index]['tags'] # Prendi i tag originali per gli indici filtrati

        # Funzione per controllare se tutti i tag cercati sono presenti
        def check_tags(tag_list):
            if not isinstance(tag_list, list): return False
            tag_list_lower = [t.lower() for t in tag_list]
            return all(search_tag in tag_list_lower for search_tag in tags_to_search)

        mask = original_tags_series.apply(check_tags)
        filtered_df = filtered_df[mask]


# --- Ordinamento ---
st.sidebar.header("📊 Ordinamento")
sort_column = st.sidebar.selectbox(
    "Ordina per:",
    options=['Added', 'Title', 'Author'], # Colonne visualizzate
    index=0 # Default su 'Added'
)
sort_ascending = st.sidebar.checkbox("Ordine Ascendente", False) # Default decrescente

# Mappa nome colonna display a colonna dati reale per ordinamento
sort_key_map = {
    'Added': 'added_dt', # Ordina sulla data effettiva
    'Title': 'Title',
    'Author': 'Author'
}
sort_by_column = sort_key_map.get(sort_column, 'added_dt')

# Esegui l'ordinamento sul DataFrame filtrato
# Gestisci NaT (Not a Time) mettendoli in fondo se ascendente, in cima se discendente
na_pos = 'last' if not sort_ascending else 'first'
sorted_df = filtered_df.sort_values(by=sort_by_column, ascending=sort_ascending, na_position=na_pos)


# --- Visualizzazione Tabella ---
st.header("Elenco Libri")

# Colonne da mostrare effettivamente nella tabella
display_columns = ['Title', 'Author', 'Tags', 'Added']

# Usa st.data_editor per rendere la tabella modificabile e selezionabile
# Nota: la modifica diretta qui è complessa da sincronizzare con TinyDB
# Useremo la selezione per triggerare azioni esterne (Cancella, Apri)

# Stiamo usando st.dataframe per ora, che non ha selezione nativa
# Per selezione/azioni, st.data_editor sarebbe meglio, ma complicherebbe l'editing iniziale
# SOLUZIONE INTERMEDIA: Mostriamo un bottone "Cancella" per ogni riga

final_df_to_display = sorted_df[display_columns + ['doc_id', 'filename']].reset_index(drop=True)

# Mostriamo i bottoni in colonne separate per pulizia
col1, col2, col3, col4, col5, col6 = st.columns([4, 3, 3, 2, 1, 1]) # Adatta le proporzioni

with col1: st.subheader("Titolo")
with col2: st.subheader("Autore")
with col3: st.subheader("Tags")
with col4: st.subheader("Aggiunto")
with col5: st.subheader("Azioni")
with col6: st.subheader("Apri")


st.markdown("---") # Separatore

if final_df_to_display.empty:
    st.info("Nessun libro trovato con i filtri applicati.")
else:
    # Itera sulle righe del DataFrame per creare la visualizzazione con bottoni
    for index, row in final_df_to_display.iterrows():
        doc_id = row['doc_id']
        filename = row['filename']

        col1b, col2b, col3b, col4b, col5b, col6b = st.columns([4, 3, 3, 2, 1, 1])

        with col1b: st.write(row['Title'])
        with col2b: st.write(row['Author'])
        with col3b: st.caption(row['Tags']) # Usiamo caption per testo più piccolo
        with col4b: st.write(row['Added'])

        with col5b:
            # Crea un bottone unico per ogni riga usando l'indice o doc_id come parte della chiave
            delete_key = f"delete_{doc_id}_{index}"
            if st.button("🗑️", key=delete_key, help=f"Cancella '{row['Title']}'"):
                try:
                    db.remove(doc_ids=[doc_id])
                    st.success(f"Libro '{row['Title']}' cancellato con successo!")
                    # Forza il rerun per aggiornare la tabella (semplice ma efficace)
                    # In alternativa potremmo rimuovere la riga dal dataframe in session state
                    st.cache_data.clear() # Pulisce la cache per forzare il reload dal DB
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante la cancellazione del libro ID {doc_id}: {e}")

        with col6b:
            open_key = f"open_{doc_id}_{index}"
            # Disabilita se non c'è filename
            disabled = not bool(filename)
            if st.button("↗️", key=open_key, help=f"Apri PDF" if not disabled else "Nessun file", disabled=disabled):
                 open_file(filename)


st.markdown("---")

# --- Pulsante per ricaricare manualmente i dati ---
if st.sidebar.button("🔄 Ricarica Dati dal DB"):
    st.cache_data.clear()
    st.rerun()

# Aggiungeremo Modifica e Aggiunta in un secondo momento, magari usando st.form e st.expander
st.sidebar.header("📝 Azioni (Prossimamente)")
st.sidebar.button("➕ Aggiungi Nuovo Libro", disabled=True)
# La modifica potrebbe essere attivata da un bottone che appare qui dopo la selezione (se usassimo st.data_editor)

# Chiudi il DB alla fine? Non strettamente necessario con TinyDB se l'app termina,
# ma buona pratica se l'app dovesse rimanere attiva a lungo o fare molte scritture.
# In Streamlit è complesso gestire la chiusura pulita, TinyDB di solito gestisce bene.
# db.close()