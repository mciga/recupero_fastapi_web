"""Route CRUD generiche, parametrizzate sul nome della tabella. Un unico
router serve tutte le tabelle grazie alla configurazione in crud.TABLES."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError
import crud
from schemas import (Impianto, Prodotto, ProdottoStorico, Materiale, Macro, Scarto, Processo,
                     IndiceRivalutazione, Intermedio, Sottoprocesso, Reagente)

router = APIRouter(prefix="/api", tags=["crud"])

MODELS: dict[str, type[BaseModel]] = {
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

URL_NAMES = {
    "db_reagenti": "reagenti",
    "db_impianti": "impianti",
    "db_prodotti": "prodotti",
    "db_prodotti_storico": "prodotti-storico",
    "db_materiali": "materiali",
    "db_scarti": "scarti",
    "db_macro": "macro",
    "db_processi": "processi",
    "db_indici_rivalutazione": "indici-rivalutazione",
    "db_intermedi": "intermedi",
    "db_sottoprocessi": "sottoprocessi",
}


def _pk_from_path(table: str, pk1: str, pk2: str | None) -> list[str]:
    pk_cols = crud.TABLES[table]["pk"]
    values = [pk1] if pk2 is None else [pk1, pk2]
    if len(values) != len(pk_cols):
        raise HTTPException(400, f"Chiave primaria attesa: {pk_cols}")
    return values


def _validate(model, body):
    try:
        return model(**body)
    except ValidationError as e:
        msgs = []
        for er in e.errors():
            loc = ".".join(map(str, er["loc"]))
            msgs.append(f"{loc}: {er['msg']}" if loc else er["msg"].replace("Value error, ", ""))
        raise HTTPException(422, "; ".join(msgs))


def register_table_routes(table: str):
    model = MODELS[table]
    url = URL_NAMES[table]
    composite = len(crud.TABLES[table]["pk"]) == 2
    path_single = f"/{url}/{{pk1}}" if not composite else f"/{url}/{{pk1}}/{{pk2}}"

    @router.get(f"/{url}", name=f"list_{table}")
    def list_(table=table):
        return crud.list_rows(table)

    @router.post(f"/{url}", status_code=201, name=f"create_{table}")
    def create_(body: dict, table=table, model=model):
        validated = _validate(model, body)
        try:
            data = validated.model_dump()
            if table in ("db_processi", "db_sottoprocessi"):
                data = crud.normalizza_scarto(data)
            return crud.create_row(table, data)
        except Exception as e:
            raise HTTPException(400, str(e))

    @router.put(path_single, name=f"update_{table}")
    def update_(pk1: str, body: dict, pk2: str | None = None, table=table, model=model, composite=composite):
        validated = _validate(model, body)
        pk_values = _pk_from_path(table, pk1, pk2 if composite else None)
        existing = crud.get_row(table, pk_values)
        if not existing:
            raise HTTPException(404, "Record non trovato")
        try:
            data = validated.model_dump()
            if table in ("db_processi", "db_sottoprocessi"):
                data = crud.normalizza_scarto(data)
            return crud.update_row(table, pk_values, data)
        except Exception as e:
            raise HTTPException(400, str(e))

    @router.delete(path_single, status_code=204, name=f"delete_{table}")
    def delete_(pk1: str, pk2: str | None = None, table=table, composite=composite):
        pk_values = _pk_from_path(table, pk1, pk2 if composite else None)
        existing = crud.get_row(table, pk_values)
        if not existing:
            raise HTTPException(404, "Record non trovato")
        try:
            crud.delete_row(table, pk_values)
        except Exception as e:
            # tipicamente una violazione di chiave esterna (record ancora referenziato)
            raise HTTPException(409, f"Impossibile eliminare: {e}")


for _table in MODELS:
    register_table_routes(_table)
