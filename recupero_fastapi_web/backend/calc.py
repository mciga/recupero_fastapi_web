"""Filtri a cascata e motore di calcolo economico.

Catena (nessuno scenario: i macroprocessi si scelgono per singolo
macrocomponente, come alternative dirette):

  Impianto --[db_macro_processi]--> Macrocomponente (sempre scomposto)
           --[db_processi, se attivato]--> Prodotto (terminale) e/o Intermedio
                                            (venduto as-is oppure lavorato con
                                            db_sottoprocessi, ricorsivamente,
                                            fino a quando tutte le uscite sono
                                            Prodotti terminali)

BILANCIO DI MASSA — a due stadi ovunque un prodotto (elemento o composto) ha
un "elemento di confronto" con un contenuto noto per l'input in corso (in
db_macro se l'input e' un macrocomponente, in db_intermedi_composizione se
l'input e' un intermedio come BM o MHP):
     massa_elemento_in_ingresso = massa_input x %contenuto
     massa_elemento_recuperata  = massa_elemento_in_ingresso x %efficienza (recupero_pct)
     massa_prodotto             = massa_elemento_recuperata / peso_molare_elemento
                                   / parametro_equivalenza x peso_molare_prodotto
Il prodotto puo' essere l'elemento stesso (elemento_confronto = se stesso,
parametro_equivalenza=1: nessuna conversione) oppure un composto (es. LiOH,
CoSO4). Se il prodotto non ha un contenuto noto per quell'input (es.
materiali strutturali come Cu/Al in una cella), si ricade sul modello
diretto a un stadio: massa_uscita = massa_input_kg x %resa — usato sempre,
in ogni caso, per generare un altro INTERMEDIO (una miscela non ha una
formula chimica univoca, quindi nessuna conversione stechiometrica).

"Elemento non estratto" (ex "scarto"): per ogni elemento tracciato (con un
contenuto noto per quell'input) non completamente recuperato dalle uscite,
si espone massa_contenuta - massa_recuperata — non piu' un unico complemento
al 100% della massa in ingresso, ma un valore per ciascun elemento.

Filosofia dei prezzi: ogni prodotto/intermedio/macrocomponente ha un prezzo
di default nel database, usato SEMPRE a meno che l'utente non lo sovrascriva
esplicitamente (dashboard: clic sulla card + conferma nuovo prezzo). Il
ricavo e' quindi sempre calcolato; ogni voce espone un flag
"prezzo_personalizzato" per evidenziare in dashboard cosa e' stato
rivalutato dall'utente rispetto al prezzo di listino.

I costi (capex/opex di entrambi gli stadi) vengono comunque rivalutati
all'anno di dismissione con l'indice scelto (es. ISTAT).
"""
from sqlalchemy import text
from db import ENGINE, SCHEMA

# ---------------------------------------------------------------- filtri --
def tipologie() -> list[str]:
    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        rows = conn.execute(text(f"SELECT DISTINCT tipologia FROM {SCHEMA}.db_macro ORDER BY 1"))
        return [r[0] for r in rows]


def sotto_tecnologie(tipologia: str) -> list[str]:
    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        rows = conn.execute(
            text(f"SELECT DISTINCT sotto_tecnologia FROM {SCHEMA}.db_macro WHERE tipologia=:t ORDER BY 1"),
            {"t": tipologia})
        return [r[0] for r in rows]


def macro_componenti(tipologia: str, sotto: str) -> list[str]:
    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        rows = conn.execute(
            text(f"SELECT DISTINCT macro_componente FROM {SCHEMA}.db_macro "
                 f"WHERE tipologia=:t AND sotto_tecnologia=:s ORDER BY 1"),
            {"t": tipologia, "s": sotto})
        return [r[0] for r in rows]


def macro_processi_disponibili(tipologia: str, sotto: str, macro: str) -> list[dict]:
    """Macroprocessi alternativi per scomporre l'impianto in QUESTO
    macrocomponente (es. PALE: smontaggio+trasporto / solo disassemblaggio /
    taglio in sito)."""
    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        rows = conn.execute(
            text(f"SELECT id_processo_macro, tecnica, capex_eur_ton, opex_eur_ton, "
                 f"prezzo_vendita_eur_kg, descrizione_fasi FROM {SCHEMA}.db_macro_processi "
                 f"WHERE tipologia=:t AND sotto_tecnologia=:s AND macro_componente=:m ORDER BY tecnica"),
            {"t": tipologia, "s": sotto, "m": macro})
        return [dict(r._mapping) for r in rows]


