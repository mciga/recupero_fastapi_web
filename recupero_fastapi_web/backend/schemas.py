"""Modelli Pydantic per le 8 tabelle. Un solo modello per tabella (usato sia
in lettura che in scrittura): la chiave primaria viaggia anche nel path
dell'URL per le operazioni di update/delete, qui serve solo a validare il
body della richiesta."""
from typing import Literal
from pydantic import BaseModel, Field

Tipologia = Literal["EOLICO", "FOTOVOLTAICO", "BESS"]
Categoria = Literal["strategico", "critico", "utile"]
TipoOutput = Literal["prodotto", "intermedio"]


class Impianto(BaseModel):
    id_imp: str
    tipologia: Tipologia
    sotto_tecnologia: str
    potenza_mw: float = Field(gt=0)
    anno_installazione: int
    anno_dismissione: int
    regione: str | None = None
    provincia: str | None = None
    lat: float | None = None
    lon: float | None = None


class Prodotto(BaseModel):
    """Elemento puro (elemento_confronto = se stesso, parametro_equivalenza=1)
    o composto (elemento_confronto = l'elemento la cui massa recuperata viene
    convertita in massa del composto; parametro_equivalenza = quanti atomi
    dell'elemento per formula del composto, es. Li2CO3 -> 2)."""
    prodotto: str
    nome: str
    categoria: Categoria
    peso_molare: float = Field(gt=0)
    elemento_confronto: str
    parametro_equivalenza: float = Field(gt=0, default=1)
    prezzo_attuale_eur_kg: float = Field(ge=0)
    proiezione_prezzo_p1: float = Field(ge=0, le=1)
    proiezione_prezzo_p2: float = Field(ge=0, le=1)


class Macro(BaseModel):
    """Un rigo per (macrocomponente, prodotto elementare contenuto): il
    contenuto elementare serve al bilancio di massa a due stadi."""
    id_macro: str
    tipologia: Tipologia
    sotto_tecnologia: str
    macro_componente: str
    massa_kg_per_mw: float = Field(gt=0)
    prodotto: str
    pct_contenuto_min: float = Field(gt=0, le=1)
    pct_contenuto_max: float = Field(gt=0, le=1)


class IntermedioComposizione(BaseModel):
    """Un rigo per (intermedio, prodotto elementare contenuto): analoga a
    Macro ma per un intermedio (es. BM, MHP) invece che un macrocomponente."""
    intermedio: str
    prodotto: str
    pct_contenuto_min: float = Field(gt=0, le=1)
    pct_contenuto_max: float = Field(gt=0, le=1)


class MacroProcesso(BaseModel):
    id_processo_macro: str
    tipologia: Tipologia
    sotto_tecnologia: str
    macro_componente: str
    tecnica: str
    capex_eur_ton: float = Field(ge=0)
    opex_eur_ton: float = Field(ge=0)
    prezzo_vendita_eur_kg: float = Field(ge=0, default=0)
    proiezione_prezzo_p1: float = Field(ge=0, le=1, default=0)
    proiezione_prezzo_p2: float = Field(ge=0, le=1, default=0)
    descrizione_fasi: str | None = None


class Processo(BaseModel):
    id: int | None = None
    id_processo: str
    tipologia: Tipologia
    sotto_tecnologia: str
    macro_componente: str
    tecnica: str
    capex_eur_ton: float = Field(ge=0)
    opex_eur_ton: float = Field(ge=0)
    tipo_output: TipoOutput
    prodotto: str | None = None
    intermedio_output: str | None = None
    recupero_pct_min: float = Field(gt=0, le=1)
    recupero_pct_max: float = Field(gt=0, le=1)
    descrizione_fasi: str | None = None


class IndiceRivalutazione(BaseModel):
    id_indice: str
    nome: str
    tasso_annuo: float = Field(ge=-1, le=1)


class Intermedio(BaseModel):
    intermedio: str
    nome: str
    prezzo_attuale_eur_kg: float = Field(ge=0)
    proiezione_prezzo_p1: float = Field(ge=0, le=1)
    proiezione_prezzo_p2: float = Field(ge=0, le=1)


class Sottoprocesso(BaseModel):
    id: int | None = None
    id_sottoprocesso: str
    intermedio: str
    tecnica: str
    capex_eur_ton: float = Field(ge=0)
    opex_eur_ton: float = Field(ge=0)
    tipo_output: TipoOutput
    prodotto: str | None = None
    intermedio_output: str | None = None
    recupero_pct_min: float = Field(gt=0, le=1)
    recupero_pct_max: float = Field(gt=0, le=1)
    descrizione_fasi: str | None = None
