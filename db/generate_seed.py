import json

# ============================================================
# IMPIANTI (invariati)
# ============================================================
impianti = [
    ["IMP01","FOTOVOLTAICO","SI_MONO",50,2010,2035,"Sardegna","Cagliari",39.22,9.11],
    ["IMP02","FOTOVOLTAICO","SI_MONO",20,2012,2037,"Puglia","Foggia",41.46,15.55],
    ["IMP03","FOTOVOLTAICO","SI_MONO",80,2015,2040,"Sicilia","Trapani",38.02,12.51],
    ["IMP04","EOLICO","GB_PMSG",30,2008,2033,"Puglia","Foggia",41.46,15.55],
    ["IMP05","EOLICO","GB_PMSG",45,2011,2036,"Sardegna","Nuoro",40.32,9.33],
    ["IMP06","EOLICO","GB_PMSG",60,2013,2038,"Basilicata","Potenza",40.64,15.81],
    ["IMP07","BESS","NMC",10,2019,2034,"Lombardia","Milano",45.46,9.19],
    ["IMP08","BESS","NMC",25,2020,2035,"Piemonte","Torino",45.07,7.69],
    ["IMP09","BESS","LFP",15,2021,2036,"Emilia-Romagna","Bologna",44.49,11.34],
    ["IMP10","EOLICO","GB_PMSG",100,2009,2029,"Sicilia","Trapani",38.02,12.51],
]

# ============================================================
# DB_PRODOTTI (ex db_elementi): 17 originali + 4 nuovi composti terminali
# ============================================================
prodotti = [
    ["Si","Silicio","strategico",3.0],
    ["Al","Alluminio","critico",2.3],
    ["Cu","Rame","critico",8.6],
    ["Ag","Argento","utile",760.0],
    ["Fe","Ferro","utile",0.12],
    ["Te","Tellurio","strategico",75.0],
    ["Nd","Neodimio","critico",80.0],
    ["Dy","Disprosio","critico",350.0],
    ["Pr","Praseodimio","critico",95.0],
    ["Tb","Terbio","critico",900.0],
    ["Li","Litio","strategico",14.0],
    ["Co","Cobalto","strategico",30.0],
    ["Ni","Nichel","strategico",17.0],
    ["Ga","Gallio","critico",280.0],
    ["Mn","Manganese","critico",2.0],
    ["Pb","Piombo","utile",2.0],
    ["Zn","Zinco","utile",2.5],
    ["COSO4","Solfato di Cobalto","strategico",12.0],
    ["LI2CO3","Carbonato di Litio","strategico",20.0],
    ["NISO4","Solfato di Nichel","strategico",7.0],
    ["LIOH","Idrossido di Litio","strategico",22.0],
]
growth = {"strategico": (0.05, 0.08), "critico": (0.04, 0.07), "utile": (0.015, 0.03)}

# ============================================================
# DB_SOTTOPRODOTTI: solo Black Mass e NHP, nessuna categoria
# ============================================================
sottoprodotti = [
    ["BLACK_MASS","Black Mass",5.5,0.03,0.05],
    ["NHP","Idrossido misto Ni-Co (NHP)",8.0,0.04,0.07],
]

# ============================================================
# DB_MACRO: composizione macrocomponenti (BLACK_MASS rimossa: non e' piu'
# un macrocomponente, e' un sottoprodotto generato da un processo su CELLE)
# ============================================================
macro_def = [
    ("M_EOL_PALE","EOLICO","GB_PMSG","PALE",8000,[("Fe",0.02)]),
    ("M_EOL_GEARBOX","EOLICO","GB_PMSG","GEARBOX",6000,[("Fe",0.90),("Cu",0.01)]),
    ("M_EOL_MAGNETI","EOLICO","GB_PMSG","MAGNETI_PERMANENTI",600,[("Nd",0.29),("Dy",0.04),("Pr",0.03),("Tb",0.01)]),
    ("M_EOL_CABLAGGI","EOLICO","GB_PMSG","CABLAGGI",2000,[("Cu",0.60),("Al",0.05)]),
    ("M_EOL_QUADRI","EOLICO","GB_PMSG","QUADRI_ELETTRICI",500,[("Cu",0.20),("Al",0.10),("Fe",0.30)]),
    ("M_EOL_STRUTTURA","EOLICO","GB_PMSG","STRUTTURA_ACCIAIO",50000,[("Fe",0.95)]),
    ("M_EOL_ARMATURE","EOLICO","GB_PMSG","ARMATURE_ACCIAIO",40000,[("Fe",0.90)]),
    ("M_PV_MODULI","FOTOVOLTAICO","SI_MONO","MODULI_FOTOVOLTAICI",60000,[("Si",0.04),("Al",0.10),("Ag",0.0005),("Cu",0.01)]),
    ("M_PV_INVERTER","FOTOVOLTAICO","SI_MONO","INVERTER",3000,[("Cu",0.15),("Al",0.20),("Fe",0.10)]),
    ("M_PV_STRUTTURA","FOTOVOLTAICO","SI_MONO","STRUTTURA_MONTAGGIO",25000,[("Al",0.40),("Fe",0.47)]),
    ("M_PV_CABLAGGI","FOTOVOLTAICO","SI_MONO","CABLAGGI",2000,[("Cu",0.70)]),
    ("M_PV_QUADRI","FOTOVOLTAICO","SI_MONO","QUADRI_ELETTRICI",500,[("Cu",0.20),("Fe",0.30)]),
    ("M_BESSN_CELLE","BESS","NMC","CELLE",6000,[("Li",0.02),("Co",0.05),("Ni",0.10),("Mn",0.05)]),
    ("M_BESSN_BMS","BESS","NMC","BMS_ELETTRONICA",500,[("Cu",0.10),("Fe",0.05)]),
    ("M_BESSN_INVOLUCRO","BESS","NMC","INVOLUCRO_STRUTTURA",8000,[("Al",0.30),("Fe",0.40)]),
    ("M_BESSN_CABLAGGI","BESS","NMC","CABLAGGI",1000,[("Cu",0.60)]),
    ("M_BESSL_CELLE","BESS","LFP","CELLE",6000,[("Li",0.015),("Fe",0.15)]),
    ("M_BESSL_BMS","BESS","LFP","BMS_ELETTRONICA",500,[("Cu",0.10),("Fe",0.05)]),
    ("M_BESSL_INVOLUCRO","BESS","LFP","INVOLUCRO_STRUTTURA",8000,[("Al",0.30),("Fe",0.40)]),
    ("M_BESSL_CABLAGGI","BESS","LFP","CABLAGGI",1000,[("Cu",0.60)]),
]