def processi_disponibili(tipologia: str, sotto: str, macro: str) -> list[dict]:
    """Processi alternativi applicabili al macrocomponente (recupero diretto
    a prodotto e/o trasformazione in intermedio)."""
    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        rows = conn.execute(
            text(f"SELECT id_processo, tecnica, tipo_output, capex_eur_ton, opex_eur_ton "
                 f"FROM {SCHEMA}.db_processi WHERE tipologia=:t AND sotto_tecnologia=:s AND macro_componente=:m "
                 f"ORDER BY tecnica"),
            {"t": tipologia, "s": sotto, "m": macro})
        seen, out = set(), []
        for r in rows:
            r = dict(r._mapping)
            if r["id_processo"] in seen:
                continue
            seen.add(r["id_processo"])
            out.append(r)
        return out


def sottoprocessi_disponibili(intermedio: str) -> list[dict]:
    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        rows = conn.execute(
            text(f"SELECT DISTINCT id_sottoprocesso, tecnica FROM {SCHEMA}.db_sottoprocessi "
                 f"WHERE intermedio=:s ORDER BY tecnica"),
            {"s": intermedio})
        return [dict(r._mapping) for r in rows]


def prodotti_lista() -> list[dict]:
    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        rows = conn.execute(text(
            f"SELECT prodotto, nome, categoria, prezzo_attuale_eur_kg FROM {SCHEMA}.db_prodotti ORDER BY prodotto"))
        return [dict(r._mapping) for r in rows]


def intermedi_lista() -> list[dict]:
    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        rows = conn.execute(text(
            f"SELECT intermedio, nome, prezzo_attuale_eur_kg FROM {SCHEMA}.db_intermedi ORDER BY intermedio"))
        return [dict(r._mapping) for r in rows]


def impianti_lista() -> list[dict]:
    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        rows = conn.execute(text(
            f"SELECT id_imp, tipologia, sotto_tecnologia, potenza_mw, anno_dismissione, regione "
            f"FROM {SCHEMA}.db_impianti ORDER BY tipologia, sotto_tecnologia, id_imp"))
        return [dict(r._mapping) for r in rows]


def indici_rivalutazione() -> list[dict]:
    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        rows = conn.execute(text(f"SELECT id_indice, nome, tasso_annuo FROM {SCHEMA}.db_indici_rivalutazione ORDER BY id_indice"))
        return [dict(r._mapping) for r in rows]


# --------------------------------------------------------- query di supporto --
QUERY_MASSA_KG_PER_MW = text(f"""
    SELECT DISTINCT massa_kg_per_mw FROM {SCHEMA}.db_macro
    WHERE tipologia=:t AND sotto_tecnologia=:s AND macro_componente=:m
""")

QUERY_CONTENUTO_ELEMENTO = text(f"""
    SELECT pct_contenuto_min, pct_contenuto_max FROM {SCHEMA}.db_macro
    WHERE tipologia=:t AND sotto_tecnologia=:s AND macro_componente=:m AND prodotto=:p
""")

QUERY_CONTENUTO_ELEMENTO_INTERMEDIO = text(f"""
    SELECT pct_contenuto_min, pct_contenuto_max FROM {SCHEMA}.db_intermedi_composizione
    WHERE intermedio=:i AND prodotto=:p
""")

QUERY_MACRO_PROCESSO = text(f"""
    SELECT tecnica, capex_eur_ton, opex_eur_ton, descrizione_fasi, prezzo_vendita_eur_kg
    FROM {SCHEMA}.db_macro_processi WHERE id_processo_macro = :id
""")

QUERY_PROCESSO_RIGHE = text(f"""
    SELECT tecnica, capex_eur_ton, opex_eur_ton, tipo_output, prodotto, intermedio_output,
           recupero_pct_min, recupero_pct_max, descrizione_fasi
    FROM {SCHEMA}.db_processi WHERE id_processo = :id
""")

QUERY_SOTTOPROCESSO_RIGHE = text(f"""
    SELECT tecnica, capex_eur_ton, opex_eur_ton, tipo_output, prodotto, intermedio_output,
           recupero_pct_min, recupero_pct_max, descrizione_fasi
    FROM {SCHEMA}.db_sottoprocessi WHERE id_sottoprocesso=:id
""")

