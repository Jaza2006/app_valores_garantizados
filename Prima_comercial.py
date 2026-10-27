# Prima_comercial.py
from PNN import calcular_pnn, calcular_anualidad_pagos


def calcular_ppt(
    df_tabla, tipo_seguro: str, x: int, n: int = None, p: int = None,
    sa: float = 1.0,
    gasto_admin_millar: float = 0.005,   # γ, fracción de la SA (0.005 = 5 al millar)
    gasto_cobranza_pct: float = 0.05,    # β, fracción de B
    alpha_honorarios: float = 0.0,       # α, fracción de la SA
    k_comision: float = 0.0,             # K, fracción de B (ej. 0.05 * p)
    detalle: bool = False,
):
    # Todo por unidad de suma asegurada
    pnn_u = calcular_pnn(df_tabla, tipo_seguro, x, n=n, p=p, sa=1.0)
    ax_pagos = calcular_anualidad_pagos(df_tabla, tipo_seguro, x, n=n, p=p)
    ax_seguro = calcular_anualidad_pagos(df_tabla, tipo_seguro, x, n=n, p=None)

    numerador = pnn_u * ax_pagos + alpha_honorarios + gasto_admin_millar * ax_seguro
    denominador = ax_pagos - k_comision - gasto_cobranza_pct * ax_pagos

    if denominador <= 0:
        raise ValueError(
            "Denominador <= 0: los recargos K y β son demasiado altos "
            f"para ä_x:p = {ax_pagos:.4f}."
        )

    ppt_u = numerador / denominador
    total = ppt_u * sa

    if detalle:
        return {
            'PNN_unitaria': pnn_u, 'a_x_p': ax_pagos, 'a_x_n': ax_seguro,
            'numerador': numerador, 'denominador': denominador,
            'K': k_comision, 'PPT_unitaria': ppt_u, 'PPT_total': total,
        }
    return total