# ============================================================
# DB_MACRO_PROCESSI: niente piu' scenari. Piu' righe per lo stesso
# macrocomponente = macroprocessi alternativi.
# (id_processo_macro, tipologia, sotto, macro_componente, tecnica, capex, opex, prezzo_vendita, p1, p2, fasi)
# ============================================================
macro_processi_def = [
    # EOLICO - variante completa (con trasporto)
    ("MP_EOL_PALE","EOLICO","GB_PMSG","PALE","RIMOZIONE_E_TRASPORTO",30,60,0.02,0.01,0.02,
     "RIMOZIONE_PALA, TRASPORTO_A_TERRA, STOCCAGGIO"),
    ("MP_EOL_GEARBOX","EOLICO","GB_PMSG","GEARBOX","SMONTAGGIO_E_TRASPORTO",40,80,0.25,0.015,0.025,
     "APERTURA_NAVICELLA, SGANCIO_GEARBOX, CALATA_A_TERRA, TRASPORTO"),
    ("MP_EOL_MAGNETI","EOLICO","GB_PMSG","MAGNETI_PERMANENTI","SMONTAGGIO_E_TRASPORTO",60,120,8.0,0.04,0.07,
     "APERTURA_GENERATORE, ESTRAZIONE_ROTORE, SEPARAZIONE_MAGNETI, TRASPORTO"),
    ("MP_EOL_CABLAGGI","EOLICO","GB_PMSG","CABLAGGI","SMONTAGGIO_E_TRASPORTO",20,40,3.5,0.03,0.05,
     "SEZIONAMENTO_ELETTRICO, ESTRAZIONE_CAVI, TRASPORTO"),
    ("MP_EOL_QUADRI","EOLICO","GB_PMSG","QUADRI_ELETTRICI","SMONTAGGIO_E_TRASPORTO",25,50,1.2,0.02,0.035,
     "SEZIONAMENTO_ELETTRICO, RIMOZIONE_QUADRI, TRASPORTO"),
    ("MP_EOL_STRUTTURA","EOLICO","GB_PMSG","STRUTTURA_ACCIAIO","SMONTAGGIO_E_TRASPORTO",35,70,0.22,0.015,0.025,
     "ABBATTIMENTO_TORRE, SEZIONAMENTO_TRONCONI, TRASPORTO"),
    ("MP_EOL_ARMATURE","EOLICO","GB_PMSG","ARMATURE_ACCIAIO","SMONTAGGIO_E_TRASPORTO",45,90,0.18,0.015,0.025,
     "DEMOLIZIONE_FONDAZIONE, ESTRAZIONE_ARMATURE, TRASPORTO"),
    # EOLICO - variante solo disassemblaggio (senza trasporto, costi piu' bassi)
    ("MP_EOL_PALE_SD","EOLICO","GB_PMSG","PALE","SOLO_DISASSEMBLAGGIO",22,36,0.02,0.01,0.02,
     "RIMOZIONE_PALA, STOCCAGGIO_IN_SITO"),
    ("MP_EOL_GEARBOX_SD","EOLICO","GB_PMSG","GEARBOX","SOLO_DISASSEMBLAGGIO",30,50,0.25,0.015,0.025,
     "APERTURA_NAVICELLA, SGANCIO_GEARBOX, CALATA_A_TERRA"),
    ("MP_EOL_MAGNETI_SD","EOLICO","GB_PMSG","MAGNETI_PERMANENTI","SOLO_DISASSEMBLAGGIO",45,75,8.0,0.04,0.07,
     "APERTURA_GENERATORE, ESTRAZIONE_ROTORE, SEPARAZIONE_MAGNETI"),
    ("MP_EOL_CABLAGGI_SD","EOLICO","GB_PMSG","CABLAGGI","SOLO_DISASSEMBLAGGIO",15,26,3.5,0.03,0.05,
     "SEZIONAMENTO_ELETTRICO, ESTRAZIONE_CAVI"),
    ("MP_EOL_QUADRI_SD","EOLICO","GB_PMSG","QUADRI_ELETTRICI","SOLO_DISASSEMBLAGGIO",18,33,1.2,0.02,0.035,
     "SEZIONAMENTO_ELETTRICO, RIMOZIONE_QUADRI"),
    ("MP_EOL_STRUTTURA_SD","EOLICO","GB_PMSG","STRUTTURA_ACCIAIO","SOLO_DISASSEMBLAGGIO",26,46,0.22,0.015,0.025,
     "ABBATTIMENTO_TORRE, SEZIONAMENTO_TRONCONI"),
    ("MP_EOL_ARMATURE_SD","EOLICO","GB_PMSG","ARMATURE_ACCIAIO","SOLO_DISASSEMBLAGGIO",33,59,0.18,0.015,0.025,
     "DEMOLIZIONE_FONDAZIONE, ESTRAZIONE_ARMATURE"),
    # EOLICO - variante aggiuntiva solo per PALE: taglio in sito
    ("MP_EOL_PALE_TAGLIO","EOLICO","GB_PMSG","PALE","TAGLIO_IN_SITO",45,70,0.015,0.01,0.02,
     "TAGLIO_PALA_IN_SITO, FRANTUMAZIONE_SEGMENTI, STOCCAGGIO"),

    # FOTOVOLTAICO - unica variante
    ("MP_PV_MODULI","FOTOVOLTAICO","SI_MONO","MODULI_FOTOVOLTAICI","SMONTAGGIO_E_TRASPORTO",15,30,0.08,0.015,0.03,
     "SCOLLEGAMENTO_STRINGHE, RIMOZIONE_MODULI, IMBALLAGGIO, TRASPORTO"),
    ("MP_PV_INVERTER","FOTOVOLTAICO","SI_MONO","INVERTER","SMONTAGGIO_E_TRASPORTO",20,35,1.0,0.02,0.035,
     "SEZIONAMENTO_ELETTRICO, RIMOZIONE_INVERTER, TRASPORTO"),
    ("MP_PV_STRUTTURA","FOTOVOLTAICO","SI_MONO","STRUTTURA_MONTAGGIO","SMONTAGGIO_E_TRASPORTO",25,45,0.6,0.02,0.03,
     "SVITATURA_STAFFE, RIMOZIONE_STRUTTURA, TRASPORTO"),
    ("MP_PV_CABLAGGI","FOTOVOLTAICO","SI_MONO","CABLAGGI","SMONTAGGIO_E_TRASPORTO",15,25,3.5,0.03,0.05,
     "SEZIONAMENTO_ELETTRICO, ESTRAZIONE_CAVI, TRASPORTO"),
    ("MP_PV_QUADRI","FOTOVOLTAICO","SI_MONO","QUADRI_ELETTRICI","SMONTAGGIO_E_TRASPORTO",20,35,1.2,0.02,0.035,
     "SEZIONAMENTO_ELETTRICO, RIMOZIONE_QUADRI, TRASPORTO"),

    # BESS NMC - un solo insieme di macrocomponenti (niente piu' variante black mass qui:
    # la black mass ora nasce da un PROCESSO applicato a CELLE, vedi db_processi)
    ("MP_BESSN_CELLE","BESS","NMC","CELLE","SMONTAGGIO_MODULI",50,90,2.5,0.03,0.05,
     "SCARICA_SICUREZZA, APERTURA_CONTENITORE, ESTRAZIONE_MODULI_CELLE"),
    ("MP_BESSN_BMS","BESS","NMC","BMS_ELETTRONICA","SMONTAGGIO",20,35,1.0,0.02,0.035,
     "SEZIONAMENTO_ELETTRICO, RIMOZIONE_BMS"),
    ("MP_BESSN_INVOLUCRO","BESS","NMC","INVOLUCRO_STRUTTURA","SMONTAGGIO",25,45,0.5,0.015,0.025,
     "APERTURA_CONTAINER, RIMOZIONE_PANNELLI"),
    ("MP_BESSN_CABLAGGI","BESS","NMC","CABLAGGI","SMONTAGGIO",15,25,3.5,0.03,0.05,
     "SEZIONAMENTO_ELETTRICO, ESTRAZIONE_CAVI"),

    # BESS LFP
    ("MP_BESSL_CELLE","BESS","LFP","CELLE","SMONTAGGIO_MODULI",50,90,1.0,0.02,0.035,
     "SCARICA_SICUREZZA, APERTURA_CONTENITORE, ESTRAZIONE_MODULI_CELLE"),
    ("MP_BESSL_BMS","BESS","LFP","BMS_ELETTRONICA","SMONTAGGIO",20,35,1.0,0.02,0.035,
     "SEZIONAMENTO_ELETTRICO, RIMOZIONE_BMS"),
    ("MP_BESSL_INVOLUCRO","BESS","LFP","INVOLUCRO_STRUTTURA","SMONTAGGIO",25,45,0.5,0.015,0.025,
     "APERTURA_CONTAINER, RIMOZIONE_PANNELLI"),
    ("MP_BESSL_CABLAGGI","BESS","LFP","CABLAGGI","SMONTAGGIO",15,25,3.5,0.03,0.05,
     "SEZIONAMENTO_ELETTRICO, ESTRAZIONE_CAVI"),

    # FOTOVOLTAICO - variante alternativa (smontaggio rapido/in sito, per ogni macrocomponente)
    ("MP_PV_MODULI_ALT","FOTOVOLTAICO","SI_MONO","MODULI_FOTOVOLTAICI","SMONTAGGIO_RAPIDO",12,24,0.08,0.015,0.03,
     "SCOLLEGAMENTO_RAPIDO_CONNETTORI, RIMOZIONE_MODULI, STOCCAGGIO_IN_SITO"),
    ("MP_PV_INVERTER_ALT","FOTOVOLTAICO","SI_MONO","INVERTER","SMONTAGGIO_IN_SITO",15,28,1.0,0.02,0.035,
     "SEZIONAMENTO_ELETTRICO, RIMOZIONE_INVERTER_IN_SITO"),
    ("MP_PV_STRUTTURA_ALT","FOTOVOLTAICO","SI_MONO","STRUTTURA_MONTAGGIO","TAGLIO_STRUTTURA_IN_SITO",20,36,0.6,0.02,0.03,
     "TAGLIO_STAFFE, RIMOZIONE_STRUTTURA_IN_SITO"),
    ("MP_PV_CABLAGGI_ALT","FOTOVOLTAICO","SI_MONO","CABLAGGI","TAGLIO_CAVI_IN_SITO",12,20,3.5,0.03,0.05,
     "TAGLIO_CAVI, STOCCAGGIO_IN_SITO"),
    ("MP_PV_QUADRI_ALT","FOTOVOLTAICO","SI_MONO","QUADRI_ELETTRICI","SMONTAGGIO_RAPIDO_QUADRI",16,28,1.2,0.02,0.035,
     "SEZIONAMENTO_ELETTRICO, RIMOZIONE_RAPIDA_QUADRI"),

    # BESS NMC - variante alternativa (smontaggio/taglio rapido)
    ("MP_BESSN_CELLE_ALT","BESS","NMC","CELLE","SMONTAGGIO_RAPIDO_MODULI",40,75,2.5,0.03,0.05,
     "SCARICA_SICUREZZA, APERTURA_RAPIDA, ESTRAZIONE_MODULI"),
    ("MP_BESSN_BMS_ALT","BESS","NMC","BMS_ELETTRONICA","SMONTAGGIO_RAPIDO",16,28,1.0,0.02,0.035,
     "SEZIONAMENTO_ELETTRICO, RIMOZIONE_RAPIDA_BMS"),
    ("MP_BESSN_INVOLUCRO_ALT","BESS","NMC","INVOLUCRO_STRUTTURA","TAGLIO_RAPIDO_CONTAINER",20,36,0.5,0.015,0.025,
     "APERTURA_CONTAINER, TAGLIO_PANNELLI"),
    ("MP_BESSN_CABLAGGI_ALT","BESS","NMC","CABLAGGI","TAGLIO_CAVI_IN_SITO",12,20,3.5,0.03,0.05,
     "TAGLIO_CAVI, STOCCAGGIO_IN_SITO"),

    # BESS LFP - variante alternativa (stessa logica)
    ("MP_BESSL_CELLE_ALT","BESS","LFP","CELLE","SMONTAGGIO_RAPIDO_MODULI",40,75,1.0,0.02,0.035,
     "SCARICA_SICUREZZA, APERTURA_RAPIDA, ESTRAZIONE_MODULI"),
    ("MP_BESSL_BMS_ALT","BESS","LFP","BMS_ELETTRONICA","SMONTAGGIO_RAPIDO",16,28,1.0,0.02,0.035,
     "SEZIONAMENTO_ELETTRICO, RIMOZIONE_RAPIDA_BMS"),
    ("MP_BESSL_INVOLUCRO_ALT","BESS","LFP","INVOLUCRO_STRUTTURA","TAGLIO_RAPIDO_CONTAINER",20,36,0.5,0.015,0.025,
     "APERTURA_CONTAINER, TAGLIO_PANNELLI"),
    ("MP_BESSL_CABLAGGI_ALT","BESS","LFP","CABLAGGI","TAGLIO_CAVI_IN_SITO",12,20,3.5,0.03,0.05,
     "TAGLIO_CAVI, STOCCAGGIO_IN_SITO"),
]

