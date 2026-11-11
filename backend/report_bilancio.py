"""Report Excel del bilancio di massa di un calcolo (scenario centrale).

Parte dal risultato di calc.calcola_gruppo e scrive, per ogni macrocomponente e per ogni
sottoprocesso a valle, DA DOVE arriva ogni quantita' e COME e' valorizzata:

  Riepilogo            parametri, impianti, costi/ricavi e chiusura del bilancio per corsia
  Dettaglio flussi     una riga per (materiale in ingresso -> uscita): prodotto puro,
                       impurita', intermedio, scarto, non trattato; resa, massa, prezzo, ricavo
  Uscite               una riga per prodotto/intermedio: totale = puro + impurita', prezzo, ricavo
  Scarti               massa e costo di smaltimento
  Reagenti             reagenti stechiometrici e prodotti per cui sono usati
  Controllo materiali  per ogni materiale: ingresso e ripartizione fra le uscite

Il ricavo e' calcolato solo sulla parte pura (massa pura x prezzo); le impurita' sono
massa in piu' nello stesso prodotto, non valorizzata.
"""
import io
from collections import OrderedDict
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill("solid", fgColor="1F5A43")
HEADER_FONT = Font(bold=True, color="FFFFFF")
BOLD = Font(bold=True)
TOT_FILL = PatternFill("solid", fgColor="E8F1EC")
F_KG, F_PCT, F_EUR, F_PREZZO = "#,##0.00", "0.000%", "#,##0", "#,##0.000"
REAG_ING = "__reagenti__"


def _foglio(wb, nome, colonne):
    """colonne: [(titolo, larghezza, formato|None)]"""
    ws = wb.create_sheet(nome)
    ws.append([c[0] for c in colonne])
    for i, (_, larg, _) in enumerate(colonne, start=1):
        c = ws.cell(row=1, column=i)
        c.font, c.fill = HEADER_FONT, HEADER_FILL
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = larg
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = "A2"
    ws._formati = [c[2] for c in colonne]
    return ws


def _riga(ws, valori, bold=False, fill=None):
    ws.append(valori)
    r = ws.max_row
    for i, f in enumerate(ws._formati, start=1):
        c = ws.cell(row=r, column=i)
        if f and c.value is not None:
            c.number_format = f
        if bold:
            c.font = BOLD
        if fill:
            c.fill = fill
    return r


def _fine(ws):
    if ws.max_row > 1:
        ws.auto_filter.ref = f"A1:{get_column_letter(ws.max_column)}{ws.max_row}"


def _nodi(result):
    """Ogni corsia (macrocomponente + processo) e, ricorsivamente, ogni sottoprocesso a valle.
    -> (macro, fase, nodo, ingressi) con ingressi = {chiave: (nome, massa_kg)}"""
    def rami(macro, percorso, uscite):
        for u in uscite or []:
            ramo = u.get("ramo")
            if not ramo:
                continue
            sp = ramo["sottoprocesso"]
            fase = f"{percorso} > {u['codice']} > {sp['id_sottoprocesso']}"
            yield macro, fase, ramo, {u["codice"]: (u.get("nome") or u["codice"], ramo["massa_input_kg"])}
            yield from rami(macro, fase, ramo["uscite"])

    for c in result["componenti"]:
        if "error" in c:
            continue
        macro = c["macro_componente"] + (f" [{c['assieme']}]" if c.get("assieme") else "")
        fase = c["processo"]["id_processo"]
        ing = OrderedDict((i["ingresso"], (i["nome"], i["massa_kg"])) for i in c.get("ingressi", []))
        yield macro, fase, c, ing
        yield from rami(macro, fase, c["uscite"])


