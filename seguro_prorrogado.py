# seguro_prorrogado.py
import pandas as pd
from conmutacion_tabla import obtener_valores_conmutados
from V_rescate import calcular_valor_rescate
from utils import normalizar_tipo   # la _normalizar_tipo única que sugerí


def calcular_seguro_prorrogado(
    tipo_seguro: str, df_tabla: pd.DataFrame, x: int, t: int,
    n: int = None, p: int = None, sa: float = 1.0,
    gasto_admin_millar: float = 0.005, gasto_cobranza_pct: float = 0.05,
    alpha_honorarios: float = 0.0
) -> dict:
    tipo = normalizar_tipo(tipo_seguro)
    vr_info = calcular_valor_rescate(tipo_seguro, df_tabla, x, t, n, p, sa,
                                     gasto_admin_millar, gasto_cobranza_pct,
                                     alpha_honorarios)
    vr = vr_info['Valor_Rescate_Final']
    x_t = x + t

    resultado_cero = {'anios_prorroga': 0, 'meses_prorroga': 0, 'dias_prorroga': 0,
                      'dias_adicionales': 0, 'dote_sobrante_futura': 0.0}
    if vr <= 0:
        return resultado_cero

    # Tope de la prórroga: m <= n - t (o hasta el fin de la tabla si es vitalicio)
    if tipo == 'vitalicio':
        m_max = int(df_tabla['x'].max()) + 1 - x_t
    else:
        if n is None:
            raise ValueError("Se requiere n para calcular el seguro prorrogado.")
        m_max = n - t
    if m_max <= 0:
        return resultado_cero

    d_xt = obtener_valores_conmutados(df_tabla, x_t)
    if not d_xt['Dx']:
        raise ValueError(f"Dx = 0 a la edad {x_t}.")

    # Rescate expresado en unidades de M:  V/SA = (M_{x+t} - M_{x+t+m}) / D_{x+t}
    objetivo = vr / sa * d_xt['Dx']
    m_xt = d_xt['Mx']

    m = 0
    while m < m_max:
        costo_sig = m_xt - obtener_valores_conmutados(df_tabla, x_t + m + 1)['Mx']
        if costo_sig <= objetivo:
            m += 1
        else:
            break

    costo_m = m_xt - obtener_valores_conmutados(df_tabla, x_t + m)['Mx']
    sobrante_M = objetivo - costo_m          # en unidades de M, edad x+t

    dias_ad = 0
    dote = 0.0
    if m < m_max:
        # Interpolación lineal dentro del año m+1:  C_{x+t+m} = M_{x+t+m} - M_{x+t+m+1}
        c = obtener_valores_conmutados(df_tabla, x_t + m)['Cx']
        fraccion = sobrante_M / c            # 0 <= fraccion < 1
        dias_ad = int(round(fraccion * 365))
    elif tipo != 'vitalicio' and sobrante_M > 1e-9:
        # Alcanzó toda la vigencia: el excedente compra un dotal puro
        d_fin = obtener_valores_conmutados(df_tabla, x_t + m)['Dx']
        if d_fin:
            dote = sobrante_M * sa / d_fin   # = excedente / nEx

    return {
        'anios_prorroga': m,
        'meses_prorroga': dias_ad // 30,     # aproximación comercial
        'dias_prorroga': dias_ad % 30,
        'dias_adicionales': dias_ad,         # dato exacto (base 365)
        'dote_sobrante_futura': dote,
    }