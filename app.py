import glob
import streamlit as st
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import st_folium

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Portal de Vacantes Escolares", page_icon="🎒", layout="wide")


# --- CARGAR BASES ---
@st.cache_data
def cargar_datos():
    # Cargar información de establecimientos
    df_niveles = pd.read_excel("jisc.xlsx", sheet_name="comuna_estable_nivel")
    df_contacto = pd.read_excel("jisc.xlsx", sheet_name="direccion_vacantes")
    df_contacto.rename(columns={"CÓDIGO": "COD_ESTABLEC"}, inplace=True)
    df_base = pd.merge(df_contacto, df_niveles, on="COD_ESTABLEC", how="inner")

    # Buscar automáticamente el archivo de grupos más reciente
    archivos = sorted(glob.glob("grupos_gesparvu_*.xlsx"), reverse=True)
    if not archivos:
        st.error("No se encontró ningún archivo grupos_gesparvu_*.xlsx en la carpeta.")
        st.stop()
    archivo_grupos = archivos[0]

    df_grupos = pd.read_excel(archivo_grupos, sheet_name="Datos Grupos")
    df_resumen_estab = pd.read_excel(archivo_grupos, sheet_name="Resumen por Establecimiento")

    # Normalizar columna de código — distintas versiones del scraper usan nombres distintos:
    # - versión nueva: "Código JUNJI"
    # - versión antigua: "Establecimiento"
    # - edge case: quedó como índice del DataFrame
    posibles = ["Código JUNJI", "Establecimiento"]
    if df_resumen_estab.index.name in posibles:
        df_resumen_estab = df_resumen_estab.reset_index()
    for nombre in posibles:
        if nombre in df_resumen_estab.columns:
            df_resumen_estab.rename(columns={nombre: "COD_ESTABLEC"}, inplace=True)
            break

    if "COD_ESTABLEC" not in df_resumen_estab.columns:
        st.error(
            f"No se encontró columna de código en la hoja 'Resumen por Establecimiento'. "
            f"Columnas disponibles: {df_resumen_estab.columns.tolist()}"
        )
        st.stop()

    # Normalizar columna de código en df_grupos (nueva vs antigua)
    if "Código JUNJI" in df_grupos.columns:
        col_cod_grupos = "Código JUNJI"
    else:
        col_cod_grupos = "Establecimiento"

    # Asegurar tipo string para que los merges no fallen por int vs str
    df_base["COD_ESTABLEC"] = df_base["COD_ESTABLEC"].astype(str).str.strip()
    df_resumen_estab["COD_ESTABLEC"] = df_resumen_estab["COD_ESTABLEC"].astype(str).str.strip()
    df_grupos[col_cod_grupos] = df_grupos[col_cod_grupos].astype(str).str.strip()

    return df_base, df_grupos, df_resumen_estab, archivo_grupos, col_cod_grupos


df, df_grupos, df_resumen_estab, archivo_grupos, col_cod_grupos = cargar_datos()


# --- TÍTULO ---
st.title("🎒 Portal de Vacantes Escolares")
st.caption(f"Fuente de datos: `{archivo_grupos}`")
st.markdown("---")


# --- ESTADÍSTICAS GENERALES ---
col1, col2, col3, col4 = st.columns(4)
total_capacidad = df_resumen_estab["Capacidad"].sum()
total_matriculas = df_resumen_estab["Matrículas"].sum()
total_vacantes = df_resumen_estab["Vacantes"].sum()
ocupacion_promedio = (total_matriculas / total_capacidad * 100) if total_capacidad > 0 else 0

with col1:
    st.metric("🏫 Establecimientos", len(df_resumen_estab))
with col2:
    st.metric("👥 Capacidad Total", f"{total_capacidad:,}")
with col3:
    st.metric("✅ Matrículas", f"{total_matriculas:,}")
with col4:
    st.metric("📊 Vacantes Disponibles", f"{total_vacantes:,}")

st.markdown(f"**Tasa de Ocupación General:** {ocupacion_promedio:.1f}%")
st.progress(ocupacion_promedio / 100)
st.markdown("---")


