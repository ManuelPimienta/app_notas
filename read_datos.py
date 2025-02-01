import pandas as pd

# Cargar el archivo de Excel
df = pd.read_excel("notas.xlsx")

# Convertir el DataFrame a un diccionario para facilitar el acceso
notas = df.to_dict(orient="records")