def workbook(result: dict, richiesta: dict | None = None) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)

    # ------------------------------------------------------------ Riepilogo
    ws = wb.create_sheet("Riepilogo")
    ws.column_dimensions["A"].width = 44
    for col in "BCDEFGHIJ":
        ws.column_dimensions[col].width = 20

    def r(*v, bold=False):
        ws.append(list(v))
        if bold:
            for c in ws[ws.max_row]:
                c.font = BOLD

    r("MACTEE - Bilancio di massa e valorizzazione", bold=True)
    r("Generato il", datetime.now().strftime("%d/%m/%Y %H:%M"))
    r("Scenario", "centrale (dove indicato anche min / max)")
    r("Tipologia", result.get("tipologia"))
    r("Indice di rivalutazione dei costi", (richiesta or {}).get("id_indice_costi"),
      f"tasso annuo {result.get('tasso_costi_annuo', 0):.2%}")
    r("Ricavi", "massa PURA del prodotto x prezzo; le impurita' non sono valorizzate")
    r()
    r("Impianto", "Sotto-tecnologia", "Anno dismissione (calcolo)", "Fattore rivalutazione costi", bold=True)
    for i in result.get("impianti", []):
        r(i["nome"], i.get("sotto_tecnologia"), i["anno_dismissione_calcolo"], round(i["fattore_rivalutazione"], 4))
    r()
    r("Macrocomponente", "Processo", "Massa componente (kg)", "Massa trattata (kg)", "Reagenti (kg)", "Uscite (kg)",
      "Chiusura bilancio (kg)", "Costo totale (EUR)", "Ricavo (EUR)", "Margine (EUR)", bold=True)
    for c in result["componenti"]:
        if "error" in c:
            continue
        b = c["bilancio"]["centrale"]
        r(c["macro_componente"] + (f" [{c['assieme']}]" if c.get("assieme") else ""), c["processo"]["id_processo"],
          c["massa_componente_kg"], c["massa_trattata_kg"], b["reagenti_kg"] + b["reagenti_non_specificati_kg"],
          b["uscite_kg"], b["chiusura_kg"], c["costo_totale_eur"], c["ricavo_eur"], c["ricavo_eur"] - c["costo_totale_eur"])
        for col, f in zip("CDEFGHIJ", [F_KG] * 5 + [F_EUR] * 3):
            ws[f"{col}{ws.max_row}"].number_format = f
    r("TOTALE", None, result["massa_totale_kg"], result["massa_trattata_kg"], None, None, None,
      result["costo_totale_eur"], result["ricavo_eur"], result["margine_eur"], bold=True)
    for col, f in zip("CDHIJ", [F_KG] * 2 + [F_EUR] * 3):
        ws[f"{col}{ws.max_row}"].number_format = f
    r()
    r("Costi per fase", "Fase", "Capex attribuito (EUR)", "Opex (EUR)", "Smaltimento scarti (EUR)", "Costo fase (EUR)",
      "Capex specifico (EUR/t)", "Opex specifico (EUR/t)", "Taglia (t/anno)", bold=True)
    for macro, fase, nodo, _ in _nodi(result):
        p = nodo.get("processo") or nodo["sottoprocesso"]
        r(macro, fase, p["capex_eur"], p["opex_eur"], p["smaltimento_eur"], p["costo_eur"],
          p["capex_eur_ton"], p["opex_eur_ton"], p.get("taglia_t_anno"))
        for col in "CDEF":
            ws[f"{col}{ws.max_row}"].number_format = F_EUR
        ws[f"I{ws.max_row}"].number_format = F_KG

    # ------------------------------------------------------- Dettaglio flussi
    wd = _foglio(wb, "Dettaglio flussi", [
        ("Macrocomponente", 30, None), ("Fase (processo > sottoprocesso)", 34, None),
        ("Materiale in ingresso", 44, None), ("Massa in ingresso (kg)", 16, F_KG),
        ("Destinazione", 18, None), ("Uscita (codice)", 22, None), ("Uscita (nome)", 34, None),
        ("Resa da processo", 12, F_PCT), ("Massa in uscita (kg)", 16, F_KG), ("Resa effettiva", 12, F_PCT),
        ("Valorizzata", 11, None), ("Prezzo (EUR/kg)", 12, F_PREZZO), ("Ricavo (EUR)", 15, F_EUR),
        ("Costo smaltimento (EUR)", 15, F_EUR), ("Note", 50, None)])
    wu = _foglio(wb, "Uscite", [
        ("Macrocomponente", 30, None), ("Fase", 34, None), ("Tipo", 13, None), ("Codice", 22, None),
        ("Nome", 36, None), ("Categoria", 12, None), ("Massa totale (kg)", 16, F_KG), ("di cui pura (kg)", 16, F_KG),
        ("di cui impurita' (kg)", 16, F_KG), ("Quota impurita'", 11, F_PCT), ("Pura min (kg)", 15, F_KG),
        ("Pura max (kg)", 15, F_KG), ("Prezzo (EUR/kg)", 12, F_PREZZO), ("Ricavo (EUR) = pura x prezzo", 17, F_EUR),
        ("Elementi forniti dai reagenti (kg)", 40, None), ("Note", 40, None)])
    wsc = _foglio(wb, "Scarti", [
        ("Macrocomponente", 30, None), ("Fase", 34, None), ("Scarto", 38, None), ("Massa (kg)", 16, F_KG),
        ("Massa min (kg)", 15, F_KG), ("Massa max (kg)", 15, F_KG), ("Costo smaltimento (EUR/t)", 14, F_KG),
        ("Costo smaltimento (EUR)", 16, F_EUR), ("Elementi principali (kg)", 60, None)])
    wr = _foglio(wb, "Reagenti", [
        ("Macrocomponente", 30, None), ("Fase", 34, None), ("Reagente", 16, None), ("Nome", 34, None),
        ("Formula", 12, None), ("Massa (kg)", 16, F_KG), ("Massa min (kg)", 15, F_KG), ("Massa max (kg)", 15, F_KG),
        ("Usato per (kg)", 60, None)])
    wc = _foglio(wb, "Controllo materiali", [
        ("Macrocomponente", 30, None), ("Fase", 34, None), ("Materiale in ingresso", 44, None),
        ("Massa in ingresso (kg)", 16, F_KG), ("a prodotti/intermedi, parte pura (kg)", 17, F_KG),
        ("a impurita' (kg)", 16, F_KG), ("a scarti (kg)", 16, F_KG), ("non trattato (kg)", 16, F_KG),
        ("Totale uscite (kg)", 16, F_KG), ("Uscite - ingresso (kg)", 16, F_KG), ("Note", 60, None)])

    def it(v):   # numero in formato italiano: 1.234,5
        return f"{v:,.1f}".replace(",", "§").replace(".", ",").replace("§", ".")

    def el_txt(lista, n=6):
        v = sorted((e for e in lista or [] if e.get("massa_kg", 0) > 0.05), key=lambda e: -e["massa_kg"])[:n]
        return "; ".join(f"{e['elemento']} {it(e['massa_kg'])}" for e in v)

    for macro, fase, nodo, ingressi in _nodi(result):
        # controllo per materiale: chiave ingresso -> [puro, impurita, scarti, non trattato]
        ctrl = OrderedDict((k, [0.0, 0.0, 0.0, 0.0]) for k in ingressi)
        nomi = {k: v[0] for k, v in ingressi.items()}

        def massa_ing(k):
            return ingressi[k][1] if k in ingressi and k != REAG_ING else None

        def det(chiave, nome, dest, codice, nome_u, resa, massa, prezzo=None, smalt=None, nota=None):
            mi = massa_ing(chiave)
            riga = _riga(wd, [macro, fase, nome, mi, dest, codice, nome_u, resa, massa,
                              (massa / mi) if mi else None,
                              "si'" if prezzo is not None else "no", prezzo, None, smalt, nota])
            if prezzo is not None:
                c = wd.cell(row=riga, column=13, value=f"=I{riga}*L{riga}")
                c.number_format = F_EUR

        for u in nodo["uscite"]:
            trasf = bool(u.get("ramo"))
            tipo = "prodotto" if u["tipo"] == "prodotto" else ("intermedio (trasformato)" if trasf else "intermedio")
            prezzo = None if trasf else u.get("prezzo_eur_kg")
            tot = u["massa_kg"] + u["impurita_kg"]
            note = []
            if u.get("prezzo_personalizzato"):
                note.append("prezzo personalizzato")
            if trasf:
                note.append("lavorato dal sottoprocesso a valle: il ricavo e' quello delle sue uscite")
            if any(a.get("tipo") == "resa_limitata" for a in u.get("avvisi", [])):
                note.append("resa ridotta al massimo stechiometrico")
            _riga(wu, [macro, fase, tipo, u["codice"], u.get("nome"), u.get("categoria"), tot, u["massa_kg"],
                       u["impurita_kg"], (u["impurita_kg"] / tot) if tot else None, u["massa_kg_min"], u["massa_kg_max"],
                       prezzo, None if trasf else u["ricavo_eur"], el_txt(u.get("elementi_da_reagenti")),
                       "; ".join(note)])
            for c in u["contributi"]:
                da_reag = c["ingresso"] == REAG_ING
                if c["ingresso"] in ctrl:
                    ctrl[c["ingresso"]][0] += c["massa_kg"]
                nota = None
                if da_reag:
                    nota = "formato dai residui dei reagenti, non da un materiale in ingresso"
                elif u.get("elementi_da_reagenti"):
                    nota = "la massa comprende gli elementi della formula forniti dai reagenti"
                det(c["ingresso"], c["nome"], tipo + " - parte pura", u["codice"], u.get("nome"),
                    None if da_reag else c["recupero"], c["massa_kg"], prezzo if not trasf else None, None, nota)
            for c in u["impurita_da"]:
                if c["ingresso"] in ctrl:
                    ctrl[c["ingresso"]][1] += c["massa_kg"]
                det(c["ingresso"], c["nome"], "impurita'", u["codice"], u.get("nome"), c.get("pct"), c["massa_kg"],
                    None, None, "massa in piu' nel prodotto, non valorizzata")
        for s in nodo["scarti"]:
            etichetta = {"non_allocato": "Non allocato (somma recuperi < 1)",
                         "non_attribuito": "Elementi non attribuiti"}.get(s.get("speciale"), s["scarto"])
            _riga(wsc, [macro, fase, etichetta, s["massa_kg"], s["massa_kg_min"], s["massa_kg_max"],
                        s["costo_smaltimento_eur_ton"], s["costo_smaltimento_eur"], el_txt(s.get("elementi"))])
            for m in s["materiali"]:
                if m["ingresso"] in ctrl:
                    ctrl[m["ingresso"]][2] += m["massa_kg"]
                quota = s["costo_smaltimento_eur"] * m["massa_kg"] / s["massa_kg"] if s["massa_kg"] else 0.0
                det(m["ingresso"], m["nome"], "scarto", etichetta, None,
                    m.get("pct") if m["ingresso"] != REAG_ING else None, m["massa_kg"], None, quota or None, None)
        for m in (nodo.get("non_trattato") or {}).get("materiali", []):
            chiave = next((k for k, v in ingressi.items() if v[0] == m["material"]), None)
            if chiave in ctrl:
                ctrl[chiave][3] += m["massa_kg"]
            det(chiave, m["material"], "non trattato", None, None, None, m["massa_kg"], None, None,
                "nessuna riga del processo per questo materiale")
        for rg in nodo.get("reagenti", []):
            _riga(wr, [macro, fase, rg["reagente"] if rg["specificato"] else "(non specificati)", rg["nome"],
                       rg.get("formula_chimica"), rg["massa_kg"], rg["massa_kg_min"], rg["massa_kg_max"],
                       "; ".join(f"{x['prodotto']} {it(x['massa_kg'])}" for x in rg.get("uso", []))])
        for k, (puro, imp, sc, nt) in ctrl.items():
            mi = ingressi[k][1]
            tot = puro + imp + sc + nt
            diff = tot - mi
            nota = None
            if diff > 1e-6 * max(1.0, mi):
                nota = "uscite > ingresso: i prodotti con formula comprendono elementi forniti dai reagenti"
            elif diff < -1e-6 * max(1.0, mi):
                nota = "uscite < ingresso: massa non allocata dalle rese"
            _riga(wc, [macro, fase, nomi[k], mi, puro, imp, sc, nt, tot, diff, nota])

    # totali
    for ws_, cols in ((wd, "IMN"), (wu, "GHIN"), (wsc, "DH"), (wr, "F"), (wc, "DEFGHIJ")):
        n = ws_.max_row
        if n > 1:
            riga = [None] * ws_.max_column
            riga[0] = "TOTALE"
            r_tot = _riga(ws_, riga, bold=True, fill=TOT_FILL)
            for col in cols:
                c = ws_[f"{col}{r_tot}"]
                c.value = f"=SUBTOTAL(9,{col}2:{col}{n})"
                c.number_format = ws_._formati[c.column - 1] or F_KG
                c.font = BOLD
        if n > 1:   # il filtro non deve comprendere la riga dei totali
            ws_.auto_filter.ref = f"A1:{get_column_letter(ws_.max_column)}{n}"

    wb.properties.creator = "MACTEE"
    wb.properties.title = "MACTEE - bilancio di massa"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def filename() -> str:
    return f"MACTEE_bilancio_massa_{datetime.now():%Y%m%d_%H%M}.xlsx"
