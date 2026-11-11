"""Export/import Excel per le tabelle. Un foglio per tabella, stesso nome
delle chiavi usate nelle route REST (routers/tables.py URL_NAMES) cosi' il
frontend puo' riusare la stessa mappatura.

Export: legge da Postgres con crud.list_rows, scrive un .xlsx con openpyxl.
Import: legge un .xlsx, valida ogni riga con i modelli Pydantic di schemas.py,
poi fa un upsert (crea se la chiave non esiste, aggiorna se esiste) tabella
per tabella, in un ordine che rispetta le chiavi esterne (db_prodotti e
db_intermedi prima di chi le referenzia).
"""
import io
import re
from datetime import datetime
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

import crud
from schemas import (Impianto, Prodotto, ProdottoStorico, Materiale, Macro, Scarto, Processo,
                     IndiceRivalutazione, Intermedio, Sottoprocesso, Reagente)

SHEET_NAMES = {
    "db_reagenti": "reagenti",
    "db_impianti": "impianti",
    "db_prodotti": "prodotti",
    "db_prodotti_storico": "prodotti_storico",
    "db_materiali": "materiali",
    "db_scarti": "scarti",
    "db_macro": "macro",
    "db_processi": "processi",
    "db_indici_rivalutazione": "indici_rivalutazione",
    "db_intermedi": "intermedi",
    "db_sottoprocessi": "sottoprocessi",
}
TABLE_BY_SHEET = {v: k for k, v in SHEET_NAMES.items()}

MODELS = {
    "db_impianti": Impianto,
    "db_prodotti": Prodotto,
    "db_prodotti_storico": ProdottoStorico,
    "db_materiali": Materiale,
    "db_scarti": Scarto,
    "db_macro": Macro,
    "db_processi": Processo,
    "db_indici_rivalutazione": IndiceRivalutazione,
    "db_intermedi": Intermedio,
    "db_sottoprocessi": Sottoprocesso,
    "db_reagenti": Reagente,
}

# rispetta le FK: le tabelle referenziate prima di chi le referenzia
IMPORT_ORDER = ["db_prodotti", "db_prodotti_storico", "db_intermedi", "db_scarti", "db_reagenti", "db_impianti",
                "db_indici_rivalutazione", "db_materiali", "db_macro", "db_processi", "db_sottoprocessi"]

PERCENT_COLUMNS = {
    "proiezione_prezzo_p1", "proiezione_prezzo_p2",
    "recupero_pct_min", "recupero_pct", "recupero_pct_max",
    "tasso_annuo",
}

HEADER_FILL = PatternFill("solid", fgColor="1F5A43")
HEADER_FONT = Font(bold=True, color="FFFFFF")

# testo UTF-8 riletto come Windows-1252 (es. passando da un CSV o da psql su Windows):
# "impurità" diventa "impuritÃ ", "Li₃PO₄" diventa "Liâ‚ƒPOâ‚„"
_CORROTTO = re.compile(r"Ã.|Â.|â€|â‚")


def ripara_testo(v):
    """Ripara le lettere accentate e i pedici corrotti; lascia invariato il resto.
    Ripete la conversione (al massimo 3 volte) per i testi corrotti piu' volte."""
    if not isinstance(v, str) or not _CORROTTO.search(v):
        return v
    # "à" corrotta diventa "Ã" + spazio speciale; copiando il testo lo spazio speciale diventa normale
    s = re.sub(r"Ã[ \xa0]", "à", v)
    for _ in range(3):
        if not _CORROTTO.search(s):
            break
        try:
            s2 = s.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            try:   # caratteri non mappati in cp1252 (es. \xa0 di "impuritÃ ")
                s2 = s.encode("latin-1").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                break
        if s2 == s:
            break
        s = s2
    return s


def export_workbook(tables: list[str] | None = None) -> bytes:
    tables = tables or list(SHEET_NAMES.keys())
    wb = Workbook()
    wb.remove(wb.active)
    for table in tables:
        cfg = crud.TABLES[table]
        ws = wb.create_sheet(SHEET_NAMES[table])
        cols = cfg["columns"]
        ws.append(cols)
        for c in range(1, len(cols) + 1):
            cell = ws.cell(row=1, column=c)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
        rows = crud.list_rows(table)
        for row in rows:
            # nel database "impurita" e' senza accento; nel file Excel lo scriviamo come "impurità"
            # (l'import accetta entrambe le forme). I testi sono riparati se corrotti.
            ws.append([("impurità" if (c == "tipo_output" and row[c] == "impurita") else ripara_testo(row[c]))
                       for c in cols])
        for c_idx, col in enumerate(cols, start=1):
            if col in PERCENT_COLUMNS:
                for r_idx in range(2, len(rows) + 2):
                    ws.cell(row=r_idx, column=c_idx).number_format = "0.00%"
            width = max(12, min(40, len(col) + 4))
            ws.column_dimensions[ws.cell(row=1, column=c_idx).column_letter].width = width
        ws.freeze_panes = "A2"

    wb.properties.creator = "MACTEE"
    wb.properties.title = "MACTEE - export database"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _row_from_sheet(ws, header: list[str], riparati: list) -> list[dict]:
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        rec = {}
        for h, v in zip(header, row):
            r = ripara_testo(v)
            if r != v:
                riparati.append(v)
            rec[h] = r
        records.append(rec)
    return records