FASI_MAGNETI_DIRETTO = "SMONTAGGIO, DEMAGNETIZZAZIONE, ROTTURA_CON_IDROGENO, MACINAZIONE, PRESSATURA_IN_CAMPO_MAGNETICO, SINTERIZZAZIONE, TRATTAMENTO_TERMICO"
FASI_MAGNETI_IDRO = "SMONTAGGIO, DEMAGNETIZZAZIONE, FRANTUMAZIONE, MACINAZIONE, LISCIVIAZIONE_ACIDA, SEPARAZIONE_SOLIDO_LIQUIDO, ESTRAZIONE_CON_SOLVENTE, PRECIPITAZIONE_REE, FILTRAZIONE_PRECIPITATO, CALCINAZIONE"
FASI_MAGNETI_PIRO = "SMONTAGGIO, DEMAGNETIZZAZIONE, FRANTUMAZIONE, FUSIONE_ARROSTIMENTO, RAFFINAZIONE"
FASI_MAGNETI_PIROIDRO = "SMONTAGGIO, ARROSTIMENTO, FRANTUMAZIONE, MACINAZIONE, LISCIVIAZIONE_ACIDA, SEPARAZIONE_SOLIDO_LIQUIDO, ESTRAZIONE_CON_SOLVENTE, PRECIPITAZIONE_REE, FILTRAZIONE_PRECIPITATO, CALCINAZIONE"

