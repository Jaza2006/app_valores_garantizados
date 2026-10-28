
def normalizar_tipo(tipo_seguro: str) -> str:
    """Regresa: 'vitalicio', 'temporal', 'dotal_mixto' o 'dotal_puro'."""
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