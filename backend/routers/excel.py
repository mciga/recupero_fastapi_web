from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from fastapi.responses import StreamingResponse
import io
import excel_io
import crud

router = APIRouter(prefix="/api", tags=["excel"])


@router.get("/export/excel")
def export_excel(tables: str | None = Query(None, description="Elenco tabelle separate da virgola, es. 'db_prodotti,db_macro'. Vuoto = tutte.")):
    table_list = None
    if tables:
        table_list = [t.strip() for t in tables.split(",") if t.strip()]
        invalid = [t for t in table_list if t not in crud.TABLES]
        if invalid:
            raise HTTPException(400, f"Tabelle non valide: {invalid}")
    content = excel_io.export_workbook(table_list)
    filename = excel_io.export_filename()
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import/excel")
async def import_excel(
    file: UploadFile = File(...),
    dry_run: bool = Query(False),
    replace: bool = Query(False, description="True = cancella tutte le righe di tutte le tabelle prima di importare (ignorato se dry_run=True: l'anteprima non cancella mai nulla)"),
):
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(400, "Carica un file .xlsx")
    content = await file.read()
    try:
        report = excel_io.import_workbook(content, dry_run=dry_run, replace=replace)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"File non leggibile come Excel valido: {e}")
    return {"dry_run": dry_run, "replace": replace, "report": report}


@router.post("/database/wipe")
def wipe_database(confirm: bool = Query(False, description="Deve essere true: conferma esplicita di un'operazione distruttiva e irreversibile")):
    if not confirm:
        raise HTTPException(400, "Operazione distruttiva: ripeti la richiesta con confirm=true")
    counts = crud.wipe_all_tables()
    return {"cancellati": counts, "totale": sum(counts.values())}
