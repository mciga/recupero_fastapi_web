"""Filtri a cascata e motore di calcolo economico (modello v8).

Catena:

  Impianto -> Macrocomponente (MATERIALI con massa in kg, per assieme, da db_macro)
           --[processo: righe materiale -> prodotto / impurità / scarto / intermedio]-->
               Prodotto (venduto), Impurità (massa in piu' in un prodotto, senza ricavo),
               Scarto (con eventuale costo di smaltimento), Intermedio (venduto o lavorato
               con un sottoprocesso, ricorsivamente)

BILANCIO DI MASSA (tre SCENARI: recupero_pct_min / recupero_pct / recupero_pct_max):
  per ogni materiale M e scenario k:   massa_uscita = massa_M x recupero_k
  I recuperi sono usati COSI' COME SONO: la loro somma per materiale NON deve
  fare 1 (sono ricavati dalla stechiometria: un prodotto puo' contenere atomi dei
  reagenti), quindi nessun controllo sulla somma e nessun riscalamento.
  I materiali senza righe nel processo restano "non trattati".

ASSIEMI: di default lo stesso materiale e' sommato su tutti gli assiemi del
macrocomponente. Se il processo ha righe con assieme_dettaglio valorizzato,
la massa di quel materiale in quell'assieme segue quelle righe e il resto le
righe generiche. Inoltre la dashboard puo' separare un assieme in una corsia
a parte (con un proprio processo).

REAGENTI (v9, db_reagenti): una riga "prodotto" con reagente prende dal reagente gli
elementi della formula diversi dall'elemento di confronto, in quantita' stechiometrica
(es. Li2CO3 <- Na2CO3: il CO3). Gli elementi del reagente non usati formano il suo
sale_residuo (Na -> Na2SO4 con il solfato dell'H2SO4); il resto va allo scarto_residuo.
BILANCIO DI MASSA: ingresso + reagenti = prodotti + impurita' + scarti (compresi gli
elementi non attribuiti, che hanno massa) + non trattato; la chiusura e' verificata a
ogni calcolo ("bilancio"). Elementi che non arrivano da materiale o reagente indicato
= "reagenti non specificati"; rese tal quali oltre il disponibile = "massa non bilanciata".

BILANCIO PER ELEMENTO (composizione dei materiali in db_materiali, formula
chimica dei prodotti):
  1. elementi in ingresso = massa x composizione (n.d. = parte non nota);
  2. prodotti con formula: catturano i loro elementi secondo la formula. Per
     l'elemento di confronto, se non basta quello disponibile (anche contando
     la parte n.d.), la massa del prodotto e' ridotta al massimo
     stechiometrico (avviso). Gli altri elementi della formula, se mancano,
     si assumono dai reagenti aggiunti (nessun controllo: es. Na in Na2SO4);
  3. uscite senza formula (rottami, impurità, scarti, intermedi): portano la
     composizione dell'ingresso, nei limiti degli elementi ancora disponibili;
  4. elementi rimasti senza uscita: "non attribuiti" (avviso informativo).
  La composizione calcolata di ogni intermedio si propaga ai sottoprocessi.

Costi: capex/opex (EUR/t di materiale trattato) + smaltimento scarti (EUR/t,
db_scarti), rivalutati all'anno di dismissione. Ricavi: solo sulla massa pura
dei prodotti (non sulle impurità).
"""
from collections import OrderedDict
from sqlalchemy import text
from db import ENGINE, SCHEMA
import chimica

TIPOLOGIE = ["BESS", "EOLICO", "FOTOVOLTAICO"]
ND = "n.d."
NON_DISP = "(composizione non disponibile)"
EPS = 1e-9
SEP = "@@"
COL_REC = ("recupero_pct_min", "recupero_pct", "recupero_pct_max")
NON_ALLOCATO = "Non allocato (somma recuperi < 1)"
NON_ATTRIBUITO = "Elementi non attribuiti (bilancio per elemento)"


def _conn():
    conn = ENGINE.connect()
    conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
    return conn


def _rows(conn, sql, **params):
    return [dict(r._mapping) for r in conn.execute(text(sql), params)]


# ---------------------------------------------------------------- filtri --
def tipologie() -> list[str]:
    with _conn() as conn:
        presenti = {r["tipologia"] for r in _rows(conn, "SELECT DISTINCT tipologia FROM db_impianti")}
    return [t for t in TIPOLOGIE if t in presenti]


def impianti_lista(tipologia: str | None = None) -> list[dict]:
    with _conn() as conn:
        return _rows(conn,
                     "SELECT id_imp, nome, tipologia, sotto_tecnologia, potenza_mw, anno_dismissione, regione "
                     "FROM db_impianti WHERE (CAST(:t AS TEXT) IS NULL OR tipologia = :t) ORDER BY tipologia, nome",
                     t=tipologia)


def _ids(id_imps) -> list[str]:
    """uno o piu' impianti: 'A', ['A', 'B'] o 'A,B' -> ['A', 'B'] (ordine mantenuto, senza doppioni)"""
    if id_imps is None:
        return []
    if isinstance(id_imps, str):
        id_imps = id_imps.split(",")
    return list(OrderedDict.fromkeys(i.strip() for i in id_imps if i and i.strip()))


def _impianto(conn, id_imp: str) -> dict | None:
    r = _impianti(conn, [id_imp])
    return r[0] if r else None


def _impianti(conn, id_imps) -> list[dict]:
    ids = _ids(id_imps)
    r = {x["id_imp"]: x for x in _rows(conn,
                                        "SELECT id_imp, nome, tipologia, sotto_tecnologia, anno_dismissione "
                                        "FROM db_impianti WHERE id_imp = ANY(:i)", i=ids)}
    return [r[i] for i in ids if i in r]


def _righe_macro(conn, id_imps, macro: str) -> list[dict]:
    """righe di db_macro del macrocomponente per uno o piu' impianti (con l'impianto d'origine)"""
    return _rows(conn,
                 "SELECT id_macro AS id_imp, material_id, material, assieme_dettaglio, massa_kg FROM db_macro "
                 "WHERE id_macro = ANY(:i) AND macro_componente=:m AND massa_kg > 0 ORDER BY massa_kg DESC",
                 i=_ids(id_imps), m=macro)


def _filtra_assiemi(righe, assieme, escludi):
    """assieme=None -> tutto il componente tranne gli assiemi in 'escludi';
    assieme valorizzato -> solo quell'assieme."""
    if assieme is not None:
        return [r for r in righe if (r["assieme_dettaglio"] or "") == assieme]
    escl = set(escludi or [])
    return [r for r in righe if (r["assieme_dettaglio"] or "") not in escl]


def _sotto_tecnologie(valore) -> set[str]:
    """'DD_PMG; MS_PMG' -> {'DD_PMG', 'MS_PMG'} (maiuscole/minuscole e spazi indifferenti)"""
    return {v.strip().upper() for v in (valore or "").split(";") if v.strip()}


def _sotto_ok(sotto_proc, sotto_imp):
    """Un processo senza sotto-tecnologia vale per tutti gli impianti; altrimenti per gli
    impianti senza sotto-tecnologia o con una di quelle indicate (piu' valori separati da ';')."""
    proc = _sotto_tecnologie(sotto_proc)
    return not proc or not sotto_imp or sotto_imp.strip().upper() in proc


