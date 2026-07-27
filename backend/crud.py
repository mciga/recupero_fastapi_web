"""CRUD generico per le 8 tabelle, basato sulla configurazione TABLES.
Ogni tabella ha una chiave primaria (singola o composita) usata per
identificare la riga da aggiornare/cancellare nelle route REST."""
from typing import Any
from sqlalchemy import text
from db import ENGINE, SCHEMA

TABLES: dict[str, dict[str, Any]] = {
    "db_impianti": {
        "pk": ["id_imp"],
        "columns": ["id_imp", "tipologia", "sotto_tecnologia", "potenza_mw",
                    "anno_installazione", "anno_dismissione", "regione", "provincia", "lat", "lon"],
    },
    "db_prodotti": {
        "pk": ["prodotto"],
        "columns": ["prodotto", "nome", "categoria", "peso_molare", "elemento_confronto", "parametro_equivalenza",
                    "prezzo_attuale_eur_kg", "proiezione_prezzo_p1", "proiezione_prezzo_p2"],
    },
    "db_macro": {
        "pk": ["id_macro", "prodotto"],
        "columns": ["id_macro", "tipologia", "sotto_tecnologia", "macro_componente", "massa_kg_per_mw",
                    "prodotto", "pct_contenuto_min", "pct_contenuto_max"],
    },
    "db_intermedi_composizione": {
        "pk": ["intermedio", "prodotto"],
        "columns": ["intermedio", "prodotto", "pct_contenuto_min", "pct_contenuto_max"],
    },
    "db_macro_processi": {
        "pk": ["id_processo_macro"],
        "columns": ["id_processo_macro", "tipologia", "sotto_tecnologia", "macro_componente",
                    "tecnica", "capex_eur_ton", "opex_eur_ton",
                    "prezzo_vendita_eur_kg", "proiezione_prezzo_p1", "proiezione_prezzo_p2",
                    "descrizione_fasi"],
    },
    "db_processi": {
        "pk": ["id"],
        "columns": ["id", "id_processo", "tipologia", "sotto_tecnologia", "macro_componente", "tecnica",
                    "capex_eur_ton", "opex_eur_ton", "tipo_output", "prodotto", "intermedio_output",
                    "recupero_pct_min", "recupero_pct_max", "descrizione_fasi"],
    },
    "db_indici_rivalutazione": {
        "pk": ["id_indice"],
        "columns": ["id_indice", "nome", "tasso_annuo"],
    },
    "db_intermedi": {
        "pk": ["intermedio"],
        "columns": ["intermedio", "nome", "prezzo_attuale_eur_kg",
                    "proiezione_prezzo_p1", "proiezione_prezzo_p2"],
    },
    "db_sottoprocessi": {
        "pk": ["id"],
        "columns": ["id", "id_sottoprocesso", "intermedio", "tecnica", "capex_eur_ton", "opex_eur_ton",
                    "tipo_output", "prodotto", "intermedio_output",
                    "recupero_pct_min", "recupero_pct_max", "descrizione_fasi"],
    },
}


def list_rows(table: str, order_by: str | None = None) -> list[dict]:
    cfg = TABLES[table]
    order = order_by or cfg["pk"][0]
    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        rows = conn.execute(text(f"SELECT {','.join(cfg['columns'])} FROM {SCHEMA}.{table} ORDER BY {order}"))
        return [dict(r._mapping) for r in rows]


def get_row(table: str, pk_values: list[str]) -> dict | None:
    cfg = TABLES[table]
    where = " AND ".join(f"{c} = :{c}" for c in cfg["pk"])
    params = dict(zip(cfg["pk"], pk_values))
    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        row = conn.execute(text(f"SELECT {','.join(cfg['columns'])} FROM {SCHEMA}.{table} WHERE {where}"), params).first()
        return dict(row._mapping) if row else None


def create_row(table: str, data: dict) -> dict:
    cfg = TABLES[table]
    # scarta colonne None (es. chiave seriale non fornita: la genera il DB;
    # oppure prodotto/intermedio_output quando l'altro e' valorizzato)
    cols = [c for c in cfg["columns"] if data.get(c) is not None]
    collist = ",".join(cols)
    vallist = ",".join(f":{c}" for c in cols)
    pk_cols = cfg["pk"]
    with ENGINE.begin() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        result = conn.execute(
            text(f"INSERT INTO {SCHEMA}.{table} ({collist}) VALUES ({vallist}) RETURNING {','.join(pk_cols)}"),
            data)
        pk_values = list(result.first())
    return get_row(table, pk_values)


def update_row(table: str, pk_values: list[str], data: dict) -> dict | None:
    cfg = TABLES[table]
    set_cols = [c for c in cfg["columns"] if c not in cfg["pk"]]
    setlist = ",".join(f"{c}=:{c}" for c in set_cols)
    where = " AND ".join(f"{c}=:pk_{c}" for c in cfg["pk"])
    params = {**{c: data[c] for c in set_cols}, **{f"pk_{c}": v for c, v in zip(cfg["pk"], pk_values)}}
    with ENGINE.begin() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        conn.execute(text(f"UPDATE {SCHEMA}.{table} SET {setlist} WHERE {where}"), params)
    new_pk = [data[c] if data.get(c) is not None else v for c, v in zip(cfg["pk"], pk_values)]
    return get_row(table, new_pk)


def delete_row(table: str, pk_values: list[str]) -> None:
    cfg = TABLES[table]
    where = " AND ".join(f"{c} = :{c}" for c in cfg["pk"])
    params = dict(zip(cfg["pk"], pk_values))
    with ENGINE.begin() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        conn.execute(text(f"DELETE FROM {SCHEMA}.{table} WHERE {where}"), params)


# ordine di cancellazione sicuro per le chiavi esterne: le tabelle che
# referenziano le altre vengono svuotate per prime (l'esatto contrario
# dell'ordine di import, che invece crea prima le tabelle referenziate)
WIPE_ORDER = ["db_sottoprocessi", "db_processi", "db_macro", "db_intermedi_composizione", "db_macro_processi",
              "db_indici_rivalutazione", "db_impianti", "db_intermedi", "db_prodotti"]


def wipe_all_tables() -> dict[str, int]:
    """Cancella TUTTE le righe di TUTTE le tabelle (non le tabelle stesse:
    lo schema resta intatto). Operazione distruttiva e irreversibile."""
    counts: dict[str, int] = {}
    with ENGINE.begin() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        for table in WIPE_ORDER:
            result = conn.execute(text(f"DELETE FROM {SCHEMA}.{table}"))
            counts[table] = result.rowcount
    return counts
