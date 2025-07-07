import mysql.connector
from pymongo import MongoClient

# --- Conexión a MySQL ---
try:
    mysql_conn = mysql.connector.connect(
        host="localhost",
        user="root",          # Cambia si usas otro usuario
        password="",          # Pon tu contraseña de MySQL si tienes
        database="sistema de inventario"
    )
    mysql_cursor = mysql_conn.cursor(dictionary=True)
except mysql.connector.Error as err:
    print(f"❌ Error al conectar con MySQL: {err}")
    exit()

# --- Conexión a MongoDB local (Compass) ---
try:
    mongo_client = MongoClient("mongodb://localhost:27017/")
    mongo_db = mongo_client["sistema_inventario_mongo"]
except Exception as err:
    print(f"❌ Error al conectar con MongoDB: {err}")
    mysql_cursor.close()
    mysql_conn.close()
    exit()

# --- Tablas a exportar ---
tablas = ["usuarioos", "inventario"]

for tabla in tablas:
    try:
        print(f"📦 Exportando tabla: {tabla}")
        mysql_cursor.execute(f"SELECT * FROM {tabla}")
        datos = mysql_cursor.fetchall()
        if datos:
            mongo_db[tabla].insert_many(datos)
            print(f"✅ {len(datos)} registros insertados en MongoDB -> colección '{tabla}'")
        else:
            print(f"⚠️ La tabla '{tabla}' está vacía.")
    except Exception as e:
        print(f"❌ Error al exportar la tabla '{tabla}': {e}")

# --- Cierre de conexiones ---
mysql_cursor.close()
mysql_conn.close()
mongo_client.close()

print("✅ Exportación completa.")
