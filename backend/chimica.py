"""Pesi atomici e composizione in massa da una formula chimica (es. FePO4,
Li2CO3, Ca(OH)2, CuSO4·5H2O). Usato dal bilancio per elemento: un prodotto
con formula cattura i suoi elementi in proporzione alla sua composizione."""
import re

# pesi atomici standard (IUPAC, arrotondati a 3 decimali)
PESI_ATOMICI = {
    "H": 1.008, "He": 4.003, "Li": 6.94, "Be": 9.012, "B": 10.81, "C": 12.011, "N": 14.007, "O": 15.999,
    "F": 18.998, "Ne": 20.180, "Na": 22.990, "Mg": 24.305, "Al": 26.982, "Si": 28.085, "P": 30.974,
    "S": 32.06, "Cl": 35.45, "Ar": 39.948, "K": 39.098, "Ca": 40.078, "Sc": 44.956, "Ti": 47.867,
    "V": 50.942, "Cr": 51.996, "Mn": 54.938, "Fe": 55.845, "Co": 58.933, "Ni": 58.693, "Cu": 63.546,
    "Zn": 65.38, "Ga": 69.723, "Ge": 72.630, "As": 74.922, "Se": 78.971, "Br": 79.904, "Kr": 83.798,
    "Rb": 85.468, "Sr": 87.62, "Y": 88.906, "Zr": 91.224, "Nb": 92.906, "Mo": 95.95, "Ru": 101.07,
    "Rh": 102.906, "Pd": 106.42, "Ag": 107.868, "Cd": 112.414, "In": 114.818, "Sn": 118.710,
    "Sb": 121.760, "Te": 127.60, "I": 126.904, "Xe": 131.293, "Cs": 132.905, "Ba": 137.327,
    "La": 138.905, "Ce": 140.116, "Pr": 140.908, "Nd": 144.242, "Sm": 150.36, "Eu": 151.964,
    "Gd": 157.25, "Tb": 158.925, "Dy": 162.500, "Ho": 164.930, "Er": 167.259, "Yb": 173.045,
    "Lu": 174.967, "Hf": 178.49, "Ta": 180.948, "W": 183.84, "Re": 186.207, "Os": 190.23,
    "Ir": 192.217, "Pt": 195.084, "Au": 196.967, "Hg": 200.592, "Tl": 204.38, "Pb": 207.2,
    "Bi": 208.980, "U": 238.029,
}

_SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def normalizza(formula: str) -> str:
    """Na₂SO₄ -> Na2SO4 (pedici unicode), spazi rimossi."""
    return (formula or "").translate(_SUB).replace(" ", "")


def atomi(formula: str) -> dict[str, float]:
    """'Li2CO3' -> {'Li': 2, 'C': 1, 'O': 3}. Supporta parentesi e idrati (·/.)."""
    f = normalizza(formula)
    if not f:
        raise ValueError("formula vuota")
    totale: dict[str, float] = {}
    for parte in re.split(r"[·.*]", f):
        m = re.match(r"^(\d+)(.*)$", parte)
        molt, parte = (int(m.group(1)), m.group(2)) if m else (1, parte)
        for el, n in _parse(parte).items():
            totale[el] = totale.get(el, 0) + n * molt
    return totale


def _parse(s: str) -> dict[str, float]:
    stack = [{}]
    i = 0
    while i < len(s):
        c = s[i]
        if c == "(":
            stack.append({})
            i += 1
        elif c == ")":
            i += 1
            m = re.match(r"\d+", s[i:])
            n = int(m.group()) if m else 1
            i += len(m.group()) if m else 0
            grp = stack.pop()
            for el, k in grp.items():
                stack[-1][el] = stack[-1].get(el, 0) + k * n
        else:
            m = re.match(r"([A-Z][a-z]?)(\d*)", s[i:])
            if not m:
                raise ValueError(f"formula non valida: {s}")
            el, n = m.group(1), int(m.group(2) or 1)
            if el not in PESI_ATOMICI:
                raise ValueError(f"elemento sconosciuto nella formula: {el}")
            stack[-1][el] = stack[-1].get(el, 0) + n
            i += len(m.group())
    if len(stack) != 1:
        raise ValueError(f"parentesi non bilanciate: {s}")
    return stack[0]


def peso_molare(formula: str) -> float:
    return sum(PESI_ATOMICI[e] * n for e, n in atomi(formula).items())


def composizione(formula: str) -> dict[str, float]:
    """frazioni in massa (0..1) degli elementi nella formula"""
    a = atomi(formula)
    pm = sum(PESI_ATOMICI[e] * n for e, n in a.items())
    return {e: PESI_ATOMICI[e] * n / pm for e, n in a.items()}