QUERY_INTERMEDIO_INFO = text(f"""
    SELECT intermedio, nome, prezzo_attuale_eur_kg FROM {SCHEMA}.db_intermedi WHERE intermedio=:s
""")

QUERY_PRODOTTO_INFO = text(f"""
    SELECT prodotto, nome, categoria, prezzo_attuale_eur_kg, peso_molare, elemento_confronto, parametro_equivalenza
    FROM {SCHEMA}.db_prodotti WHERE prodotto=:p
""")

QUERY_PREZZO_MACRO_DEFAULT = text(f"""
    SELECT prezzo_vendita_eur_kg FROM {SCHEMA}.db_macro_processi
    WHERE tipologia=:t AND sotto_tecnologia=:s AND macro_componente=:m
    ORDER BY tecnica LIMIT 1
""")


def _fattore_rivalutazione(conn, id_indice_costi: str, anni: int) -> tuple[float, float]:
    row = conn.execute(
        text(f"SELECT tasso_annuo FROM {SCHEMA}.db_indici_rivalutazione WHERE id_indice=:i"),
        {"i": id_indice_costi}).first()
    tasso = float(row[0]) if row else 0.0
    return tasso, (1 + tasso) ** anni


def _prodotto_info(conn, prodotto: str) -> dict:
    row = conn.execute(QUERY_PRODOTTO_INFO, {"p": prodotto}).first()
    return dict(row._mapping) if row else {}


