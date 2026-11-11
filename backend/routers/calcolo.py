import io
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import calc
import report_bilancio

router = APIRouter(prefix="/api", tags=["calcolo"])

ANNO_CORRENTE = 2026


class FiglioScelta(BaseModel):
    """Scelta dell'utente per un intermedio generato da un processo/
    sottoprocesso: se lavorarlo oltre (id_sottoprocesso) e con quali
    ulteriori scelte a valle (figli, ricorsivo)."""
    id_sottoprocesso: str | None = None
    figli: dict[str, "FiglioScelta"] | None = None


FiglioScelta.model_rebuild()


class ComponenteInput(BaseModel):
    macro_componente: str
    id_processo: str
    assieme: str | None = None                 # valorizzato = corsia separata con solo quell'assieme
    escludi_assiemi: list[str] | None = None   # assiemi separati in altre corsie
    prezzi_prodotti_override: dict[str, float] | None = None
    prezzi_intermedi_override: dict[str, float] | None = None
    figli_processo: dict[str, FiglioScelta] | None = None
    taglia_t_anno: float | None = None         # taglia dell'impianto (t/anno); vuota = tratta la massa in 1 anno
    anno_costruzione: int | None = None        # anno a cui si rivaluta il capex dell'impianto; vuoto = anno corrente


class CalcoloImpiantoInput(BaseModel):
    """Uno o piu' impianti della stessa tipologia (id_imps; id_imp per compatibilita'):
    le masse dei materiali sono sommate sugli impianti e il processo e' applicato al totale."""
    id_imp: str | None = None
    id_imps: list[str] | None = None
    anno_dismissione: int | None = None  # None = ogni impianto con il proprio anno (db_impianti)
    anno_corrente: int = ANNO_CORRENTE
    id_indice_costi: str = "ISTAT"
    componenti: list[ComponenteInput]

    def impianti(self) -> list[str]:
        return list(self.id_imps or []) + ([self.id_imp] if self.id_imp else [])


class CalcoloIntermedioInput(BaseModel):
    """Punto di partenza alternativo: si acquista un quantitativo di
    intermedio gia' separato e lo si tratta con un sottoprocesso."""
    intermedio: str
    massa_ton: float
    id_sottoprocesso: str
    anno_dismissione: int
    anno_corrente: int = ANNO_CORRENTE
    id_indice_costi: str = "ISTAT"
    prezzo_acquisto_override: float | None = None
    prezzi_prodotti_override: dict[str, float] | None = None
    prezzi_intermedi_override: dict[str, float] | None = None
    figli_sottoprocesso: dict[str, FiglioScelta] | None = None
    taglia_t_anno: float | None = None


@router.get("/filtri/tipologie")
def r_tipologie():
    return calc.tipologie()


@router.get("/filtri/impianti")
def r_impianti(tipologia: str | None = None):
    return calc.impianti_lista(tipologia)


def _imp_param(id_imp: str | None, id_imps: str | None) -> list[str]:
    ids = calc._ids(id_imps) + calc._ids(id_imp)
    if not ids:
        raise HTTPException(400, "indicare id_imps (elenco separato da virgole) o id_imp")
    return ids


@router.get("/filtri/macrocomponenti")
def r_macro(id_imp: str | None = None, id_imps: str | None = None):
    """Macrocomponenti di uno o piu' impianti (id_imps separati da virgola) con almeno un
    materiale con massa e almeno un processo che tratti uno di quei materiali; masse
    sommate sugli impianti."""
    return calc.macro_componenti(_imp_param(id_imp, id_imps))


@router.get("/filtri/processi")
def r_processi(tipologia: str, macro_componente: str, id_imp: str | None = None, id_imps: str | None = None):
    ids = calc._ids(id_imps) + calc._ids(id_imp)
    return calc.processi_disponibili(tipologia, macro_componente, ids or None)


class MaterialiComponenteInput(BaseModel):
    id_imp: str | None = None
    id_imps: list[str] | None = None
    macro_componente: str
    assieme: str | None = None
    escludi_assiemi: list[str] | None = None


@router.get("/filtri/materiali-componente")
def r_materiali_componente(macro_componente: str, id_imp: str | None = None, id_imps: str | None = None,
                           assieme: str | None = None):
    return calc.materiali_componente_dettaglio(_imp_param(id_imp, id_imps), macro_componente, assieme)


@router.post("/filtri/materiali-componente")
def r_materiali_componente_post(body: MaterialiComponenteInput):
    ids = list(body.id_imps or []) + ([body.id_imp] if body.id_imp else [])
    if not ids:
        raise HTTPException(400, "indicare id_imps o id_imp")
    return calc.materiali_componente_dettaglio(ids, body.macro_componente, body.assieme, body.escludi_assiemi)


@router.get("/filtri/sottoprocessi")
def r_sottoprocessi(intermedio: str):
    return calc.sottoprocessi_disponibili(intermedio)


@router.get("/filtri/prodotti")
def r_prodotti():
    return calc.prodotti_lista()


@router.get("/filtri/intermedi")
def r_intermedi():
    return calc.intermedi_lista()


@router.get("/filtri/indici-rivalutazione")
def r_indici():
    return calc.indici_rivalutazione()


@router.get("/storico-prodotto/{prodotto}")
def r_storico(prodotto: str):
    return calc.storico_prodotto(prodotto)


@router.post("/calcolo-impianto/export")
def r_calcolo_impianto_export(body: CalcoloImpiantoInput):
    """Stesso calcolo di /calcolo-impianto, restituito come report Excel del bilancio di massa
    (da dove arriva ogni quantita' e come e' valorizzata)."""
    result = r_calcolo_impianto(body)
    content = report_bilancio.workbook(result, body.model_dump())
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{report_bilancio.filename()}"'},
    )


@router.post("/calcolo-impianto")
def r_calcolo_impianto(body: CalcoloImpiantoInput):
    if not body.componenti:
        raise HTTPException(400, "Nessun macrocomponente fornito")
    if not body.impianti():
        raise HTTPException(400, "Nessun impianto fornito (id_imps)")
    try:
        result = calc.calcola_gruppo(body.impianti(), [c.model_dump() for c in body.componenti],
                                     body.anno_dismissione, body.anno_corrente, body.id_indice_costi)
    except ValueError as e:
        raise HTTPException(404, str(e))
    if "error" in result:
        raise HTTPException(404, result["error"])
    errors = [c for c in result["componenti"] if "error" in c]
    if errors:
        raise HTTPException(404, "; ".join(f"{e['macro_componente']}: {e['error']}" for e in errors))
    return result


@router.post("/calcolo-da-intermedio")
def r_calcolo_da_intermedio(body: CalcoloIntermedioInput):
    if body.massa_ton <= 0:
        raise HTTPException(400, "massa_ton deve essere positiva")
    d = body.model_dump()
    try:
        result = calc.calcola_da_intermedio(
            d["intermedio"], d["massa_ton"], d["id_sottoprocesso"], d["anno_dismissione"], d["anno_corrente"],
            d["id_indice_costi"], d["prezzo_acquisto_override"], d["prezzi_prodotti_override"],
            d["prezzi_intermedi_override"], d["figli_sottoprocesso"], d["taglia_t_anno"])
    except ValueError as e:
        raise HTTPException(404, str(e))
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result