def processi_disponibili(tipologia: str, macro: str, id_imps=None) -> list[dict]:
    """Processi per (tipologia, macrocomponente). Con uno o piu' impianti, solo quelli
    compatibili con la sotto-tecnologia di TUTTI gli impianti e che trattano almeno
    un materiale presente nel macrocomponente (somma sugli impianti)."""
    with _conn() as conn:
        procs = _rows(conn,
                      "SELECT id_processo, MIN(tecnica) AS tecnica, MIN(sotto_tecnologia) AS sotto_tecnologia, "
                      "MIN(capex_eur_ton) AS capex_eur_ton, MIN(opex_eur_ton) AS opex_eur_ton, "
                      "MIN(descrizione_fasi) AS descrizione_fasi "
                      "FROM db_processi WHERE tipologia=:t AND macro_componente=:m "
                      "GROUP BY id_processo ORDER BY MIN(id)", t=tipologia, m=macro)
        ids = _ids(id_imps)
        if not ids:
            return procs
        imps = _impianti(conn, ids)
        out = []
        for p in procs:
            if not all(_sotto_ok(p["sotto_tecnologia"], i["sotto_tecnologia"]) for i in imps):
                continue
            r = _rows(conn,
                      "SELECT COALESCE(SUM(m.massa_kg),0) AS massa, COUNT(DISTINCT m.material_id) AS n FROM db_macro m "
                      "WHERE m.id_macro = ANY(:i) AND m.macro_componente=:mc AND m.massa_kg > 0 AND m.material_id IN "
                      "(SELECT material_id FROM db_processi WHERE id_processo=:p)",
                      i=ids, mc=macro, p=p["id_processo"])[0]
            if r["n"] > 0:
                p["massa_trattabile_kg"] = float(r["massa"])
                p["n_materiali_trattati"] = r["n"]
                out.append(p)
        return out


def macro_componenti(id_imps) -> list[dict]:
    """Macrocomponenti SELEZIONABILI per uno o piu' impianti della stessa tipologia (almeno
    un materiale con massa e almeno un processo che ne tratti uno), con masse sommate sugli
    impianti, l'elenco degli assiemi e la massa di ogni impianto."""
    ids = _ids(id_imps)
    with _conn() as conn:
        imps = _impianti(conn, ids)
        if not imps or len({i["tipologia"] for i in imps}) > 1:
            return []
        ids = [i["id_imp"] for i in imps]
        comps = _rows(conn,
                      "SELECT macro_componente, SUM(massa_kg) AS massa_kg, COUNT(DISTINCT material_id) AS n_materiali "
                      "FROM db_macro WHERE id_macro = ANY(:i) AND massa_kg > 0 GROUP BY macro_componente "
                      "ORDER BY macro_componente", i=ids)
        assiemi = _rows(conn,
                        "SELECT macro_componente, COALESCE(assieme_dettaglio,'') AS assieme, SUM(massa_kg) AS massa_kg, "
                        "COUNT(DISTINCT material_id) AS n_materiali FROM db_macro WHERE id_macro = ANY(:i) AND massa_kg > 0 "
                        "GROUP BY 1,2 ORDER BY 1, 3 DESC", i=ids)
        per_imp = _rows(conn,
                        "SELECT macro_componente, id_macro AS id_imp, SUM(massa_kg) AS massa_kg FROM db_macro "
                        "WHERE id_macro = ANY(:i) AND massa_kg > 0 GROUP BY 1,2", i=ids)
    nomi = {i["id_imp"]: i["nome"] for i in imps}
    out = []
    for c in comps:
        procs = processi_disponibili(imps[0]["tipologia"], c["macro_componente"], ids)
        if procs:
            ass = [{"assieme": a["assieme"], "massa_kg": float(a["massa_kg"]), "n_materiali": a["n_materiali"]}
                   for a in assiemi if a["macro_componente"] == c["macro_componente"]]
            if len(ass) == 1 and ass[0]["assieme"] == "":
                ass = []
            imp_c = sorted(({"id_imp": r["id_imp"], "nome": nomi.get(r["id_imp"]), "massa_kg": float(r["massa_kg"])}
                            for r in per_imp if r["macro_componente"] == c["macro_componente"]),
                           key=lambda x: -x["massa_kg"])
            out.append({"macro_componente": c["macro_componente"], "massa_kg": float(c["massa_kg"]),
                        "n_materiali": c["n_materiali"], "processi": procs, "assiemi": ass, "impianti": imp_c})
    return out


def sottoprocessi_disponibili(intermedio: str) -> list[dict]:
    with _conn() as conn:
        return _rows(conn,
                     "SELECT id_sottoprocesso, MIN(tecnica) AS tecnica FROM db_sottoprocessi "
                     "WHERE intermedio=:s GROUP BY id_sottoprocesso ORDER BY MIN(id)", s=intermedio)


def prodotti_lista() -> list[dict]:
    with _conn() as conn:
        return _rows(conn, "SELECT prodotto, nome, categoria, prezzo_attuale_eur_kg FROM db_prodotti ORDER BY prodotto")


def intermedi_lista() -> list[dict]:
    with _conn() as conn:
        return _rows(conn, "SELECT intermedio, nome, prezzo_attuale_eur_kg FROM db_intermedi ORDER BY intermedio")


def indici_rivalutazione() -> list[dict]:
    with _conn() as conn:
        return _rows(conn, "SELECT id_indice, nome, tasso_annuo FROM db_indici_rivalutazione ORDER BY id_indice")


def storico_prodotto(prodotto: str) -> list[dict]:
    with _conn() as conn:
        return _rows(conn,
                     "SELECT anno, prezzo_usd_t, produzione_eu_kt, consumo_mondiale_mt, fonte "
                     "FROM db_prodotti_storico WHERE prodotto=:p ORDER BY anno", p=prodotto)


def materiali_componente_dettaglio(id_imps, macro: str, assieme: str | None = None,
                                   escludi: list[str] | None = None) -> list[dict]:
    """Materiali del macrocomponente (sommati su assiemi e impianti) con dettaglio per
    assieme, per impianto e composizione (informativa)."""
    with _conn() as conn:
        nomi = {i["id_imp"]: i["nome"] for i in _impianti(conn, id_imps)}
        righe = _filtra_assiemi(_righe_macro(conn, id_imps, macro), assieme, escludi)
        comps = _composizioni(conn, {r["material_id"] for r in righe})
    out = OrderedDict()
    for r in righe:
        m = out.setdefault(r["material_id"], {"material_id": r["material_id"], "material": r["material"],
                                              "massa_kg": 0.0, "assiemi": [], "impianti": {}})
        kg = float(r["massa_kg"])
        m["massa_kg"] += kg
        m["assiemi"].append({"assieme": r["assieme_dettaglio"] or "", "massa_kg": kg,
                             "id_imp": r["id_imp"], "impianto": nomi.get(r["id_imp"])})
        d = m["impianti"].setdefault(r["id_imp"], {"id_imp": r["id_imp"], "nome": nomi.get(r["id_imp"]), "massa_kg": 0.0})
        d["massa_kg"] += kg
    res = sorted(out.values(), key=lambda x: -x["massa_kg"])
    for m in res:
        m["impianti"] = sorted(m["impianti"].values(), key=lambda x: -x["massa_kg"])
    for m in res:
        c = comps[m["material_id"]]
        m["composizione"] = [{"elemento": e, "frazione_pct": f * 100}
                             for e, f in sorted(c.items(), key=lambda x: -x[1]) if e != ND]
    return res


# ------------------------------------------------------------ utilita' --
def _fattore_rivalutazione(conn, id_indice_costi: str, anni: int) -> tuple[float, float]:
    r = _rows(conn, "SELECT tasso_annuo FROM db_indici_rivalutazione WHERE id_indice=:i", i=id_indice_costi)
    tasso = float(r[0]["tasso_annuo"]) if r else 0.0
    return tasso, (1 + tasso) ** anni


class _Cache:
    """Prodotti, intermedi e scarti letti una volta per calcolo."""

    def __init__(self, conn):
        self.conn = conn
        self.prod, self.inter, self.scarti = {}, {}, None

    def prodotto(self, codice):
        if codice not in self.prod:
            r = _rows(self.conn, "SELECT nome, categoria, prezzo_attuale_eur_kg, formula_chimica, elemento_confronto "
                                 "FROM db_prodotti WHERE prodotto=:p", p=codice)
            info = r[0] if r else {}
            info["comp_formula"] = None
            if info.get("formula_chimica"):
                try:
                    info["comp_formula"] = chimica.composizione(info["formula_chimica"])
                except ValueError:
                    info["comp_formula"] = None
            self.prod[codice] = info
        return self.prod[codice]

    def intermedio(self, codice):
        if codice not in self.inter:
            r = _rows(self.conn, "SELECT nome, prezzo_attuale_eur_kg FROM db_intermedi WHERE intermedio=:s", s=codice)
            self.inter[codice] = r[0] if r else {}
        return self.inter[codice]

    def reagente(self, codice):
        """reagente con composizione dalla formula e destinazione dei suoi residui"""
        if not hasattr(self, "reag"):
            self.reag = {}
        if codice not in self.reag:
            r = _rows(self.conn, "SELECT reagente, nome, formula_chimica, sale_residuo, reagente_sale, scarto_residuo "
                                 "FROM db_reagenti WHERE reagente=:r", r=codice)
            info = r[0] if r else {}
            info["comp"] = None
            if info.get("formula_chimica"):
                try:
                    info["comp"] = chimica.composizione(info["formula_chimica"])
                except ValueError:
                    info["comp"] = None
            self.reag[codice] = info
        return self.reag[codice]

    def costo_scarto(self, nome):
        if self.scarti is None:
            self.scarti = {r["scarto"].lower(): float(r["costo_smaltimento_eur_ton"])
                           for r in _rows(self.conn, "SELECT scarto, costo_smaltimento_eur_ton FROM db_scarti")}
        return self.scarti.get((nome or "").lower(), 0.0)


