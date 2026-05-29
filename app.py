#!/usr/bin/env python3
"""
SIGEP — Sistema Integrado de Gestão de Processos
Sistema web interno para gestão administrativa municipal.
Execute: python3 sigep.py
Acesso: http://localhost:5000
Admin padrão: admin / admin123
"""

import os
import io
import sqlite3
import unicodedata
from datetime import datetime
from functools import wraps

from flask import (Flask, render_template_string, request, redirect,
                   url_for, session, jsonify, send_file, flash)
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SIGEP_SECRET", "sigep-chave-secreta-2024")
DB_PATH = os.path.join(os.path.dirname(__file__), "sigep.db")

# Domínios
ORGAOS = ["SESAU","SEFAZ","CGM","PROJUR","SEMOB","SEMED","SEMDUR",
          "SEMAS","SEAGRI","GPS","SGA","SEMDES","SEMGEST","SEMC"]
TIPOS_PROCESSO = ["Contrato","Aditivo","Credenciamento","Dispensa",
                  "Inexigibilidade","Pagamento Direto","Pregão","Convenio","Outros"]
SITUACOES = ["Em Análise","Aguardando Documentação","Finalizado",
             "Cancelado","Em Diligência"]
FONTES = ["Tesouro Municipal","Transferência Federal","Transferência Estadual",
          "Recursos Próprios","Convênio","Outro"]

# Mapeamento de colunas da planilha → campo interno
COL_MAP = {
    "credor/objeto": "credor_objeto", "credor objeto": "credor_objeto",
    "credor": "credor_objeto", "objeto": "credor_objeto",
    "numero de protocolo": "numero_protocolo", "numero protocolo": "numero_protocolo",
    "no protocolo": "numero_protocolo", "protocolo": "numero_protocolo",
    "quant entrada": "quant_entrada", "quantidade entrada": "quant_entrada",
    "quant de entrada": "quant_entrada", "quantidade": "quant_entrada",
    "data": "data_registro", "data registro": "data_registro",
    "data de registro": "data_registro",
    "orgao": "orgao", "orgão": "orgao",
    "competencia": "competencia", "competência": "competencia",
    "tipo de processo": "tipo_processo", "tipo processo": "tipo_processo",
    "tipo": "tipo_processo",
    "nota/fatura": "nota_fatura", "nota fatura": "nota_fatura",
    "nota": "nota_fatura", "fatura": "nota_fatura",
    "fonte": "fonte",
    "valor": "valor", "valor r$": "valor", "valor rs": "valor",
    "destino": "destino",
    "situacao": "situacao", "situação": "situacao",
    "data de saida": "data_saida", "data saida": "data_saida",
    "data de saída": "data_saida",
    "obs": "observacoes", "obs:": "observacoes",
    "observacoes": "observacoes", "observações": "observacoes",
    "observacao": "observacoes", "observação": "observacoes",
    "analista": "analista_responsavel", "analista responsavel": "analista_responsavel",
    "analista responsável": "analista_responsavel",
}


def normalizar(texto):
    """Remove acentos e converte para minúsculas."""
    if not isinstance(texto, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem_acento.lower().strip()


def mapear_coluna(nome):
    return COL_MAP.get(normalizar(nome))


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            perfil TEXT NOT NULL DEFAULT 'analista',
            criado_em TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS processos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_protocolo TEXT,
            credor_objeto TEXT NOT NULL,
            quant_entrada TEXT,
            data_registro TEXT,
            orgao TEXT,
            competencia TEXT,
            tipo_processo TEXT,
            nota_fatura TEXT,
            fonte TEXT,
            valor REAL,
            destino TEXT,
            situacao TEXT DEFAULT 'Em Análise',
            data_saida TEXT,
            analista_responsavel TEXT,
            observacoes TEXT,
            criado_em TEXT DEFAULT (datetime('now')),
            atualizado_em TEXT DEFAULT (datetime('now'))
        );
        """)
        # Admin padrão
        existe = conn.execute("SELECT 1 FROM usuarios WHERE perfil='admin' LIMIT 1").fetchone()
        if not existe:
            conn.execute(
                "INSERT INTO usuarios (username, password_hash, perfil) VALUES (?,?,?)",
                ("admin", generate_password_hash("admin123"), "admin")
            )
            conn.commit()

        # Migrar dados da tabela legada 'inventario' para 'processos' (executa apenas uma vez)
        tabelas = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if 'inventario' in tabelas:
            ja_migrado = conn.execute("SELECT COUNT(*) FROM processos").fetchone()[0]
            if ja_migrado == 0:
                linhas = conn.execute("SELECT * FROM inventario").fetchall()
                for row in linhas:
                    r = dict(row)
                    try:
                        import re as _re
                        val_str = str(r.get('VALOR') or '0').replace(',', '.').strip()
                        val_num = float(_re.sub(r'[^\d.]', '', val_str) or '0')
                    except Exception:
                        val_num = 0.0
                    credor = (r.get('CREDOR/OBJETO') or '').strip()
                    if not credor:
                        continue
                    conn.execute("""
                        INSERT INTO processos
                        (numero_protocolo, credor_objeto, quant_entrada, data_registro,
                         orgao, competencia, tipo_processo, nota_fatura, fonte, valor,
                         destino, situacao, data_saida, analista_responsavel, observacoes)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        r.get('NÚMERO DE PROTOCOLO') or None,
                        credor,
                        str(r.get('QUANT. ENTRADA') or '') or None,
                        r.get('DATA') or None,
                        r.get('ÓRGÃO') or None,
                        r.get('COMPETÊNCIA') or None,
                        r.get('TIPO DE PROCESSO') or None,
                        r.get('NOTA/FATURA') or None,
                        r.get('FONTE') or None,
                        val_num,
                        r.get('DESTINO') or None,
                        r.get('SITUAÇÃO') or 'Em Análise',
                        r.get('DATA DE SAÍDA') or None,
                        r.get('ANALISTA') or None,
                        r.get('OBS:') or None,
                    ))
                conn.commit()
                print(f"  Migração concluída: {len(linhas)} registros importados de 'inventario' para 'processos'.")


# ---------------------------------------------------------------------------
# Decoradores
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("perfil") != "admin":
            return jsonify({"erro": "Acesso negado"}), 403
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Template HTML principal
# ---------------------------------------------------------------------------
HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SIGEP — Sistema Integrado de Gestão de Processos - PMDD-TI </title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Sora:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0f1117;
  --bg2: #161820;
  --bg3: #1e2030;
  --bg4: #252838;
  --border: #2e3148;
  --border2: #3d4166;
  --text: #c9cde8;
  --text2: #7c83b0;
  --text3: #4e5380;
  --accent: #4f7fff;
  --accent2: #3563e9;
  --accent-glow: rgba(79,127,255,0.15);
  --success: #3dd68c;
  --danger: #f25f5c;
  --warning: #f7b731;
  --header-h: 56px;
  --tab-h: 44px;
  --mono: 'JetBrains Mono', monospace;
  --sans: 'Sora', sans-serif;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body { height: 100%; font-family: var(--sans); background: var(--bg); color: var(--text); font-size: 13px; }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg2); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