# ----------------------------------------------------- motore ricorsivo --
def _calcola_uscite(conn, righe: list[dict], massa_input_kg: float,
                     prezzi_prodotti_override: dict, prezzi_intermedi_override: dict,
                     figli_scelte: dict | None, fattore_rivalutazione: float,
                     contesto: dict | None = None):
    """Calcola le uscite di UN processo/sottoprocesso (righe gia' filtrate):
    per ciascuna, se e' un prodotto lo prezza (default o override) ed e'
    terminale; se e' un intermedio, o lo prezza come vendita diretta
    (default) o, se l'utente ha scelto di lavorarlo oltre, ricorre su un
    sottoprocesso. Ritorna (uscite, ricavo_min, ricavo_max, ha_override,
    costo_extra, elementi_non_estratti).

    contesto: {"tipo":"macro", "tipologia":.., "sotto":.., "macro":..} oppure
    {"tipo":"intermedio", "intermedio":..}. Per un'uscita "prodotto" il cui
    elemento di confronto ha un contenuto noto (in db_macro o
    db_intermedi_composizione a seconda del contesto), si applica SEMPRE il
    modello A DUE STADI (contenuto elementare x efficienza, poi conversione
    stechiometrica in massa del composto). Senza un contenuto noto (es. Cu/Al
    strutturali) si ricade sul modello diretto (massa_input_kg x resa), che
    pero' non alimenta piu' un concetto di scarto aggregato: "elemento non
    estratto" e' riferito solo agli elementi effettivamente tracciati (con
    un contenuto noto), per ciascuno: massa_contenuta - massa_recuperata."""
    uscite = []
    ricavo_min_tot = ricavo_max_tot = 0.0
    costo_extra = 0.0
    ha_override = False
    tracciati: dict[str, dict] = {}  # elemento -> {nome, content_min, content_max, estratto_min, estratto_max}

    for r in righe:
        due_stadi = False
        p = None
        if r["tipo_output"] == "prodotto":
            p = _prodotto_info(conn, r["prodotto"])
            if contesto:
                elemento = p.get("elemento_confronto")
                if elemento:
                    cont = _lookup_contenuto(conn, contesto, elemento)
                    if cont:
                        due_stadi = True
                        cont_min, cont_max = cont
                        el_info = p if elemento == r["prodotto"] else _prodotto_info(conn, elemento)
                        peso_molare_el = float(el_info["peso_molare"])
                        peso_molare_comp = float(p["peso_molare"])
                        param_eq = float(p["parametro_equivalenza"])

        if due_stadi:
            massa_el_in_min = massa_input_kg * cont_min
            massa_el_in_max = massa_input_kg * cont_max
            massa_el_estratta_min = massa_el_in_min * float(r["recupero_pct_min"])
            massa_el_estratta_max = massa_el_in_max * float(r["recupero_pct_max"])
            massa_out_min = massa_el_estratta_min / peso_molare_el / param_eq * peso_molare_comp
            massa_out_max = massa_el_estratta_max / peso_molare_el / param_eq * peso_molare_comp

            t = tracciati.setdefault(elemento, {
                "nome": el_info.get("nome"), "content_min": 0.0, "content_max": 0.0,
                "estratto_min": 0.0, "estratto_max": 0.0,
            })
            t["content_min"] += massa_el_in_min
            t["content_max"] += massa_el_in_max
            t["estratto_min"] += massa_el_estratta_min
            t["estratto_max"] += massa_el_estratta_max
        else:
            massa_out_min = massa_input_kg * float(r["recupero_pct_min"])
            massa_out_max = massa_input_kg * float(r["recupero_pct_max"])
        massa_out_mid = (massa_out_min + massa_out_max) / 2

        if r["tipo_output"] == "prodotto":
            prezzo_default = float(p.get("prezzo_attuale_eur_kg") or 0)
            override = prezzi_prodotti_override.get(r["prodotto"])
            personalizzato = override is not None
            prezzo_eff = float(override) if personalizzato else prezzo_default
            if personalizzato:
                ha_override = True
            ricavo_min = massa_out_min * prezzo_eff
            ricavo_max = massa_out_max * prezzo_eff
            ricavo_min_tot += ricavo_min
            ricavo_max_tot += ricavo_max
            uscite.append({
                "tipo": "prodotto", "codice": r["prodotto"], "nome": p.get("nome"), "categoria": p.get("categoria"),
                "due_stadi": due_stadi,
                "massa_kg_min": massa_out_min, "massa_kg_max": massa_out_max,
                "prezzo_default_eur_kg": prezzo_default, "prezzo_eur_kg": prezzo_eff,
                "prezzo_personalizzato": personalizzato,
                "ricavo_eur_min": ricavo_min, "ricavo_eur_max": ricavo_max, "ramo": None,
            })
        else:
            sp = _intermedio_info(conn, r["intermedio_output"])
            prezzo_default = float(sp.get("prezzo_attuale_eur_kg") or 0)
            scelta = (figli_scelte or {}).get(r["intermedio_output"]) or {}
            id_sub = scelta.get("id_sottoprocesso")

            if id_sub:
                ramo = calcola_ramo_sottoprocesso(
                    conn, r["intermedio_output"], massa_out_mid, id_sub, fattore_rivalutazione,
                    prezzi_prodotti_override, prezzi_intermedi_override, scelta.get("figli"))
                costo_extra += ramo["costo_eur"]
                ricavo_min_tot += ramo["ricavo_eur_min"]
                ricavo_max_tot += ramo["ricavo_eur_max"]
                if ramo["ha_override"]:
                    ha_override = True
                uscite.append({
                    "tipo": "intermedio", "codice": r["intermedio_output"], "nome": sp.get("nome"),
                    "categoria": None, "massa_kg_min": massa_out_min, "massa_kg_max": massa_out_max,
                    "trasformato": True, "ramo": ramo,
                    "prezzo_default_eur_kg": prezzo_default, "prezzo_eur_kg": None, "prezzo_personalizzato": False,
                    "ricavo_eur_min": ramo["ricavo_eur_min"], "ricavo_eur_max": ramo["ricavo_eur_max"],
                })
            else:
                override = prezzi_intermedi_override.get(r["intermedio_output"])
                personalizzato = override is not None
                prezzo_eff = float(override) if personalizzato else prezzo_default
                if personalizzato:
                    ha_override = True
                ricavo_min = massa_out_min * prezzo_eff
                ricavo_max = massa_out_max * prezzo_eff
                ricavo_min_tot += ricavo_min
                ricavo_max_tot += ricavo_max
                uscite.append({
                    "tipo": "intermedio", "codice": r["intermedio_output"], "nome": sp.get("nome"),
                    "categoria": None, "massa_kg_min": massa_out_min, "massa_kg_max": massa_out_max,
                    "trasformato": False, "ramo": None,
                    "prezzo_default_eur_kg": prezzo_default, "prezzo_eur_kg": prezzo_eff,
                    "prezzo_personalizzato": personalizzato,
                    "ricavo_eur_min": ricavo_min, "ricavo_eur_max": ricavo_max,
                })

    # "elemento non estratto" = massa contenuta - massa estratta, per ciascun
    # elemento tracciato. Accoppiamento inverso come per un complemento: il
    # minimo del non-estratto corrisponde al massimo estratto e viceversa.
    elementi_non_estratti = []
    for elemento, t in tracciati.items():
        non_estratto_min = max(0.0, t["content_min"] - t["estratto_max"])
        non_estratto_max = max(0.0, t["content_max"] - t["estratto_min"])
        if non_estratto_max > 0:
            elementi_non_estratti.append({
                "elemento": elemento, "nome": t["nome"],
                "massa_kg_min": non_estratto_min, "massa_kg_max": non_estratto_max,
            })

    return uscite, ricavo_min_tot, ricavo_max_tot, ha_override, costo_extra, elementi_non_estratti


