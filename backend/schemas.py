"""Modelli Pydantic per le tabelle (schema v8). Un solo modello per tabella,
usato sia in lettura che in scrittura (CRUD e import Excel)."""
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

import chimica

Tipologia = Literal["EOLICO", "FOTOVOLTAICO", "BESS"]
Categoria = Literal["strategico", "critico", "utile"]
# nel database il tipo "impurità" e' salvato SENZA accento ("impurita"): cosi' non dipende
# dalla codifica del client (psql su Windows, Excel...). In ingresso si accettano tutte le varianti.
TipoOutput = Literal["prodotto", "impurita", "scarto", "intermedio"]


def _vuoto_a_none(v):
    return None if (v is None or (isinstance(v, str) and v.strip() == "")) else v


class Impianto(BaseModel):
    id_imp: str
    nome: str
    tipologia: Tipologia
    sotto_tecnologia: str | None = None
    potenza_mw: float | None = Field(default=None, gt=0)
    anno_installazione: int | None = None
    anno_dismissione: int
    regione: str | None = None
    provincia: str | None = None
    lat: float | None = None
    lon: float | None = None


class Prodotto(BaseModel):
    """formula_chimica: composizione dai pesi atomici (bilancio per elemento);
    peso_molare viene ricalcolato dalla formula se presente.
    elemento_confronto: elemento che deve venire dal materiale (controllo
    stechiometrico); vuoto per prodotti dai reagenti aggiunti (es. Na2SO4)."""
    prodotto: str
    nome: str
    categoria: Categoria
    formula_chimica: str | None = None
    peso_molare: float | None = Field(default=None, gt=0)
    elemento_confronto: str | None = None
    parametro_equivalenza: float | None = Field(default=None, gt=0)
    prezzo_attuale_eur_kg: float = Field(ge=0)
    proiezione_prezzo_p1: float = Field(ge=0, le=1)
    proiezione_prezzo_p2: float = Field(ge=0, le=1)

    @field_validator("formula_chimica", "elemento_confronto", mode="before")
    @classmethod
    def _norm(cls, v):
        v = _vuoto_a_none(v)
        return chimica.normalizza(v) if v else None

    @model_validator(mode="after")
    def _formula(self):
        if self.formula_chimica:
            try:
                self.peso_molare = round(chimica.peso_molare(self.formula_chimica), 3)
            except ValueError as e:
                raise ValueError(f"formula_chimica non valida: {e}")
        return self


class ProdottoStorico(BaseModel):
    prodotto: str
    anno: int
    prezzo_usd_t: float | None = Field(default=None, ge=0)
    produzione_eu_kt: float | None = Field(default=None, ge=0)
    consumo_mondiale_mt: float | None = Field(default=None, ge=0)
    fonte: str | None = None


class Materiale(BaseModel):
    """Una riga per (materiale, elemento). Composizione ignota: elemento
    "(composizione non disponibile)" e frazione vuota."""
    material_id: str
    material: str
    elemento: str = "(composizione non disponibile)"
    frazione_pct: float | None = Field(default=None, ge=0, le=100)


class Macro(BaseModel):
    id: int | None = None
    impianto: str
    id_macro: str
    tipologia: Tipologia
    sotto_tecnologia: str | None = None
    macro_componente: str
    assieme_dettaglio: str | None = None
    material: str
    material_id: str
    massa_kg: float = Field(ge=0)

    @field_validator("assieme_dettaglio", "sotto_tecnologia", mode="before")
    @classmethod
    def _v(cls, v):
        return _vuoto_a_none(v)


class Scarto(BaseModel):
    scarto: str
    descrizione: str | None = None
    costo_smaltimento_eur_ton: float = Field(default=0, ge=0)


class Reagente(BaseModel):
    """Reagente di processo (v9): solo la composizione chimica (dalla formula);
    i costi sono negli opex. sale_residuo / reagente_sale / scarto_residuo: dove
    finiscono gli elementi non usati dal prodotto (es. Na2CO3 -> Na2SO4 con H2SO4)."""
    reagente: str
    nome: str
    formula_chimica: str
    peso_molare: float | None = Field(default=None, gt=0)
    sale_residuo: str | None = None
    reagente_sale: str | None = None
    scarto_residuo: str | None = None
    descrizione: str | None = None

    @field_validator("reagente", "formula_chimica", "sale_residuo", "reagente_sale", mode="before")
    @classmethod
    def _norm(cls, v):
        v = _vuoto_a_none(v)
        return chimica.normalizza(v) if v else v

    @field_validator("scarto_residuo", "descrizione", mode="before")
    @classmethod
    def _v(cls, v):
        return _vuoto_a_none(v)

    @model_validator(mode="after")
    def _formula(self):
        try:
            self.peso_molare = round(chimica.peso_molare(self.formula_chimica), 3)
        except ValueError as e:
            raise ValueError(f"formula_chimica non valida: {e}")
        if self.reagente_sale and self.reagente_sale == self.reagente:
            raise ValueError("reagente_sale non puo' essere il reagente stesso")
        return self


