import sqlite3
db = sqlite3.connect('tutomotion.db')
db.execute("UPDATE utilisateurs SET role = 'admin' WHERE email = 'guillaumec27@yahoo.com'")
db.commit()
db.close()
print('Compte passé en admin !')
