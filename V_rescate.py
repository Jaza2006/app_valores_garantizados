# V_rescate.py
import pandas as pd
from PNUS import calcular_pnu
from PNN import calcular_anualidad_pagos, calcular_pnn
from Prima_comercial import calcular_ppt
from tipo_recargo import calcular_k
from utils import normalizar_tipo


def calcular_valor_rescate(
    tipo_seguro: str, df_tabla: pd.DataFrame, x: int, t: int,
    n: int = None, p: int = None, sa: float = 1.0,
    gasto_admin_millar: float = 0.005, gasto_cobranza_pct: float = 0.05,
    alpha_honorarios: float = 0.0,
    prima_comercial: float = None      # B anual TOTAL, si ya la calculaste
) -> dict:
    tipo = normalizar_tipo(tipo_seguro)
    es_vit = (tipo == 'vitalicio')
    if t < 0:
        raise ValueError("t no puede ser negativo.")

    if es_vit:
        n = None
        p = p if (p and p > 0) else None          # None = paga toda la vida
    else:
        if n is None or n <= 0:
            raise ValueError(f"Se requiere n > 0 para '{tipo}'.")
        if t > n:
            raise ValueError(f"t={t} excede el plazo del seguro n={n}.")
        p = p if (p and p > 0) else n
        if p > n:
            raise ValueError(f"El plazo de pago p={p} no puede exceder n={n}.")

    x_t = x + t
    n_rest = None if es_vit else n - t

    # Vencimiento: dotales pagan la SA, el temporal ya no tiene valor
    if n_rest == 0:
        reserva = 0.0 if tipo == 'temporal' else sa
        return {'t': t, 'edad_actual': x_t, 'Reserva_Neta': reserva,
                'Ajuste_Zillmer': 0.0, 'Reserva_Matematica': reserva,
                'Valor_Rescate_Final': reserva}

    # 1. PNU prospectiva a la edad x+t por el resto de la vigencia
    pnu_futura = calcular_pnu(df_tabla, tipo, x_t, n=n_rest, sa=sa)

    # 2. Primas futuras y ajuste de Zillmer (solo mientras t < p)
    if p is None or t < p:
        p_rest = None if p is None else p - t
        ax_futura = calcular_anualidad_pagos(df_tabla, tipo, x_t, n=n_rest, p=p_rest)
        ax_inicial = calcular_anualidad_pagos(df_tabla, tipo, x, n=n, p=p)
        pnn_anual = calcular_pnn(df_tabla, tipo, x, n=n, p=p, sa=sa)

        p_k = p if p else int(df_tabla['x'].max()) + 1 - x   # vitalicio sin p
        k = calcular_k(tipo, p_k)

        if prima_comercial is None:
            prima_comercial = calcular_ppt(
                df_tabla, tipo, x, n=n, p=p, sa=sa,
                gasto_admin_millar=gasto_admin_millar,
                gasto_cobranza_pct=gasto_cobranza_pct,
                alpha_honorarios=alpha_honorarios, k_comision=k)

        ajuste_zillmer = k * prima_comercial * ax_futura / ax_inicial
    else:
        ax_futura = 0.0
        pnn_anual = 0.0
        ajuste_zillmer = 0.0

    reserva_neta = pnu_futura - pnn_anual * ax_futura
    reserva_zillmer = reserva_neta - ajuste_zillmer

    return {
        't': t,
        'edad_actual': x_t,
        'Reserva_Neta': reserva_neta,
        'Ajuste_Zillmer': ajuste_zillmer,
        'Reserva_Matematica': reserva_zillmer,
        'Valor_Rescate_Final': max(0.0, reserva_zillmer),
    }