def import_workbook(file_bytes: bytes, dry_run: bool = False, replace: bool = False) -> dict:
    """replace=True: cancella TUTTE le righe di TUTTE le tabelle prima di
    importare (usato solo se dry_run=False: in anteprima non si cancella
    mai nulla, si simula soltanto cosa accadrebbe)."""
    wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    report = {}

    sheets_by_table = {}
    riparati = []
    for sheet_name in wb.sheetnames:
        table = TABLE_BY_SHEET.get(sheet_name)
        if table:
            ws = wb[sheet_name]
            header = [ripara_testo(c.value) for c in ws[1]]
            sheets_by_table[table] = _row_from_sheet(ws, header, riparati)
        else:
            report.setdefault("_fogli_ignorati", []).append(sheet_name)
    if riparati:
        report["_testi_riparati"] = {"celle": len(riparati),
                                     "esempi": sorted({str(v)[:60] for v in riparati})[:5]}

    if "db_reagenti" in sheets_by_table:
        # i reagenti usati come reagente_sale (es. H2SO4) vanno creati prima di chi li cita
        sheets_by_table["db_reagenti"].sort(key=lambda r: bool(r.get("reagente_sale")))

    if replace and not dry_run:
        report["_cancellati"] = crud.wipe_all_tables()

    for table in IMPORT_ORDER:
        if table not in sheets_by_table:
            continue
        cfg = crud.TABLES[table]
        model = MODELS[table]
        created = updated = 0
        errors = []
        for i, raw in enumerate(sheets_by_table[table], start=2):
            try:
                raw = {crud.ALIAS_COLONNE.get(k, k) if crud.ALIAS_COLONNE.get(k, k) not in raw else k: v
                       for k, v in raw.items()}
                clean = {k: v for k, v in raw.items() if k in cfg["columns"]}
                validated = model(**clean)
                data = validated.model_dump()
                if table in ("db_processi", "db_sottoprocessi") and not dry_run:
                    data = crud.normalizza_scarto(data)
                # chiave auto-generata (es. "id" seriale) lasciata vuota nel
                # foglio: nessuna riga esistente da cercare, si crea sempre.
                # In modalita' "sostituisci tutto" ogni riga e' comunque una
                # creazione (la cancellazione avviene prima, o e' simulata
                # in anteprima): non ha senso cercare righe esistenti.
                if replace or any(data.get(k) is None for k in cfg["pk"]):
                    existing = None
                else:
                    pk_values = [str(data[k]) for k in cfg["pk"]]
                    existing = crud.get_row(table, pk_values)
                if dry_run:
                    if existing:
                        updated += 1
                    else:
                        created += 1
                    continue
                if existing:
                    crud.update_row(table, pk_values, data)
                    updated += 1
                else:
                    crud.create_row(table, data)
                    created += 1
            except Exception as e:  # noqa: BLE001
                errors.append(f"riga {i}: {e}")
        report[table] = {"creati": created, "aggiornati": updated, "errori": errors,
                          "totale_foglio": len(sheets_by_table[table])}

    if not dry_run:
        _riallinea_sequenze()
    return report


def _riallinea_sequenze():
    """Dopo un import con id espliciti (colonna "id" seriale compilata), le
    sequenze Postgres vanno riallineate al massimo id presente, altrimenti
    il prossimo inserimento senza id collide con una riga esistente."""
    from sqlalchemy import text
    from db import ENGINE, SCHEMA
    with ENGINE.begin() as conn:
        for table, cfg in crud.TABLES.items():
            if cfg["pk"] == ["id"]:
                conn.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{SCHEMA}.{table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {SCHEMA}.{table}), 0) + 1, false)"))


def export_filename() -> str:
    return f"MACTEE_export_{datetime.now():%Y%m%d_%H%M}.xlsx"
