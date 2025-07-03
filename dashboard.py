
import json
import sqlite3
import pandas as pd
from flask import Flask, jsonify, render_template
import os

app = Flask(__name__)

DATABASE_PATH = os.path.join('results', 'evaluation.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    # 自動検出したAgentバージョンを昇順で取得
    agent_versions = pd.read_sql_query(
        "SELECT DISTINCT agent_version FROM results ORDER BY agent_version", conn
    )['agent_version'].tolist()
    conn.close()
    return render_template('index.html', agent_versions=agent_versions)

@app.route('/api/data')
def get_data():
    conn = get_db_connection()
    query = """
    SELECT r.run_id, r.timestamp, res.* 
    FROM evaluation_runs r JOIN results res ON r.run_id = res.run_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Convert timestamp to string for JSON serialization
    df['timestamp'] = df['timestamp'].astype(str)
    
    return jsonify(df.to_dict(orient='records'))

if __name__ == '__main__':
    app.run(debug=True)
