import sqlite3


dp = sqlite3.connect('registr.db')
cur = dp.cursor()


def display_table_contents(table_name):
    cur.execute(f'SELECT * FROM {table_name}')
    rows = cur.fetchall()
    
    print(f'Содержимое таблицы {table_name}:')
    for row in rows:
        print(row)
    print() 


display_table_contents('articles')
display_table_contents('message_history')
