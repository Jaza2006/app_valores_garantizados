# seguro_saldado.py
import pandas as pd
from V_rescate import calcular_valor_rescate
from PNUS import calcular_pnu
from utils import normalizar_tipo   # la normalizar_tipo única


def calcular_seguro_saldado(
    tipo_seguro: str, df_tabla: pd.DataFrame, x: int, t: int,
    n: int = None, p: int = None, sa: float = 1.0,
    gasto_admin_millar: float = 0.005, gasto_cobranza_pct: float = 0.05,
    alpha_honorarios: float = 0.0
) -> dict:
    tipo = normalizar_tipo(tipo_seguro)   # 'vitalicio', 'temporal', 'dotal_mixto', 'dotal_puro'
    if t < 0:
        raise ValueError("t no puede ser negativo.")

    if tipo == 'vitalicio':
        n_restante = None
    else:
        if n is None or n <= 0:
            raise ValueError(f"Se requiere n > 0 para '{tipo}'.")
        if t > n:
            raise ValueError(f"t={t} excede el plazo del seguro n={n}.")
        n_restante = n - t

    x_t = x + t

    # Vencimiento del plan: no hay prima única que dividir
    if n_restante == 0:
        sa_saldada = 0.0 if tipo == 'temporal' else sa   # dotales pagan la SA
        return {'t': t, 'edad_actual': x_t, 'SA_Saldada': sa_saldada}

    vr = calcular_valor_rescate(tipo_seguro, df_tabla, x, t, n, p, sa,
                                gasto_admin_millar, gasto_cobranza_pct,
                                alpha_honorarios)['Valor_Rescate_Final']

    if vr <= 0:
        return {'t': t, 'edad_actual': x_t, 'SA_Saldada': 0.0}

    # Prima única unitaria a edad x+t por el resto de la vigencia
    pnu_u = calcular_pnu(df_tabla, tipo_seguro, x_t, n=n_restante, sa=1.0)
    if pnu_u <= 0:
        raise ValueError(f"PNU unitaria <= 0 a la edad {x_t}; revisa la tabla.")

    sa_saldada = vr / pnu_u

    if sa_saldada > sa * (1 + 1e-9):
        raise ValueError(
            f"La suma saldada ({sa_saldada:,.2f}) excede la SA ({sa:,.2f}). "
            "Revisa el valor de rescate (reserva, K, B o índices)."
        )

    return {'t': t, 'edad_actual': x_t, 'SA_Saldada': min(sa_saldada, sa)}
    #& C:\Users\Admon\AppData\Local\Python\pythoncore-3.14-64\python.exe -m streamlit run c:/Users/Admon/Downloads/interfaz.py