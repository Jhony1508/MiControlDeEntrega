import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Mi Control de Entrega — primera versión
# Los datos se guardan en datos.json junto a app.py.
DATA_FILE = Path(__file__).parent / "datos.json"
TARIFA_ESTIMADA = 1.10

st.set_page_config(
    page_title="Mi Control de Entrega",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #172554 48%, #312e81 100%);
        color: #f8fafc;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111827 0%, #1e1b4b 100%);
    }
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.13);
        padding: 16px;
        border-radius: 16px;
    }
    /* Valores numéricos de las tarjetas: amarillo para destacar el resumen mensual */
    [data-testid="stMetricValue"] {
        color: #FFD84D !important;
    }
    [data-testid="stMetricValue"] > div {
        color: #FFD84D !important;
    }
    .hero {
        padding: 1.4rem 1.6rem;
        border-radius: 22px;
        background: linear-gradient(110deg, rgba(14,165,233,.22), rgba(139,92,246,.28));
        border: 1px solid rgba(255,255,255,.16);
        margin-bottom: 1rem;
    }
    .hero h1 { margin-bottom: .25rem; }
    .muted { color: #cbd5e1; }
    div.stButton > button {
        border-radius: 12px;
        min-height: 2.7rem;
        font-weight: 650;
    }
    @keyframes floatBox {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-7px); }
    }
    .delivery-icon { display: inline-block; animation: floatBox 2.4s ease-in-out infinite; }
    </style>
    """,
    unsafe_allow_html=True,
)


def cargar_datos():
    base = {
        "objetivo": 3000.0,
        "fecha_objetivo": date.today().replace(day=28).isoformat(),
        "tarifa": TARIFA_ESTIMADA,
        "registros": [],
        "combustible": [],
    }
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as f:
                guardado = json.load(f)
            base.update(guardado)
        except (json.JSONDecodeError, OSError):
            st.warning("No se pudo leer datos.json. Se usarán datos iniciales.")
    return base


def guardar_datos():
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def euros(valor):
    return f"{valor:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


datos = cargar_datos()
hoy = date.today()
mes_actual = hoy.strftime("%Y-%m")

# Navegación
st.sidebar.markdown("## 📦 Mi Control de Entrega")
pagina = st.sidebar.radio(
    "Menú",
    ["🏠 Inicio", "📦 Registro diario", "⛽ Combustible", "🎯 Objetivo e historial"],
)
st.sidebar.caption("Estimaciones orientativas · Datos guardados localmente")


if pagina == "🏠 Inicio":
    st.markdown(
        """
        <div class="hero">
          <h1>👋 ¡Hola! <span class="delivery-icon">📦</span></h1>
          <div class="muted">Tu jornada, tus entregas y tu objetivo bajo control.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "objetivo_configurado" not in datos:
        datos["objetivo_configurado"] = False

    st.subheader("🎯 ¿Cuál es tu objetivo este mes?")
    with st.form("form_objetivo_inicio"):
        col1, col2 = st.columns(2)
        with col1:
            objetivo_nuevo = st.number_input(
                "Objetivo económico (€)", min_value=0.0, value=float(datos["objetivo"]), step=100.0
            )
        with col2:
            try:
                fecha_guardada = date.fromisoformat(datos["fecha_objetivo"])
            except (ValueError, TypeError):
                fecha_guardada = hoy
            fecha_nueva = st.date_input("¿Para qué fecha quieres conseguirlo?", value=fecha_guardada)
        confirmar_objetivo = st.form_submit_button("Guardar objetivo", type="primary", width="stretch")
        if confirmar_objetivo:
            datos["objetivo"] = float(objetivo_nuevo)
            datos["fecha_objetivo"] = fecha_nueva.isoformat()
            datos["objetivo_configurado"] = True
            guardar_datos()
            st.success("Objetivo guardado. ¡Vamos a por él!")
            st.rerun()

    registros = datos.get("registros", [])
    df = pd.DataFrame(registros)
    if not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
        df["ingreso"] = pd.to_numeric(df["paquetes"], errors="coerce").fillna(0) * pd.to_numeric(
            df["tarifa"], errors="coerce"
        ).fillna(TARIFA_ESTIMADA)
        df_mes = df[df["fecha"].apply(lambda f: f.strftime("%Y-%m") == mes_actual)]
        total_mes = float(df_mes["ingreso"].sum())
        paquetes_mes = int(df_mes["paquetes"].sum())
        dias_trabajados = int(df_mes["fecha"].nunique())
        total_historico = float(df["ingreso"].sum())
        paquetes_historico = int(df["paquetes"].sum())
        hoy_df = df[df["fecha"] == hoy]
        paquetes_hoy = int(hoy_df["paquetes"].sum())
        ingreso_hoy = float(hoy_df["ingreso"].sum())
    else:
        df_mes = pd.DataFrame()
        total_mes = paquetes_mes = dias_trabajados = total_historico = paquetes_historico = paquetes_hoy = ingreso_hoy = 0

    objetivo = float(datos["objetivo"])
    faltante = max(0.0, objetivo - total_mes)
    porcentaje = min(100.0, total_mes / objetivo * 100) if objetivo > 0 else 0.0
    dias_restantes = max(0, (date.fromisoformat(datos["fecha_objetivo"]) - hoy).days)
    ritmo = faltante / max(1, dias_restantes + 1)

    st.divider()
    st.subheader("📊 Resumen del mes")
    m1, m2, m3 = st.columns(3)
    m1.metric("Facturación estimada", euros(total_mes))
    m2.metric("Te falta", euros(faltante))
    m3.metric("Objetivo alcanzado", f"{porcentaje:.1f}%")
    st.progress(porcentaje / 100)
    m4, m5, m6 = st.columns(3)
    m4.metric("Paquetes este mes", f"{paquetes_mes:,}".replace(",", "."))
    m5.metric("Estimación de hoy", euros(ingreso_hoy), f"{paquetes_hoy} paquetes")
    promedio = total_mes / dias_trabajados if dias_trabajados else 0
    m6.metric("Promedio por día trabajado", euros(promedio))
    st.info(
        f"Para alcanzar tu objetivo antes del {date.fromisoformat(datos['fecha_objetivo']).strftime('%d/%m/%Y')}, "
        f"necesitarías una media aproximada de **{euros(ritmo)} por día natural** desde hoy."
    )
    st.caption("Importes estimados según la tarifa orientativa guardada para cada día; no son ingresos confirmados.")

    gastos = datos.get("combustible", [])
    gasto_mes = sum(float(g["importe"]) for g in gastos if str(g["fecha"]).startswith(mes_actual))
    st.subheader("⛽ Combustible este mes")
    st.metric("Total de combustible", euros(gasto_mes))

    if not df.empty:
        st.subheader("📈 Evolución de la facturación estimada")
        serie = df.groupby("fecha", as_index=False)["ingreso"].sum().sort_values("fecha")
        serie["fecha"] = serie["fecha"].astype(str)
        st.line_chart(serie.set_index("fecha")["ingreso"])
    else:
        st.write("Registra tus primeras entregas para ver aquí la evolución de la facturación.")