class _ConRecuperi(BaseModel):
    """tipo_output: prodotto / impurità (nel prodotto indicato) / scarto /
    intermedio. Tre scenari di recupero (0..1), usati cosi' come sono: la somma per
    materiale puo' superare 1 (la massa in piu' e' quella dei reagenti).
    reagente (v9, solo per i prodotti): reagente che fornisce gli elementi della
    formula diversi dall'elemento di confronto."""
    tipo_output: TipoOutput
    prodotto: str | None = None
    intermedio_output: str | None = None
    scarto: str | None = None
    recupero_pct_min: float = Field(ge=0, le=1)
    recupero_pct: float = Field(ge=0, le=1)
    recupero_pct_max: float = Field(ge=0, le=1)
    descrizione_fasi: str | None = None
    reagente: str | None = None
    # capex e taglia (v9.1): capex_eur_ton = EUR per t/anno di capacita'
    taglia_riferimento_t_anno: float | None = Field(default=None, gt=0)   # vuota = capex lineare con la taglia
    esponente_scala: float = Field(default=0.6, gt=0, le=1)
    vita_utile_anni: float = Field(default=15, gt=0)

    @field_validator("taglia_riferimento_t_anno", mode="before")
    @classmethod
    def _tr(cls, v):
        return _vuoto_a_none(v)

    @field_validator("esponente_scala", "vita_utile_anni", mode="before")
    @classmethod
    def _def(cls, v, info):
        v = _vuoto_a_none(v)
        return v if v is not None else {"esponente_scala": 0.6, "vita_utile_anni": 15}[info.field_name]

    @field_validator("reagente", mode="before")
    @classmethod
    def _reag(cls, v):
        v = _vuoto_a_none(v)
        return chimica.normalizza(v) if v else v

    @field_validator("tipo_output", mode="before")
    @classmethod
    def _tipo(cls, v):
        v = (v or "").strip().lower()
        return "impurita" if v.startswith("impur") else v

    @field_validator("prodotto", "intermedio_output", "scarto", mode="before")
    @classmethod
    def _cod(cls, v):
        v = _vuoto_a_none(v)
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode="after")
    def _check(self):
        t = self.tipo_output
        if self.reagente and t != "prodotto":
            raise ValueError("il reagente si indica solo sulle righe tipo_output=prodotto")
        if t == "scarto":
            if not self.scarto:
                # formato del file utente: il nome dello scarto sta nella colonna "prodotto"
                self.scarto = self.prodotto
            if not self.scarto:
                raise ValueError("tipo_output=scarto: indicare lo scarto")
            self.prodotto = self.intermedio_output = None
        elif t == "intermedio":
            if not self.intermedio_output:
                raise ValueError("tipo_output=intermedio: indicare intermedio_output")
            self.prodotto = self.scarto = None
        else:
            if self.prodotto:
                self.prodotto = chimica.normalizza(self.prodotto)
            if not (self.prodotto or self.intermedio_output):
                raise ValueError(f"tipo_output={t}: indicare il prodotto (o l'intermedio) che riceve l'uscita")
            self.scarto = None
        return self


class Processo(_ConRecuperi):
    id: int | None = None
    id_processo: str
    tipologia: Tipologia
    sotto_tecnologia: str | None = None
    macro_componente: str
    tecnica: str
    capex_eur_ton: float = Field(ge=0)
    opex_eur_ton: float = Field(ge=0)
    material_id: str
    assieme_dettaglio: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _alias(cls, d):
        if isinstance(d, dict) and not d.get("material_id") and d.get("material"):
            d = {**d, "material_id": d["material"]}   # colonna "material" del file utente
        return d

    @field_validator("sotto_tecnologia", "assieme_dettaglio", mode="before")
    @classmethod
    def _v(cls, v):
        return _vuoto_a_none(v)


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


class Sottoprocesso(_ConRecuperi):
    id: int | None = None
    id_sottoprocesso: str
    intermedio: str
    tecnica: str
    capex_eur_ton: float = Field(ge=0)
    opex_eur_ton: float = Field(ge=0)