# --- FILTROS ---
st.subheader("🔍 Filtros de Búsqueda")
col_f1, col_f2 = st.columns(2)
with col_f1:
    comunas = sorted(df["DESC_COMUNA"].unique().tolist())
    comuna_filtro = st.multiselect("Selecciona Comuna(s):", comunas, default=comunas)
with col_f2:
    vacante_filtro = st.selectbox(
        "Filtrar por vacantes:",
        ["Todos", "Con vacantes disponibles (>0)", "Sin vacantes (0)"]
    )


# --- SELECTOR DE ESTABLECIMIENTO ---
st.subheader("🗺️ Mapa de Establecimientos y Vacantes")
df_filtrado = df[df["DESC_COMUNA"].isin(comuna_filtro)]
est_seleccion = st.selectbox(
    "📍 Selecciona un establecimiento para resaltarlo en el mapa:",
    options=["(mostrar todos)"] + sorted(df_filtrado["NOM_ESTABLEC"].unique().tolist())
)
destacado = est_seleccion if est_seleccion != "(mostrar todos)" else None


# --- MAPA ---
df_mapa = df_filtrado.copy()
df_mapa["LAT"] = pd.to_numeric(df_mapa["LAT"], errors="coerce")
df_mapa["LONG"] = pd.to_numeric(df_mapa["LONG"], errors="coerce")
df_mapa = df_mapa.merge(
    df_resumen_estab[["COD_ESTABLEC", "Vacantes", "% Ocupación"]],
    on="COD_ESTABLEC",
    how="left"
)

if vacante_filtro == "Con vacantes disponibles (>0)":
    df_mapa = df_mapa[df_mapa["Vacantes"] > 0]
elif vacante_filtro == "Sin vacantes (0)":
    df_mapa = df_mapa[df_mapa["Vacantes"] == 0]

if not df_mapa.empty:
    centro_lat = df_mapa["LAT"].mean()
    centro_lon = df_mapa["LONG"].mean()
else:
    centro_lat, centro_lon = -33.515, -70.725

m = folium.Map(location=[centro_lat, centro_lon], zoom_start=12)

for cod in df_mapa["COD_ESTABLEC"].unique():
    fila = df_mapa[df_mapa["COD_ESTABLEC"] == cod].iloc[0]
    lat, lon = fila["LAT"], fila["LONG"]

    if pd.isna(lat) or pd.isna(lon):
        continue

    # Obtener datos de grupos por nivel (columna varía según versión del scraper)
    grupos_estab = df_grupos[df_grupos[col_cod_grupos] == cod]

    if not grupos_estab.empty:
        resumen_nivel = grupos_estab.groupby("Nivel").agg({
            "Capacidad": "sum",
            "Matrículas": "sum",
            "Vacantes": "sum"
        }).reset_index()
        tabla_html = resumen_nivel.to_html(index=False, classes="table table-striped")
    else:
        tabla_html = "<i>No hay datos registrados</i>"

    vacantes_total = fila["Vacantes"] if pd.notna(fila["Vacantes"]) else 0

    if destacado and fila["NOM_ESTABLEC"] == destacado:
        icono = folium.Icon(color="red", icon="star")
    elif vacantes_total > 10:
        icono = folium.Icon(color="green", icon="home")
    elif vacantes_total > 0:
        icono = folium.Icon(color="orange", icon="home")
    else:
        icono = folium.Icon(color="darkred", icon="home")

    ocupacion = fila["% Ocupación"] if pd.notna(fila["% Ocupación"]) else 0

    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(f"""
            <div style="width:400px">
                <h4>{fila['NOM_ESTABLEC']}</h4>
                <p><b>Directora:</b> {fila['Nombre Directora']}<br>
                <b>Correo:</b> {fila['Correo electrónico Directora']}<br>
                <b>Dirección:</b> {fila['DIRECCIÓN  ']}<br>
                <b>Comuna:</b> {fila['DESC_COMUNA']}</p>
                <hr>
                <p><b>📊 Vacantes Totales:</b> {int(vacantes_total)}<br>
                <b>📈 Ocupación:</b> {ocupacion:.1f}%</p>
                <hr>
                <h5>Detalle por Nivel:</h5>
                {tabla_html}
            </div>
        """, max_width=450),
        tooltip=f"{fila['NOM_ESTABLEC']} - {int(vacantes_total)} vacantes",
        icon=icono
    ).add_to(m)

