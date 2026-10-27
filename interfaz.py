# app.py
import os
import pandas as pd
import streamlit as st

from conmutacion_tabla import cargar_y_conmutar_tabla
from tipo_recargo import obtener_recargos, calcular_k
from Prima_comercial import calcular_ppt
from V_rescate import calcular_valor_rescate
from seguro_saldado import calcular_seguro_saldado
from seguro_prorrogado import calcular_seguro_prorrogado
from reporte_pdf import generar_pdf_ejecutivo
from login import requiere_login, boton_cerrar_sesion

st.set_page_config(
    page_title="Seguros JR - Valores Garantizados",
    page_icon="🛡️",
    layout="wide",
)

# Inicio de sesión (ver login.py)
requiere_login()

st.title("🛡️ Seguros JR - Valores Garantizados")
st.caption("Calculadora de Prima Comercial y Valores Garantizados")
st.markdown("---")

boton_cerrar_sesion()

# ---------------------------------------------------------------
# 1. PARÁMETROS FINANCIEROS Y TABLA
# ---------------------------------------------------------------
st.sidebar.header("📁 1. Configuración Financiera y Tabla")
archivo_subido = st.sidebar.file_uploader(
    "Cargar Tabla de Mortalidad (.xlsm / .xlsx)", type=["xlsm", "xlsx"]
)

tasa_pct = st.sidebar.number_input(
    "Tasa de Interés Anual (i) [%]",
    min_value=0.01, max_value=10.00, value=4.00, step=0.25, format="%.2f",
)
tasa_interes = tasa_pct / 100.0


@st.cache_data
def obtener_tabla_conmutada(archivo, tasa):
    if archivo is not None:
        return cargar_y_conmutar_tabla(archivo, tasa)
    ruta_defecto = "tabla de mortalidad 2000 para programa.xlsm"
    if os.path.exists(ruta_defecto):
        return cargar_y_conmutar_tabla(ruta_defecto, tasa)
    return None


try:
    df_tabla = obtener_tabla_conmutada(archivo_subido, tasa_interes)
except Exception as e:
    st.error(f"❌ No pude leer la tabla de mortalidad: {e}")
    st.stop()

if df_tabla is None:
    st.warning("⚠️ Por favor sube la tabla de mortalidad para continuar.")
    st.stop()

edad_max_tabla = int(df_tabla["x"].max())
# w = última edad de la tabla con sobrevivientes (l_x > 0)
edad_omega = int(df_tabla.loc[df_tabla["l_x"] > 0, "x"].max())

# ---------------------------------------------------------------
# 2. PARÁMETROS DE LA PÓLIZA
# ---------------------------------------------------------------
st.sidebar.header("📋 2. Parámetros de la Póliza")

TIPOS = {
    "Dotal mixto": "dotal_mixto",
    "Dotal puro": "dotal_puro",
    "Temporal": "temporal",
    "Vitalicio": "vitalicio",
}
tipo_etiqueta = st.sidebar.selectbox("Tipo de Seguro", list(TIPOS.keys()), index=0)
tipo_seguro = TIPOS[tipo_etiqueta]
es_vitalicio = tipo_seguro == "vitalicio"

edad_x = int(st.sidebar.number_input(
    "Edad de Contratación (x)", min_value=12, max_value=100, value=25, step=1
))

suma_asegurada = st.sidebar.number_input(
    "Suma Asegurada ($)", min_value=10000, value=450000, step=10000
)

if edad_x >= edad_omega:
    st.error(f"❌ La edad x={edad_x} debe ser menor que la edad límite de la tabla ({edad_omega}).")
    st.stop()

if es_vitalicio:
    # Vitalicio: no hay n. Se proyecta automáticamente hasta la edad límite w.
    n_poliza = None
    horizonte = edad_omega - edad_x
    st.sidebar.info(
        f"Se proyecta hasta la edad límite de la tabla (w = {edad_omega}): "
        f"{horizonte} años."
    )
    pago_vitalicio = st.sidebar.checkbox("Pagar primas toda la vida", value=False)
    if pago_vitalicio:
        p_poliza = None
    else:
        max_p = edad_omega - edad_x
        p_poliza = int(st.sidebar.number_input(
            "Plazo Pagos (p)", min_value=1, max_value=max_p, value=min(20, max_p)
        ))
else:
    n_poliza = int(st.sidebar.number_input(
        "Plazo Cobertura (n)", min_value=1, max_value=50, value=25
    ))
    p_poliza = int(st.sidebar.number_input(
        "Plazo Pagos (p)", min_value=1, max_value=50, value=min(20, n_poliza)
    ))
    if p_poliza > n_poliza:
        st.error("❌ El plazo de pagos (p) no puede ser mayor que el plazo de cobertura (n).")
        st.stop()
    if edad_x + n_poliza > edad_omega:
        st.error(
            f"❌ La edad final ({edad_x + n_poliza}) excede la máxima edad "
            f"disponible en la tabla ({edad_omega})."
        )
        st.stop()
    horizonte = n_poliza