def _composizioni(conn, material_ids) -> dict[str, dict[str, float]]:
    """material_id -> {elemento: frazione 0..1}; il resto (o tutto, se la
    composizione manca) e' attribuito al pseudo-elemento "n.d."."""
    out = {m: {} for m in material_ids}
    if material_ids:
        for r in _rows(conn, "SELECT material_id, elemento, frazione_pct FROM db_materiali "
                             "WHERE material_id = ANY(:ids) AND frazione_pct IS NOT NULL AND elemento <> :nd",
                       ids=list(material_ids), nd=NON_DISP):
            out[r["material_id"]][r["elemento"]] = float(r["frazione_pct"]) / 100
    for m, comp in out.items():
        tot = sum(comp.values())
        if tot > 1:
            for e in comp:
                comp[e] /= tot
            tot = 1.0
        if 1 - tot > 1e-12:          # anche la parte non nota minima, perche' il bilancio chiuda esatto
            comp[ND] = 1 - tot
    return out


def T(a=0.0, b=None, c=None):
    return [float(a), float(a if b is None else b), float(a if c is None else c)]


def _ord(v3):
    """da tre scenari a (min, centrale, max)"""
    return [min(v3), v3[1], max(v3)]


def _tdict(prefix, t, suffix=""):
    return {f"{prefix}_min{suffix}": t[0], f"{prefix}{suffix}": t[1], f"{prefix}_max{suffix}": t[2]}


def _el_add(dst: dict, src: dict, k: float = 1.0):
    for e, v in src.items():
        dst[e] = dst.get(e, 0.0) + v * k


def _el_lista(el3: list[dict]) -> list[dict]:
    elementi = set().union(*[set(d) for d in el3])
    out = []
    for e in elementi:
        v = _ord([d.get(e, 0.0) for d in el3])
        if v[2] > 1e-9:
            out.append({"elemento": e, **_tdict("massa_kg", v)})
    out.sort(key=lambda x: (x["elemento"] == ND, -x["massa_kg"]))
    return out


def _norm_tipo(righe):
    """tipo_output dal database: "impurita" (anche se scritto con accento o
    con l'accento corrotto da una codifica sbagliata, es. "impuritÃ ")."""
    for r in righe:
        t = (r.get("tipo_output") or "").strip().lower()
        r["tipo_output"] = "impurita" if t.startswith("impur") else t
    return righe


def _key_uscita(r):
    if r["tipo_output"] == "scarto":
        return ("scarto", r["scarto"])
    if r["tipo_output"] == "intermedio":
        return ("intermedio", r["intermedio_output"])
    # prodotto o impurità: il codice e' quello del prodotto (o dell'intermedio) che le riceve
    if r.get("prodotto"):
        return ("prodotto", r["prodotto"])
    return ("intermedio", r["intermedio_output"])


# ------------------------------------------------- bilancio massa + elementi --
REAG_ING = "(reagenti)"
NON_SPECIFICATI = "(reagenti non specificati)"


