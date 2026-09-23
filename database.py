import sqlite3
import os

DB_NAME = 'ticket_manager.db'

def init_db():
    if os.path.exists(DB_NAME):
        print(f"O banco de dados '{DB_NAME}' já existe. Apague-o primeiro para recriar.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE monitored_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            achievement_id INTEGER, 
            item_type TEXT NOT NULL CHECK(item_type IN ('game', 'achievement')),
            notes TEXT,
            ticket_count INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE notified_tickets (
            ticket_id INTEGER PRIMARY KEY,
            ra_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("Banco de dados atualizado recriado com sucesso!")

if __name__ == '__main__':
    init_db()