# ============================================================
# DB_PROCESSI: recupero diretto (tipo_output=prodotto, come prima) + NUOVO
# CELLE -> BLACK_MASS (tipo_output=sottoprodotto)
# (id_processo, tipologia, sotto, macro_componente, tecnica, capex, opex, tipo_output, [(prodotto_o_sottoprodotto, resa)], fasi)
# ============================================================
proc_def = [
    ("P_EOL_PALE","EOLICO","GB_PMSG","PALE","TRITURAZIONE_MECCANICA",50,100,"prodotto",[("Fe",0.70)],
     "TRITURAZIONE, VAGLIATURA, SEPARAZIONE_MAGNETICA_METALLI"),
    ("P_EOL_GEARBOX","EOLICO","GB_PMSG","GEARBOX","SMONTAGGIO_RECUPERO_METALLICO",150,300,"prodotto",[("Fe",0.92),("Cu",0.85)],
     "SMONTAGGIO, DRENAGGIO_OLIO, FRANTUMAZIONE, SEPARAZIONE_METALLI"),
    ("P_EOL_MAGNETI_DIRETTO","EOLICO","GB_PMSG","MAGNETI_PERMANENTI","RICICLO_DIRETTO",1200,15000,"prodotto",
     [("Nd",0.95),("Dy",0.96),("Pr",0.95),("Tb",0.95)], FASI_MAGNETI_DIRETTO),
    ("P_EOL_MAGNETI_IDRO","EOLICO","GB_PMSG","MAGNETI_PERMANENTI","IDROMETALLURGIA",2000,30000,"prodotto",
     [("Nd",0.90),("Dy",0.98),("Pr",0.90),("Tb",0.90)], FASI_MAGNETI_IDRO),
    ("P_EOL_MAGNETI_PIRO","EOLICO","GB_PMSG","MAGNETI_PERMANENTI","PIROMETALLURGIA",1500,20000,"prodotto",
     [("Nd",0.80),("Dy",0.95),("Pr",0.80),("Tb",0.80)], FASI_MAGNETI_PIRO),
    ("P_EOL_MAGNETI_PIROIDRO","EOLICO","GB_PMSG","MAGNETI_PERMANENTI","PIROMETALLURGIA_E_IDROMETALLURGIA",2500,35000,"prodotto",
     [("Nd",0.90),("Dy",0.98),("Pr",0.90),("Tb",0.90)], FASI_MAGNETI_PIROIDRO),
    ("P_EOL_CABLAGGI","EOLICO","GB_PMSG","CABLAGGI","SPELLATURA_RECUPERO_RAME",80,150,"prodotto",[("Cu",0.95),("Al",0.85)],
     "SPELLATURA_GUAINE, GRANULAZIONE, SEPARAZIONE_DENSIMETRICA"),
    ("P_EOL_QUADRI","EOLICO","GB_PMSG","QUADRI_ELETTRICI","SMONTAGGIO_COMPONENTI_ELETTRONICI",200,400,"prodotto",
     [("Cu",0.90),("Fe",0.85),("Al",0.80)], "SMONTAGGIO, SEPARAZIONE_SCHEDE, RECUPERO_METALLI"),
    ("P_EOL_STRUTTURA","EOLICO","GB_PMSG","STRUTTURA_ACCIAIO","FRANTUMAZIONE_RECUPERO_ACCIAIO",50,100,"prodotto",
     [("Fe",0.96)], "TAGLIO, FRANTUMAZIONE, SEPARAZIONE_MAGNETICA"),
    ("P_EOL_ARMATURE","EOLICO","GB_PMSG","ARMATURE_ACCIAIO","FRANTUMAZIONE_RECUPERO_ACCIAIO",50,100,"prodotto",
     [("Fe",0.94)], "DEMOLIZIONE, FRANTUMAZIONE, SEPARAZIONE_MAGNETICA"),
    ("P_PV_MODULI_MECC","FOTOVOLTAICO","SI_MONO","MODULI_FOTOVOLTAICI","RICICLO_MECCANICO",150,250,"prodotto",
     [("Si",0.60),("Al",0.95),("Ag",0.50),("Cu",0.70)], "SMONTAGGIO_TELAIO, FRANTUMAZIONE, VAGLIATURA, SEPARAZIONE_MATERIALI"),
    ("P_PV_MODULI_TERMOCHIM","FOTOVOLTAICO","SI_MONO","MODULI_FOTOVOLTAICI","RICICLO_TERMICO_CHIMICO",400,600,"prodotto",
     [("Si",0.90),("Al",0.96),("Ag",0.92),("Cu",0.85)], "DELAMINAZIONE_TERMICA, LISCIVIAZIONE_ACIDA, RECUPERO_METALLI, PURIFICAZIONE_SILICIO"),
    ("P_PV_INVERTER","FOTOVOLTAICO","SI_MONO","INVERTER","SMONTAGGIO_ELETTRONICO",200,350,"prodotto",
     [("Cu",0.88),("Al",0.90),("Fe",0.85)], "SMONTAGGIO, SEPARAZIONE_SCHEDE, RECUPERO_METALLI"),
    ("P_PV_STRUTTURA","FOTOVOLTAICO","SI_MONO","STRUTTURA_MONTAGGIO","FRANTUMAZIONE_METALLI",60,100,"prodotto",
     [("Al",0.95),("Fe",0.92)], "SMONTAGGIO, TAGLIO, SEPARAZIONE_LEGHE"),
    ("P_PV_CABLAGGI","FOTOVOLTAICO","SI_MONO","CABLAGGI","SPELLATURA_RECUPERO_RAME",80,150,"prodotto",
     [("Cu",0.95)], "SPELLATURA_GUAINE, GRANULAZIONE, SEPARAZIONE_DENSIMETRICA"),
    ("P_PV_QUADRI","FOTOVOLTAICO","SI_MONO","QUADRI_ELETTRICI","SMONTAGGIO_COMPONENTI_ELETTRONICI",200,400,"prodotto",
     [("Cu",0.90),("Fe",0.85)], "SMONTAGGIO, SEPARAZIONE_SCHEDE, RECUPERO_METALLI"),

    # BESS NMC: due processi alternativi per CELLE
    ("P_BESSN_CELLE_DIRETTO","BESS","NMC","CELLE","IDROMETALLURGIA_NMC",3000,25000,"prodotto",
     [("Li",0.85),("Co",0.95),("Ni",0.95),("Mn",0.90)], "SCARICA, SMONTAGGIO, FRANTUMAZIONE, LISCIVIAZIONE_ACIDA, ESTRAZIONE_SOLVENTE, PRECIPITAZIONE"),
    ("P_BESSN_CELLE_BLACKMASS","BESS","NMC","CELLE","PIROLISI_E_TRITURAZIONE",1800,16000,"sottoprodotto",
     [("BLACK_MASS",0.50)], "SCARICA_SICUREZZA, PIROLISI, TRITURAZIONE, VAGLIATURA_BLACK_MASS"),
    ("P_BESSN_BMS","BESS","NMC","BMS_ELETTRONICA","SMONTAGGIO_ELETTRONICO",250,500,"prodotto",
     [("Cu",0.85),("Fe",0.80)], "SMONTAGGIO, SEPARAZIONE_SCHEDE, RECUPERO_METALLI"),
    ("P_BESSN_INVOLUCRO","BESS","NMC","INVOLUCRO_STRUTTURA","FRANTUMAZIONE_METALLI",60,100,"prodotto",
     [("Al",0.93),("Fe",0.90)], "SMONTAGGIO, TAGLIO, SEPARAZIONE_LEGHE"),
    ("P_BESSN_CABLAGGI","BESS","NMC","CABLAGGI","SPELLATURA_RECUPERO_RAME",80,150,"prodotto",
     [("Cu",0.95)], "SPELLATURA_GUAINE, GRANULAZIONE, SEPARAZIONE_DENSIMETRICA"),

    # BESS LFP: due processi alternativi per CELLE
    ("P_BESSL_CELLE_DIRETTO","BESS","LFP","CELLE","IDROMETALLURGIA_LFP",2500,20000,"prodotto",
     [("Li",0.80),("Fe",0.90)], "SCARICA, SMONTAGGIO, FRANTUMAZIONE, LISCIVIAZIONE_ACIDA, PRECIPITAZIONE"),
    ("P_BESSL_CELLE_BLACKMASS","BESS","LFP","CELLE","PIROLISI_E_TRITURAZIONE",1600,14000,"sottoprodotto",
     [("BLACK_MASS",0.45)], "SCARICA_SICUREZZA, PIROLISI, TRITURAZIONE, VAGLIATURA_BLACK_MASS"),
    ("P_BESSL_BMS","BESS","LFP","BMS_ELETTRONICA","SMONTAGGIO_ELETTRONICO",250,500,"prodotto",
     [("Cu",0.85),("Fe",0.80)], "SMONTAGGIO, SEPARAZIONE_SCHEDE, RECUPERO_METALLI"),
    ("P_BESSL_INVOLUCRO","BESS","LFP","INVOLUCRO_STRUTTURA","FRANTUMAZIONE_METALLI",60,100,"prodotto",
     [("Al",0.93),("Fe",0.90)], "SMONTAGGIO, TAGLIO, SEPARAZIONE_LEGHE"),
    ("P_BESSL_CABLAGGI","BESS","LFP","CABLAGGI","SPELLATURA_RECUPERO_RAME",80,150,"prodotto",
     [("Cu",0.95)], "SPELLATURA_GUAINE, GRANULAZIONE, SEPARAZIONE_DENSIMETRICA"),

    # ---- alternative aggiuntive (una seconda tecnica di recupero diretto per
    # macrocomponenti che altrimenti ne avrebbero solo una) ----
    ("P_EOL_PALE_ALT2","EOLICO","GB_PMSG","PALE","SEPARAZIONE_MANUALE_FERRO",40,80,"prodotto",
     [("Fe",0.60)], "TAGLIO_MANUALE, SEPARAZIONE_FERRO"),
    ("P_EOL_GEARBOX_ALT2","EOLICO","GB_PMSG","GEARBOX","RIGENERAZIONE_COMPONENTI",120,250,"prodotto",
     [("Fe",0.85),("Cu",0.75)], "SMONTAGGIO, PULIZIA, RIGENERAZIONE, RECUPERO_METALLI"),
    ("P_EOL_CABLAGGI_ALT2","EOLICO","GB_PMSG","CABLAGGI","GRANULAZIONE_A_FREDDO",70,130,"prodotto",
     [("Cu",0.90)], "RAFFREDDAMENTO_CRIOGENICO, GRANULAZIONE, SEPARAZIONE"),
    ("P_EOL_QUADRI_ALT2","EOLICO","GB_PMSG","QUADRI_ELETTRICI","RECUPERO_MANUALE_COMPONENTI",170,350,"prodotto",
     [("Cu",0.80)], "SMONTAGGIO_MANUALE, CERNITA_COMPONENTI, RECUPERO_METALLI"),
    ("P_EOL_STRUTTURA_ALT2","EOLICO","GB_PMSG","STRUTTURA_ACCIAIO","TAGLIO_OSSIACETILENICO",45,90,"prodotto",
     [("Fe",0.97)], "TAGLIO_OSSIACETILENICO, CERNITA_ROTTAME"),
    ("P_EOL_ARMATURE_ALT2","EOLICO","GB_PMSG","ARMATURE_ACCIAIO","RECUPERO_MANUALE_ARMATURE",45,90,"prodotto",
     [("Fe",0.90)], "DEMOLIZIONE_MANUALE, CERNITA_ARMATURE"),
    ("P_PV_INVERTER_ALT2","FOTOVOLTAICO","SI_MONO","INVERTER","RIGENERAZIONE_COMPONENTI",180,320,"prodotto",
     [("Cu",0.86)], "SMONTAGGIO, RIGENERAZIONE, RECUPERO_METALLI"),
    ("P_PV_STRUTTURA_ALT2","FOTOVOLTAICO","SI_MONO","STRUTTURA_MONTAGGIO","TAGLIO_MANUALE_LEGHE",55,90,"prodotto",
     [("Al",0.94)], "TAGLIO_MANUALE, SEPARAZIONE_LEGHE"),
    ("P_PV_CABLAGGI_ALT2","FOTOVOLTAICO","SI_MONO","CABLAGGI","GRANULAZIONE_A_FREDDO",70,130,"prodotto",
     [("Cu",0.90)], "RAFFREDDAMENTO_CRIOGENICO, GRANULAZIONE, SEPARAZIONE"),
    ("P_PV_QUADRI_ALT2","FOTOVOLTAICO","SI_MONO","QUADRI_ELETTRICI","RECUPERO_MANUALE_COMPONENTI",170,350,"prodotto",
     [("Cu",0.80)], "SMONTAGGIO_MANUALE, CERNITA_COMPONENTI, RECUPERO_METALLI"),
    ("P_BESSN_BMS_ALT2","BESS","NMC","BMS_ELETTRONICA","RIGENERAZIONE_SCHEDE",230,460,"prodotto",
     [("Cu",0.86)], "SMONTAGGIO, TEST_SCHEDE, RIGENERAZIONE, RECUPERO_METALLI"),
    ("P_BESSN_INVOLUCRO_ALT2","BESS","NMC","INVOLUCRO_STRUTTURA","TAGLIO_MANUALE_LEGHE",55,90,"prodotto",
     [("Al",0.92)], "SMONTAGGIO, TAGLIO_MANUALE, SEPARAZIONE_LEGHE"),
    ("P_BESSN_CABLAGGI_ALT2","BESS","NMC","CABLAGGI","GRANULAZIONE_A_FREDDO",70,130,"prodotto",
     [("Cu",0.90)], "RAFFREDDAMENTO_CRIOGENICO, GRANULAZIONE, SEPARAZIONE"),
    ("P_BESSL_BMS_ALT2","BESS","LFP","BMS_ELETTRONICA","RIGENERAZIONE_SCHEDE",230,460,"prodotto",
     [("Cu",0.86)], "SMONTAGGIO, TEST_SCHEDE, RIGENERAZIONE, RECUPERO_METALLI"),
    ("P_BESSL_INVOLUCRO_ALT2","BESS","LFP","INVOLUCRO_STRUTTURA","TAGLIO_MANUALE_LEGHE",55,90,"prodotto",
     [("Al",0.92)], "SMONTAGGIO, TAGLIO_MANUALE, SEPARAZIONE_LEGHE"),
    ("P_BESSL_CABLAGGI_ALT2","BESS","LFP","CABLAGGI","GRANULAZIONE_A_FREDDO",70,130,"prodotto",
     [("Cu",0.90)], "RAFFREDDAMENTO_CRIOGENICO, GRANULAZIONE, SEPARAZIONE"),
]