def _lookup_contenuto(conn, contesto: dict, elemento: str) -> tuple[float, float] | None:
    if contesto["tipo"] == "macro":
        row = conn.execute(QUERY_CONTENUTO_ELEMENTO, {
            "t": contesto["tipologia"], "s": contesto["sotto"], "m": contesto["macro"], "p": elemento}).first()
    else:
        row = conn.execute(QUERY_CONTENUTO_ELEMENTO_INTERMEDIO, {"i": contesto["intermedio"], "p": elemento}).first()
    return (float(row[0]), float(row[1])) if row else None


def _intermedio_info(conn, intermedio: str) -> dict:
    row = conn.execute(QUERY_INTERMEDIO_INFO, {"s": intermedio}).first()
    return dict(row._mapping) if row else {}


def calcola_ramo_sottoprocesso(conn, codice_intermedio: str, massa_input_kg: float, id_sottoprocesso: str | None,
                                fattore_rivalutazione: float, prezzi_prodotti_override: dict,
                                prezzi_intermedi_override: dict, figli_scelte: dict | None) -> dict:
    """Un ramo della catena di lavorazione di un intermedio: se
    id_sottoprocesso e' None il ramo non e' impostato (la vendita diretta la
    gestisce il chiamante); altrimenti applica il sottoprocesso — a due
    stadi per i prodotti il cui elemento di confronto ha un contenuto noto
    in db_intermedi_composizione per questo intermedio, diretto altrimenti
    — e ricorre sulle uscite che sono a loro volta intermedi trasformati."""
    if id_sottoprocesso is None:
        return {"input": codice_intermedio, "massa_input_kg": massa_input_kg, "sottoprocesso": None,
                "costo_eur": 0.0, "uscite": [], "ricavo_eur_min": 0.0, "ricavo_eur_max": 0.0, "ha_override": False}

    righe = conn.execute(QUERY_SOTTOPROCESSO_RIGHE, {"id": id_sottoprocesso}).all()
    if not righe:
        return {"error": "sottoprocesso_non_trovato", "input": codice_intermedio}
    righe = [dict(r._mapping) for r in righe]
    massa_input_ton = massa_input_kg / 1000
    capex_step = float(righe[0]["capex_eur_ton"]) * massa_input_ton * fattore_rivalutazione
    opex_step = float(righe[0]["opex_eur_ton"]) * massa_input_ton * fattore_rivalutazione
    costo_step = capex_step + opex_step

    contesto = {"tipo": "intermedio", "intermedio": codice_intermedio}
    uscite, ricavo_min, ricavo_max, ha_override, costo_extra, elementi_non_estratti = _calcola_uscite(
        conn, righe, massa_input_kg, prezzi_prodotti_override, prezzi_intermedi_override,
        figli_scelte, fattore_rivalutazione, contesto)

    return {
        "input": codice_intermedio, "massa_input_kg": massa_input_kg,
        "sottoprocesso": {"id_sottoprocesso": id_sottoprocesso, "tecnica": righe[0]["tecnica"],
                           "capex_eur_ton": righe[0]["capex_eur_ton"], "opex_eur_ton": righe[0]["opex_eur_ton"],
                           "descrizione_fasi": righe[0]["descrizione_fasi"],
                           "capex_eur": capex_step, "opex_eur": opex_step, "costo_eur": costo_step,
                           "elementi_non_estratti": elementi_non_estratti},
        "costo_eur": costo_step + costo_extra, "uscite": uscite,
        "ricavo_eur_min": ricavo_min, "ricavo_eur_max": ricavo_max, "ha_override": ha_override,
    }