elif pagina == "📦 Registro diario":
    st.title("📦 Registro diario")
    st.write("Introduce cuántos paquetes has entregado. La cantidad por paquete es una estimación.")
    with st.form("registro_entregas"):
        fecha_registro = st.date_input("Fecha", value=hoy, key="fecha_registro")
        paquetes = st.number_input("Paquetes entregados", min_value=0, step=1, value=0)
        tarifa = st.number_input(
            "Estimación por paquete (€)", min_value=0.0, value=float(datos.get("tarifa", TARIFA_ESTIMADA)), step=0.05, format="%.2f"
        )
        st.caption(f"Estimación para este registro: **{euros(paquetes * tarifa)}**")
        guardar_registro = st.form_submit_button("Guardar entregas", type="primary", width="stretch")
        if guardar_registro:
            if paquetes < 0:
                st.error("El número de paquetes no puede ser negativo.")
            else:
                # Si ya existe un registro para esa fecha, se reemplaza para evitar duplicados accidentales.
                datos["registros"] = [r for r in datos.get("registros", []) if r["fecha"] != fecha_registro.isoformat()]
                datos["registros"].append(
                    {
                        "fecha": fecha_registro.isoformat(),
                        "paquetes": int(paquetes),
                        "tarifa": float(tarifa),
                        "creado": datetime.now().isoformat(timespec="seconds"),
                    }
                )
                datos["tarifa"] = float(tarifa)
                guardar_datos()
                st.success(f"Registro guardado: {paquetes} paquetes · {euros(paquetes * tarifa)} estimados.")
                st.rerun()

    st.caption("Si vuelves a guardar un día ya registrado, el registro anterior de esa fecha se sustituye.")
    registros = sorted(datos.get("registros", []), key=lambda r: r["fecha"], reverse=True)
    if registros:
        st.subheader("Últimos registros")
        df_reg = pd.DataFrame(registros)
        df_reg["Facturación estimada"] = df_reg["paquetes"] * df_reg["tarifa"]
        df_reg["Fecha"] = pd.to_datetime(df_reg["fecha"]).dt.strftime("%d/%m/%Y")
        df_reg["Importe estimado"] = df_reg["Facturación estimada"].map(euros)
        st.dataframe(df_reg[["Fecha", "paquetes", "tarifa", "Importe estimado"]].rename(
            columns={"paquetes": "Paquetes", "tarifa": "€/paquete"}
        ), width="stretch", hide_index=True)


