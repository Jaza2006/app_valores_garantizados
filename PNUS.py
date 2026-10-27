# PNUS.py
import pandas as pd
from conmutacion_tabla import obtener_valores_conmutados


def _normalizar_tipo(tipo_seguro: str) -> str:
    t = str(tipo_seguro).lower().strip().replace(" ", "_")
    if t in ("vitalicio", "vida_entera"):
        return "vitalicio"
    if t in ("dotal", "dotal_mixto"):      # "dotal" a secas = mixto
        return "dotal_mixto"
    if t == "dotal_puro":
        return "dotal_puro"
    if t.startswith("temporal"):
        return "temporal"
    raise ValueError(f"Tipo de seguro no válido: '{tipo_seguro}'.")


def calcular_pnu(df_tabla: pd.DataFrame, tipo_seguro: str, x: int,
                 n: int = None, sa: float = 1.0) -> float:
    tipo = _normalizar_tipo(tipo_seguro)
    if sa <= 0:
        raise ValueError("La suma asegurada debe ser positiva.")

    datos_x = obtener_valores_conmutados(df_tabla, x)
    if not datos_x['Dx']:
        raise ValueError(f"Dx = 0 a la edad {x}.")

    if tipo == 'vitalicio':
        unitaria = datos_x['Mx'] / datos_x['Dx']
    else:
        if n is None or n <= 0:
            raise ValueError(f"El plazo n > 0 es requerido para '{tipo}'.")
        xn = obtener_valores_conmutados(df_tabla, x + n)
        if tipo == 'temporal':
            unitaria = (datos_x['Mx'] - xn['Mx']) / datos_x['Dx']
        elif tipo == 'dotal_mixto':
            unitaria = (datos_x['Mx'] - xn['Mx'] + xn['Dx']) / datos_x['Dx']
        else:  # dotal_puro
            unitaria = xn['Dx'] / datos_x['Dx']

    return sa * unitaria