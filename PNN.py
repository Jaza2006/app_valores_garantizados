# PNN.py
import pandas as pd
from conmutacion_tabla import obtener_valores_conmutados
from PNUS import calcular_pnu


def _normalizar_tipo(tipo_seguro: str) -> str:
    t = str(tipo_seguro).lower().strip().replace(" ", "_")
    if t in ("vitalicio", "vida_entera"):
        return "vitalicio"
    if t.startswith("dotal"):      # dotal_mixto, dotal_puro
        return "dotal"
    if t.startswith("temporal"):
        return "temporal"
    raise ValueError(f"Tipo de seguro no válido: '{tipo_seguro}'.")


def calcular_anualidad_pagos(
    df_tabla: pd.DataFrame,
    tipo_seguro: str,
    x: int,
    n: int = None,
    p: int = None
) -> float:
    """ä_{x:p]} = (Nx - N_{x+p}) / Dx  (anualidad anticipada de pago de primas).
    p=None o 0 significa pago durante todo el plazo del seguro.
    En vitalicio sin p, es la anualidad vitalicia ä_x = Nx / Dx."""
    tipo = _normalizar_tipo(tipo_seguro)
    p = p or None  # 0 se trata como "sin plazo de pago limitado"

    if p is not None and p < 0:
        raise ValueError("El plazo de pago p no puede ser negativo.")

    if tipo == "vitalicio":
        plazo_p = p  # None = vitalicio pagando toda la vida
    else:
        if n is None or n <= 0:
            raise ValueError("Para dotal/temporal se requiere n > 0.")
        plazo_p = n if p is None else p
        if plazo_p > n:
            raise ValueError(f"El plazo de pago p={plazo_p} no puede exceder n={n}.")

    datos_x = obtener_valores_conmutados(df_tabla, x)
    if not datos_x['Dx']:
        raise ValueError(f"Dx = 0 a la edad {x}; no se puede calcular la anualidad.")

    if plazo_p is None:
        return datos_x['Nx'] / datos_x['Dx']

    datos_xp = obtener_valores_conmutados(df_tabla, x + plazo_p)
    anualidad = (datos_x['Nx'] - datos_xp['Nx']) / datos_x['Dx']
    if anualidad <= 0:
        raise ValueError("La anualidad de pagos resultó <= 0; revisa x, p y la tabla.")
    return anualidad


def calcular_pnn(
    df_tabla: pd.DataFrame,
    tipo_seguro: str,
    x: int,
    n: int = None,
    p: int = None,
    sa: float = 1.0
) -> float:
    pnu = calcular_pnu(df_tabla=df_tabla, tipo_seguro=tipo_seguro,
                       x=x, n=n, sa=sa)
    ax_pagos = calcular_anualidad_pagos(df_tabla, tipo_seguro, x, n, p)
    return pnu / ax_pagos