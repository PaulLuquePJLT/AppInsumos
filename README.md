# AppInsumos

Mini WMS Insumos es una aplicación Streamlit para gestionar inventario, ubicaciones y cuentas logísticas.

## Requisitos

- Python 3.11+
- `streamlit`
- `pandas`
- `sqlalchemy`
- `pyodbc`
- `python-dotenv`
- `bcrypt`
- `plotly`
- `python-docx`

## Variables de entorno

Crea un archivo `.env` con:

```env
DB_SERVER=...
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_DRIVER=ODBC Driver 18 for SQL Server
```

## Ejecutar localmente

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Docker

```bash
docker build -t appinsumos .
docker run -p 8501:8501 --env-file .env appinsumos
```

## GitHub Actions

El flujo `.github/workflows/ci.yml` valida la instalación de dependencias y compila los archivos Python.
