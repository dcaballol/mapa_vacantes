# Portal de Vacantes Escolares

Este proyecto es una app desarrollada en Streamlit para que directoras de establecimientos puedan ingresar:
- Vacantes disponibles por nivel
- Estudiantes en lista de espera por nivel

Además, cualquier usuario puede visualizar esta información en un mapa interactivo.

## Archivos incluidos

- `app.py`: aplicación principal de Streamlit
- `requirements.txt`: librerías necesarias
- `vacantes.xlsx`: archivo de datos que se va actualizando con las declaraciones
- Debes incluir `jisc.xlsx` (no distribuido aquí por privacidad de datos)

## Instrucciones para ejecutar localmente

1. Instalar dependencias:
```
pip install -r requirements.txt
```

2. Ejecutar la aplicación:
```
streamlit run app.py
```

## Despliegue en Streamlit Cloud

1. Sube `app.py`, `requirements.txt`, `vacantes.xlsx` y `jisc.xlsx` a un repositorio en GitHub
2. Desde [streamlit.io/cloud](https://streamlit.io/cloud), conecta el repositorio
3. Asegúrate de que el archivo principal sea `app.py`
4. ¡Listo!

---

Creado con ❤️ por Data Nerd y Daniel