def _bilancio(cache: _Cache, righe: list[dict], ingressi: "OrderedDict[str, dict]"):
    """Applica le righe di un processo/sottoprocesso agli ingressi (vedi docstring
    del modulo). Ritorna (uscite, scarti, trattati, avvisi, reagenti).

    REAGENTI (v9). Una riga "prodotto" con reagente prende dal reagente gli elementi
    della propria formula diversi dall'elemento di confronto, in quantita'
    stechiometrica: massa reagente = max_e (elemento richiesto_e / frazione_e nel reagente).
    Gli elementi del reagente non usati (es. il Na del Na2CO3) formano il sale_residuo
    del reagente (Na2SO4), con gli elementi mancanti presi dal reagente_sale (H2SO4); cio'
    che avanza va allo scarto_residuo. Gli elementi di una formula che non arrivano ne'
    dal materiale ne' da un reagente indicato sono "reagenti non specificati".
    Il risultato chiude: ingresso + reagenti = uscite (vedi "bilancio")."""
    _norm_tipo(righe)
    per_ingresso: "OrderedDict[str, list[dict]]" = OrderedDict()
    for r in righe:
        if r["chiave_ingresso"] in ingressi:
            per_ingresso.setdefault(r["chiave_ingresso"], []).append(r)

    uscite: "OrderedDict[tuple, dict]" = OrderedDict()
    scarti: "OrderedDict[str, dict]" = OrderedDict()
    avvisi = []
    # reagenti consumati: codice -> massa, elementi, uso per prodotto (3 scenari)
    reag: "OrderedDict[str, dict]" = OrderedDict()
    residui = {}                                    # codice reagente -> [3 dict elemento -> kg] non usati
    non_spec = [{}, {}, {}]                         # elementi da reagenti non specificati
    sbilancio = [0.0, 0.0, 0.0]                     # massa di uscite "tal quali" senza elementi disponibili

    def _reag(codice):
        return reag.setdefault(codice, {"massa": [0.0] * 3, "el": [{}, {}, {}], "uso": {}})

    def _uscita(key):
        return uscite.setdefault(key, {
            "massa": [0.0] * 3, "impurita": [0.0] * 3, "el": [{}, {}, {}], "el_imp": [{}, {}, {}],
            "da_reagenti": [{}, {}, {}], "contributi": [], "impurita_da": [], "avvisi": []})

    def _scarto(nome, speciale=None):
        return scarti.setdefault(nome, {"massa": [0.0] * 3, "el": [{}, {}, {}], "materiali": {}, "speciale": speciale})

    for chiave, rr in per_ingresso.items():
        ing = ingressi[chiave]
        comp = ing["comp"]
        info_righe = []
        for r in rr:
            info = cache.prodotto(r["prodotto"]) if (r["tipo_output"] == "prodotto" and r.get("prodotto")) else {}
            info_righe.append(info)
        mat_scarti = {}   # nome scarto -> {"massa": [3], "el": [3 dict]}
        mat_imp = {}      # key uscita -> {"massa": [3], "el": [3 dict]}

        for k in range(3):
            m = ing["massa"][k]
            # recuperi usati cosi' come sono (nessun controllo sulla somma, nessun riscalamento)
            rec = [float(r[COL_REC[k]] or 0) for r in rr]
            out = [m * x for x in rec]
            dispon = {e: m * f for e, f in comp.items()}
            nd_pool = dispon.pop(ND, 0.0)
            el_righe = [dict() for _ in rr]
            asis = []
            # --- prodotti con formula
            for i, r in enumerate(rr):
                info = info_righe[i]
                cf = info.get("comp_formula")
                if r["tipo_output"] != "prodotto" or not cf:
                    asis.append(i)
                    continue
                e_conf = info.get("elemento_confronto")
                if e_conf and e_conf in cf and out[i] > 0:
                    rich = out[i] * cf[e_conf]
                    noto = min(rich, dispon.get(e_conf, 0.0))
                    da_nd = min(rich - noto, nd_pool)
                    preso = noto + da_nd
                    scala = preso / rich if rich > EPS else 1.0
                    if scala < 1 - 1e-9:
                        cont = comp.get(e_conf, 0.0)
                        _uscita(_key_uscita(r))["avvisi"].append({
                            "tipo": "resa_limitata", "scenario": ("min", "centrale", "max")[k],
                            "ingresso": chiave, "nome": ing["nome"], "elemento": e_conf,
                            "resa_richiesta": rec[i], "resa_effettiva": rec[i] * scala,
                            "contenuto_elemento_pct": cont * 100,
                            "resa_max_stechiometrica": (cont + comp.get(ND, 0.0)) / cf[e_conf],
                            "massa_richiesta_kg": out[i], "massa_kg": out[i] * scala})
                    elif da_nd > 1e-9 and k == 1:
                        _uscita(_key_uscita(r))["avvisi"].append({
                            "tipo": "non_verificabile", "ingresso": chiave, "nome": ing["nome"], "elemento": e_conf,
                            "contenuto_elemento_pct": comp.get(e_conf, 0.0) * 100,
                            "quota_nd_pct": comp.get(ND, 0.0) * 100})
                    out[i] *= scala
                    dispon[e_conf] = dispon.get(e_conf, 0.0) - noto
                    nd_pool -= da_nd
                    el_righe[i][e_conf] = preso
                # --- reagente indicato: fornisce gli elementi della formula che contiene
                ri = cache.reagente(r["reagente"]) if r.get("reagente") else None
                rc = (ri or {}).get("comp") or {}
                dal_reag = {e: out[i] * f for e, f in cf.items() if e != e_conf and e in rc}
                if dal_reag and out[i] > 0:
                    n = max(v / rc[e] for e, v in dal_reag.items())          # kg di reagente
                    rg = _reag(r["reagente"])
                    rg["massa"][k] += n
                    _el_add(rg["el"][k], rc, n)
                    uso = rg["uso"].setdefault(r["prodotto"], [0.0] * 3)
                    uso[k] += n
                    res = residui.setdefault(r["reagente"], [{}, {}, {}])[k]
                    for e, f in rc.items():
                        avanzo = n * f - dal_reag.get(e, 0.0)
                        if avanzo > 1e-12:
                            res[e] = res.get(e, 0.0) + avanzo
                    u = _uscita(_key_uscita(r))
                    u.setdefault("reagenti", set()).add(r["reagente"])
                    _el_add(u["da_reagenti"][k], dal_reag)
                    for e, v in dal_reag.items():
                        el_righe[i][e] = el_righe[i].get(e, 0.0) + v
                for e, f in cf.items():
                    if e == e_conf or e in dal_reag:
                        continue
                    vuole = out[i] * f
                    preso = min(vuole, dispon.get(e, 0.0))
                    dispon[e] = dispon.get(e, 0.0) - preso
                    if preso > 0:
                        el_righe[i][e] = el_righe[i].get(e, 0.0) + preso
                    if vuole - preso > 1e-9:  # da reagenti non specificati
                        _el_add(_uscita(_key_uscita(r))["da_reagenti"][k], {e: vuole - preso})
                        _el_add(non_spec[k], {e: vuole - preso})
                        el_righe[i][e] = el_righe[i].get(e, 0.0) + (vuole - preso)
            # --- uscite senza formula (impurita', scarti, intermedi, prodotti senza formula):
            #     portano via QUELLO CHE RESTA del materiale dopo i prodotti con formula, in
            #     proporzione alla loro massa (stessa composizione del residuo)
            pool = {e: v for e, v in dispon.items() if v > 0}
            if nd_pool > 0:
                pool[ND] = nd_pool
            if asis:
                p_tot = sum(pool.values())
                a_tot = sum(out[i] for i in asis)
                base = max(a_tot, p_tot)
                if base > EPS:
                    for e in list(pool):
                        v = pool[e]
                        for i in asis:
                            el_righe[i][e] = el_righe[i].get(e, 0.0) + v * out[i] / base
                        pool[e] = v * (1 - a_tot / base)
                # massa delle uscite tal quali che il materiale non riesce a coprire (rese oltre il disponibile)
                if a_tot > p_tot + 1e-9:
                    sbilancio[k] += a_tot - p_tot
            # --- elementi rimasti senza uscita: hanno massa (il bilancio deve chiudere)
            resto = {e: v for e, v in pool.items() if v > 1e-9}
            if resto:
                s = mat_scarti.setdefault(NON_ATTRIBUITO, {"massa": [0.0] * 3, "el": [{}, {}, {}]})
                _el_add(s["el"][k], resto)
                s["massa"][k] += sum(resto.values())
            # --- registra le uscite
            for i, r in enumerate(rr):
                t = r["tipo_output"]
                if t == "scarto":
                    s = mat_scarti.setdefault(r["scarto"], {"massa": [0.0] * 3, "el": [{}, {}, {}]})
                    s["massa"][k] += out[i]
                    _el_add(s["el"][k], el_righe[i])
                    continue
                key = _key_uscita(r)
                u = _uscita(key)
                if t == "impurita":
                    u["impurita"][k] += out[i]
                    _el_add(u["el_imp"][k], el_righe[i])
                    mi = mat_imp.setdefault(key, {"massa": [0.0] * 3, "el": [{}, {}, {}]})
                    mi["massa"][k] += out[i]
                    _el_add(mi["el"][k], el_righe[i])
                else:
                    u["massa"][k] += out[i]
                    _el_add(u["el"][k], el_righe[i])
                    if k == 1:
                        u["contributi"].append({"ingresso": chiave, "nome": ing["nome"], "massa_ingresso_kg": m,
                                                "recupero_min": float(r[COL_REC[0]] or 0),
                                                "recupero": float(r[COL_REC[1]] or 0),
                                                "recupero_max": float(r[COL_REC[2]] or 0), "massa_kg": out[i]})
        # --- per materiale: scarti e impurità
        for nome, v in mat_scarti.items():
            spec = "non_allocato" if nome == NON_ALLOCATO else ("non_attribuito" if nome == NON_ATTRIBUITO else None)
            s = _scarto(nome, spec)
            for k in range(3):
                s["massa"][k] += v["massa"][k]
                _el_add(s["el"][k], v["el"][k])
            s["materiali"][chiave] = {"ingresso": chiave, "nome": ing["nome"], "massa_kg": v["massa"][1],
                                      "pct": v["massa"][1] / ing["massa"][1] if ing["massa"][1] else 0,
                                      "elementi": _el_lista(v["el"])}
            if spec == "non_allocato":
                avvisi.append({"tipo": "non_allocato", "ingresso": chiave, "nome": ing["nome"],
                               "massa_kg": v["massa"][1]})
        for key, v in mat_imp.items():
            _uscita(key)["impurita_da"].append({"ingresso": chiave, "nome": ing["nome"], "massa_kg": v["massa"][1],
                                                "pct": v["massa"][1] / ing["massa"][1] if ing["massa"][1] else 0,
                                                "elementi": _el_lista(v["el"])})

    # ------------------------------------------------ residui dei reagenti -> sale e scarto
    def _a_scarto(nome, el3, origine):
        nome = nome or NON_ATTRIBUITO
        spec = "non_attribuito" if nome == NON_ATTRIBUITO else None
        s = _scarto(nome, spec)
        for k in range(3):
            s["massa"][k] += sum(el3[k].values())
            _el_add(s["el"][k], el3[k])
        prev = s["materiali"].get(REAG_ING, {"massa_kg": 0.0})
        s["materiali"][REAG_ING] = {"ingresso": REAG_ING, "nome": f"residui dei reagenti ({origine})",
                                    "massa_kg": prev["massa_kg"] + sum(el3[1].values()), "pct": 0,
                                    "elementi": _el_lista(el3)}

    gruppi = OrderedDict()       # (sale, reagente_sale, scarto) -> {"pool": [3 dict], "da": set()}
    for codice, el3 in residui.items():
        ri = cache.reagente(codice)
        g = gruppi.setdefault((ri.get("sale_residuo"), ri.get("reagente_sale"), ri.get("scarto_residuo")),
                              {"pool": [{}, {}, {}], "da": []})
        g["da"].append(codice)
        for k in range(3):
            _el_add(g["pool"][k], el3[k])
    for (sale, rsale, sc), g in gruppi.items():
        origine = ", ".join(g["da"])
        info = cache.prodotto(sale) if sale else {}
        cs = info.get("comp_formula") or {}
        r2 = cache.reagente(rsale) if rsale else {}
        c2 = r2.get("comp") or {}
        avanzi = [{}, {}, {}]
        avanzi_r2 = [{}, {}, {}]
        for k in range(3):
            pool = dict(g["pool"][k])
            limitanti = [e for e in cs if pool.get(e, 0) > EPS and e not in c2]
            q = min(pool[e] / cs[e] for e in limitanti) if (cs and limitanti) else 0.0   # kg di sale
            if q > EPS:
                el_sale = {}
                deficit = {}
                for e, f in cs.items():
                    serve = q * f
                    da_pool = min(serve, pool.get(e, 0.0))
                    pool[e] = pool.get(e, 0.0) - da_pool
                    el_sale[e] = serve
                    if serve - da_pool > 1e-12:
                        deficit[e] = serve - da_pool
                dal_r2 = {e: v for e, v in deficit.items() if e in c2}
                if dal_r2:
                    n2 = max(v / c2[e] for e, v in dal_r2.items())
                    rg = _reag(rsale)
                    rg["massa"][k] += n2
                    _el_add(rg["el"][k], c2, n2)
                    rg["uso"].setdefault(sale, [0.0] * 3)[k] += n2
                    for e, f in c2.items():
                        avanzo = n2 * f - dal_r2.get(e, 0.0)
                        if avanzo > 1e-12:
                            avanzi_r2[k][e] = avanzi_r2[k].get(e, 0.0) + avanzo
                altro = {e: v for e, v in deficit.items() if e not in c2}
                if altro:
                    _el_add(non_spec[k], altro)
                u = _uscita(("prodotto", sale))
                u["massa"][k] += q
                _el_add(u["el"][k], el_sale)
                _el_add(u["da_reagenti"][k], el_sale)
                u.setdefault("reagenti", set()).update(g["da"] + ([rsale] if dal_r2 else []))
                if k == 1:
                    u["contributi"].append({"ingresso": REAG_ING, "nome": f"residui dei reagenti ({origine})",
                                            "massa_ingresso_kg": 0.0, "recupero_min": 0.0, "recupero": 0.0,
                                            "recupero_max": 0.0, "massa_kg": q})
            for e, v in pool.items():
                if v > 1e-12:
                    avanzi[k][e] = avanzi[k].get(e, 0.0) + v
        if any(avanzi[k] for k in range(3)):
            _a_scarto(sc, avanzi, origine)
        if any(avanzi_r2[k] for k in range(3)):
            _a_scarto(r2.get("scarto_residuo") or sc, avanzi_r2, rsale)
    if any(non_spec[k] for k in range(3)):
        r_ns = _reag(NON_SPECIFICATI)
        for k in range(3):
            r_ns["massa"][k] += sum(non_spec[k].values())
            _el_add(r_ns["el"][k], non_spec[k])
    for u in uscite.values():
        u["reagenti"] = sorted(u.get("reagenti", set()))
    return uscite, scarti, set(per_ingresso), avvisi, {"reagenti": reag, "sbilancio": sbilancio}


