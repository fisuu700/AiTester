"""Application bancaire de démonstration (cible des tests E2E).

Petite webapp Flask + SQLite : liste des comptes, formulaire de virement,
API REST /api/transfer. Sert de cible réaliste pour l'agent de test IA.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template_string, request, url_for

DB_PATH = Path(__file__).parent / "demo_bank.db"

app = Flask(__name__)

PAGE = """\
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>Ma Banque — Démo</title>
  <style>
    body { font-family: sans-serif; max-width: 640px; margin: 40px auto; background: #f8fafc; }
    h1 { color: #0f172a; }
    table { border-collapse: collapse; width: 100%; margin-bottom: 24px; background: white; }
    th, td { border: 1px solid #cbd5e1; padding: 8px 12px; text-align: left; }
    th { background: #e2e8f0; }
    form { background: white; padding: 20px; border: 1px solid #cbd5e1; border-radius: 8px; }
    label { display: block; margin: 10px 0 4px; font-weight: 600; }
    select, input { padding: 8px; width: 100%; box-sizing: border-box; }
    button { margin-top: 16px; padding: 10px 24px; background: #0369a1; color: white; border: none;
             border-radius: 6px; font-size: 15px; cursor: pointer; }
    .flash { padding: 10px; border-radius: 6px; margin-bottom: 16px; }
    .success { background: #dcfce7; color: #166534; }
    .error { background: #fee2e2; color: #991b1b; }
  </style>
</head>
<body>
  <h1>Ma Banque — Démo</h1>
  {% if flash %}
  <div class="flash {{ 'success' if flash.ok else 'error' }}">{{ flash.message }}</div>
  {% endif %}
  <table>
    <tr><th>Compte</th><th>Titulaire</th><th>Type</th><th>Solde (TND)</th></tr>
    {% for account in accounts %}
    <tr><td>{{ account.iban }}</td><td>{{ account.owner }}</td><td>{{ account.account_type }}</td>
        <td>{{ '%.2f'|format(account.balance) }}</td></tr>
    {% endfor %}
  </table>
  <h2>Nouveau virement</h2>
  <form method="post" action="{{ url_for('submit_transfer') }}">
    <label for="source">Compte débité</label>
    <select id="source" name="source">
      {% for account in accounts %}
      <option value="{{ account.iban }}">{{ account.iban }} — {{ account.owner }} ({{ '%.2f'|format(account.balance) }} TND)</option>
      {% endfor %}
    </select>
    <label for="destination">Compte crédité</label>
    <select id="destination" name="destination">
      {% for account in accounts %}
      <option value="{{ account.iban }}">{{ account.iban }} — {{ account.owner }}</option>
      {% endfor %}
    </select>
    <label for="amount">Montant (TND)</label>
    <input id="amount" name="amount" type="number" step="0.01" required>
    <button id="submit-transfer" type="submit">Effectuer le virement</button>
  </form>
</body>
</html>
"""


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            iban TEXT PRIMARY KEY,
            owner TEXT NOT NULL,
            account_type TEXT NOT NULL,
            balance REAL NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    if conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO accounts (iban, owner, account_type, balance) VALUES (?, ?, ?, ?)",
            [
                ("TN5910006035180001234567", "Ahmed Ben Salah", "courant", 1500.00),
                ("TN5910006035180009876543", "Ahmed Ben Salah", "epargne", 10000.00),
            ],
        )
    conn.commit()
    conn.close()


@app.get("/")
def index():
    conn = get_db()
    accounts = conn.execute("SELECT * FROM accounts ORDER BY iban").fetchall()
    conn.close()
    flash = None
    if "ok" in request.args and "message" in request.args:
        flash = {"ok": request.args["ok"] == "1", "message": request.args["message"]}
    return render_template_string(PAGE, accounts=accounts, flash=flash)


@app.post("/api/transfer")
def api_transfer():
    data = request.get_json(silent=True) or {
        "source": request.form.get("source"),
        "destination": request.form.get("destination"),
        "amount": request.form.get("amount"),
    }
    source, destination, amount = data.get("source"), data.get("destination"), data.get("amount")
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Montant invalide"}), 400

    if source == destination:
        return jsonify({"status": "error", "message": "Comptes identiques"}), 400
    if amount <= 0:
        return jsonify({"status": "error", "message": "Le montant doit être positif"}), 400
    if amount > 10000:
        return jsonify({"status": "error", "message": "Plafond de virement dépassé (10000 TND)"}), 400

    conn = get_db()
    try:
        src = conn.execute("SELECT * FROM accounts WHERE iban = ?", (source,)).fetchone()
        dst = conn.execute("SELECT * FROM accounts WHERE iban = ?", (destination,)).fetchone()
        if not src or not dst:
            return jsonify({"status": "error", "message": "Compte introuvable"}), 404
        if src["balance"] < amount:
            return jsonify({"status": "error", "message": "Solde insuffisant"}), 400

        conn.execute("UPDATE accounts SET balance = balance - ? WHERE iban = ?", (amount, source))
        conn.execute("UPDATE accounts SET balance = balance + ? WHERE iban = ?", (amount, destination))
        conn.execute(
            "INSERT INTO transfers (source, destination, amount) VALUES (?, ?, ?)",
            (source, destination, amount),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify({"status": "ok", "message": "Virement effectué", "amount": amount})


@app.post("/transfer")
def submit_transfer():
    result = api_transfer()
    status, code = result
    payload = status.get_json()
    ok = code == 200
    message = payload.get("message", "Erreur inconnue")
    if ok:
        amount = payload.get("amount")
        message = f"Virement de {amount} TND effectué avec succès."
    return redirect(url_for("index", ok="1" if ok else "0", message=message))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8001, debug=False)
