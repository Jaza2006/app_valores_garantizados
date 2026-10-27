def _normalizar_tipo(tipo_seguro: str) -> str:
    tipo = str(tipo_seguro).lower().strip().replace(" ", "_")
    if tipo in ("vitalicio", "vida_entera") or tipo.startswith("dotal"):
        return "vitalicio_dotal"
    if tipo.startswith("temporal"):
        return "temporal"
    raise ValueError(
        f"Tipo de seguro no reconocido: '{tipo_seguro}'. "
        "Usa vitalicio, dotal (mixto/puro) o temporal."
    )


def obtener_recargos(tipo_seguro: str) -> dict:
    grupo = _normalizar_tipo(tipo_seguro)
    if grupo == "vitalicio_dotal":
        return {
            'admin_min': 0.005, 'admin_max': 0.007,
            'cobranza_min': 0.05, 'cobranza_max': 0.07
        }
    return {  # temporal
        'admin_min': 0.002, 'admin_max': 0.003,
        'cobranza_min': 0.05, 'cobranza_max': 0.07
    }


def calcular_k(tipo_seguro: str, p: int) -> float:
    """k = % de comisión de agenciamiento sobre la prima comercial B.
    p = plazo de pago de primas en años."""
    if p is None or p <= 0:
        raise ValueError("El plazo de pago p debe ser un entero positivo.")

    grupo = _normalizar_tipo(tipo_seguro)
    if grupo == "vitalicio_dotal":
        return min(0.05 * p, 1.00)
    return min(0.03 * p, 0.60)  # temporal