def _reagenti_lista(cache, info) -> list[dict]:
    out = []
    for codice, v in info["reagenti"].items():
        ri = cache.reagente(codice) if codice != NON_SPECIFICATI else {}
        out.append({"reagente": codice, "nome": ri.get("nome") or "elementi da reagenti non specificati",
                    "formula_chimica": ri.get("formula_chimica"), "specificato": codice != NON_SPECIFICATI,
                    **_tdict("massa_kg", _ord(v["massa"])), "elementi": _el_lista(v["el"]),
                    "uso": [{"prodotto": p, **_tdict("massa_kg", _ord(m))} for p, m in v["uso"].items()]})
    out.sort(key=lambda x: (not x["specificato"], -x["massa_kg"]))
    return out


def _bilancio_massa(ingresso3, uscite, scarti, reag_info, non_trattato_kg=0.0) -> dict:
    """Chiusura del bilancio di massa per scenario (valori grezzi, non riordinati):
    ingresso + reagenti + reagenti non specificati + massa non bilanciata = uscite.
    uscite = prodotti + impurita' + intermedi + scarti (anche elementi non attribuiti) + non trattato."""
    per = []
    for k in range(3):
        usc = (sum(u["massa"][k] + u["impurita"][k] for u in uscite.values())
               + sum(s["massa"][k] for s in scarti.values()) + non_trattato_kg)
        reag_k = sum(v["massa"][k] for c, v in reag_info["reagenti"].items() if c != NON_SPECIFICATI)
        ns_k = sum(v["massa"][k] for c, v in reag_info["reagenti"].items() if c == NON_SPECIFICATI)
        sb_k = reag_info["sbilancio"][k]
        ing = ingresso3[k] + non_trattato_kg
        per.append({"ingresso_kg": ing, "reagenti_kg": reag_k, "reagenti_non_specificati_kg": ns_k,
                    "massa_non_bilanciata_kg": sb_k, "uscite_kg": usc,
                    "chiusura_kg": usc - (ing + reag_k + ns_k + sb_k)})
    chiude = all(abs(p["chiusura_kg"]) <= 1e-6 * max(1.0, p["uscite_kg"]) for p in per)
    completo = all(p["reagenti_non_specificati_kg"] <= 1e-6 * max(1.0, p["uscite_kg"]) and
                   p["massa_non_bilanciata_kg"] <= 1e-6 * max(1.0, p["uscite_kg"]) for p in per)
    return {"min": per[0], "centrale": per[1], "max": per[2], "chiude": chiude,
            "solo_reagenti_indicati": completo}


def _composizione_da_elementi(el: dict, massa: float) -> dict:
    if massa <= EPS or not el:
        return {ND: 1.0}
    tot = sum(el.values())
    comp = {e: v / massa for e, v in el.items() if v > 0}
    if tot < massa * (1 - 1e-9):
        comp[ND] = comp.get(ND, 0.0) + (massa - tot) / massa
    s = sum(comp.values())
    return {e: v / s for e, v in comp.items()} if s > 1 else comp


def _comp_lista(comp):
    return [{"elemento": e, "frazione": f} for e, f in sorted(comp.items(), key=lambda x: (x[0] == ND, -x[1]))]


def _fattore_pesato(voci, fattori_ingresso, default):
    """fattore di rivalutazione medio di un'uscita, pesato sulle masse che le arrivano dai
    singoli ingressi (ognuno con il fattore dei propri impianti)"""
    if not fattori_ingresso:
        return default
    num = den = 0.0
    for v in voci:
        num += v["massa_kg"] * fattori_ingresso.get(v["ingresso"], default)
        den += v["massa_kg"]
    return num / den if den > EPS else default


def _capex_taglia(riga: dict, taglia_t_anno, massa_t: float, fattore: float, anno_costruzione=None) -> dict:
    """Capex dipendente dalla taglia dell'impianto (v9.1).
    capex_eur_ton = capex specifico in EUR per t/anno di capacita'.
      capex impianto = capex_eur_ton x taglia                              (lineare)
                     = capex_eur_ton x taglia_rif x (taglia/taglia_rif)^esp (regola dello 0,6, se c'e' taglia_rif)
      tempo          = massa trattata / taglia (anni)
      capex attribuito al materiale = capex impianto x tempo / vita utile (quota d'uso)
    Senza taglia indicata si propone l'impianto che tratta la massa in 1 anno.
    fattore: rivalutazione all'anno di costruzione dell'impianto (uguale per tutto il gruppo:
    il costo dell'impianto non dipende da quali impianti lo alimentano)."""
    spec = float(riga.get("capex_eur_ton") or 0)
    rif = float(riga["taglia_riferimento_t_anno"]) if riga.get("taglia_riferimento_t_anno") else None
    esp = float(riga.get("esponente_scala") or 0.6)
    vita = float(riga.get("vita_utile_anni") or 15)
    proposta = massa_t if massa_t > EPS else 1.0
    impostata = bool(taglia_t_anno and float(taglia_t_anno) > 0)
    taglia = float(taglia_t_anno) if impostata else proposta
    base = spec * rif * (taglia / rif) ** esp if rif else spec * taglia
    impianto = base * fattore
    tempo = massa_t / taglia if taglia > EPS else 0.0
    quota = tempo / vita
    return {"taglia_t_anno": taglia, "taglia_proposta_t_anno": proposta, "taglia_impostata": impostata,
            "taglia_riferimento_t_anno": rif, "esponente_scala": esp, "regola_scala": "0,6" if rif else "lineare",
            "tempo_anni": tempo, "vita_utile_anni": vita, "quota_uso": quota,
            "anno_costruzione": anno_costruzione, "fattore_capex": fattore,
            "capex_impianto_eur": impianto, "capex_eur": impianto * quota}