# ============================================================
# DB_SOTTOPROCESSI: BLACK_MASS -> NHP (sottoprodotto) + LI2CO3 (prodotto)
#                    NHP -> COSO4 + NISO4 + LIOH (tutti prodotti)
# (id_sottoprocesso, sottoprodotto_input, tecnica, capex, opex, [(tipo,codice,resa)], fasi)
# ============================================================
sottoprocessi_def = [
    ("SP_BLACKMASS_IDROMET","BLACK_MASS","IDROMETALLURGIA_BLACK_MASS",2000,17000,
     [("sottoprodotto","NHP",0.55),("prodotto","LI2CO3",0.15)],
     "LISCIVIAZIONE_ACIDA_BLACK_MASS, SEPARAZIONE_SOLIDO_LIQUIDO, PRECIPITAZIONE_NHP, PRECIPITAZIONE_CARBONATO_LITIO"),
    # NHP non ha una tabella di composizione (a differenza dei macrocomponenti):
    # qui la resa e' SEMPRE una frazione diretta della massa in ingresso, quindi
    # la somma delle rese di piu' uscite dello stesso sottoprocesso deve restare
    # ben al di sotto del 100% (il resto e' scarto/perdita di processo)
    ("SP_NHP_SOLFATI","NHP","PRECIPITAZIONE_SELETTIVA_SOLFATI",2500,19000,
     [("prodotto","COSO4",0.25),("prodotto","NISO4",0.32),("prodotto","LIOH",0.09)],
     "LISCIVIAZIONE_ACIDA_NHP, PRECIPITAZIONE_SOLFATO_COBALTO, PRECIPITAZIONE_SOLFATO_NICHEL, CRISTALLIZZAZIONE_IDROSSIDO_LITIO"),

    # alternative aggiuntive (una seconda tecnica anche per BLACK_MASS e NHP)
    ("SP_BLACKMASS_ALT","BLACK_MASS","PIROMETALLURGIA_BLACK_MASS",1700,15000,
     [("sottoprodotto","NHP",0.45)],
     "ARROSTIMENTO_BLACK_MASS, FUSIONE, SEPARAZIONE_SCORIE, PRECIPITAZIONE_NHP"),
    ("SP_NHP_ALT","NHP","ESTRAZIONE_SOLVENTE_DIRETTA",2200,17000,
     [("prodotto","COSO4",0.23),("prodotto","NISO4",0.31)],
     "LISCIVIAZIONE_NHP, ESTRAZIONE_SOLVENTE_SELETTIVA, CRISTALLIZZAZIONE"),
]

