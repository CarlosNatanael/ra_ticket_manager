from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from dotenv import load_dotenv
import requests
import sqlite3
import os

load_dotenv()

app = Flask(__name__)
DB_NAME = 'ticket_manager.db'
RA_USER = os.getenv('RA_API_USER')
RA_KEY = os.getenv('RA_API_KEY')
RA_API_BASE = "https://retroachievements.org/API/"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute('''
        CREATE TABLE IF NOT EXISTS system_info (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    return conn

@app.route('/')
def monitor():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM monitored_items').fetchall()
    
    sync_data = conn.execute("SELECT value FROM system_info WHERE key = 'last_sync'").fetchone()
    last_sync = sync_data['value'] if sync_data else "Nunca sincronizado"
    
    conn.close()
    return render_template('monitor.html', items=items, last_sync=last_sync)

@app.route('/add_view')
def add_view():
    return render_template('add.html')

@app.route('/add', methods=['POST'])
def add():
    game_id = request.form['game_id']
    achievement_id = request.form.get('achievement_id', '')
    item_type = request.form['item_type']
    notes = request.form['notes']

    if not achievement_id:
        achievement_id = None

    if game_id and item_type:
        title = "Desconhecido"
        icon_url = "https://media.retroachievements.org/Badge/00000.png"

        if item_type == 'game':
            params = {'z': RA_USER, 'y': RA_KEY, 'i': game_id}
            try:
                resp = requests.get(f"{RA_API_BASE}API_GetGame.php", params=params, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    title = data.get('GameTitle', f'Jogo {game_id}')
                    icon_path = data.get('ImageIcon', '')
                    if icon_path:
                        icon_url = f"https://media.retroachievements.org{icon_path}"
            except Exception as e:
                title = f'Jogo {game_id}'
        else:
            params = {'z': RA_USER, 'y': RA_KEY, 'i': game_id}
            try:
                resp = requests.get(f"{RA_API_BASE}API_GetGameExtended.php", params=params, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    achievements = data.get('Achievements', {})

                    ach_data = achievements.get(str(achievement_id))
                    
                    if ach_data:
                        title = ach_data.get('Title', f'Conquista {achievement_id}')
                        badge = ach_data.get('BadgeName', '00000')
                        icon_url = f"https://media.retroachievements.org/Badge/{badge}.png"
                    else:
                        title = f'Conquista {achievement_id}'
            except Exception as e:
                title = f'Conquista {achievement_id}'

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO monitored_items (game_id, achievement_id, item_type, notes, title, icon_url) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (game_id, achievement_id, item_type, notes, title, icon_url))
        conn.commit()
        conn.close()
        
    return redirect(url_for('monitor'))

@app.route('/delete/<int:item_id>', methods=['POST'])
def delete(item_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM monitored_items WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('monitor'))

if __name__ == '__main__':
    app.run(debug=True)