def _valorizza_uscite(cache, uscite, prezzi_prodotti_override, prezzi_intermedi_override,
                      figli_scelte, fattore_rivalutazione, fattori_ingresso=None, tempo_anni=1.0,
                      capex_anno=None):
    lista = []
    ricavo = T()
    costo_extra = 0.0
    ha_override = False
    for (tipo, codice), u in uscite.items():
        massa = _ord(u["massa"])
        imp = _ord(u["impurita"])
        comp = _composizione_da_elementi(u["el"][1], u["massa"][1])
        base = {"tipo": tipo, "codice": codice,
                **_tdict("massa_kg", massa), **_tdict("impurita_kg", imp),
                "massa_totale_kg": massa[1] + imp[1],
                "elementi": _el_lista(u["el"]), "elementi_impurita": _el_lista(u["el_imp"]),
                "elementi_da_reagenti": _el_lista(u["da_reagenti"]), "reagenti": u.get("reagenti", []),
                "composizione": _comp_lista(comp), "avvisi": u["avvisi"],
                "contributi": u["contributi"], "impurita_da": u["impurita_da"]}
        if tipo == "prodotto":
            info = cache.prodotto(codice)
            default = float(info.get("prezzo_attuale_eur_kg") or 0)
            ov = (prezzi_prodotti_override or {}).get(codice)
            prezzo = float(ov) if ov is not None else default
            ha_override |= ov is not None
            r = [x * prezzo for x in massa]
            ricavo = [a + b for a, b in zip(ricavo, r)]
            lista.append({**base, "nome": info.get("nome"), "categoria": info.get("categoria"),
                          "formula_chimica": info.get("formula_chimica"),
                          "prezzo_default_eur_kg": default, "prezzo_eur_kg": prezzo,
                          "prezzo_personalizzato": ov is not None, **_tdict("ricavo_eur", r), "ramo": None})
            continue
        info = cache.intermedio(codice)
        default = float(info.get("prezzo_attuale_eur_kg") or 0)
        scelta = (figli_scelte or {}).get(codice) or {}
        id_sub = scelta.get("id_sottoprocesso")
        if id_sub:
            f_ramo = _fattore_pesato(u["contributi"] + u["impurita_da"], fattori_ingresso, fattore_rivalutazione)
            ramo = calcola_ramo_sottoprocesso(cache, codice, massa, comp, id_sub, f_ramo,
                                              prezzi_prodotti_override, prezzi_intermedi_override, scelta.get("figli"),
                                              tempo_anni, capex_anno)
            if "error" in ramo:
                raise ValueError(ramo["error"])
            costo_extra += ramo["costo_eur"]
            ricavo = [a + b for a, b in zip(ricavo, [ramo["ricavo_eur_min"], ramo["ricavo_eur"], ramo["ricavo_eur_max"]])]
            ha_override |= ramo["ha_override"]
            lista.append({**base, "nome": info.get("nome"), "categoria": None, "trasformato": True, "ramo": ramo,
                          "prezzo_default_eur_kg": default, "prezzo_eur_kg": None, "prezzo_personalizzato": False,
                          "ricavo_eur_min": ramo["ricavo_eur_min"], "ricavo_eur": ramo["ricavo_eur"],
                          "ricavo_eur_max": ramo["ricavo_eur_max"]})
        else:
            ov = (prezzi_intermedi_override or {}).get(codice)
            prezzo = float(ov) if ov is not None else default
            ha_override |= ov is not None
            r = [x * prezzo for x in massa]
            ricavo = [a + b for a, b in zip(ricavo, r)]
            lista.append({**base, "nome": info.get("nome"), "categoria": None, "trasformato": False, "ramo": None,
                          "prezzo_default_eur_kg": default, "prezzo_eur_kg": prezzo,
                          "prezzo_personalizzato": ov is not None, **_tdict("ricavo_eur", r)})
    return lista, ricavo, costo_extra, ha_override


def _scarti_lista(cache, scarti, fattore, fattori_ingresso=None):
    out = []
    costo = 0.0
    for nome, v in scarti.items():
        massa = _ord(v["massa"])
        c_ton = 0.0 if v["speciale"] else cache.costo_scarto(nome)
        f = _fattore_pesato(list(v["materiali"].values()), fattori_ingresso, fattore)
        c = massa[1] / 1000 * c_ton * f
        costo += c
        out.append({"scarto": nome, "speciale": v["speciale"], **_tdict("massa_kg", massa),
                    "elementi": _el_lista(v["el"]), "materiali": list(v["materiali"].values()),
                    "costo_smaltimento_eur_ton": c_ton, "costo_smaltimento_eur": c})
    order = {None: 0, "non_allocato": 1, "non_attribuito": 2}
    out.sort(key=lambda x: (order[x["speciale"]], -x["massa_kg"]))
    return out, costo


def calcola_ramo_sottoprocesso(cache: _Cache, intermedio: str, massa_in: list, comp_in: dict,
                               id_sottoprocesso: str | None, fattore_rivalutazione: float,
                               prezzi_prodotti_override: dict | None, prezzi_intermedi_override: dict | None,
                               figli_scelte: dict | None, tempo_anni: float = 1.0,
                               capex_anno: tuple | None = None) -> dict:
    """tempo_anni: tempo in cui arriva l'intermedio (quello dell'impianto a monte): il
    sottoprocesso e' dimensionato per trattarlo nello stesso tempo.
    capex_anno: (anno di costruzione, fattore) dell'impianto a monte, usato anche qui;
    senza, il capex e' rivalutato come gli opex."""
    righe = _rows(cache.conn, "SELECT * FROM db_sottoprocessi WHERE id_sottoprocesso=:i ORDER BY id", i=id_sottoprocesso)
    if not righe:
        return {"error": f"sottoprocesso_non_trovato: {id_sottoprocesso}"}
    if righe[0]["intermedio"] != intermedio:
        return {"error": f"il sottoprocesso {id_sottoprocesso} non lavora l'intermedio {intermedio}"}
    for r in righe:
        r["chiave_ingresso"] = intermedio
    info = cache.intermedio(intermedio)
    ingressi = OrderedDict([(intermedio, {"nome": info.get("nome") or intermedio, "massa": massa_in, "comp": comp_in})])
    uscite, scarti, _, avvisi, reag_info = _bilancio(cache, righe, ingressi)
    bil = _bilancio_massa(massa_in, uscite, scarti, reag_info)
    ton = massa_in[1] / 1000
    tempo = tempo_anni if tempo_anni and tempo_anni > EPS else 1.0
    anno_c, f_capex = capex_anno if capex_anno else (None, fattore_rivalutazione)
    cx = _capex_taglia(righe[0], ton / tempo if ton > EPS else None, ton, f_capex, anno_c)
    capex = cx["capex_eur"]
    opex = float(righe[0]["opex_eur_ton"]) * ton * fattore_rivalutazione
    lista, ricavo, costo_extra, ha_override = _valorizza_uscite(
        cache, uscite, prezzi_prodotti_override, prezzi_intermedi_override, figli_scelte, fattore_rivalutazione,
        tempo_anni=tempo, capex_anno=capex_anno)
    scarti_l, costo_sm = _scarti_lista(cache, scarti, fattore_rivalutazione)
    return {
        "input": intermedio, **_tdict("massa_input_kg", massa_in), "composizione_input": _comp_lista(comp_in),
        "sottoprocesso": {"id_sottoprocesso": id_sottoprocesso, "tecnica": righe[0]["tecnica"],
                          "capex_eur_ton": float(righe[0]["capex_eur_ton"]),
                          "opex_eur_ton": float(righe[0]["opex_eur_ton"]),
                          "descrizione_fasi": righe[0]["descrizione_fasi"], **cx,
                          "capex_eur": capex, "opex_eur": opex, "smaltimento_eur": costo_sm,
                          "costo_eur": capex + opex + costo_sm},
        "uscite": lista, "scarti": scarti_l, "avvisi": avvisi,
        "reagenti": _reagenti_lista(cache, reag_info), "bilancio": bil,
        "costo_eur": capex + opex + costo_sm + costo_extra,
        **_tdict("ricavo_eur", ricavo), "ha_override": ha_override,
    }