# ---------------------------------------------------------------
# 3. RECARGOS Y GASTOS
# ---------------------------------------------------------------
st.sidebar.header("⚙️ 3. Recargos y Gastos")
rangos = obtener_recargos(tipo_seguro)

escenario = st.sidebar.radio("Escenario de recargo:", ["Mínimo", "Máximo"], index=1)
sufijo = "min" if escenario == "Mínimo" else "max"
gasto_admin = rangos[f"admin_{sufijo}"]        # γ, fracción de la SA
gasto_cobranza = rangos[f"cobranza_{sufijo}"]  # β, fracción de B

alpha_millar = st.sidebar.number_input(
    "Honorarios médicos (α) [al millar de la SA]",
    min_value=0.0, value=0.0, step=0.5,
)
alpha_honorarios = alpha_millar / 1000.0       # fracción de la SA

# K de adquisición (sobre B): se calcula con el plazo de pago de primas
p_para_k = p_poliza if p_poliza else (edad_max_tabla + 1 - edad_x)  # vitalicio pago vitalicio
try:
    k_comision = calcular_k(tipo_seguro, p_para_k)
except Exception as e:
    st.error(f"❌ Error calculando K: {e}")
    st.stop()

# ---------------------------------------------------------------
# 4. EVALUACIÓN PUNTUAL
# ---------------------------------------------------------------
st.sidebar.header("🔍 4. Evaluación de Rescate")
anio_evaluar = st.sidebar.slider(
    "Año a evaluar (t)", min_value=1, max_value=int(horizonte), value=min(5, int(horizonte))
)

calcular = st.sidebar.button("🚀 Calcular Resultados", type="primary")

