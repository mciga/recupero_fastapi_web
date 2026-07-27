from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import calc

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
    id_processo_macro: str
    id_processo: str | None = None  # None = macrocomponente non trattato (vendita as-is)
    prezzo_macro_override: float | None = None
    prezzi_prodotti_override: dict[str, float] | None = None
    prezzi_intermedi_override: dict[str, float] | None = None
    figli_processo: dict[str, FiglioScelta] | None = None


class CalcoloImpiantoInput(BaseModel):
    tipologia: str
    sotto_tecnologia: str
    potenza_mw: float
    anno_dismissione: int
    anno_corrente: int = ANNO_CORRENTE
    id_indice_costi: str = "ISTAT"
    componenti: list[ComponenteInput]


class CalcoloMacroComponenteInput(BaseModel):
    """Punto di partenza alternativo: si acquista un quantitativo di
    macrocomponente gia' separato (niente impianto/macroprocesso) e lo si
    tratta con un processo, esattamente come nel resto dell'app."""
    tipologia: str
    sotto_tecnologia: str
    macro_componente: str
    massa_ton: float
    id_processo: str
    anno_dismissione: int
    anno_corrente: int = ANNO_CORRENTE
    id_indice_costi: str = "ISTAT"
    prezzo_acquisto_override: float | None = None
    prezzi_prodotti_override: dict[str, float] | None = None
    prezzi_intermedi_override: dict[str, float] | None = None
    figli_processo: dict[str, FiglioScelta] | None = None


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


@router.get("/filtri/tipologie")
def r_tipologie():
    return calc.tipologie()


@router.get("/filtri/sotto-tecnologie")
def r_sotto(tipologia: str):
    return calc.sotto_tecnologie(tipologia)


@router.get("/filtri/macrocomponenti")
def r_macro(tipologia: str, sotto_tecnologia: str):
    return calc.macro_componenti(tipologia, sotto_tecnologia)


@router.get("/filtri/macro-processi")
def r_macro_processi(tipologia: str, sotto_tecnologia: str, macro_componente: str):
    return calc.macro_processi_disponibili(tipologia, sotto_tecnologia, macro_componente)


@router.get("/filtri/processi")
def r_processi(tipologia: str, sotto_tecnologia: str, macro_componente: str):
    return calc.processi_disponibili(tipologia, sotto_tecnologia, macro_componente)


@router.get("/filtri/sottoprocessi")
def r_sottoprocessi(intermedio: str):
    return calc.sottoprocessi_disponibili(intermedio)


@router.get("/filtri/prodotti")
def r_prodotti():
    return calc.prodotti_lista()


@router.get("/filtri/intermedi")
def r_intermedi():
    return calc.intermedi_lista()


@router.get("/filtri/impianti")
def r_impianti():
    return calc.impianti_lista()


@router.get("/filtri/indici-rivalutazione")
def r_indici():
    return calc.indici_rivalutazione()


@router.post("/calcolo-impianto")
def r_calcolo_impianto(body: CalcoloImpiantoInput):
    if body.potenza_mw <= 0:
        raise HTTPException(400, "potenza_mw deve essere positiva")
    if not body.componenti:
        raise HTTPException(400, "Nessun macrocomponente fornito")
    result = calc.calcola_impianto(
        body.tipologia, body.sotto_tecnologia,
        [c.model_dump() for c in body.componenti],
        body.potenza_mw, body.anno_dismissione, body.anno_corrente,
        body.id_indice_costi,
    )
    errors = [c for c in result["componenti"] if "error" in c]
    if errors:
        raise HTTPException(404, f"Errore su {len(errors)} macrocomponente/i: {[e['macro_componente'] for e in errors]}")
    return result


@router.post("/calcolo-da-macrocomponente")
def r_calcolo_da_macro(body: CalcoloMacroComponenteInput):
    if body.massa_ton <= 0:
        raise HTTPException(400, "massa_ton deve essere positiva")
    data = body.model_dump()
    result = calc.calcola_da_macrocomponente(
        data["tipologia"], data["sotto_tecnologia"], data["macro_componente"], data["massa_ton"],
        data["id_processo"], data["anno_dismissione"], data["anno_corrente"], data["id_indice_costi"],
        data["prezzo_acquisto_override"], data["prezzi_prodotti_override"], data["prezzi_intermedi_override"],
        data["figli_processo"],
    )
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.post("/calcolo-da-intermedio")
def r_calcolo_da_intermedio(body: CalcoloIntermedioInput):
    if body.massa_ton <= 0:
        raise HTTPException(400, "massa_ton deve essere positiva")
    data = body.model_dump()
    result = calc.calcola_da_intermedio(
        data["intermedio"], data["massa_ton"], data["id_sottoprocesso"],
        data["anno_dismissione"], data["anno_corrente"], data["id_indice_costi"],
        data["prezzo_acquisto_override"], data["prezzi_prodotti_override"], data["prezzi_intermedi_override"],
        data["figli_sottoprocesso"],
    )
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result