def calcola_componente(cache: _Cache, imps, macro: str, id_processo: str,
                       fattori_impianto, prezzi_prodotti_override: dict | None = None,
                       prezzi_intermedi_override: dict | None = None, figli_processo: dict | None = None,
                       assieme: str | None = None, escludi_assiemi: list[str] | None = None,
                       taglia_t_anno: float | None = None, capex_anno: tuple | None = None) -> dict:
    """Applica un processo al macrocomponente di uno o piu' impianti: le masse dello stesso
    materiale sono SOMMATE sugli impianti (e sugli assiemi) e il processo lavora sul totale.
    fattori_impianto: {id_imp: fattore di rivalutazione dei costi} (o un solo numero). Ogni
    materiale porta il fattore medio dei suoi impianti, pesato sulle masse: capex, opex e
    smaltimento risultano uguali alla somma dei costi dei singoli impianti, ciascuno
    rivalutato al proprio anno di dismissione."""
    conn = cache.conn
    if isinstance(imps, dict):
        imps = [imps]
    if not isinstance(fattori_impianto, dict):
        fattori_impianto = {i["id_imp"]: float(fattori_impianto) for i in imps}
    imp = imps[0]
    etichetta = {"macro_componente": macro, "assieme": assieme, "escludi_assiemi": escludi_assiemi or []}
    righe_m = _filtra_assiemi(_righe_macro(conn, [i["id_imp"] for i in imps], macro), assieme, escludi_assiemi)
    righe = _rows(conn, "SELECT * FROM db_processi WHERE id_processo=:p ORDER BY id", p=id_processo)
    if not righe:
        return {**etichetta, "error": f"processo_non_trovato: {id_processo}"}
    if righe[0]["tipologia"] != imp["tipologia"] or righe[0]["macro_componente"] != macro:
        return {**etichetta, "error": f"il processo {id_processo} non si applica a {macro}"}
    fuori = [i["nome"] for i in imps if not _sotto_ok(righe[0]["sotto_tecnologia"], i["sotto_tecnologia"])]
    if fuori:
        return {**etichetta, "error": f"il processo {id_processo} e' per la sotto-tecnologia {righe[0]['sotto_tecnologia']} "
                                      f"(non compatibili: {', '.join(fuori)})"}

    # righe specifiche per assieme: (material_id, assieme) -> chiave separata
    specifiche = {(r["material_id"], r["assieme_dettaglio"]) for r in righe if r.get("assieme_dettaglio")}
    for r in righe:
        r["chiave_ingresso"] = (r["material_id"] + SEP + r["assieme_dettaglio"]) if r.get("assieme_dettaglio") \
            else r["material_id"]
    comps = _composizioni(conn, {r["material_id"] for r in righe_m})
    ingressi: "OrderedDict[str, dict]" = OrderedDict()
    for r in righe_m:
        a = r["assieme_dettaglio"] or ""
        if (r["material_id"], a) in specifiche:
            key, nome = r["material_id"] + SEP + a, f"{r['material']} [{a}]"
        else:
            key, nome = r["material_id"], r["material"]
        ing = ingressi.setdefault(key, {"nome": nome, "material_id": r["material_id"], "massa": T(),
                                        "comp": comps[r["material_id"]], "assiemi": [], "impianti": {}})
        ing["massa"] = [x + float(r["massa_kg"]) for x in ing["massa"]]
        ing["assiemi"].append({"assieme": a, "massa_kg": float(r["massa_kg"])})
        ing["impianti"][r["id_imp"]] = ing["impianti"].get(r["id_imp"], 0.0) + float(r["massa_kg"])
    massa_comp = sum(float(r["massa_kg"]) for r in righe_m)
    # fattore di rivalutazione di ogni ingresso, pesato sulle masse dei suoi impianti
    fattori = {k: (sum(kg * fattori_impianto.get(i, 1.0) for i, kg in ing["impianti"].items()) / ing["massa"][1]
                   if ing["massa"][1] > EPS else 1.0) for k, ing in ingressi.items()}

    uscite, scarti, trattati, avvisi, reag_info = _bilancio(cache, righe, ingressi)
    massa_trattata = sum(ingressi[k]["massa"][1] for k in trattati)
    massa_x_fattore = sum(ingressi[k]["massa"][1] * fattori[k] for k in trattati)
    fattore_medio = massa_x_fattore / massa_trattata if massa_trattata > EPS else \
        (sum(fattori_impianto.values()) / len(fattori_impianto) if fattori_impianto else 1.0)
    non_trattati, el_nt = [], {}
    for key, ing in ingressi.items():
        if key in trattati:
            continue
        el = {e: ing["massa"][1] * f for e, f in ing["comp"].items()}
        _el_add(el_nt, el)
        non_trattati.append({"material_id": ing["material_id"], "material": ing["nome"], "massa_kg": ing["massa"][1],
                             "elementi": _el_lista([el, el, el])})

    # capex: impianto della taglia scelta, quota d'uso attribuita al materiale (v9.1); opex: EUR/t trattata
    # il capex dell'impianto e' rivalutato all'anno di costruzione (uguale per tutto il gruppo);
    # gli opex all'anno di dismissione di ogni impianto
    anno_c, f_capex = capex_anno if capex_anno else (None, fattore_medio)
    cx = _capex_taglia(righe[0], taglia_t_anno, massa_trattata / 1000, f_capex, anno_c)
    capex = cx["capex_eur"]
    opex = float(righe[0]["opex_eur_ton"]) * massa_x_fattore / 1000
    lista, ricavo, costo_extra, ha_override = _valorizza_uscite(
        cache, uscite, prezzi_prodotti_override, prezzi_intermedi_override, figli_processo, fattore_medio, fattori,
        tempo_anni=cx["tempo_anni"] or 1.0, capex_anno=capex_anno)
    scarti_l, costo_sm = _scarti_lista(cache, scarti, fattore_medio, fattori)

    massa_nt = sum(n["massa_kg"] for n in non_trattati)
    tratt3 = [sum(ingressi[k]["massa"][j] for k in trattati) for j in range(3)]
    bil = _bilancio_massa(tratt3, uscite, scarti, reag_info, massa_nt)
    bilancio_c = bil["centrale"]["uscite_kg"]
    nomi = {i["id_imp"]: i["nome"] for i in imps}
    per_imp = {}
    for r in righe_m:
        per_imp[r["id_imp"]] = per_imp.get(r["id_imp"], 0.0) + float(r["massa_kg"])
    return {
        **etichetta, "massa_componente_kg": massa_comp, "massa_trattata_kg": massa_trattata,
        "n_materiali": len({r["material_id"] for r in righe_m}),
        "fattore_rivalutazione_medio": fattore_medio,
        "impianti": [{"id_imp": i, "nome": nomi.get(i), "massa_kg": kg}
                     for i, kg in sorted(per_imp.items(), key=lambda x: -x[1])],
        "processo": {"id_processo": id_processo, "tecnica": righe[0]["tecnica"],
                     "sotto_tecnologia": righe[0]["sotto_tecnologia"],
                     "capex_eur_ton": float(righe[0]["capex_eur_ton"]), "opex_eur_ton": float(righe[0]["opex_eur_ton"]),
                     "descrizione_fasi": righe[0]["descrizione_fasi"], **cx,
                     "capex_eur": capex, "opex_eur": opex, "smaltimento_eur": costo_sm,
                     "costo_eur": capex + opex + costo_sm},
        "uscite": lista, "scarti": scarti_l, "avvisi": avvisi,
        # materiali in ingresso al processo (masse centrali), usati dal report del bilancio di massa
        "ingressi": [{"ingresso": k, "material_id": ing["material_id"], "nome": ing["nome"],
                      "massa_kg": ing["massa"][1], "trattato": k in trattati} for k, ing in ingressi.items()],
        "non_trattato": {"massa_kg": sum(n["massa_kg"] for n in non_trattati), "materiali": non_trattati,
                         "elementi": _el_lista([el_nt, el_nt, el_nt])},
        "bilancio_massa_centrale_kg": bilancio_c,
        "reagenti": _reagenti_lista(cache, reag_info), "bilancio": bil,
        "costo_totale_eur": capex + opex + costo_sm + costo_extra,
        **_tdict("ricavo_eur", ricavo), "ha_override": ha_override,
    }


