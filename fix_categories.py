import sqlite3, os
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tutomotion.db')
db = sqlite3.connect(DB_PATH)
db.execute("UPDATE tutoriels SET categorie = REPLACE(categorie, 'Développement Web', 'Design Graphique')")
db.commit()
print('ok —', db.execute("SELECT COUNT(DISTINCT categorie) FROM tutoriels").fetchone()[0], 'catégories')
db.close()