# ---------------------------------------------------------------
# CÁLCULOS
# ---------------------------------------------------------------
if calcular or st.session_state.get("generado"):
    st.session_state["generado"] = True

    try:
        # Primas (una sola llamada; detalle=True trae los componentes)
        det = calcular_ppt(
            df_tabla=df_tabla, tipo_seguro=tipo_seguro, x=edad_x,
            n=n_poliza, p=p_poliza, sa=suma_asegurada,
            gasto_admin_millar=gasto_admin,
            gasto_cobranza_pct=gasto_cobranza,
            alpha_honorarios=alpha_honorarios,
            k_comision=k_comision,
            detalle=True,
        )
        pnn = det["PNN_unitaria"] * suma_asegurada
        ppt = det["PPT_total"]

        # Tabla proyectada (B se calcula una vez y se reutiliza en el rescate)
        filas = []
        for t in range(1, int(horizonte) + 1):
            res_vr = calcular_valor_rescate(
                tipo_seguro, df_tabla, edad_x, t, n_poliza, p_poliza,
                suma_asegurada, gasto_admin, gasto_cobranza, alpha_honorarios,
                prima_comercial=ppt,
            )
            res_ss = calcular_seguro_saldado(
                tipo_seguro, df_tabla, edad_x, t, n_poliza, p_poliza,
                suma_asegurada, gasto_admin, gasto_cobranza, alpha_honorarios,
            )
            res_sp = calcular_seguro_prorrogado(
                tipo_seguro, df_tabla, edad_x, t, n_poliza, p_poliza,
                suma_asegurada, gasto_admin, gasto_cobranza, alpha_honorarios,
            )
            filas.append({"t": t, "vr": res_vr, "ss": res_ss, "sp": res_sp})

    except Exception as e:
        st.error(f"❌ Error en cálculo actuarial: {e}")
        st.stop()

    # ---------------- Resultados de primas ----------------
    st.subheader("💵 Resultados de la Póliza (Primas)")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Prima Neta Nivelada (PNN)", f"${pnn:,.2f}")
    c2.metric("Prima Comercial (PPT)", f"${ppt:,.2f}")
    c3.metric("Gasto Admin (γ)", f"{gasto_admin * 1000:.2f} ‰")
    c4.metric("Gasto Cobranza (β)", f"{gasto_cobranza * 100:.2f}%")
    c5.metric("Comisión (K)", f"{k_comision * 100:.1f}%")

    with st.expander("🔎 Detalle del cálculo de la prima comercial"):
        st.write({
            "PNN unitaria": det["PNN_unitaria"],
            "ä_x:p (pagos)": det["a_x_p"],
            "ä_x:n (seguro)": det["a_x_n"],
            "Numerador": det["numerador"],
            "Denominador": det["denominador"],
            "K": det["K"],
            "PPT unitaria": det["PPT_unitaria"],
            "PPT total": det["PPT_total"],
        })

    st.markdown("---")

    # ---------------- Valores garantizados al año t ----------------
    fila_t = next(f for f in filas if f["t"] == anio_evaluar)
    vr_t, ss_t, sp_t = fila_t["vr"], fila_t["ss"], fila_t["sp"]

    prorroga_str = (
        f"{sp_t.get('anios_prorroga', 0)} años, "
        f"{sp_t.get('meses_prorroga', 0)} meses, "
        f"{sp_t.get('dias_prorroga', 0)} días"
    )

    st.subheader(f"📌 Valores Garantizados al Año t = {anio_evaluar} (Edad {edad_x + anio_evaluar})")
    v1, v2, v3, v4 = st.columns(4)
    v1.metric("1. Valor de Rescate", f"${vr_t['Valor_Rescate_Final']:,.2f}")
    v2.metric("2. Seguro Saldado", f"${ss_t.get('SA_Saldada', 0.0):,.2f}")
    v3.metric("3. Seguro Prorrogado", prorroga_str)
    v4.metric("Dote Sobrante", f"${sp_t.get('dote_sobrante_futura', 0.0):,.2f}")

    with st.expander("🔎 Detalle de la reserva al año t"):
        st.write({
            "Reserva neta": vr_t.get("Reserva_Neta"),
            "Ajuste de Zillmer": vr_t.get("Ajuste_Zillmer"),
            "Reserva Zillmerizada": vr_t.get("Reserva_Matematica"),
            "Valor de rescate (mín. 0)": vr_t.get("Valor_Rescate_Final"),
        })

    st.markdown("---")

    # ---------------- Tabla proyectada ----------------
    st.subheader("📋 Tabla Proyectada de Valores Garantizados")

    df_resultado = pd.DataFrame([
        {
            "Año (t)": f["t"],
            "Edad (x+t)": edad_x + f["t"],
            "Reserva Neta ($)": f["vr"].get("Reserva_Neta", 0.0),
            "Ajuste Zillmer ($)": f["vr"].get("Ajuste_Zillmer", 0.0),
            "Valor de Rescate ($)": f["vr"]["Valor_Rescate_Final"],
            "Seguro Saldado ($)": f["ss"].get("SA_Saldada", 0.0),
            "Prórroga (Tiempo)": (
                f"{f['sp'].get('anios_prorroga', 0)}a "
                f"{f['sp'].get('meses_prorroga', 0)}m "
                f"{f['sp'].get('dias_prorroga', 0)}d"
            ),
            "Dote Sobrante ($)": f["sp"].get("dote_sobrante_futura", 0.0),
        }
        for f in filas
    ])

    st.dataframe(
        df_resultado.style.format({
            "Reserva Neta ($)": "{:,.2f}",
            "Ajuste Zillmer ($)": "{:,.2f}",
            "Valor de Rescate ($)": "{:,.2f}",
            "Seguro Saldado ($)": "{:,.2f}",
            "Dote Sobrante ($)": "{:,.2f}",
        }),
        width="stretch",
    )

    # ---------------- Exportar ----------------
    col_csv, col_pdf = st.columns(2)

    col_csv.download_button(
        "⬇️ Descargar tabla (CSV)",
        df_resultado.to_csv(index=False).encode("utf-8-sig"),
        file_name="valores_garantizados.csv",
        mime="text/csv",
        use_container_width=True,
    )

    try:
        nombre_tabla = (
            archivo_subido.name if archivo_subido is not None
            else "tabla de mortalidad 2000 (por defecto)"
        )
        pdf_bytes = generar_pdf_ejecutivo(
            params={
                "tipo": tipo_etiqueta,
                "edad": edad_x,
                "sa": suma_asegurada,
                "plazo_cobertura": f"{n_poliza} años" if n_poliza else f"Vitalicio (hasta la edad {edad_omega})",
                "plazo_pagos": f"{p_poliza} años" if p_poliza else "Toda la vida",
                "tasa_pct": tasa_pct,
                "tabla": nombre_tabla,
                "escenario": escenario,
            },
            primas={
                "pnn": pnn, "ppt": ppt,
                "gamma": gasto_admin, "beta": gasto_cobranza,
                "k": k_comision, "alpha": alpha_honorarios,
            },
            garantizados_t={
                "t": anio_evaluar,
                "edad": edad_x + anio_evaluar,
                "rescate": vr_t["Valor_Rescate_Final"],
                "saldado": ss_t.get("SA_Saldada", 0.0),
                "prorroga": prorroga_str,
                "dote": sp_t.get("dote_sobrante_futura", 0.0),
            },
            df_proyeccion=df_resultado,
        )
        col_pdf.download_button(
            "📄 Descargar reporte ejecutivo (PDF)",
            pdf_bytes,
            file_name=f"reporte_ejecutivo_{tipo_seguro}_x{edad_x}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
    except Exception as e:
        col_pdf.error(f"❌ No pude generar el PDF: {e}")
    #& C:\Users\Admon\AppData\Local\Python\pythoncore-3.14-64\python.exe -m streamlit run c:/Users/Admon/Downloads/interfaz.py
    