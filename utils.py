import pandas as pd
import numpy as np
from collections import Counter
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

def cargar_desde_google_sheets(sheet_id, sheet_name, creds_file):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        pd.read_json(creds_file, typ='series').to_dict(), scope
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    return procesar_archivo(df, from_df=True)

def procesar_archivo(uploaded_file_or_df, from_df=False):
    df = uploaded_file_or_df if from_df else pd.read_csv(uploaded_file_or_df)

    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]

    df["Mes"] = np.nan
    month_rows = df[df.apply(lambda row: row.astype(str).str.contains('|'.join(months)).any(), axis=1)]
    month_indices = month_rows.index.tolist()
    month_names = []

    for idx in month_indices:
        row = df.iloc[idx].astype(str)
        for mes in months:
            if mes in row.values:
                month_names.append(mes)
                break

    df["Mes"] = df["Mes"].astype(object)
    for i in range(len(month_indices)):
        start = month_indices[i] + 1
        end = month_indices[i + 1] if i + 1 < len(month_indices) else len(df)
        df.loc[start:end - 1, "Mes"] = month_names[i]

    header_cat = df.iloc[2]
    header_sub = df.iloc[4]
    combined = [
        f"{str(cat).strip()} - {str(sub).strip()}" if pd.notna(cat) and str(cat).strip() != 'nan'
        else str(sub).strip()
        for cat, sub in zip(header_cat[:-1], header_sub[:-1])
    ]
    df.columns = combined + ["Mes"]
    df = df.iloc[5:].reset_index(drop=True)
    df = df.dropna(how="all")

    df.drop(df.columns[[0, 1]], axis=1, inplace=True)

    def normalize(cols):
        clean = []
        counter = Counter()
        for col in cols:
            base = str(col).replace("nan", "").strip()
            counter[base] += 1
            clean.append(f"{base} ({counter[base]})" if counter[base] > 1 else base)
        return clean

    df.columns = normalize(df.columns)

    num_cols = [col for col in df.columns if col != "Mes"]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=num_cols, how="all")

    stats = df.groupby("Mes").agg(["sum", "mean", "max", "min", "count"]).round(2)
    return df, stats

def kpis_generales(df):
    total = df[[col for col in df.columns if "crm" in col.lower()]].sum().sum()
    viables = df[[col for col in df.columns if "viables" in col.lower()]].sum().sum()
    conversion = (viables / total * 100) if total > 0 else 0
    descarte = 100 - conversion if total > 0 else 0
    return int(total), int(viables), conversion, descarte

def graficar_plotly_candidatos_viables(df):
    cands = [col for col in df.columns if "crm" in col.lower()]
    viables = [col for col in df.columns if "viables" in col.lower()]
    if not cands or not viables:
        return px.bar(title="❌ Columnas no encontradas")
    data = df.groupby("Mes")[[cands[0], viables[0]]].sum().reset_index()
    return px.bar(data, x="Mes", y=[cands[0], viables[0]], barmode="group", title="Candidatos vs Viables")

def graficar_plotly_descartes(df):
    keywords = ["perfil", "skills", "presupuesto", "localidad", "química", "inpuntual", "experiencia", "inglés"]
    descarte_cols = [col for col in df.columns if any(k in col.lower() for k in keywords)]
    if not descarte_cols:
        return px.bar(title="❌ No hay datos de descarte")
    data = df[descarte_cols].sum().sort_values(ascending=False).head(5)
    return px.bar(x=data.values, y=data.index, orientation="h", title="Top 5 Razones de Descarte")

def graficar_plotly_comparativa(df):
    resumen = df.groupby("Mes").sum(numeric_only=True)
    if resumen.empty:
        return px.line(title="❌ Datos insuficientes")
    return px.line(resumen.T, title="Comparativa por Variable")