def calcola_impianto(id_imp: str, componenti: list[dict], anno_dismissione: int | None = None,
                     anno_corrente: int = 2026, id_indice_costi: str = "ISTAT") -> dict:
    """un solo impianto (compatibilita'): vedi calcola_gruppo"""
    return calcola_gruppo([id_imp], componenti, anno_dismissione, anno_corrente, id_indice_costi)


def calcola_gruppo(id_imps, componenti: list[dict], anno_dismissione: int | None = None,
                   anno_corrente: int = 2026, id_indice_costi: str = "ISTAT") -> dict:
    """Calcolo su un GRUPPO di impianti della stessa tipologia: per ogni macrocomponente le
    masse dei materiali sono sommate sugli impianti e il processo e' applicato al totale.
    anno_dismissione: None = ogni impianto rivalutato al proprio anno di dismissione;
    valorizzato = stesso anno per tutti.
    componenti: [{macro_componente, id_processo, assieme|None, escludi_assiemi|None,
    prezzi_prodotti_override|None, prezzi_intermedi_override|None, figli_processo|None}, ...]"""
    ids = _ids(id_imps)
    with _conn() as conn:
        imps = _impianti(conn, ids)
        mancanti = [i for i in ids if i not in {x["id_imp"] for x in imps}]
        if not imps or mancanti:
            return {"error": f"impianto_non_trovato: {', '.join(mancanti) or ids}"}
        if len({i["tipologia"] for i in imps}) > 1:
            return {"error": "gli impianti di un gruppo devono essere della stessa tipologia"}
        anni_dism = {i["id_imp"]: int(anno_dismissione or i["anno_dismissione"]) for i in imps}
        tasso, _ = _fattore_rivalutazione(conn, id_indice_costi, 0)
        fattori = {i: (1 + tasso) ** max(a - anno_corrente, 0) for i, a in anni_dism.items()}
        cache = _Cache(conn)
        risultati = [
            calcola_componente(cache, imps, c["macro_componente"], c["id_processo"], fattori,
                               c.get("prezzi_prodotti_override"), c.get("prezzi_intermedi_override"),
                               c.get("figli_processo"), c.get("assieme"), c.get("escludi_assiemi"),
                               c.get("taglia_t_anno"),
                               # anno di costruzione dell'impianto (vuoto = anno corrente, nessuna rivalutazione)
                               (int(c.get("anno_costruzione") or anno_corrente),
                                (1 + tasso) ** max(int(c.get("anno_costruzione") or anno_corrente) - anno_corrente, 0)))
            for c in componenti
        ]
    ok = [r for r in risultati if "error" not in r]
    costo = sum(r["costo_totale_eur"] for r in ok)
    ric = [sum(r["ricavo_eur_min"] for r in ok), sum(r["ricavo_eur"] for r in ok), sum(r["ricavo_eur_max"] for r in ok)]
    m_tratt = sum(r["massa_trattata_kg"] for r in ok)
    fattore = (sum(r["massa_trattata_kg"] * r["fattore_rivalutazione_medio"] for r in ok) / m_tratt
               if m_tratt > EPS else sum(fattori.values()) / len(fattori))
    anni = sorted(set(anni_dism.values()))
    return {
        "impianto": imps[0] if len(imps) == 1 else None, "tipologia": imps[0]["tipologia"],
        "impianti": [{**i, "anno_dismissione_calcolo": anni_dism[i["id_imp"]], "fattore_rivalutazione": fattori[i["id_imp"]]}
                     for i in imps],
        "anno_dismissione": anni[0] if len(anni) == 1 else None,
        "anno_dismissione_min": anni[0], "anno_dismissione_max": anni[-1],
        "anno_unico_forzato": anno_dismissione is not None,
        "massa_totale_kg": sum(r["massa_componente_kg"] for r in ok),
        "massa_trattata_kg": m_tratt,
        "bilancio": {
            **{c: sum(r["bilancio"]["centrale"][c] for r in ok)
               for c in ("ingresso_kg", "reagenti_kg", "reagenti_non_specificati_kg", "massa_non_bilanciata_kg",
                         "uscite_kg", "chiusura_kg")},
            "chiude": all(r["bilancio"]["chiude"] for r in ok),
            "solo_reagenti_indicati": all(r["bilancio"]["solo_reagenti_indicati"] for r in ok)},
        "fattore_rivalutazione_costi": fattore, "tasso_costi_annuo": tasso,
        "costo_totale_eur": costo, **_tdict("ricavo_eur", ric),
        "margine_eur_min": ric[0] - costo, "margine_eur": ric[1] - costo, "margine_eur_max": ric[2] - costo,
        "ha_prezzi_personalizzati": any(r["ha_override"] for r in ok),
        "componenti": risultati,
    }


# --------------------------------------- modalita' "intermedio acquistato" --
def calcola_da_intermedio(intermedio: str, massa_ton: float, id_sottoprocesso: str,
                          anno_dismissione: int, anno_corrente: int = 2026, id_indice_costi: str = "ISTAT",
                          prezzo_acquisto_override: float | None = None,
                          prezzi_prodotti_override: dict | None = None,
                          prezzi_intermedi_override: dict | None = None,
                          figli_sottoprocesso: dict | None = None, taglia_t_anno: float | None = None) -> dict:
    """L'intermedio acquistato non ha un'origine nota: composizione "n.d.".
    taglia_t_anno: taglia dell'impianto del sottoprocesso (vuota = tratta la quantita' in 1 anno)."""
    massa_kg = massa_ton * 1000
    tempo = massa_ton / float(taglia_t_anno) if (taglia_t_anno and float(taglia_t_anno) > 0) else 1.0
    anni = max(anno_dismissione - anno_corrente, 0)
    with _conn() as conn:
        tasso, fattore = _fattore_rivalutazione(conn, id_indice_costi, anni)
        cache = _Cache(conn)
        info = cache.intermedio(intermedio)
        if not info:
            return {"error": "intermedio_non_trovato"}
        default = float(info.get("prezzo_attuale_eur_kg") or 0)
        prezzo = float(prezzo_acquisto_override) if prezzo_acquisto_override is not None else default
        costo_acquisto = massa_kg * prezzo
        ramo = calcola_ramo_sottoprocesso(cache, intermedio, T(massa_kg), {ND: 1.0}, id_sottoprocesso, fattore,
                                          prezzi_prodotti_override, prezzi_intermedi_override, figli_sottoprocesso,
                                          tempo)
    if "error" in ramo:
        return ramo
    costo = costo_acquisto + ramo["costo_eur"]
    ric = [ramo["ricavo_eur_min"], ramo["ricavo_eur"], ramo["ricavo_eur_max"]]
    return {
        "intermedio": intermedio, "nome": info.get("nome"), "massa_input_kg": massa_kg,
        "acquisto": {"prezzo_default_eur_kg": default, "prezzo_eur_kg": prezzo,
                     "prezzo_personalizzato": prezzo_acquisto_override is not None, "costo_eur": costo_acquisto},
        "sottoprocesso": ramo["sottoprocesso"], "uscite": ramo["uscite"], "scarti": ramo["scarti"],
        "avvisi": ramo["avvisi"], "reagenti": ramo["reagenti"], "bilancio": ramo["bilancio"],
        "costo_totale_eur": costo, **_tdict("ricavo_eur", ric),
        "margine_eur_min": ric[0] - costo, "margine_eur": ric[1] - costo, "margine_eur_max": ric[2] - costo,
        "fattore_rivalutazione_costi": fattore, "tasso_costi_annuo": tasso,
        "ha_prezzi_personalizzati": ramo["ha_override"] or prezzo_acquisto_override is not None,
    }
