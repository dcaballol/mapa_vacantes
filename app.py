import streamlit as st
import pandas as pd
import os
from datetime import datetime
import folium
from streamlit_folium import st_folium

# --- CARGAR BASE ---
df_niveles = pd.read_excel("jisc.xlsx", sheet_name="comuna_estable_nivel")
df_contacto = pd.read_excel("jisc.xlsx", sheet_name="direccion_vacantes")
df_contacto.rename(columns={"CÓDIGO": "COD_ESTABLEC"}, inplace=True)
df = pd.merge(df_contacto, df_niveles, on="COD_ESTABLEC", how="inner")

# --- CARGAR O CREAR VACANTES ---
vacantes_file = "vacantes.xlsx"
if os.path.exists(vacantes_file):
    df_vacantes = pd.read_excel(vacantes_file)
else:
    df_vacantes = pd.DataFrame(columns=["COD_ESTABLEC", "DESC_NIVEL", "Vacantes", "Fecha_actualización"])
    df_vacantes.to_excel(vacantes_file, index=False)

# --- SELECCIÓN DE MODO ---
st.title("🎒 Portal de Vacantes Escolares")
modo = st.radio("Selecciona el modo:", ["🌐 Ver vacantes", "✏️ Declarar vacantes (Directora)"])

# --- MODO: DECLARAR VACANTES ---
if modo == "✏️ Declarar vacantes (Directora)":
    st.sidebar.title("Ingreso de Vacantes")
    establecimientos = df["NOM_ESTABLEC"].unique()
    establecimiento = st.sidebar.selectbox("Selecciona tu establecimiento", establecimientos)

    df_estab = df[df["NOM_ESTABLEC"] == establecimiento]
    cod_estab = df_estab["COD_ESTABLEC"].values[0]
    comuna = df_estab["DESC_COMUNA"].values[0]
    directora = df_estab["Nombre Directora"].values[0]
    correo = df_estab["Correo electrónico Directora"].values[0]
    direccion = df_estab["DIRECCIÓN  "].values[0]

    st.sidebar.markdown(f"**Directora:** {directora}")
    st.sidebar.markdown(f"**Correo:** {correo}")
    st.sidebar.markdown(f"**Comuna:** {comuna}")

    niveles = df_estab["DESC_NIVEL"].unique()
    vacantes_input = {}

    st.sidebar.subheader("Vacantes por Nivel")
    for nivel in niveles:
        vac = st.sidebar.number_input(f"{nivel}", min_value=0, step=1)
        vacantes_input[nivel] = vac

    if st.sidebar.button("Guardar Vacantes"):
        hoy = datetime.today().strftime("%Y-%m-%d")
        registros = []
        for nivel, vac in vacantes_input.items():
            registros.append({
                "COD_ESTABLEC": cod_estab,
                "DESC_NIVEL": nivel,
                "Vacantes": vac,
                "Fecha_actualización": hoy
            })

        df_nuevo = pd.DataFrame(registros)

        # Quitar duplicados previos
        df_vacantes = df_vacantes[~((df_vacantes["COD_ESTABLEC"] == cod_estab) &
                                    (df_vacantes["DESC_NIVEL"].isin(niveles)))]

        df_vacantes = pd.concat([df_vacantes, df_nuevo], ignore_index=True)
        df_vacantes.to_excel(vacantes_file, index=False)
        st.sidebar.success("✅ Vacantes actualizadas correctamente.")

# --- MODO: MAPA INTERACTIVO ---
st.subheader("🗺️ Mapa de establecimientos y vacantes")
df_mapa = df.copy()
df_mapa["LAT"] = pd.to_numeric(df_mapa["LAT"], errors="coerce")
df_mapa["LONG"] = pd.to_numeric(df_mapa["LONG"], errors="coerce")

m = folium.Map(location=[-33.515, -70.725], zoom_start=13.1)

for cod in df_mapa["COD_ESTABLEC"].unique():
    fila = df_mapa[df_mapa["COD_ESTABLEC"] == cod].iloc[0]
    lat, lon = fila["LAT"], fila["LONG"]

    if pd.isna(lat) or pd.isna(lon):
        continue

    vacantes_estab = df_vacantes[df_vacantes["COD_ESTABLEC"] == cod]
    if not vacantes_estab.empty:
        tabla_html = vacantes_estab[["DESC_NIVEL", "Vacantes"]].to_html(index=False)
    else:
        tabla_html = "<i>No hay vacantes registradas</i>"

    popup = folium.Popup(f"""
        <b>{fila['NOM_ESTABLEC']}</b><br>
        <b>Directora:</b> {fila['Nombre Directora']}<br>
        <b>Correo:</b> {fila['Correo electrónico Directora']}<br>
        <b>Dirección:</b> {fila['DIRECCIÓN  ']}<br><br>
        {tabla_html}
    """, max_width=400)

    folium.Marker(
        location=[lat, lon],
        popup=popup,
        tooltip=fila['NOM_ESTABLEC'],
        icon=folium.Icon(color='blue', icon='info-sign')
    ).add_to(m)

st_folium(m, width=800, height=600)