elif pagina == "⛽ Combustible":
    st.title("⛽ Control de combustible")
    st.write("Cada repostaje se guarda y se suma automáticamente al mes correspondiente.")
    with st.form("form_combustible"):
        fecha_gasto = st.date_input("Fecha del repostaje", value=hoy)
        importe = st.number_input("Importe gastado (€)", min_value=0.0, value=0.0, step=5.0, format="%.2f")
        guardar_gasto = st.form_submit_button("Guardar gasto", type="primary", width="stretch")
        if guardar_gasto:
            if importe <= 0:
                st.error("Introduce un importe mayor que cero.")
            else:
                datos.setdefault("combustible", []).append(
                    {"fecha": fecha_gasto.isoformat(), "importe": round(float(importe), 2)}
                )
                guardar_datos()
                st.success(f"Gasto guardado: {euros(importe)}.")
                st.rerun()

    gastos = sorted(datos.get("combustible", []), key=lambda g: g["fecha"], reverse=True)
    df_gastos = pd.DataFrame(gastos)
    if not df_gastos.empty:
        df_gastos["mes"] = df_gastos["fecha"].str[:7]
        st.subheader("Resumen por mes")
        resumen = df_gastos.groupby("mes", as_index=False).agg(
            Total=("importe", "sum"), Repostajes=("importe", "count")
        ).sort_values("mes", ascending=False)
        resumen["Total"] = resumen["Total"].map(euros)
        st.dataframe(resumen.rename(columns={"mes": "Mes", "Repostajes": "Número de repostajes"}), width="stretch", hide_index=True)
        st.subheader("Historial de repostajes")
        df_gastos["Fecha"] = pd.to_datetime(df_gastos["fecha"]).dt.strftime("%d/%m/%Y")
        df_gastos["Importe"] = df_gastos["importe"].map(euros)
        st.dataframe(df_gastos[["Fecha", "Importe"]], width="stretch", hide_index=True)
    else:
        st.info("Todavía no has registrado gastos de combustible.")


else:
    st.title("🎯 Objetivo e historial")
    st.write("Consulta tus registros y el objetivo guardado.")
    st.metric("Objetivo mensual", euros(float(datos["objetivo"])))
    st.write(f"**Fecha límite:** {date.fromisoformat(datos['fecha_objetivo']).strftime('%d/%m/%Y')}")
    st.write(f"**Tarifa estimada actual:** {euros(float(datos.get('tarifa', TARIFA_ESTIMADA)))} por paquete")

    if datos.get("registros"):
        df = pd.DataFrame(datos["registros"])
        df["Facturación estimada"] = df["paquetes"] * df["tarifa"]
        df["Fecha"] = pd.to_datetime(df["fecha"]).dt.strftime("%d/%m/%Y")
        df["Importe estimado"] = df["Facturación estimada"].map(euros)
        st.subheader("Historial de entregas")
        st.dataframe(df[["Fecha", "paquetes", "tarifa", "Importe estimado"]].rename(
            columns={"paquetes": "Paquetes", "tarifa": "€/paquete"}
        ), width="stretch", hide_index=True)
        csv = df[["fecha", "paquetes", "tarifa", "Facturación estimada"]].to_csv(index=False).encode("utf-8-sig")
        st.download_button("Descargar historial de entregas (CSV)", data=csv, file_name="historial_entregas.csv", mime="text/csv")
    else:
        st.info("Todavía no hay registros de entregas.")

    st.warning("Guarda una copia de datos.json de vez en cuando: contiene tu historial y tu configuración.")