legend_html = '''
<div style="position: fixed;
            bottom: 50px; right: 50px; width: 220px;
            background-color: white; z-index:9999; font-size:15px;
            border:3px solid #333; border-radius: 8px; padding: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);">
    <p style="margin: 0 0 10px 0; font-weight: bold; font-size: 16px; color: #333;
              border-bottom: 2px solid #ddd; padding-bottom: 5px;">
        📍 Leyenda de Vacantes
    </p>
    <div style="margin: 8px 0; display: flex; align-items: center;">
        <span style="display: inline-block; width: 20px; height: 20px; background-color: green;
                     border-radius: 50%; margin-right: 10px; border: 2px solid #333;"></span>
        <span style="color: #333; font-weight: 500;">> 10 vacantes</span>
    </div>
    <div style="margin: 8px 0; display: flex; align-items: center;">
        <span style="display: inline-block; width: 20px; height: 20px; background-color: orange;
                     border-radius: 50%; margin-right: 10px; border: 2px solid #333;"></span>
        <span style="color: #333; font-weight: 500;">1-10 vacantes</span>
    </div>
    <div style="margin: 8px 0; display: flex; align-items: center;">
        <span style="display: inline-block; width: 20px; height: 20px; background-color: darkred;
                     border-radius: 50%; margin-right: 10px; border: 2px solid #333;"></span>
        <span style="color: #333; font-weight: 500;">Sin vacantes</span>
    </div>
    <div style="margin: 8px 0; display: flex; align-items: center;">
        <span style="display: inline-block; width: 20px; height: 20px; background-color: red;
                     border-radius: 50%; margin-right: 10px; border: 2px solid #333;">⭐</span>
        <span style="color: #333; font-weight: 500;">Seleccionado</span>
    </div>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))
st_folium(m, width=1200, height=600)


# --- TABLA DE RESUMEN ---
st.markdown("---")
st.subheader("📋 Tabla de Resumen por Establecimiento")

df_tabla = df.merge(df_resumen_estab, on="COD_ESTABLEC", how="left")
df_tabla = df_tabla[[
    "NOM_ESTABLEC", "DESC_COMUNA", "Nombre Directora",
    "Correo electrónico Directora", "Capacidad", "Matrículas",
    "Vacantes", "% Ocupación"
]].drop_duplicates()

df_tabla = df_tabla[df_tabla["DESC_COMUNA"].isin(comuna_filtro)]
if vacante_filtro == "Con vacantes disponibles (>0)":
    df_tabla = df_tabla[df_tabla["Vacantes"] > 0]
elif vacante_filtro == "Sin vacantes (0)":
    df_tabla = df_tabla[df_tabla["Vacantes"] == 0]

df_tabla = df_tabla.sort_values("Vacantes", ascending=False)
df_tabla["% Ocupación"] = df_tabla["% Ocupación"].apply(
    lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A"
)

st.dataframe(
    df_tabla,
    use_container_width=True,
    hide_index=True,
    column_config={
        "NOM_ESTABLEC": "Establecimiento",
        "DESC_COMUNA": "Comuna",
        "Nombre Directora": "Directora",
        "Correo electrónico Directora": "Correo",
        "Capacidad": st.column_config.NumberColumn("Capacidad", format="%d"),
        "Matrículas": st.column_config.NumberColumn("Matrículas", format="%d"),
        "Vacantes": st.column_config.NumberColumn("Vacantes", format="%d"),
        "% Ocupación": "% Ocupación"
    }
)


# --- PIE DE PÁGINA ---
st.markdown("---")
st.caption(f"📅 Última actualización: {datetime.today().strftime('%d/%m/%Y')}")
st.caption("ℹ️ Los datos de vacantes se cargan automáticamente desde el sistema GESPARVU")