/* ── LOGIN ── */
.login-wrap {
  min-height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background: radial-gradient(ellipse at 60% 40%, rgba(79,127,255,.07) 0%, transparent 60%), var(--bg);
}
.login-card {
  width: 380px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 40px 36px 36px;
  box-shadow: 0 24px 80px rgba(0,0,0,.5);
}
.login-logo {
  text-align: center; margin-bottom: 28px;
}
.login-logo .sigil {
  display: inline-flex; align-items: center; justify-content: center;
  width: 52px; height: 52px;
  background: var(--accent); border-radius: 14px;
  font-family: var(--mono); font-size: 20px; font-weight: 600;
  color: #fff; margin-bottom: 12px;
  box-shadow: 0 0 30px rgba(79,127,255,.4);
}
.login-logo h1 { font-size: 15px; font-weight: 700; letter-spacing: 2px; color: var(--text); text-transform: uppercase; }
.login-logo p { font-size: 11px; color: var(--text2); margin-top: 3px; letter-spacing: .5px; }
.login-field { margin-bottom: 16px; }
.login-field label { display: block; font-size: 11px; font-weight: 600; color: var(--text2); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
.login-field input {
  width: 100%; padding: 10px 14px;
  background: var(--bg3); border: 1px solid var(--border); border-radius: 8px;
  color: var(--text); font-family: var(--sans); font-size: 13px;
  transition: all .2s;
}
.login-field input:focus { outline: none; border-color: var(--accent); background: #fff; color: #111; box-shadow: 0 0 0 3px var(--accent-glow); }
.btn-login {
  width: 100%; padding: 11px; margin-top: 8px;
  background: var(--accent); color: #fff;
  border: none; border-radius: 8px; cursor: pointer;
  font-family: var(--sans); font-size: 13px; font-weight: 600;
  letter-spacing: .5px; transition: all .2s;
}
.btn-login:hover { background: var(--accent2); transform: translateY(-1px); box-shadow: 0 6px 20px rgba(79,127,255,.35); }
.login-err { background: rgba(242,95,92,.12); border: 1px solid rgba(242,95,92,.3); border-radius: 8px; color: var(--danger); font-size: 12px; padding: 10px 14px; margin-bottom: 16px; }

/* ── APP SHELL ── */
#app { display: flex; flex-direction: column; height: 100vh; }

.header {
  height: var(--header-h); flex-shrink: 0;
  background: var(--bg2); border-bottom: 1px solid var(--border);
  display: flex; align-items: center; padding: 0 20px; gap: 14px;
}
.header-logo {
  display: flex; align-items: center; gap: 10px;
}
.header-sigil {
  width: 32px; height: 32px; background: var(--accent); border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--mono); font-size: 12px; font-weight: 600; color: #fff;
}
.header-title { font-size: 13px; font-weight: 700; color: var(--text); letter-spacing: 1.5px; text-transform: uppercase; }
.header-subtitle { font-size: 10px; color: var(--text3); letter-spacing: .5px; }
.header-spacer { flex: 1; }
.header-user { font-size: 11px; color: var(--text2); display: flex; align-items: center; gap: 8px; }
.header-badge {
  padding: 2px 8px; border-radius: 20px; font-size: 10px; font-weight: 600;
  background: var(--accent-glow); border: 1px solid var(--accent); color: var(--accent);
  text-transform: uppercase; letter-spacing: .5px;
}
.btn-logout {
  padding: 6px 14px; background: transparent; border: 1px solid var(--border2);
  border-radius: 6px; color: var(--text2); cursor: pointer; font-size: 11px; font-family: var(--sans);
  transition: all .2s;
}
.btn-logout:hover { border-color: var(--danger); color: var(--danger); }

.tabs-bar {
  height: var(--tab-h); flex-shrink: 0;
  background: var(--bg2); border-bottom: 1px solid var(--border);
  display: flex; align-items: flex-end; padding: 0 20px; gap: 2px;
}
.tab-btn {
  padding: 0 20px; height: 38px;
  background: transparent; border: none; border-bottom: 2px solid transparent;
  color: var(--text3); cursor: pointer; font-family: var(--sans);
  font-size: 11px; font-weight: 600; letter-spacing: 1.2px; text-transform: uppercase;
  transition: all .2s;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }

.content { flex: 1; overflow: hidden; position: relative; }
.tab-panel { display: none; height: 100%; overflow-y: auto; padding: 20px; }
.tab-panel.active { display: block; }

/* ── FORMS ── */
.card {
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: 10px; padding: 20px 24px; margin-bottom: 16px;
}
.card-title { font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: var(--text2); margin-bottom: 18px; display: flex; align-items: center; gap: 8px; }
.card-title::before { content: ''; display: block; width: 3px; height: 14px; background: var(--accent); border-radius: 2px; }

.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
.form-field label { display: block; font-size: 10px; font-weight: 600; color: var(--text2); text-transform: uppercase; letter-spacing: .8px; margin-bottom: 5px; }
.form-field input, .form-field select, .form-field textarea {
  width: 100%; padding: 8px 12px;
  background: var(--bg3); border: 1px solid var(--border); border-radius: 6px;
  color: var(--text); font-family: var(--sans); font-size: 12px;
  transition: all .2s;
}
.form-field input:focus, .form-field select:focus, .form-field textarea:focus {
  outline: none; border-color: var(--accent);
  background: #fff; color: #111;
  box-shadow: 0 0 0 3px var(--accent-glow);
}
.form-field select option { background: #1e2030; color: var(--text); }
.form-field textarea { resize: vertical; min-height: 70px; }
.form-field.wide { grid-column: 1 / -1; }

.btn { padding: 8px 18px; border: none; border-radius: 6px; cursor: pointer; font-family: var(--sans); font-size: 12px; font-weight: 600; transition: all .2s; letter-spacing: .3px; display: inline-flex; align-items: center; gap: 6px; }
.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover { background: var(--accent2); transform: translateY(-1px); box-shadow: 0 4px 14px rgba(79,127,255,.3); }
.btn-danger { background: rgba(242,95,92,.12); border: 1px solid rgba(242,95,92,.3); color: var(--danger); }
.btn-danger:hover { background: rgba(242,95,92,.2); }
.btn-danger:disabled { opacity: .4; cursor: not-allowed; transform: none; }
.btn-ghost { background: transparent; border: 1px solid var(--border2); color: var(--text2); }
.btn-ghost:hover { border-color: var(--accent); color: var(--accent); }
.btn-success { background: rgba(61,214,140,.12); border: 1px solid rgba(61,214,140,.3); color: var(--success); }
.btn-success:hover { background: rgba(61,214,140,.2); }

.alert { padding: 10px 14px; border-radius: 6px; font-size: 12px; margin-bottom: 14px; }
.alert-success { background: rgba(61,214,140,.1); border: 1px solid rgba(61,214,140,.25); color: var(--success); }
.alert-danger { background: rgba(242,95,92,.1); border: 1px solid rgba(242,95,92,.25); color: var(--danger); }
.alert-info { background: rgba(79,127,255,.1); border: 1px solid rgba(79,127,255,.25); color: var(--accent); }

/* ── METRICS ── */
.metrics-row { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.metric-card {
  flex: 1; min-width: 150px;
  background: var(--bg3); border: 1px solid var(--border2);
  border-radius: 8px; padding: 12px 16px;
}
.metric-label { font-size: 10px; font-weight: 600; color: var(--text3); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
.metric-val { font-family: var(--mono); font-size: 22px; font-weight: 600; color: var(--text); }
.metric-val.accent { color: var(--accent); }

/* ── TABLE ── */
.table-wrap { overflow: auto; border: 1px solid var(--border); border-radius: 8px; }
table { width: 100%; border-collapse: collapse; min-width: 1100px; }
thead th {
  background: var(--bg4); color: var(--text2);
  font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .8px;
  padding: 10px 10px; text-align: left; border-bottom: 1px solid var(--border2);
  white-space: nowrap; position: sticky; top: 0; z-index: 1;
}
tbody tr { border-bottom: 1px solid var(--border); transition: background .15s; }
tbody tr:nth-child(even) { background: rgba(255,255,255,.015); }
tbody tr:hover { background: var(--accent-glow); }
tbody td { padding: 7px 10px; vertical-align: middle; }
tbody td input, tbody td select {
  background: transparent; border: none; color: var(--text);
  font-family: var(--sans); font-size: 12px; width: 100%; min-width: 80px;
  padding: 2px 4px; border-radius: 4px;
}
tbody td input:focus, tbody td select:focus {
  outline: none; background: #fff; color: #111; box-shadow: 0 0 0 2px var(--accent);
}
tbody td select option { background: #1e2030; color: var(--text); }
.cb-col { width: 36px; text-align: center; }
.id-col { width: 40px; font-family: var(--mono); font-size: 11px; color: var(--text3); }
input[type=checkbox] { accent-color: var(--accent); width: 14px; height: 14px; cursor: pointer; }
.changed-row td:first-child { box-shadow: inset 3px 0 0 var(--warning); }

/* ── FILTERS ── */
.filter-toggle { cursor: pointer; font-size: 11px; color: var(--text2); display: flex; align-items: center; gap: 6px; user-select: none; }
.filter-toggle:hover { color: var(--accent); }
.filter-body { display: none; margin-top: 12px; }
.filter-body.open { display: flex; flex-wrap: wrap; gap: 12px; }
.filter-item { display: flex; flex-direction: column; gap: 4px; min-width: 160px; }
.filter-item label { font-size: 10px; font-weight: 600; color: var(--text3); text-transform: uppercase; letter-spacing: .8px; }
.filter-item select, .filter-item input {
  padding: 7px 10px; background: var(--bg3); border: 1px solid var(--border);
  border-radius: 6px; color: var(--text); font-family: var(--sans); font-size: 12px;
}
.filter-item select:focus, .filter-item input:focus { outline: none; border-color: var(--accent); background: #fff; color: #111; }

/* ── USERS ── */
.user-list { display: flex; flex-direction: column; gap: 8px; }
.user-row {
  display: flex; align-items: center; gap: 12px;
  background: var(--bg3); border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px;
}
.user-avatar {
  width: 34px; height: 34px; border-radius: 50%;
  background: var(--accent-glow); border: 1px solid var(--accent);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 13px; color: var(--accent); flex-shrink: 0;
}
.user-info { flex: 1; }
.user-name { font-size: 13px; font-weight: 600; color: var(--text); }
.user-meta { font-size: 11px; color: var(--text3); }
.badge { display: inline-flex; padding: 2px 8px; border-radius: 20px; font-size: 10px; font-weight: 700; letter-spacing: .5px; text-transform: uppercase; }
.badge-admin { background: rgba(247,183,49,.12); border: 1px solid rgba(247,183,49,.3); color: var(--warning); }
.badge-analista { background: rgba(79,127,255,.12); border: 1px solid rgba(79,127,255,.3); color: var(--accent); }

/* ── IMPORT ── */
.import-zone {
  border: 2px dashed var(--border2); border-radius: 8px; padding: 28px;
  text-align: center; cursor: pointer; transition: all .2s; margin-bottom: 14px;
}
.import-zone:hover, .import-zone.drag { border-color: var(--accent); background: var(--accent-glow); }
.import-zone p { color: var(--text2); font-size: 12px; }
.preview-table-wrap { max-height: 220px; overflow: auto; border: 1px solid var(--border); border-radius: 6px; }
.preview-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.preview-table th { background: var(--bg4); padding: 6px 10px; color: var(--text2); font-size: 10px; text-transform: uppercase; letter-spacing: .5px; }
.preview-table td { padding: 5px 10px; border-bottom: 1px solid var(--border); color: var(--text); }

/* ── MISC ── */
.btn-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; align-items: center; }
.sel-count { font-size: 11px; color: var(--text2); padding: 4px 10px; background: var(--bg3); border-radius: 20px; font-family: var(--mono); }
.hidden { display: none !important; }
</style>
</head>
<body>

{% if not session.get('user_id') %}
<!-- ══════════════════ LOGIN ══════════════════ -->
<div class="login-wrap">
  <div class="login-card">
    <div class="login-logo">
      <div class="sigil" style="background:transparent;padding:0;overflow:hidden"><img src="data:image/png;base64,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" style="width:52px;height:52px;object-fit:cover;border-radius:14px"></div>
      <h1>SIGEP</h1>
      <p>Sistema Integrado de Gestão de Processos</p>
    </div>
    {% if error %}
    <div class="login-err">{{ error }}</div>
    {% endif %}
    <form method="POST" action="/login">
      <div class="login-field">
        <label>Usuário</label>
        <input type="text" name="username" required autofocus autocomplete="username">
      </div>
      <div class="login-field">
        <label>Senha</label>
        <input type="password" name="password" required autocomplete="current-password">
      </div>
      <button type="submit" class="btn-login">Entrar no Sistema</button>
    </form>
  </div>
</div>

{% else %}
<!-- ══════════════════ APP ══════════════════ -->
<div id="app">
  <header class="header">
    <div class="header-logo">
      <div class="header-sigil" style="background:transparent;padding:0;overflow:hidden"><img src="data:image/png;base64,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" style="width:32px;height:32px;object-fit:cover;border-radius:8px"></div>
      <div>
        <div class="header-title">SIGEP</div>
        <div class="header-subtitle">Gestão de Processos - PMDD-TI </div>
      </div>
    </div>
    <div class="header-spacer"></div>
    <div class="header-user">
      <span>{{ session.username }}</span>
      <span class="header-badge {% if session.perfil == 'admin' %}badge-admin{% else %}badge-analista{% endif %}">
        {{ session.perfil }}
      </span>
      <button class="btn-logout" onclick="location.href='/logout'">Sair</button>
    </div>
  </header>

  <nav class="tabs-bar">
    <button class="tab-btn active" onclick="switchTab('cadastro',this)">Cadastro</button>
    <button class="tab-btn" onclick="switchTab('registros',this)">Registros</button>
    {% if session.perfil == 'admin' %}
    <button class="tab-btn" onclick="switchTab('usuarios',this)">Usuários</button>
    {% endif %}
  </nav>

  <main class="content">

    <!-- ══ ABA CADASTRO ══ -->
    <div id="tab-cadastro" class="tab-panel active">
      <div class="card">
        <div class="card-title">Novo Processo</div>
        <div id="cadastro-alert"></div>
        <form id="form-cadastro">
          <div class="form-grid">
            <div class="form-field">
              <label>Nº de Protocolo *</label>
              <input type="text" name="numero_protocolo" required>
            </div>
            <div class="form-field">
              <label>Credor / Objeto *</label>
              <input type="text" name="credor_objeto" required>
            </div>
            <div class="form-field">
              <label>Quant. Entrada</label>
              <input type="text" name="quant_entrada">
            </div>
            <div class="form-field">
              <label>Data de Registro</label>
              <input type="date" name="data_registro">
            </div>
            <div class="form-field">
              <label>Órgão</label>
              <select name="orgao">
                <option value="">-- Selecione --</option>
                {% for o in orgaos %}<option>{{ o }}</option>{% endfor %}
              </select>
            </div>
            <div class="form-field">
              <label>Competência</label>
              <input type="text" name="competencia" placeholder="Ex: 01/2024">
            </div>
            <div class="form-field">
              <label>Tipo de Processo</label>
              <select name="tipo_processo">
                <option value="">-- Selecione --</option>
                {% for t in tipos %}<option>{{ t }}</option>{% endfor %}
              </select>
            </div>
            <div class="form-field">
              <label>Nota / Fatura</label>
              <input type="text" name="nota_fatura">
            </div>
            <div class="form-field">
              <label>Fonte</label>
              <select name="fonte">
                <option value="">-- Selecione --</option>
                {% for f in fontes %}<option>{{ f }}</option>{% endfor %}
              </select>
            </div>
            <div class="form-field">
              <label>Valor (R$)</label>
              <input type="number" name="valor" step="0.01" min="0">
            </div>
            <div class="form-field">
              <label>Destino</label>
              <input type="text" name="destino">
            </div>
            <div class="form-field">
              <label>Situação</label>
              <select name="situacao">
                {% for s in situacoes %}<option>{{ s }}</option>{% endfor %}
              </select>
            </div>
            <div class="form-field">
              <label>Data de Saída</label>
              <input type="date" name="data_saida">
            </div>
            <div class="form-field">
              <label>Analista Responsável</label>
              <input type="text" name="analista_responsavel">
            </div>
            <div class="form-field wide">
              <label>Observações</label>
              <textarea name="observacoes" rows="3"></textarea>
            </div>
          </div>
          <div class="btn-row">
            <button type="submit" class="btn btn-primary">✦ Cadastrar Processo</button>
          </div>
        </form>
      </div>

      <!-- IMPORTAÇÃO -->
      <div class="card">
        <div class="card-title">Importação em Massa</div>
        <div id="import-alert"></div>
        <div class="import-zone" id="drop-zone" onclick="document.getElementById('file-input').click()">
          <p>📂 Clique ou arraste uma planilha (.xlsx, .xls, .csv) aqui</p>
          <p style="margin-top:6px;font-size:11px;color:var(--text3)">Colunas mapeadas automaticamente</p>
        </div>
        <input type="file" id="file-input" accept=".xlsx,.xls,.csv" class="hidden" onchange="handleFileSelect(this.files[0])">
        <div id="preview-area" class="hidden">
          <div class="preview-table-wrap" id="preview-table-container"></div>
          <div class="btn-row" style="margin-top:12px">
            <button class="btn btn-primary" onclick="confirmarImportacao()">✦ Confirmar Importação</button>
            <button class="btn btn-ghost" onclick="cancelarImportacao()">Cancelar</button>
            <span id="import-col-info" style="font-size:11px;color:var(--text2)"></span>
          </div>
        </div>
        <div style="margin-top:12px">
          <a href="/modelo-planilha" class="btn btn-ghost" style="text-decoration:none;font-size:11px">⬇ Baixar Modelo de Planilha</a>
        </div>
      </div>
    </div>

    <!-- ══ ABA REGISTROS ══ -->
    <div id="tab-registros" class="tab-panel">
      <div class="card" style="padding:14px 20px">
        <div class="filter-toggle" onclick="toggleFiltros()">
          <span id="filter-arrow">▶</span> <strong>FILTROS</strong>
        </div>
        <div class="filter-body" id="filter-body">
          <div class="filter-item">
            <label>Situação</label>
            <select id="f-situacao" onchange="aplicarFiltros()">
              <option value="">Todas</option>
              {% for s in situacoes %}<option>{{ s }}</option>{% endfor %}
            </select>
          </div>
          <div class="filter-item">
            <label>Órgão</label>
            <select id="f-orgao" onchange="aplicarFiltros()">
              <option value="">Todos</option>
              {% for o in orgaos %}<option>{{ o }}</option>{% endfor %}
            </select>
          </div>
          <div class="filter-item">
            <label>Data Início</label>
            <input type="date" id="f-dt-inicio" onchange="aplicarFiltros()">
          </div>
          <div class="filter-item">
            <label>Data Fim</label>
            <input type="date" id="f-dt-fim" onchange="aplicarFiltros()">
          </div>
          <div class="filter-item" style="justify-content:flex-end;padding-top:20px">
            <button class="btn btn-ghost" onclick="limparFiltros()" style="font-size:11px">Limpar Filtros</button>
          </div>
        </div>
      </div>

      <div class="metrics-row">
        <div class="metric-card">
          <div class="metric-label">Total no Banco</div>
          <div class="metric-val" id="m-total">—</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Filtrados</div>
          <div class="metric-val accent" id="m-filtrado">—</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Valor Total Filtrado</div>
          <div class="metric-val" id="m-valor">—</div>
        </div>
      </div>

      <div class="btn-row" style="margin-bottom:12px">
        <button class="btn btn-primary" onclick="salvarEdicoes()">💾 Salvar Edições</button>
        <button class="btn btn-danger" id="btn-excluir" onclick="excluirSelecionados()" disabled>🗑 Excluir Selecionados</button>
        <span class="sel-count hidden" id="sel-count">0 selecionados</span>
        <div style="flex:1"></div>
        <button class="btn btn-ghost" onclick="exportar('xlsx')">⬇ Excel</button>
        <button class="btn btn-ghost" onclick="exportar('csv')">⬇ CSV</button>
      </div>

      <div id="tab-alert"></div>
      <div class="table-wrap">
        <table id="tabela-processos">
          <thead>
            <tr>
              <th class="cb-col"><input type="checkbox" id="cb-all" onchange="toggleAllCbs(this)"></th>
              <th class="id-col">#</th>
              <th>Protocolo</th>
              <th>Credor/Objeto</th>
              <th>Qtd</th>
              <th>Data Reg.</th>
              <th>Órgão</th>
              <th>Competência</th>
              <th>Tipo</th>
              <th>Nota/Fatura</th>
              <th>Fonte</th>
              <th>Valor (R$)</th>
              <th>Destino</th>
              <th>Situação</th>
              <th>Data Saída</th>
              <th>Analista</th>
              <th>Observações</th>
            </tr>
          </thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
    </div>

    <!-- ══ ABA USUÁRIOS ══ -->
    {% if session.perfil == 'admin' %}
    <div id="tab-usuarios" class="tab-panel">
      <div class="card" style="max-width:600px">
        <div class="card-title">Novo Usuário</div>
        <div id="user-alert"></div>
        <div class="form-grid">
          <div class="form-field">
            <label>Nome de Usuário</label>
            <input type="text" id="new-username">
          </div>
          <div class="form-field">
            <label>Senha</label>
            <input type="password" id="new-password">
          </div>
          <div class="form-field">
            <label>Perfil</label>
            <select id="new-perfil">
              <option value="analista">Analista</option>
              <option value="admin">Administrador</option>
            </select>
          </div>
        </div>
        <div class="btn-row">
          <button class="btn btn-primary" onclick="criarUsuario()">✦ Criar Usuário</button>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Usuários Cadastrados</div>
        <div class="user-list" id="user-list">Carregando...</div>
      </div>
    </div>
    {% endif %}

  </main>
</div>

<script>
const IS_ADMIN = {{ 'true' if session.perfil == 'admin' else 'false' }};
const ORGAOS = {{ orgaos|tojson }};
const TIPOS = {{ tipos|tojson }};
const SITUACOES = {{ situacoes|tojson }};
const FONTES = {{ fontes|tojson }};
const CURRENT_USER = '{{ session.username }}';

let allProcessos = [];
let filteredProcessos = [];
let changedRows = new Set();
let selectedIds = new Set();

// ── TABS ──
function switchTab(name, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  const panel = document.getElementById('tab-' + name);
  if (panel) panel.classList.add('active');
  btn.classList.add('active');
  if (name === 'registros') carregarProcessos();
  if (name === 'usuarios') carregarUsuarios();
}

// ── CADASTRO ──
document.getElementById('form-cadastro').addEventListener('submit', async e => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const data = Object.fromEntries(fd.entries());
  const res = await fetch('/api/processos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
  const j = await res.json();
  const el = document.getElementById('cadastro-alert');
  if (j.ok) {
    el.innerHTML = '<div class="alert alert-success">✔ Processo cadastrado com sucesso! (ID: ' + j.id + ')</div>';
    e.target.reset();
  } else {
    el.innerHTML = '<div class="alert alert-danger">✖ ' + j.erro + '</div>';
  }
  setTimeout(() => el.innerHTML = '', 4000);
});

// ── IMPORTAÇÃO ──
let importData = null;
const dropZone = document.getElementById('drop-zone');

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag'));
dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('drag'); handleFileSelect(e.dataTransfer.files[0]); });

async function handleFileSelect(file) {
  if (!file) return;
  const fd = new FormData();
  fd.append('arquivo', file);
  const res = await fetch('/api/importar/preview', {method:'POST', body:fd});
  const j = await res.json();
  const alertEl = document.getElementById('import-alert');
  if (!j.ok) {
    alertEl.innerHTML = '<div class="alert alert-danger">' + j.erro + '</div>';
    return;
  }
  importData = j;
  document.getElementById('import-col-info').textContent = j.mapeadas + ' colunas mapeadas de ' + j.total_cols + ' encontradas';
  const rows = j.preview;
  if (!rows.length) { alertEl.innerHTML = '<div class="alert alert-info">Nenhuma linha encontrada.</div>'; return; }
  const cols = Object.keys(rows[0]);
  let html = '<table class="preview-table"><thead><tr>' + cols.map(c => '<th>' + c + '</th>').join('') + '</tr></thead><tbody>';
  rows.forEach(r => { html += '<tr>' + cols.map(c => '<td>' + (r[c] ?? '') + '</td>').join('') + '</tr>'; });
  html += '</tbody></table>';
  document.getElementById('preview-table-container').innerHTML = html;
  document.getElementById('preview-area').classList.remove('hidden');
  alertEl.innerHTML = '';
}

async function confirmarImportacao() {
  if (!importData) return;
  const res = await fetch('/api/importar/confirmar', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({dados: importData.dados})});
  const j = await res.json();
  const alertEl = document.getElementById('import-alert');
  if (j.ok) {
    alertEl.innerHTML = '<div class="alert alert-success">✔ ' + j.importados + ' registros importados com sucesso!</div>';
    cancelarImportacao();
  } else {
    alertEl.innerHTML = '<div class="alert alert-danger">✖ ' + j.erro + '</div>';
  }
}

function cancelarImportacao() {
  importData = null;
  document.getElementById('preview-area').classList.add('hidden');
  document.getElementById('preview-table-container').innerHTML = '';
  document.getElementById('file-input').value = '';
}

// ── REGISTROS ──
async function carregarProcessos() {
  const sit = document.getElementById('f-situacao')?.value || '';
  const org = document.getElementById('f-orgao')?.value || '';
  const di = document.getElementById('f-dt-inicio')?.value || '';
  const df = document.getElementById('f-dt-fim')?.value || '';
  const params = new URLSearchParams({situacao:sit, orgao:org, dt_inicio:di, dt_fim:df});
  const res = await fetch('/api/processos?' + params);
  const j = await res.json();
  allProcessos = j.todos;
  filteredProcessos = j.filtrados;
  document.getElementById('m-total').textContent = j.total;
  document.getElementById('m-filtrado').textContent = j.count;
  document.getElementById('m-valor').textContent = 'R$ ' + (j.valor_total || 0).toLocaleString('pt-BR', {minimumFractionDigits:2});
  renderTabela(filteredProcessos);
  changedRows.clear();
  selectedIds.clear();
  updateExcluirBtn();
}

function mkOption(list, val) {
  let s = '<option value="">--</option>';
  list.forEach(v => { s += '<option' + (v===val?' selected':'') + '>' + v + '</option>'; });
  return s;
}

function renderTabela(rows) {
  const tb = document.getElementById('tbody');
  const readOnly = !IS_ADMIN;
  if (!rows.length) { tb.innerHTML = '<tr><td colspan="17" style="text-align:center;padding:30px;color:var(--text3)">Nenhum registro encontrado.</td></tr>'; return; }
  tb.innerHTML = rows.map(r => {
    const editable = IS_ADMIN;
    const editSit = IS_ADMIN || true; // analista pode editar situação, analista, obs
    const inp = (field, val, readonlyCheck) => readonlyCheck
      ? '<span style="padding:2px 4px">' + (val||'') + '</span>'
      : '<input type="text" value="' + esc(val) + '" oninput="markChanged(' + r.id + ',this.closest(\'tr\'))" data-field="' + field + '" data-id="' + r.id + '">';
    const sel = (field, list, val, readonlyCheck) => readonlyCheck
      ? '<span style="padding:2px 4px">' + (val||'') + '</span>'
      : '<select onchange="markChanged(' + r.id + ',this.closest(\'tr\'))" data-field="' + field + '" data-id="' + r.id + '">' + mkOption(list, val) + '</select>';
    return '<tr data-id="' + r.id + '">'
      + '<td class="cb-col"><input type="checkbox" class="row-cb" value="' + r.id + '" onchange="toggleSel(this)"></td>'
      + '<td class="id-col">' + r.id + '</td>'
      + '<td>' + inp('numero_protocolo', r.numero_protocolo, !editable) + '</td>'
      + '<td>' + inp('credor_objeto', r.credor_objeto, !editable) + '</td>'
      + '<td>' + inp('quant_entrada', r.quant_entrada, !editable) + '</td>'
      + '<td>' + inp('data_registro', r.data_registro, !editable) + '</td>'
      + '<td>' + sel('orgao', ORGAOS, r.orgao, !editable) + '</td>'
      + '<td>' + inp('competencia', r.competencia, !editable) + '</td>'
      + '<td>' + sel('tipo_processo', TIPOS, r.tipo_processo, !editable) + '</td>'
      + '<td>' + inp('nota_fatura', r.nota_fatura, !editable) + '</td>'
      + '<td>' + sel('fonte', FONTES, r.fonte, !editable) + '</td>'
      + '<td>' + inp('valor', r.valor, !editable) + '</td>'
      + '<td>' + inp('destino', r.destino, !editable) + '</td>'
      + '<td>' + sel('situacao', SITUACOES, r.situacao, false) + '</td>'
      + '<td>' + inp('data_saida', r.data_saida, !editable) + '</td>'
      + '<td>' + inp('analista_responsavel', r.analista_responsavel, false) + '</td>'
      + '<td>' + inp('observacoes', r.observacoes, false) + '</td>'
      + '</tr>';
  }).join('');
}

function esc(v) { return (v||'').toString().replace(/"/g,'&quot;').replace(/</g,'&lt;'); }

function markChanged(id, tr) {
  changedRows.add(id);
  tr.classList.add('changed-row');
}

function toggleSel(cb) {
  if (cb.checked) selectedIds.add(parseInt(cb.value));
  else selectedIds.delete(parseInt(cb.value));
  updateExcluirBtn();
}

function toggleAllCbs(master) {
  document.querySelectorAll('.row-cb').forEach(cb => {
    cb.checked = master.checked;
    if (master.checked) selectedIds.add(parseInt(cb.value));
    else selectedIds.delete(parseInt(cb.value));
  });
  updateExcluirBtn();
}

function updateExcluirBtn() {
  const btn = document.getElementById('btn-excluir');
  const cnt = document.getElementById('sel-count');
  const n = selectedIds.size;
  btn.disabled = n === 0;
  if (n > 0) { cnt.classList.remove('hidden'); cnt.textContent = n + ' selecionado' + (n>1?'s':''); }
  else cnt.classList.add('hidden');
}

async function salvarEdicoes() {
  if (!changedRows.size) return;
  const updates = [];
  changedRows.forEach(id => {
    const tr = document.querySelector('tr[data-id="' + id + '"]');
    if (!tr) return;
    const dados = {id};
    tr.querySelectorAll('[data-field]').forEach(el => { dados[el.dataset.field] = el.value; });
    updates.push(dados);
  });
  const res = await fetch('/api/processos/bulk-update', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({updates})});
  const j = await res.json();
  const alertEl = document.getElementById('tab-alert');
  if (j.ok) {
    alertEl.innerHTML = '<div class="alert alert-success">✔ ' + j.atualizados + ' registro(s) salvo(s).</div>';
    document.querySelectorAll('.changed-row').forEach(tr => tr.classList.remove('changed-row'));
    changedRows.clear();
  } else {
    alertEl.innerHTML = '<div class="alert alert-danger">✖ Erro ao salvar.</div>';
  }
  setTimeout(() => alertEl.innerHTML = '', 3000);
}

async function excluirSelecionados() {
  if (!selectedIds.size) return;
  if (!confirm('Excluir ' + selectedIds.size + ' registro(s)? Esta ação não pode ser desfeita.')) return;
  const res = await fetch('/api/processos/bulk-delete', {method:'DELETE', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ids:[...selectedIds]})});
  const j = await res.json();
  const alertEl = document.getElementById('tab-alert');
  if (j.ok) {
    alertEl.innerHTML = '<div class="alert alert-success">✔ ' + j.excluidos + ' registro(s) excluído(s).</div>';
    selectedIds.clear();
    await carregarProcessos();
  } else {
    alertEl.innerHTML = '<div class="alert alert-danger">✖ Erro ao excluir.</div>';
  }
  setTimeout(() => alertEl.innerHTML = '', 3000);
}

async function exportar(fmt) {
  const sit = document.getElementById('f-situacao')?.value || '';
  const org = document.getElementById('f-orgao')?.value || '';
  const di = document.getElementById('f-dt-inicio')?.value || '';
  const df = document.getElementById('f-dt-fim')?.value || '';
  window.location.href = '/api/exportar?formato=' + fmt + '&situacao=' + sit + '&orgao=' + org + '&dt_inicio=' + di + '&dt_fim=' + df;
}

// ── FILTROS ──
function toggleFiltros() {
  const body = document.getElementById('filter-body');
  const arrow = document.getElementById('filter-arrow');
  body.classList.toggle('open');
  arrow.textContent = body.classList.contains('open') ? '▼' : '▶';
}

function aplicarFiltros() { carregarProcessos(); }

function limparFiltros() {
  ['f-situacao','f-orgao','f-dt-inicio','f-dt-fim'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  carregarProcessos();
}

// ── USUÁRIOS ──
async function carregarUsuarios() {
  const res = await fetch('/api/usuarios');
  const j = await res.json();
  const ul = document.getElementById('user-list');
  if (!j.length) { ul.innerHTML = '<p style="color:var(--text3)">Nenhum usuário.</p>'; return; }
  ul.innerHTML = j.map(u => `
    <div class="user-row">
      <div class="user-avatar">${u.username[0].toUpperCase()}</div>
      <div class="user-info">
        <div class="user-name">${u.username}</div>
        <div class="user-meta">Criado em ${u.criado_em || '-'}</div>
      </div>
      <span class="badge ${u.perfil==='admin'?'badge-admin':'badge-analista'}">${u.perfil}</span>
      <button class="btn btn-ghost" style="font-size:11px" onclick="alterarSenha(${u.id},'${u.username}')">🔑 Senha</button>
      ${u.username !== CURRENT_USER ? '<button class="btn btn-danger" style="font-size:11px" onclick="excluirUsuario('+u.id+',\''+u.username+'\')">🗑</button>' : ''}
    </div>
  `).join('');
}

async function criarUsuario() {
  const username = document.getElementById('new-username').value.trim();
  const password = document.getElementById('new-password').value;
  const perfil = document.getElementById('new-perfil').value;
  if (!username || !password) { showUserAlert('Preencha usuário e senha.', 'danger'); return; }
  const res = await fetch('/api/usuarios', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username,password,perfil})});
  const j = await res.json();
  if (j.ok) {
    showUserAlert('Usuário criado com sucesso!', 'success');
    document.getElementById('new-username').value = '';
    document.getElementById('new-password').value = '';
    carregarUsuarios();
  } else {
    showUserAlert(j.erro, 'danger');
  }
}

