import sqlite3
from datetime import datetime


def get_user_preferences(user_id):
    conn = sqlite3.connect('user_preferences.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()

    if result:
        return {
            'user_id': result[0],
            'dark_mode': bool(result[1]),
            'search_history': result[2].split('|') if result[2] else [],
            'created_at': result[3]
        }
    return None


def update_user_preferences(user_id, dark_mode=None, search_query=None):
    conn = sqlite3.connect('user_preferences.db')
    c = conn.cursor()

    user = get_user_preferences(user_id)

    if user:
        new_dark_mode = dark_mode if dark_mode is not None else user['dark_mode']

        if search_query:
            updated_history = '|'.join(user['search_history'] + [search_query][-10:])
        else:
            updated_history = user['search_history']

        c.execute("""
            UPDATE users 
            SET dark_mode=?, search_history=?
            WHERE user_id=?
        """, (new_dark_mode, updated_history, user_id))
    else:
        c.execute("""
            INSERT INTO users (user_id, dark_mode, search_history, created_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, dark_mode or False, search_query or '', datetime.now()))

    conn.commit()
    conn.close()
