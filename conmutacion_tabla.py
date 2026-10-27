# conmutacion_tabla.py
import pandas as pd


def obtener_valores_conmutados(df_tabla: pd.DataFrame, edad: int) -> dict:
    fila = df_tabla[df_tabla['x'] == edad]
    if fila.empty:
        # Después de la última edad de la tabla ya no hay sobrevivientes:
        # todos los valores conmutados valen 0 (no es un error)
        if edad > int(df_tabla['x'].max()):
            return {'x': edad, 'Dx': 0.0, 'D_x': 0.0, 'Nx': 0.0, 'N_x': 0.0,
                    'Mx': 0.0, 'M_x': 0.0, 'Cx': 0.0, 'C_x': 0.0}
        raise ValueError(f"La edad {edad} no se encuentra en la tabla de mortalidad.")

    row = fila.iloc[0].to_dict()

    dx = row.get('Dx', row.get('D_x'))
    nx = row.get('Nx', row.get('N_x'))
    mx = row.get('Mx', row.get('M_x'))
    cx = row.get('Cx', row.get('C_x'))

    return {
        'x': int(row['x']),
        'Dx': dx, 'D_x': dx,
        'Nx': nx, 'N_x': nx,
        'Mx': mx, 'M_x': mx,
        'Cx': cx, 'C_x': cx
    }


def cargar_y_conmutar_tabla(ruta_o_archivo, tasa_interes: float) -> pd.DataFrame:
    try:
        df = pd.read_excel(ruta_o_archivo, header=3)
    except Exception:
        df = pd.read_excel(ruta_o_archivo)

    if not any(str(c).strip().lower() in ['lx', 'edad x', 'edad'] for c in df.columns):
        df_raw = pd.read_excel(ruta_o_archivo, header=None)
        for idx, row in df_raw.iterrows():
            valores_row = [str(v).strip().lower() for v in row.values]
            if 'lx' in valores_row or 'edad x' in valores_row:
                df = pd.read_excel(ruta_o_archivo, header=idx)
                break

    mapeo_columnas = {}
    for col in df.columns:
        col_clean = str(col).strip().lower().replace('(', '').replace(')', '').replace(' ', '')
        if col_clean in ['x', 'edad', 'edadx']:
            mapeo_columnas[col] = 'x'
        elif col_clean in ['lx', 'l_x', 'l']:
            mapeo_columnas[col] = 'l_x'
        elif col_clean in ['dx', 'd_x', 'd']:
            mapeo_columnas[col] = 'd_x'

    df = df.rename(columns=mapeo_columnas)

    df = df.dropna(subset=['x', 'l_x']).copy()
    df['x'] = pd.to_numeric(df['x'], errors='coerce')
    df['l_x'] = pd.to_numeric(df['l_x'], errors='coerce')
    df = df.dropna(subset=['x', 'l_x']).copy()
    df['x'] = df['x'].astype(int)

    # Orden por edad ascendente (necesario para los acumulados Nx y Mx)
    df = df.sort_values('x').reset_index(drop=True)

    if 'd_x' not in df.columns:
        # En la última edad, l_{x+1} = 0, así que d_x = l_x
        df['d_x'] = df['l_x'] - df['l_x'].shift(-1).fillna(0)
    else:
        df['d_x'] = pd.to_numeric(df['d_x'], errors='coerce').fillna(0)

    v = 1.0 / (1.0 + tasa_interes)
    df['v_x'] = v ** df['x']
    df['v_x_1'] = v ** (df['x'] + 1)

    df['D_x'] = df['l_x'] * df['v_x']
    df['Dx'] = df['D_x']

    df['C_x'] = df['d_x'] * df['v_x_1']
    df['Cx'] = df['C_x']

    df['N_x'] = df['D_x'].iloc[::-1].cumsum().iloc[::-1]
    df['Nx'] = df['N_x']

    df['M_x'] = df['C_x'].iloc[::-1].cumsum().iloc[::-1]
    df['Mx'] = df['M_x']

    return df