async function alterarSenha(id, nome) {
  const senha = prompt('Nova senha para ' + nome + ':');
  if (!senha || senha.length < 4) { alert('Senha muito curta (mínimo 4 caracteres).'); return; }
  const res = await fetch('/api/usuarios/' + id + '/senha', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({password:senha})});
  const j = await res.json();
  showUserAlert(j.ok ? 'Senha alterada.' : j.erro, j.ok ? 'success' : 'danger');
}

async function excluirUsuario(id, nome) {
  if (!confirm('Excluir usuário "' + nome + '"?')) return;
  const res = await fetch('/api/usuarios/' + id, {method:'DELETE'});
  const j = await res.json();
  if (j.ok) { showUserAlert('Usuário excluído.', 'success'); carregarUsuarios(); }
  else showUserAlert(j.erro, 'danger');
}

function showUserAlert(msg, tipo) {
  const el = document.getElementById('user-alert');
  el.innerHTML = '<div class="alert alert-' + tipo + '">' + msg + '</div>';
  setTimeout(() => el.innerHTML = '', 3500);
}
</script>
{% endif %}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template_string(HTML, orgaos=ORGAOS, tipos=TIPOS_PROCESSO,
                                  situacoes=SITUACOES, fontes=FONTES, error=None)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with get_db() as conn:
            u = conn.execute("SELECT * FROM usuarios WHERE username=?", (username,)).fetchone()
        if u and check_password_hash(u["password_hash"], password):
            session.permanent = True
            session["user_id"] = u["id"]
            session["username"] = u["username"]
            session["perfil"] = u["perfil"]
            return redirect(url_for("index"))
        error = "Usuário ou senha inválidos."
    return render_template_string(HTML, orgaos=ORGAOS, tipos=TIPOS_PROCESSO,
                                  situacoes=SITUACOES, fontes=FONTES, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── API Processos ──

@app.route("/api/processos", methods=["GET"])
@login_required
def listar_processos():
    sit = request.args.get("situacao", "")
    org = request.args.get("orgao", "")
    di = request.args.get("dt_inicio", "")
    df = request.args.get("dt_fim", "")

    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM processos").fetchone()[0]
        q = "SELECT * FROM processos WHERE 1=1"
        params = []
        if sit: q += " AND situacao=?"; params.append(sit)
        if org: q += " AND orgao=?"; params.append(org)
        if di: q += " AND data_registro>=?"; params.append(di)
        if df: q += " AND data_registro<=?"; params.append(df)
        q += " ORDER BY id DESC"
        rows = conn.execute(q, params).fetchall()
        valor = sum(r["valor"] or 0 for r in rows)
    return jsonify({"todos": [], "filtrados": [dict(r) for r in rows],
                    "total": total, "count": len(rows), "valor_total": valor})


@app.route("/api/processos", methods=["POST"])
@login_required
def criar_processo():
    d = request.get_json()
    if not d.get("credor_objeto") or not d.get("numero_protocolo"):
        return jsonify({"ok": False, "erro": "Protocolo e Credor/Objeto são obrigatórios."})
    try:
        valor = float(d.get("valor") or 0)
    except ValueError:
        valor = 0
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO processos (numero_protocolo,credor_objeto,quant_entrada,data_registro,
            orgao,competencia,tipo_processo,nota_fatura,fonte,valor,destino,situacao,
            data_saida,analista_responsavel,observacoes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (d.get("numero_protocolo"), d.get("credor_objeto"), d.get("quant_entrada"),
              d.get("data_registro") or None, d.get("orgao"), d.get("competencia"),
              d.get("tipo_processo"), d.get("nota_fatura"), d.get("fonte"), valor,
              d.get("destino"), d.get("situacao", "Em Análise"),
              d.get("data_saida") or None, d.get("analista_responsavel"), d.get("observacoes")))
        conn.commit()
    return jsonify({"ok": True, "id": cur.lastrowid})


@app.route("/api/processos/bulk-update", methods=["PUT"])
@login_required
def bulk_update():
    updates = request.get_json().get("updates", [])
    perfil = session.get("perfil")
    CAMPOS_ANALISTA = {"situacao", "observacoes", "analista_responsavel"}
    CAMPOS_ADMIN = {"numero_protocolo","credor_objeto","quant_entrada","data_registro",
                    "orgao","competencia","tipo_processo","nota_fatura","fonte","valor",
                    "destino","data_saida"} | CAMPOS_ANALISTA
    allowed = CAMPOS_ADMIN if perfil == "admin" else CAMPOS_ANALISTA
    count = 0
    with get_db() as conn:
        for u in updates:
            pid = u.get("id")
            sets = []
            vals = []
            for campo in allowed:
                if campo in u:
                    sets.append(f"{campo}=?")
                    val = u[campo]
                    if campo == "valor":
                        try: val = float(val or 0)
                        except: val = 0
                    vals.append(val if val != "" else None)
            if sets:
                sets.append("atualizado_em=datetime('now')")
                conn.execute(f"UPDATE processos SET {','.join(sets)} WHERE id=?", vals + [pid])
                count += 1
        conn.commit()
    return jsonify({"ok": True, "atualizados": count})


@app.route("/api/processos/bulk-delete", methods=["DELETE"])
@login_required
@admin_required
def bulk_delete():
    ids = request.get_json().get("ids", [])
    if not ids:
        return jsonify({"ok": False, "erro": "Nenhum ID fornecido."})
    with get_db() as conn:
        placeholders = ",".join("?" * len(ids))
        conn.execute(f"DELETE FROM processos WHERE id IN ({placeholders})", ids)
        conn.commit()
    return jsonify({"ok": True, "excluidos": len(ids)})


# ── API Importação ──

@app.route("/api/importar/preview", methods=["POST"])
@login_required
def importar_preview():
    arquivo = request.files.get("arquivo")
    if not arquivo:
        return jsonify({"ok": False, "erro": "Nenhum arquivo enviado."})
    try:
        nome = arquivo.filename.lower()
        if nome.endswith(".csv"):
            df = pd.read_csv(arquivo, dtype=str, encoding="utf-8", errors="replace")
        else:
            xl = pd.ExcelFile(arquivo)
            # detectar aba relevante
            aba = xl.sheet_names[0]
            for sheet in xl.sheet_names:
                if any(k in sheet.lower() for k in ["processo", "dados", "registr", "planilha"]):
                    aba = sheet; break
            # Detect if headers are in row 1 (row 0 all unnamed/empty)
            df_probe = pd.read_excel(xl, sheet_name=aba, dtype=str, header=0, nrows=2)
            all_unnamed = all(str(c).startswith('Unnamed') for c in df_probe.columns)
            header_row = 1 if all_unnamed else 0
            df = pd.read_excel(xl, sheet_name=aba, dtype=str, header=header_row)
        df = df.fillna("")
        total_cols = len(df.columns)
        # mapear colunas
        col_rename = {}
        seen = set()
        for col in df.columns:
            mapped = mapear_coluna(str(col))
            if mapped and mapped not in seen:
                col_rename[col] = mapped
                seen.add(mapped)
        df_mapped = df.rename(columns=col_rename)
        # manter só colunas mapeadas
        valid_cols = [c for c in df_mapped.columns if c in col_rename.values()]
        df_clean = df_mapped[valid_cols]
        preview_rows = df_clean.head(5).to_dict(orient="records")
        all_rows = df_clean.to_dict(orient="records")
        return jsonify({"ok": True, "preview": preview_rows, "dados": all_rows,
                        "mapeadas": len(valid_cols), "total_cols": total_cols})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)})


