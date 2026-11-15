"""Dati per il cruscotto territoriale (modalita' "Cruscotto" della dashboard).

Tutto dal database: impianti (coordinate, anno di dismissione e loro fonti), masse dei materiali
per impianto e macrocomponente, composizione elementare, trasformazioni dei processi e prodotti.
Il calcolo (contenuto e recuperabile per elemento, scenari minimo/medio/massimo) e' fatto nel
browser da frontend/cruscotto.js, con le stesse regole del cruscotto MACTEE_Cruscotto_DB.html.

Per contenere la risposta le masse sono in forma compatta: indici in elenchi di codici.
"""
from sqlalchemy import text
from db import ENGINE, SCHEMA


def _q(conn, sql):
    return [dict(r._mapping) for r in conn.execute(text(sql))]


def dati() -> dict:
    with ENGINE.connect() as conn:
        conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
        impianti = _q(conn, "SELECT id_imp, nome, tipologia, sotto_tecnologia, anno_installazione, anno_dismissione, "
                            "lat, lon, fonte_coordinate, fonte_anno FROM db_impianti ORDER BY id_imp")
        masse = conn.execute(text(
            "SELECT id_macro, macro_componente, material_id, MIN(material) AS material, SUM(massa_kg) AS massa_kg "
            "FROM db_macro WHERE massa_kg > 0 GROUP BY id_macro, macro_componente, material_id "
            "ORDER BY id_macro, macro_componente, material_id")).all()
        comp = conn.execute(text(
            "SELECT material_id, elemento, frazione_pct FROM db_materiali "
            "WHERE frazione_pct IS NOT NULL AND elemento NOT LIKE '(%' ORDER BY material_id, elemento")).all()
        processi = _q(conn, "SELECT id_processo, tipologia, sotto_tecnologia, macro_componente, tecnica "
                            "FROM db_processi ORDER BY id_processo")
        righe = conn.execute(text(
            "SELECT id_processo, material_id, tipo_output, prodotto, recupero_pct_min, recupero_pct, recupero_pct_max "
            "FROM db_processi_trasformazioni ORDER BY id_processo, id")).all()
        prodotti = _q(conn, "SELECT prodotto, nome, categoria, peso_molare, elemento_confronto, parametro_equivalenza, "
                            "prezzo_attuale_eur_kg FROM db_prodotti ORDER BY prodotto")

    def indice(lista: list, mappa: dict, valore):
        if valore not in mappa:
            mappa[valore] = len(lista)
            lista.append(valore)
        return mappa[valore]

    imp_i = {r["id_imp"]: i for i, r in enumerate(impianti)}
    macro_l, macro_m, mat_l, mat_m = [], {}, [], {}
    nomi_mat = {}
    righe_masse = []
    for idm, mc, mid, nome, kg in masse:
        if idm not in imp_i:
            continue
        nomi_mat.setdefault(mid, nome)
        righe_masse.append([imp_i[idm], indice(macro_l, macro_m, mc), indice(mat_l, mat_m, mid), round(float(kg), 4)])
    composizione = {}
    for mid, el, f in comp:
        composizione.setdefault(mid, {})[el] = float(f)
    num = lambda v: None if v is None else float(v)
    for r in impianti:
        for k in ("lat", "lon"):
            r[k] = num(r[k])
    for r in prodotti:
        for k in ("peso_molare", "parametro_equivalenza", "prezzo_attuale_eur_kg"):
            r[k] = num(r[k])
    return {
        "impianti": impianti,
        "macro_componenti": macro_l,
        "materiali": [[m, nomi_mat.get(m)] for m in mat_l],
        "masse": righe_masse,                       # [indice impianto, indice macro, indice materiale, kg]
        "composizione": composizione,               # material_id -> {elemento: frazione %}
        "processi": processi,
        "trasformazioni": [[p, m, t, prod, num(a), num(b), num(c)] for p, m, t, prod, a, b, c in righe],
        "prodotti": prodotti,
    }
