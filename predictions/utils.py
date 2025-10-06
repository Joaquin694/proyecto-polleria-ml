# predictions/utils.py
import json
import joblib
import numpy as np
import pandas as pd
from django.conf import settings

def load_feature_list(model_choice: str):
    """
    Devuelve la lista de columnas esperadas segun el modelo.
    """
    store = settings.MODEL_STORE_DIR
    if model_choice == 'rf':
        path = store / 'rf_features.json'
    elif model_choice == 'dt':
        path = store / 'dt_features.json'
    else:  # 'lr'
        path = store / 'logreg_features.json'
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_model(model_choice: str):
    """
    Carga el .pkl del modelo según model_choice.
    """
    store = settings.MODEL_STORE_DIR
    if model_choice == 'rf':
        path = store / 'random_forest.pkl'
    elif model_choice == 'dt':
        path = store / 'decision_tree.pkl'
    else:  # 'lr'
        path = store / 'logistic_regression.pkl'
    return joblib.load(path)

def preprocess_dataframe(df: pd.DataFrame, model_choice: str) -> pd.DataFrame:
    """
    Preprocesa el CSV de entrada según el modelo.
    - RF/DT: tu flujo anterior (dummies en Zona_Recidencial/Metodo_Pago)
    - LR: igual que tu script de entrenamiento (one-hot también de Sexo + features ingenieriles)
    """
    df = df.copy()

    # -------- Campos de seguridad mínimos --------
    # Evita KeyError si faltan; rellena con 0 o vacío.
    def ensure(cols, default=0):
        for c in cols:
            if c not in df.columns:
                df[c] = default

    # Comunes a todos
    ensure(['Edad','Sexo',
            'Frec_Mes1','Frec_Mes2','Frec_Mes3','Frec_Mes4','Frec_Mes5',
            'Zona_Recidencial','Metodo_Pago'], default="")
    # Si usas estas en otros flujos:
    if 'Variación_Frecuencia_Visitas' not in df.columns:
        df['Variación_Frecuencia_Visitas'] = 0
    if 'Variación_porcentual (%)' not in df.columns:
        df['Variación_porcentual (%)'] = 0
    if 'Satisfacción_Servicio' not in df.columns:
        df['Satisfacción_Servicio'] = 0

    # -------- Ramas por modelo --------
    if model_choice in ('rf', 'dt'):
        # Mismo pipeline que ya tenías
        base_cols = [
            'Edad','Sexo','Frec_Mes1','Frec_Mes2','Frec_Mes3','Frec_Mes4','Frec_Mes5',
            'Variación_Frecuencia_Visitas','Variación_porcentual (%)',
            'Zona_Recidencial','Metodo_Pago','Satisfacción_Servicio'
        ]
        for c in base_cols:
            if c not in df.columns:
                df[c] = 0

        # Sexo como numérico simple (si tu entrenamiento lo usó así)
        # Convertimos a string y mapeamos M/F → dummies? No: para RF/DT tú usabas LabelEncoder.
        # Para no meter dependencia de la clase, usamos un mapeo binario simple:
        df['Sexo'] = df['Sexo'].astype(str).str.upper().map({'M':1,'F':0}).fillna(0)

        X = df[base_cols].copy()
        X = pd.get_dummies(X, columns=['Zona_Recidencial','Metodo_Pago'], dtype=float)
        X = X.fillna(0)
        return X.astype(float)

    else:  # model_choice == 'lr'
        # ======= Reproducimos tu script de entrenamiento =======
        # Sexo como texto y luego one-hot
        df['Sexo'] = df['Sexo'].astype(str)

        # Features ingenieriles
        mes_cols = ['Frec_Mes1','Frec_Mes2','Frec_Mes3','Frec_Mes4','Frec_Mes5']
        # Asegurar numéricos
        for c in mes_cols + ['Edad']:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

        x_t = np.arange(1, 6)
        def slope_1_5(row):
            y = row[mes_cols].values.astype(float)
            m, b = np.polyfit(x_t, y, 1)
            return m

        df['Tendencia_1_5']   = df.apply(slope_1_5, axis=1)
        df['Volatilidad_1_5'] = df[mes_cols].std(axis=1)

        prom_M1_4 = df[['Frec_Mes1','Frec_Mes2','Frec_Mes3','Frec_Mes4']].mean(axis=1)
        df['Pct_M5_vs_Prom_M1_4'] = (df['Frec_Mes5'] - prom_M1_4) / (prom_M1_4 + 1e-9)

        feature_cols = [
            'Edad','Sexo',
            'Frec_Mes1','Frec_Mes2','Frec_Mes3','Frec_Mes4','Frec_Mes5',
            'Zona_Recidencial','Metodo_Pago',
            'Tendencia_1_5','Volatilidad_1_5','Pct_M5_vs_Prom_M1_4'
        ]
        for c in feature_cols:
            if c not in df.columns:
                df[c] = 0

        X = df[feature_cols].copy()
        # One-hot igual que el entrenamiento:
        X = pd.get_dummies(X, columns=['Sexo','Zona_Recidencial','Metodo_Pago'], drop_first=False, dtype=float)
        X = X.fillna(0)
        return X.astype(float)

def align_features(X: pd.DataFrame, expected_cols: list) -> pd.DataFrame:
    """
    Reindexa columnas al set de entrenamiento.
    (Las faltantes se rellenan 0; las sobrantes se descartan)
    """
    return X.reindex(columns=expected_cols, fill_value=0).astype(float)