@app.route("/api/importar/confirmar", methods=["POST"])
@login_required
def importar_confirmar():
    dados = request.get_json().get("dados", [])
    if not dados:
        return jsonify({"ok": False, "erro": "Sem dados para importar."})
    count = 0
    with get_db() as conn:
        for row in dados:
            try:
                credor = row.get("credor_objeto", "").strip()
                if not credor:
                    continue
                try: valor = float(str(row.get("valor","")).replace(",",".") or 0)
                except: valor = 0
                conn.execute("""
                    INSERT INTO processos (numero_protocolo,credor_objeto,quant_entrada,data_registro,
                    orgao,competencia,tipo_processo,nota_fatura,fonte,valor,destino,situacao,
                    data_saida,analista_responsavel,observacoes)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (row.get("numero_protocolo") or None, credor, row.get("quant_entrada") or None,
                      row.get("data_registro") or None, row.get("orgao") or None,
                      row.get("competencia") or None, row.get("tipo_processo") or None,
                      row.get("nota_fatura") or None, row.get("fonte") or None, valor,
                      row.get("destino") or None, row.get("situacao") or "Em Análise",
                      row.get("data_saida") or None, row.get("analista_responsavel") or None,
                      row.get("observacoes") or None))
                count += 1
            except Exception:
                continue
        conn.commit()
    return jsonify({"ok": True, "importados": count})


# ── Modelo de planilha ──

@app.route("/modelo-planilha")
@login_required
def modelo_planilha():
    df = pd.DataFrame(columns=["NÚMERO DE PROTOCOLO","CREDOR/OBJETO","QUANT. ENTRADA",
                                "DATA","ÓRGÃO","COMPETÊNCIA","TIPO DE PROCESSO","NOTA/FATURA",
                                "FONTE","VALOR","DESTINO","SITUAÇÃO","DATA DE SAÍDA",
                                "ANALISTA RESPONSÁVEL","OBS:"])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Processos")
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="modelo_sigep.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ── Exportação ──

@app.route("/api/exportar")
@login_required
def exportar():
    fmt = request.args.get("formato", "xlsx")
    sit = request.args.get("situacao", "")
    org = request.args.get("orgao", "")
    di = request.args.get("dt_inicio", "")
    df_fim = request.args.get("dt_fim", "")
    with get_db() as conn:
        q = "SELECT * FROM processos WHERE 1=1"
        params = []
        if sit: q += " AND situacao=?"; params.append(sit)
        if org: q += " AND orgao=?"; params.append(org)
        if di: q += " AND data_registro>=?"; params.append(di)
        if df_fim: q += " AND data_registro<=?"; params.append(df_fim)
        q += " ORDER BY id DESC"
        rows = conn.execute(q, params).fetchall()
    df = pd.DataFrame([dict(r) for r in rows])
    buf = io.BytesIO()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if fmt == "csv":
        df.to_csv(buf, index=False, encoding="utf-8-sig")
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name=f"sigep_{ts}.csv", mimetype="text/csv")
    else:
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Processos")
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name=f"sigep_{ts}.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ── API Usuários ──

@app.route("/api/usuarios", methods=["GET"])
@login_required
@admin_required
def listar_usuarios():
    with get_db() as conn:
        rows = conn.execute("SELECT id, username, perfil, criado_em FROM usuarios ORDER BY id").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/usuarios", methods=["POST"])
@login_required
@admin_required
def criar_usuario():
    d = request.get_json()
    username = (d.get("username") or "").strip()
    password = d.get("password", "")
    perfil = d.get("perfil", "analista")
    if not username or not password:
        return jsonify({"ok": False, "erro": "Preencha usuário e senha."})
    if len(password) < 4:
        return jsonify({"ok": False, "erro": "Senha muito curta."})
    if perfil not in ("admin", "analista"):
        perfil = "analista"
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO usuarios (username, password_hash, perfil) VALUES (?,?,?)",
                         (username, generate_password_hash(password), perfil))
            conn.commit()
        return jsonify({"ok": True})
    except sqlite3.IntegrityError:
        return jsonify({"ok": False, "erro": "Nome de usuário já existe."})


@app.route("/api/usuarios/<int:uid>/senha", methods=["PUT"])
@login_required
@admin_required
def alterar_senha(uid):
    password = request.get_json().get("password", "")
    if len(password) < 4:
        return jsonify({"ok": False, "erro": "Senha muito curta."})
    with get_db() as conn:
        conn.execute("UPDATE usuarios SET password_hash=? WHERE id=?",
                     (generate_password_hash(password), uid))
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/usuarios/<int:uid>", methods=["DELETE"])
@login_required
@admin_required
def excluir_usuario(uid):
    if uid == session.get("user_id"):
        return jsonify({"ok": False, "erro": "Não é possível excluir o próprio usuário."})
    with get_db() as conn:
        conn.execute("DELETE FROM usuarios WHERE id=?", (uid,))
        conn.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print("=" * 55)
    print("  SIGEP — Sistema Integrado de Gestão de Processos -  PMDD-TI ")
    print("=" * 55)
    print(f"  Banco de dados: {DB_PATH}")
    print("  Acesso local:   http://localhost:5000")
    print("  Admin padrão:   admin / admin123")
    print("=" * 55)
    app.run(debug=False, host="0.0.0.0", port=5000)