def calcola_componente(conn, tipologia: str, sotto: str, macro: str, id_processo_macro: str,
                        id_processo: str | None, potenza_mw: float, anni: int,
                        fattore_rivalutazione: float,
                        prezzo_macro_override: float | None = None,
                        prezzi_prodotti_override: dict | None = None,
                        prezzi_intermedi_override: dict | None = None,
                        figli_processo: dict | None = None) -> dict:
    """Calcola il contributo di UN macrocomponente: scomposizione sempre,
    poi se attivato applica il processo scelto (a due stadi per i prodotti
    con contenuto noto, diretto altrimenti); altrimenti vendita diretta."""
    prezzi_prodotti_override = prezzi_prodotti_override or {}
    prezzi_intermedi_override = prezzi_intermedi_override or {}

    massa_row = conn.execute(QUERY_MASSA_KG_PER_MW, {"t": tipologia, "s": sotto, "m": macro}).first()
    massa_kg_per_mw = float(massa_row[0]) if massa_row else 0.0
    massa_componente_kg = massa_kg_per_mw * potenza_mw
    massa_componente_ton = massa_componente_kg / 1000

    mp_row = conn.execute(QUERY_MACRO_PROCESSO, {"id": id_processo_macro}).first()
    if not mp_row:
        return {"error": "processo_macro_non_trovato", "macro_componente": macro}
    mp = dict(mp_row._mapping)
    capex_scomposizione = float(mp["capex_eur_ton"]) * massa_componente_ton * fattore_rivalutazione
    opex_scomposizione = float(mp["opex_eur_ton"]) * massa_componente_ton * fattore_rivalutazione
    costo_scomposizione = capex_scomposizione + opex_scomposizione

    result = {
        "macro_componente": macro, "attivo": id_processo is not None,
        "massa_componente_kg": massa_componente_kg,
        "scomposizione": {"tecnica": mp["tecnica"], "descrizione_fasi": mp["descrizione_fasi"],
                           "capex_eur_ton": mp["capex_eur_ton"], "opex_eur_ton": mp["opex_eur_ton"],
                           "capex_eur": capex_scomposizione, "opex_eur": opex_scomposizione,
                           "costo_eur": costo_scomposizione},
        "processo": None, "vendita_diretta": None, "uscite": [],
        "ricavo_eur_min": 0.0, "ricavo_eur_max": 0.0,
        "costo_totale_eur": costo_scomposizione, "ha_override": False,
    }

    if id_processo is None:
        prezzo_default = float(mp["prezzo_vendita_eur_kg"] or 0)
        personalizzato = prezzo_macro_override is not None
        prezzo_eff = float(prezzo_macro_override) if personalizzato else prezzo_default
        ricavo = massa_componente_kg * prezzo_eff
        result["vendita_diretta"] = {
            "prezzo_default_eur_kg": prezzo_default, "prezzo_eur_kg": prezzo_eff,
            "prezzo_personalizzato": personalizzato, "ricavo_eur": ricavo,
        }
        result["ha_override"] = personalizzato
        result["ricavo_eur_min"] = result["ricavo_eur_max"] = ricavo
        return result

    righe = conn.execute(QUERY_PROCESSO_RIGHE, {"id": id_processo}).all()
    if not righe:
        result["error"] = "nessuna_uscita_per_processo"
        return result
    righe = [dict(r._mapping) for r in righe]
    capex_processo = float(righe[0]["capex_eur_ton"]) * massa_componente_ton * fattore_rivalutazione
    opex_processo = float(righe[0]["opex_eur_ton"]) * massa_componente_ton * fattore_rivalutazione
    costo_processo = capex_processo + opex_processo

    contesto = {"tipo": "macro", "tipologia": tipologia, "sotto": sotto, "macro": macro}
    uscite, ricavo_min, ricavo_max, ha_override, costo_extra, elementi_non_estratti = _calcola_uscite(
        conn, righe, massa_componente_kg, prezzi_prodotti_override, prezzi_intermedi_override,
        figli_processo, fattore_rivalutazione, contesto)

    result["processo"] = {"id_processo": id_processo, "tecnica": righe[0]["tecnica"],
                           "capex_eur_ton": righe[0]["capex_eur_ton"], "opex_eur_ton": righe[0]["opex_eur_ton"],
                           "descrizione_fasi": righe[0]["descrizione_fasi"],
                           "capex_eur": capex_processo, "opex_eur": opex_processo, "costo_eur": costo_processo,
                           "elementi_non_estratti": elementi_non_estratti}
    result["uscite"] = uscite
    result["ricavo_eur_min"], result["ricavo_eur_max"] = ricavo_min, ricavo_max
    result["ha_override"] = ha_override
    result["costo_totale_eur"] = costo_scomposizione + costo_processo + costo_extra
    return result


