from datetime import date, datetime
import pandas as pd
import streamlit as st
from supabase import create_client, Client

TARIFA_ESTIMADA = 1.10

st.set_page_config(page_title="Mi Control de Entrega", page_icon="📦", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
:root { --brand:#2563eb; --brand-dark:#1d4ed8; --ink:#172033; --muted:#64748b; --surface:#ffffff; --line:#e2e8f0; }
.stApp {background:#f4f7fb;color:var(--ink)}
[data-testid="stHeader"] {background:rgba(244,247,251,.92)}
[data-testid="stMainBlockContainer"] {max-width:1180px;padding-top:1.5rem;padding-bottom:3rem}
[data-testid="stSidebar"] {background:#fff;border-right:1px solid var(--line)}
[data-testid="stSidebar"] * {color:var(--ink)}
[data-testid="stSidebar"] [data-testid="stButton"] button {border-radius:12px}
.hero {padding:clamp(1.1rem,3vw,2rem);border-radius:24px;background:linear-gradient(120deg,#1d4ed8 0%,#2563eb 48%,#7c3aed 100%);color:white;box-shadow:0 14px 35px rgba(37,99,235,.18);margin-bottom:1.2rem}
.hero h1 {color:white!important;font-size:clamp(1.65rem,4vw,2.35rem);line-height:1.15;margin-bottom:.5rem}
.hero .muted {color:#e0eaff;font-size:1rem}
[data-testid="stMetric"] {background:var(--surface);border:1px solid var(--line);padding:1rem 1.1rem;border-radius:18px;box-shadow:0 4px 16px rgba(15,23,42,.035);min-height:112px}
[data-testid="stMetricLabel"] {color:var(--muted)!important;font-weight:600}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] > div {color:var(--brand-dark)!important;font-weight:750}
[data-testid="stMetricDelta"] {font-size:.82rem}
[data-testid="stProgressBar"] {height:12px}
[data-testid="stProgressBar"] > div {border-radius:99px}
[data-testid="stForm"] {background:white;border:1px solid var(--line);border-radius:18px;padding:1rem 1.1rem}
[data-testid="stDataFrame"], [data-testid="stTable"] {border-radius:14px;overflow:hidden}
[data-testid="stTabs"] button {font-weight:650}
.stTextInput input, .stNumberInput input, [data-baseweb="select"] > div, [data-testid="stDateInput"] input {border-radius:12px!important}
div.stButton > button, div.stFormSubmitButton > button, [data-testid="stDownloadButton"] button {border-radius:12px;min-height:2.8rem;font-weight:700;border:0;transition:transform .15s ease,box-shadow .15s ease}
div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] {background:var(--brand);color:white;box-shadow:0 5px 12px rgba(37,99,235,.18)}
div.stButton > button:hover, div.stFormSubmitButton > button:hover {transform:translateY(-1px)}
hr {border-color:var(--line)}
[data-testid="stAlert"] {border-radius:14px}
.delivery-icon {display:inline-block}
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] {padding:1rem .8rem 2rem}
  .hero {border-radius:18px;padding:1.15rem}
  [data-testid="stMetric"] {padding:.8rem;border-radius:14px;min-height:96px}
  [data-testid="stMetricValue"] {font-size:1.45rem}
  [data-testid="stForm"] {padding:.8rem;border-radius:15px}
  h1 {font-size:1.65rem!important}
}
</style>""", unsafe_allow_html=True)

st.sidebar.markdown("## 📦 Mi Control de Entrega")
st.sidebar.caption("Tu jornada, clara y bajo control")

# Configure these values in Streamlit Cloud > App > Settings > Secrets.
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    st.error("Falta configurar SUPABASE_URL y SUPABASE_KEY en los Secrets de Streamlit.")
    st.code('SUPABASE_URL = "https://TU-PROYECTO.supabase.co"\nSUPABASE_KEY = "sb_publishable_TU_CLAVE"', language="toml")
    st.stop()

def make_client(url, key):
    # No cache: cada sesión de Streamlit necesita su propio cliente autenticado.
    return create_client(url, key)

supabase: Client = make_client(SUPABASE_URL, SUPABASE_KEY)

if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None
if "user" not in st.session_state:
    st.session_state.user = None

# Restore the authenticated Supabase session for this browser session.
if st.session_state.access_token and st.session_state.refresh_token:
    try:
        auth_response = supabase.auth.set_session(st.session_state.access_token, st.session_state.refresh_token)
        if getattr(auth_response, "session", None):
            st.session_state.access_token = auth_response.session.access_token
            st.session_state.refresh_token = auth_response.session.refresh_token
            st.session_state.user = auth_response.user
    except Exception:
        st.session_state.access_token = None
        st.session_state.refresh_token = None
        st.session_state.user = None


def euros(valor):
    return f"{float(valor):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def usuario_id():
    u = st.session_state.user
    return u.id if u else None


def cargar_config():
    uid = usuario_id()
    default = {"objetivo": 3000.0, "fecha_objetivo": date.today().replace(day=28).isoformat(), "tarifa": TARIFA_ESTIMADA}
    result = supabase.table("configuracion_usuario").select("objetivo,fecha_objetivo,tarifa").eq("user_id", uid).limit(1).execute()
    if result.data:
        default.update(result.data[0])
    return default


def guardar_config(objetivo, fecha_objetivo, tarifa):
    uid = usuario_id()
    supabase.table("configuracion_usuario").upsert({"user_id": uid, "objetivo": float(objetivo), "fecha_objetivo": fecha_objetivo, "tarifa": float(tarifa)}, on_conflict="user_id").execute()


def cargar_entregas():
    return supabase.table("entregas").select("id,fecha,descripcion,cantidad,importe,observaciones,tarifa,creado_en").eq("user_id", usuario_id()).eq("tipo", "entrega").order("fecha", desc=True).execute().data or []


def cargar_combustible():
    return supabase.table("combustible").select("id,fecha,importe,creado_en").eq("user_id", usuario_id()).order("fecha", desc=True).execute().data or []


def guardar_entrega(fecha, paquetes, tarifa):
    uid = usuario_id()
    # Reemplazar solo el registro de entrega del usuario para esa fecha.
    supabase.table("entregas").delete().eq("user_id", uid).eq("fecha", fecha.isoformat()).eq("tipo", "entrega").execute()
    supabase.table("entregas").insert({"user_id": uid, "fecha": fecha.isoformat(), "tipo": "entrega", "descripcion": "Paquetes entregados", "cantidad": int(paquetes), "importe": round(float(paquetes) * float(tarifa), 2), "tarifa": float(tarifa)}).execute()
    cfg = cargar_config()
    guardar_config(cfg["objetivo"], cfg["fecha_objetivo"], tarifa)


def guardar_gasto(fecha, importe):
    supabase.table("combustible").insert({"user_id": usuario_id(), "fecha": fecha.isoformat(), "importe": round(float(importe), 2)}).execute()


def login_ui():
    st.markdown('<div class="hero"><h1>📦 Mi Control de Entrega</h1><div class="muted">Inicia sesión para consultar tu historial privado.</div></div>', unsafe_allow_html=True)
    tab_login, tab_reset = st.tabs(["Iniciar sesión", "Recuperar contraseña"])
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Correo electrónico")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Entrar", type="primary", width="stretch")
        if submitted:
            try:
                res = supabase.auth.sign_in_with_password({"email": email.strip(), "password": password})
                st.session_state.access_token = res.session.access_token
                st.session_state.refresh_token = res.session.refresh_token
                st.session_state.user = res.user
                st.rerun()
            except Exception:
                st.error("No se ha podido iniciar sesión. Comprueba el correo y la contraseña o contacta con el administrador.")
    with tab_reset:
        with st.form("reset_form"):
            reset_email = st.text_input("Correo electrónico de tu cuenta")
            send_reset = st.form_submit_button("Enviar enlace de recuperación")
        if send_reset:
            try:
                supabase.auth.reset_password_for_email(reset_email.strip())
                st.success("Si la cuenta existe y el correo está configurado, recibirás instrucciones para recuperar el acceso.")
            except Exception:
                st.error("No se pudo solicitar la recuperación. Contacta con el administrador.")
    st.caption("Las cuentas deben ser creadas o invitadas por el administrador. No hay registro público en esta aplicación.")

if not st.session_state.user:
    login_ui()
    st.stop()

with st.sidebar:
    st.caption(f"Sesión: {getattr(st.session_state.user, 'email', '')}")
    if st.button("Cerrar sesión", width="stretch"):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        for key in ("access_token", "refresh_token", "user"):
            st.session_state[key] = None
        st.rerun()
    pagina = st.radio("Menú", ["🏠 Inicio", "📦 Registro diario", "⛽ Combustible", "🎯 Objetivo e historial"])
    st.caption("Datos privados de tu cuenta · Guardados en Supabase")

try:
    config = cargar_config()
    registros_raw = cargar_entregas()
    gastos_raw = cargar_combustible()
except Exception as e:
    st.error("No se pudieron cargar los datos. Comprueba que ejecutaste el SQL de configuración y que las políticas RLS están activas.")
    st.code(str(e))
    st.stop()

hoy = date.today()
try:
    fecha_limite = date.fromisoformat(str(config["fecha_objetivo"]))
except (ValueError, TypeError):
    fecha_limite = hoy
mes_actual = hoy.strftime("%Y-%m")
registros = [{"id": r["id"], "fecha": r["fecha"], "paquetes": int(r["cantidad"]), "tarifa": float(r.get("tarifa") or (float(r["importe"]) / max(1, int(r["cantidad"])))), "importe": float(r["importe"])} for r in registros_raw]
gastos = [{"id": g["id"], "fecha": g["fecha"], "importe": float(g["importe"])} for g in gastos_raw]

if pagina == "🏠 Inicio":
    st.markdown('<div class="hero"><h1>👋 ¡Hola! <span class="delivery-icon">📦</span></h1><div class="muted">Tu jornada, tus entregas y tu objetivo bajo control.</div></div>', unsafe_allow_html=True)
    st.subheader("🎯 Tu objetivo mensual")
    with st.form("form_objetivo_inicio"):
        c1, c2 = st.columns(2)
        with c1:
            objetivo_nuevo = st.number_input("Objetivo económico (€)", min_value=0.0, value=float(config["objetivo"]), step=100.0)
        with c2:
            try: fecha_guardada = date.fromisoformat(str(config["fecha_objetivo"]))
            except (ValueError, TypeError): fecha_guardada = hoy
            fecha_nueva = st.date_input("Fecha objetivo", value=fecha_guardada)
        guardar_obj = st.form_submit_button("Guardar objetivo", type="primary", width="stretch")
    if guardar_obj:
        guardar_config(objetivo_nuevo, fecha_nueva.isoformat(), config["tarifa"])
        st.success("Objetivo guardado."); st.rerun()
    df = pd.DataFrame(registros)
    if not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
        df["ingreso"] = df["paquetes"] * df["tarifa"]
        df_mes = df[df["fecha"].apply(lambda f: f.strftime("%Y-%m") == mes_actual)]
        total_mes = float(df_mes["ingreso"].sum()); paquetes_mes = int(df_mes["paquetes"].sum()); dias = int(df_mes["fecha"].nunique())
        total_historico = float(df["ingreso"].sum()); hoy_df = df[df["fecha"] == hoy]
        paquetes_hoy = int(hoy_df["paquetes"].sum()); ingreso_hoy = float(hoy_df["ingreso"].sum())
    else:
        df_mes = pd.DataFrame(); total_mes = paquetes_mes = dias = total_historico = paquetes_hoy = ingreso_hoy = 0
    objetivo = float(config["objetivo"]); faltante = max(0.0, objetivo-total_mes); porcentaje = min(100.0, total_mes/objetivo*100) if objetivo else 0.0
    try: fecha_limite = date.fromisoformat(str(config["fecha_objetivo"]))
    except (ValueError, TypeError): fecha_limite = hoy
    dias_restantes = max(0, (fecha_limite-hoy).days); ritmo = faltante/max(1, dias_restantes+1)
    st.divider(); st.subheader("📊 Resumen del mes")
    a,b,c = st.columns(3); a.metric("Facturación estimada", euros(total_mes)); b.metric("Te falta", euros(faltante)); c.metric("Objetivo alcanzado", f"{porcentaje:.1f}%")
    st.progress(porcentaje/100)
    d,e,f = st.columns(3); d.metric("Paquetes este mes", f"{paquetes_mes:,}".replace(",",".")); e.metric("Estimación de hoy", euros(ingreso_hoy), f"{paquetes_hoy} paquetes"); f.metric("Promedio por día trabajado", euros(total_mes/dias if dias else 0))
    st.info(f"Para alcanzar tu objetivo antes del {fecha_limite.strftime('%d/%m/%Y')}, necesitarías una media aproximada de **{euros(ritmo)} por día natural** desde hoy.")
    st.caption("Importes estimados; no son ingresos confirmados.")
    gasto_mes = sum(g["importe"] for g in gastos if str(g["fecha"]).startswith(mes_actual))
    st.subheader("⛽ Combustible este mes"); st.metric("Total de combustible", euros(gasto_mes))
    if not df.empty:
        st.subheader("📈 Evolución de la facturación estimada")
        serie = df.groupby("fecha", as_index=False)["ingreso"].sum().sort_values("fecha"); serie["fecha"] = serie["fecha"].astype(str); st.line_chart(serie.set_index("fecha")["ingreso"])
    else: st.write("Registra tus primeras entregas para ver aquí la evolución de la facturación.")

elif pagina == "📦 Registro diario":
    st.title("📦 Registro diario"); st.write("Introduce cuántos paquetes has entregado.")
    with st.form("registro_entregas"):
        fecha_registro = st.date_input("Fecha", value=hoy); paquetes = st.number_input("Paquetes entregados", min_value=0, step=1, value=0)
        tarifa = st.number_input("Estimación por paquete (€)", min_value=0.0, value=float(config.get("tarifa", TARIFA_ESTIMADA)), step=0.05, format="%.2f")
        st.caption(f"Estimación: **{euros(paquetes*tarifa)}**"); guardar_reg = st.form_submit_button("Guardar entregas", type="primary", width="stretch")
    if guardar_reg:
        try:
            guardar_entrega(fecha_registro, paquetes, tarifa); st.success(f"Guardado: {paquetes} paquetes · {euros(paquetes*tarifa)} estimados."); st.rerun()
        except Exception as e: st.error("No se pudo guardar el registro."); st.code(str(e))
    if registros:
        st.subheader("Últimos registros"); dr = pd.DataFrame(registros); dr["Fecha"] = pd.to_datetime(dr["fecha"]).dt.strftime("%d/%m/%Y"); dr["Importe estimado"] = dr["importe"].map(euros)
        st.dataframe(dr[["Fecha","paquetes","tarifa","Importe estimado"]].rename(columns={"paquetes":"Paquetes","tarifa":"€/paquete"}), width="stretch", hide_index=True)

elif pagina == "⛽ Combustible":
    st.title("⛽ Control de combustible")
    with st.form("form_combustible"):
        fecha_gasto = st.date_input("Fecha del repostaje", value=hoy); importe = st.number_input("Importe gastado (€)", min_value=0.0, value=0.0, step=5.0, format="%.2f"); guardar_gasto_btn = st.form_submit_button("Guardar gasto", type="primary", width="stretch")
    if guardar_gasto_btn:
        if importe <= 0: st.error("Introduce un importe mayor que cero.")
        else:
            try: guardar_gasto(fecha_gasto, importe); st.success(f"Gasto guardado: {euros(importe)}."); st.rerun()
            except Exception as e: st.error("No se pudo guardar el gasto."); st.code(str(e))
    dg = pd.DataFrame(gastos)
    if not dg.empty:
        dg["mes"] = dg["fecha"].str[:7]; st.subheader("Resumen por mes"); resumen = dg.groupby("mes", as_index=False).agg(Total=("importe","sum"), Repostajes=("importe","count")).sort_values("mes", ascending=False); resumen["Total"] = resumen["Total"].map(euros)
        st.dataframe(resumen.rename(columns={"mes":"Mes","Repostajes":"Número de repostajes"}), width="stretch", hide_index=True)
        st.subheader("Historial de repostajes"); dg["Fecha"] = pd.to_datetime(dg["fecha"]).dt.strftime("%d/%m/%Y"); dg["Importe"] = dg["importe"].map(euros); st.dataframe(dg[["Fecha","Importe"]], width="stretch", hide_index=True)
    else: st.info("Todavía no has registrado gastos de combustible.")

else:
    st.title("🎯 Objetivo e historial"); st.metric("Objetivo mensual", euros(float(config["objetivo"])))
    st.write(f"**Fecha límite:** {fecha_limite.strftime('%d/%m/%Y')}"); st.write(f"**Tarifa estimada actual:** {euros(float(config.get('tarifa', TARIFA_ESTIMADA)))} por paquete")
    if registros:
        dfh = pd.DataFrame(registros); dfh["Facturación estimada"] = dfh["paquetes"]*dfh["tarifa"]; dfh["Fecha"] = pd.to_datetime(dfh["fecha"]).dt.strftime("%d/%m/%Y"); dfh["Importe estimado"] = dfh["Facturación estimada"].map(euros)
        st.subheader("Historial de entregas"); st.dataframe(dfh[["Fecha","paquetes","tarifa","Importe estimado"]].rename(columns={"paquetes":"Paquetes","tarifa":"€/paquete"}), width="stretch", hide_index=True)
        csv = dfh[["fecha","paquetes","tarifa","Facturación estimada"]].to_csv(index=False).encode("utf-8-sig"); st.download_button("Descargar historial de entregas (CSV)", data=csv, file_name="historial_entregas.csv", mime="text/csv")
    else: st.info("Todavía no hay registros de entregas.")
    st.caption("Los datos de esta sesión se guardan de forma privada en Supabase.")