# ============================================================
# Range min/max attorno al valore puntuale (invariato)
# ============================================================
def content_range(v):
    lo = round(max(v*0.85, 0.00001), 6)
    hi = round(min(v*1.15, 1.0), 6)
    return lo, hi

def recovery_range(v):
    lo = round(max(v*0.93, 0.01), 5)
    hi = round(min(v*1.05, 0.99), 5)
    return lo, hi

def esc(s):
    return s.replace("'", "''")

sql = ["SET search_path TO recupero_materie;\n"]

sql.append("-- DB_IMPIANTI")
for r in impianti:
    sql.append(
        f"INSERT INTO db_impianti (id_imp,tipologia,sotto_tecnologia,potenza_mw,anno_installazione,"
        f"anno_dismissione,regione,provincia,lat,lon) VALUES "
        f"('{r[0]}','{r[1]}','{r[2]}',{r[3]},{r[4]},{r[5]},'{esc(r[6])}','{esc(r[7])}',{r[8]},{r[9]});"
    )

sql.append("\n-- DB_PRODOTTI (ex db_elementi, + 4 composti terminali)")
for sym, nome, cat, prezzo in prodotti:
    p1, p2 = growth[cat]
    sql.append(
        f"INSERT INTO db_prodotti (prodotto,nome,categoria,prezzo_attuale_eur_kg,"
        f"proiezione_prezzo_p1,proiezione_prezzo_p2) VALUES "
        f"('{sym}','{esc(nome)}','{cat}',{prezzo},{p1},{p2});"
    )

