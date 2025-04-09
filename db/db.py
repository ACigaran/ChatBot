import sqlite3


# Creo una tabla para guardar a los usuarios
# conn = sqlite3.connect('telegram_bot.db')
# cursor = conn.cursor()

# cursor.execute('''
#     CREATE TABLE IF NOT EXISTS users (
#     id INTEGER PRIMARY KEY,
#     telegram_id INTEGER UNIQUE,
#     name TEXT
# )
# ''')

# conn.commit()
# cursor.close()
# conn.close()

# #####################

# # Creo una tabla para guardar las cuentas/cajas de ahorro
# conn = sqlite3.connect('telegram_bot.db')
# cursor = conn.cursor()

# cursor.execute('''
#     CREATE TABLE IF NOT EXISTS cuentas (
#     id INTEGER PRIMARY KEY,
#     name TEXT,
#     dinero INTEGER
# )
# ''')

# # Inserto datos iniciales en dichas cuentas
# cursor.execute('''
#     INSERT INTO cuentas (id, name, dinero)
#     VALUES 
#     (1, "Cuenta Pesos", 5000),
#     (2, "Cuenta Dolares", 250);
# ''')

# conn.commit()
# cursor.close()
# conn.close()

###################################################