def calcola_impianto(tipologia: str, sotto: str, componenti: list[dict], potenza_mw: float,
                      anno_dismissione: int, anno_corrente: int = 2026,
                      id_indice_costi: str = "ISTAT") -> dict:
    """componenti: [{macro_componente, id_processo_macro, id_processo|None,
    prezzo_macro_override|None, prezzi_prodotti_override|None,
    prezzi_intermedi_override|None, figli_processo|None}, ...]"""
    anni = max(anno_dismissione - anno_corrente, 0)
    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        tasso_costi, fattore_rivalutazione = _fattore_rivalutazione(conn, id_indice_costi, anni)

        risultati = [
            calcola_componente(conn, tipologia, sotto, c["macro_componente"], c["id_processo_macro"],
                                c.get("id_processo"), potenza_mw, anni, fattore_rivalutazione,
                                c.get("prezzo_macro_override"), c.get("prezzi_prodotti_override"),
                                c.get("prezzi_intermedi_override"), c.get("figli_processo"))
            for c in componenti
        ]

    massa_totale_kg = sum(r["massa_componente_kg"] for r in risultati)
    costo_totale = sum(r["costo_totale_eur"] for r in risultati)
    ricavo_min_tot = sum(r["ricavo_eur_min"] for r in risultati)
    ricavo_max_tot = sum(r["ricavo_eur_max"] for r in risultati)
    ha_override_qualche = any(r["ha_override"] for r in risultati)

    return {
        "massa_totale_kg": massa_totale_kg,
        "fattore_rivalutazione_costi": fattore_rivalutazione,
        "tasso_costi_annuo": tasso_costi,
        "costo_totale_eur": costo_totale,
        "ricavo_eur_min": ricavo_min_tot, "ricavo_eur_max": ricavo_max_tot,
        "margine_eur_min": ricavo_min_tot - costo_totale,
        "margine_eur_max": ricavo_max_tot - costo_totale,
        "n_componenti_attivi": sum(1 for r in risultati if r["attivo"]),
        "ha_prezzi_personalizzati": ha_override_qualche,
        "componenti": risultati,
    }


# ------------------------------------------------- modalita' "materiale acquistato" --
def calcola_da_macrocomponente(tipologia: str, sotto: str, macro: str, massa_ton: float,
                                id_processo: str, anno_dismissione: int, anno_corrente: int = 2026,
                                id_indice_costi: str = "ISTAT",
                                prezzo_acquisto_override: float | None = None,
                                prezzi_prodotti_override: dict | None = None,
                                prezzi_intermedi_override: dict | None = None,
                                figli_processo: dict | None = None) -> dict:
    prezzi_prodotti_override = prezzi_prodotti_override or {}
    prezzi_intermedi_override = prezzi_intermedi_override or {}
    massa_kg = massa_ton * 1000
    anni = max(anno_dismissione - anno_corrente, 0)

    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        tasso_costi, fattore_rivalutazione = _fattore_rivalutazione(conn, id_indice_costi, anni)

        prezzo_row = conn.execute(QUERY_PREZZO_MACRO_DEFAULT, {"t": tipologia, "s": sotto, "m": macro}).first()
        if not prezzo_row:
            return {"error": "macrocomponente_non_trovato"}
        prezzo_default = float(prezzo_row[0] or 0)
        personalizzato_acquisto = prezzo_acquisto_override is not None
        prezzo_acquisto_eff = float(prezzo_acquisto_override) if personalizzato_acquisto else prezzo_default
        costo_acquisto = massa_kg * prezzo_acquisto_eff

        righe = conn.execute(QUERY_PROCESSO_RIGHE, {"id": id_processo}).all()
        if not righe:
            return {"error": "processo_non_trovato"}
        righe = [dict(r._mapping) for r in righe]
        massa_ton_calc = massa_kg / 1000
        capex_processo = float(righe[0]["capex_eur_ton"]) * massa_ton_calc * fattore_rivalutazione
        opex_processo = float(righe[0]["opex_eur_ton"]) * massa_ton_calc * fattore_rivalutazione
        costo_processo = capex_processo + opex_processo

        contesto = {"tipo": "macro", "tipologia": tipologia, "sotto": sotto, "macro": macro}
        uscite, ricavo_min, ricavo_max, ha_override, costo_extra, elementi_non_estratti = _calcola_uscite(
            conn, righe, massa_kg, prezzi_prodotti_override, prezzi_intermedi_override,
            figli_processo, fattore_rivalutazione, contesto)

    costo_totale = costo_acquisto + costo_processo + costo_extra
    return {
        "macro_componente": macro, "massa_input_kg": massa_kg,
        "acquisto": {"prezzo_default_eur_kg": prezzo_default, "prezzo_eur_kg": prezzo_acquisto_eff,
                     "prezzo_personalizzato": personalizzato_acquisto, "costo_eur": costo_acquisto},
        "processo": {"id_processo": id_processo, "tecnica": righe[0]["tecnica"],
                     "capex_eur_ton": righe[0]["capex_eur_ton"], "opex_eur_ton": righe[0]["opex_eur_ton"],
                     "descrizione_fasi": righe[0]["descrizione_fasi"],
                     "capex_eur": capex_processo, "opex_eur": opex_processo, "costo_eur": costo_processo,
                     "elementi_non_estratti": elementi_non_estratti},
        "uscite": uscite,
        "costo_totale_eur": costo_totale,
        "ricavo_eur_min": ricavo_min, "ricavo_eur_max": ricavo_max,
        "margine_eur_min": ricavo_min - costo_totale, "margine_eur_max": ricavo_max - costo_totale,
        "fattore_rivalutazione_costi": fattore_rivalutazione, "tasso_costi_annuo": tasso_costi,
        "ha_prezzi_personalizzati": ha_override or personalizzato_acquisto,
    }