sql.append("\n-- DB_SOTTOPRODOTTI (solo Black Mass e NHP, nessuna categoria)")
for sp, nome, prezzo, p1, p2 in sottoprodotti:
    sql.append(
        f"INSERT INTO db_sottoprodotti (sottoprodotto,nome,prezzo_attuale_eur_kg,"
        f"proiezione_prezzo_p1,proiezione_prezzo_p2) VALUES "
        f"('{sp}','{esc(nome)}',{prezzo},{p1},{p2});"
    )

sql.append("\n-- DB_MACRO (un rigo per macrocomponente: solo massa per MW, dato di ingresso)")
n_macro = 0
for id_macro, tip, sott, comp, massa, elems in macro_def:
    n_macro += 1
    sql.append(
        f"INSERT INTO db_macro (id_macro,tipologia,sotto_tecnologia,macro_componente,massa_kg_per_mw) VALUES "
        f"('{id_macro}','{tip}','{sott}','{comp}',{massa});"
    )

sql.append("\n-- DB_MACRO_PROCESSI (niente scenari)")
for id_mp, tip, sott, comp, tecnica, capex, opex, pv, p1, p2, fasi in macro_processi_def:
    sql.append(
        f"INSERT INTO db_macro_processi (id_processo_macro,tipologia,sotto_tecnologia,macro_componente,"
        f"tecnica,capex_eur_ton,opex_eur_ton,prezzo_vendita_eur_kg,proiezione_prezzo_p1,proiezione_prezzo_p2,descrizione_fasi) VALUES "
        f"('{id_mp}','{tip}','{sott}','{comp}','{tecnica}',{capex},{opex},{pv},{p1},{p2},'{esc(fasi)}');"
    )

