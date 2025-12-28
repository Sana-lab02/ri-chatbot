import sqlite3
import pandas as pd


CUSTOMER_EXCEL = 'file_path'
TROUBLE_EXCEL = 'file_path'
DB_PATH = 'retailers.db'

df = pd.read_excel(CUSTOMER_EXCEL)

conn = sqlite3.connect("retailers.db")
cursor = conn.cursor()

df_customers = pd.read_excel(CUSTOMER_EXCEL)

# Clean column names
df_customers.columns = (
    df_customers.columns
  # replace spaces with underscore
    .str.strip()
    .str.replace(":", "")    # remove colons
)

print("DEBUG COLUMN NAMES:", df_customers.columns.tolist())


rename_map = {
    "Arlin": "arlin",
    "#": "ipad_number",
    "email": "email",
    "RI App Username": "ri_app_username",
    "RI App Password": "ri_app_password",
    "Retailer": "retailer",
    "Account #": "account_number",
    "App Version": "app_version",
    "iOS Version": "ios_version",
    "Serial Number": "serial_number",
    "System Model": "system_model",
    "Sensor Serial #": "sensor_serial",
    "Notes": "notes"
}


df_customers = df_customers.rename(columns=rename_map)

df_customers['account_number'] = df_customers['account_number'].astype(str).str.replace('.0$', '', regex=True)

df_customers = df_customers.where(pd.notnull(df_customers), None)

df_customers = df_customers.drop_duplicates(subset=['retailer'])


cursor.execute("DROP TABLE IF EXISTS retailers")
               
               

cursor.execute("""
CREATE TABLE retailers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arlin TEXT,
    ipad_number TEXT,
    email TEXT,
    ri_app_username TEXT,
    ri_app_password TEXT,
    retailer TEXT UNIQUE NOT NULL,
    account_number TEXT,
    app_version TEXT,
    ios_version TEXT,
    serial_number TEXT,
    system_model TEXT,
    sensor_serial TEXT,
    notes TEXT
)
""")              

df_customers["retailer"] = (
    df_customers["retailer"]
    .astype(str)
    .str.strip()
)
df_customers.to_sql("retailers", conn, if_exists="append", index=False)
print("Success: Excel imported into retailers.db")

df_trouble = pd.read_excel(TROUBLE_EXCEL)

df_trouble.columns = df_trouble.columns.str.strip()

cursor.execute("DROP TABLE IF EXISTS troubleshooting")

cursor.execute("""
CREATE TABLE troubleshooting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL
)
""")

df_trouble.to_sql("troubleshooting", conn, if_exists="append", index=False)
print(f"imported{len(df_trouble)} troubleshooting entries")

conn.commit()
conn.close()

print("SUCCESS: Both customer and troubleshooting imported into db")
