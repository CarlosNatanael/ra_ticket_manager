from datetime import datetime
from dotenv import load_dotenv
import requests
import sqlite3
import os

load_dotenv()

DB_NAME = 'ticket_manager.db'
WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
RA_USER = os.getenv('RA_API_USER')
RA_KEY = os.getenv('RA_API_KEY')

RA_API_BASE = "https://retroachievements.org/API/"

def send_discord_alert(item, ticket_id, ticket_note):
    tipo = "Conquista" if item['item_type'] == 'achievement' else "Jogo"
    ra_id = item['achievement_id'] if item['item_type'] == 'achievement' else item['game_id']
    
    nota_limpa = ticket_note if ticket_note else "Sem descrição fornecida pelo jogador."
    
    mensagem = {
        "content": f"🚨 **Novo Ticket Aberto!**\n"
                   f"**Tipo:** {tipo}\n"
                   f"**ID Monitorado:** {ra_id}\n"
                   f"**Sua Anotação:** {item['notes']}\n"
                   f"**Detalhe do Ticket:** {nota_limpa}\n"
                   f"**Link:** https://retroachievements.org/ticketmanager.php?i={ticket_id}"
    }
    
    if not WEBHOOK_URL or WEBHOOK_URL.strip() == "":
        print(f"\n[ALERTA LOCAL] Discord não configurado. Novo ticket identificado!")
        print(mensagem["content"] + "\n")
        return

    response = requests.post(WEBHOOK_URL, json=mensagem)
    if response.status_code == 204:
        print(f"Alerta enviado para o Discord (Ticket {ticket_id})")
    else:
        print(f"Erro ao enviar webhook: {response.status_code} - {response.text}")

def check_tickets():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('CREATE TABLE IF NOT EXISTS system_info (key TEXT PRIMARY KEY, value TEXT)')

    items = cursor.execute('SELECT * FROM monitored_items').fetchall()

    for item in items:
        game_id = item['game_id']
        ra_id = item['achievement_id'] or item['game_id']
        print(f"Consultando {item['item_type']} (Game ID: {game_id})...")
        
        params = {'z': RA_USER, 'y': RA_KEY, 'g': game_id, 'd': 1}
        
        try:
            response = requests.get(f"{RA_API_BASE}API_GetTicketData.php", params=params, timeout=10)
            response.raise_for_status()
            dados = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erro ao consultar API do RA para o Game ID {game_id}: {e}")
            continue

        todos_tickets_jogo = dados.get("Tickets", [])
        tickets_alvo = []
        
        for t in todos_tickets_jogo:
            if str(t.get("ReportState")) != "1":
                continue
            
            if item['item_type'] == 'achievement':
                if str(t.get("AchievementID")) == str(item['achievement_id']):
                    tickets_alvo.append(t)
            else:
                tickets_alvo.append(t)

        ticket_count = len(tickets_alvo)
        cursor.execute('UPDATE monitored_items SET ticket_count = ? WHERE id = ?', (ticket_count, item['id']))
        
        tickets_abertos_agora = []

        for ticket in tickets_alvo:
            t_id = ticket.get("ID")
            t_note = ticket.get("ReportNotes")
            
            if not t_id:
                continue
                
            tickets_abertos_agora.append(t_id)

            ja_notificado = cursor.execute('SELECT 1 FROM notified_tickets WHERE ticket_id = ?', (t_id,)).fetchone()
            
            if not ja_notificado:
                send_discord_alert(item, t_id, t_note)
                cursor.execute('INSERT INTO notified_tickets (ticket_id, ra_id, status) VALUES (?, ?, ?)',
                               (t_id, ra_id, 'open'))

        if tickets_abertos_agora:
            placeholders = ','.join('?' * len(tickets_abertos_agora))
            query = f'DELETE FROM notified_tickets WHERE ra_id = ? AND ticket_id NOT IN ({placeholders})'
            cursor.execute(query, [ra_id] + tickets_abertos_agora)
        else:
            cursor.execute('DELETE FROM notified_tickets WHERE ra_id = ?', (ra_id,))
        
        conn.commit()

    agora = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    cursor.execute('INSERT OR REPLACE INTO system_info (key, value) VALUES (?, ?)', ('last_sync', agora))
    conn.commit()
    conn.close()
    print("Verificação concluída.")

if __name__ == '__main__':
    if not RA_USER or not RA_KEY:
        print("ERRO: Configure RA_API_USER e RA_API_KEY no arquivo .env.")
    else:
        check_tickets()