def calcola_da_intermedio(intermedio: str, massa_ton: float, id_sottoprocesso: str,
                           anno_dismissione: int, anno_corrente: int = 2026,
                           id_indice_costi: str = "ISTAT",
                           prezzo_acquisto_override: float | None = None,
                           prezzi_prodotti_override: dict | None = None,
                           prezzi_intermedi_override: dict | None = None,
                           figli_sottoprocesso: dict | None = None) -> dict:
    prezzi_prodotti_override = prezzi_prodotti_override or {}
    prezzi_intermedi_override = prezzi_intermedi_override or {}
    massa_kg = massa_ton * 1000
    anni = max(anno_dismissione - anno_corrente, 0)

    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        tasso_costi, fattore_rivalutazione = _fattore_rivalutazione(conn, id_indice_costi, anni)

        sp_row = conn.execute(QUERY_INTERMEDIO_INFO, {"s": intermedio}).first()
        if not sp_row:
            return {"error": "intermedio_non_trovato"}
        sp = dict(sp_row._mapping)
        prezzo_default = float(sp.get("prezzo_attuale_eur_kg") or 0)
        personalizzato_acquisto = prezzo_acquisto_override is not None
        prezzo_acquisto_eff = float(prezzo_acquisto_override) if personalizzato_acquisto else prezzo_default
        costo_acquisto = massa_kg * prezzo_acquisto_eff

        ramo = calcola_ramo_sottoprocesso(conn, intermedio, massa_kg, id_sottoprocesso, fattore_rivalutazione,
                                           prezzi_prodotti_override, prezzi_intermedi_override, figli_sottoprocesso)
    if "error" in ramo:
        return ramo

    costo_totale = costo_acquisto + ramo["costo_eur"]
    return {
        "intermedio": intermedio, "massa_input_kg": massa_kg,
        "acquisto": {"prezzo_default_eur_kg": prezzo_default, "prezzo_eur_kg": prezzo_acquisto_eff,
                     "prezzo_personalizzato": personalizzato_acquisto, "costo_eur": costo_acquisto},
        "sottoprocesso": ramo["sottoprocesso"],
        "uscite": ramo["uscite"],
        "costo_totale_eur": costo_totale,
        "ricavo_eur_min": ramo["ricavo_eur_min"], "ricavo_eur_max": ramo["ricavo_eur_max"],
        "margine_eur_min": ramo["ricavo_eur_min"] - costo_totale, "margine_eur_max": ramo["ricavo_eur_max"] - costo_totale,
        "fattore_rivalutazione_costi": fattore_rivalutazione, "tasso_costi_annuo": tasso_costi,
        "ha_prezzi_personalizzati": ramo["ha_override"] or personalizzato_acquisto,
    }