sql.append("\n-- DB_PROCESSI (recupero diretto a prodotto, + CELLE->BLACK_MASS a sottoprodotto)")
n_proc = 0
# lookup del contenuto (da macro_def) per calcolare, UNA SOLA VOLTA in fase di
# generazione, la resa combinata (%contenuto x %efficienza) come frazione
# diretta della massa del macrocomponente: cosi' a runtime (calc.py) ogni
# bilancio di massa e' sempre "massa_in_ingresso x %resa", senza una tabella
# di contenuto intermedia da consultare
contenuto_lookup = {}
for id_macro, tip, sott, comp, massa, elems in macro_def:
    for prod, pct in elems:
        contenuto_lookup[(tip, sott, comp, prod)] = content_range(pct)

for id_proc, tip, sott, comp, tecnica, capex, opex, tipo_output, outs, fasi in proc_def:
    for codice, rec in outs:
        n_proc += 1
        if tipo_output == "prodotto":
            eff_lo, eff_hi = recovery_range(rec)
            cont_lo, cont_hi = contenuto_lookup[(tip, sott, comp, codice)]
            lo, hi = round(cont_lo * eff_lo, 6), round(cont_hi * eff_hi, 6)
            sql.append(
                f"INSERT INTO db_processi (id_processo,tipologia,sotto_tecnologia,macro_componente,tecnica,"
                f"capex_eur_ton,opex_eur_ton,tipo_output,prodotto,recupero_pct_min,recupero_pct_max,descrizione_fasi) VALUES "
                f"('{id_proc}','{tip}','{sott}','{comp}','{tecnica}',{capex},{opex},'prodotto','{codice}',{lo},{hi},'{esc(fasi)}');"
            )
        else:
            lo, hi = recovery_range(rec)
            sql.append(
                f"INSERT INTO db_processi (id_processo,tipologia,sotto_tecnologia,macro_componente,tecnica,"
                f"capex_eur_ton,opex_eur_ton,tipo_output,sottoprodotto_output,recupero_pct_min,recupero_pct_max,descrizione_fasi) VALUES "
                f"('{id_proc}','{tip}','{sott}','{comp}','{tecnica}',{capex},{opex},'sottoprodotto','{codice}',{lo},{hi},'{esc(fasi)}');"
            )

sql.append("\n-- DB_SOTTOPROCESSI (BLACK_MASS -> NHP+LI2CO3 ; NHP -> COSO4+NISO4+LIOH)")
for id_sp, input_sp, tecnica, capex, opex, outs, fasi in sottoprocessi_def:
    for tipo_output, codice, rec in outs:
        lo, hi = recovery_range(rec)
        if tipo_output == "prodotto":
            sql.append(
                f"INSERT INTO db_sottoprocessi (id_sottoprocesso,sottoprodotto,tecnica,capex_eur_ton,opex_eur_ton,"
                f"tipo_output,prodotto,recupero_pct_min,recupero_pct_max,descrizione_fasi) VALUES "
                f"('{id_sp}','{input_sp}','{tecnica}',{capex},{opex},'prodotto','{codice}',{lo},{hi},'{esc(fasi)}');"
            )
        else:
            sql.append(
                f"INSERT INTO db_sottoprocessi (id_sottoprocesso,sottoprodotto,tecnica,capex_eur_ton,opex_eur_ton,"
                f"tipo_output,sottoprodotto_output,recupero_pct_min,recupero_pct_max,descrizione_fasi) VALUES "
                f"('{id_sp}','{input_sp}','{tecnica}',{capex},{opex},'sottoprodotto','{codice}',{lo},{hi},'{esc(fasi)}');"
            )

sql.append("\n-- DB_INDICI_RIVALUTAZIONE")
sql.append("INSERT INTO db_indici_rivalutazione VALUES ('ISTAT','Indice ISTAT prezzi al consumo (FOI)',0.02);")
sql.append("INSERT INTO db_indici_rivalutazione VALUES ('EDILIZIA','Indice costi di costruzione',0.03);")
sql.append("INSERT INTO db_indici_rivalutazione VALUES ('NESSUNA','Nessuna rivalutazione (costi costanti)',0.0);")

with open("/home/claude/recupero_fastapi/db/02_seed_data.sql", "w") as f:
    f.write("\n".join(sql) + "\n")

print(f"impianti={len(impianti)} prodotti={len(prodotti)} sottoprodotti={len(sottoprodotti)} "
      f"macro_righe={n_macro} macro_processi={len(macro_processi_def)} processi_righe={n_proc} "
      f"sottoprocessi_righe={sum(len(o) for _,_,_,_,_,o,_ in sottoprocessi_def)}")
