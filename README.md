# SIGEP — Sistema Integrado de Gestão de Processos
**Prefeitura Municipal de Dias D'Ávila**

Sistema web interno para gestão e acompanhamento de processos administrativos municipais.

---

## Requisitos

- Python 3.10 ou superior
- pip

---

## Instalação

```bash
# 1. Clone ou copie os arquivos para o servidor
# Estrutura esperada:
#   /sigep/
#     app.py
#     sigep.db
#     requirements.txt

# 2. (Opcional) Crie um ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt
```

---

## Executando

```bash
python3 app.py
```

Acesse em: [http://localhost:5000](http://localhost:5000)

---

## Credenciais padrão

| Usuário | Senha     | Perfil |
|---------|-----------|--------|
| admin   | admin123  | Admin  |

> **Altere a senha do admin após o primeiro acesso.**

---

## Banco de dados

O arquivo `sigep.db` (SQLite) já vem com os dados do **Inventário 2026** pré-importados (1.902 registros).

Ele é criado automaticamente na mesma pasta do `app.py` caso não exista.

---

## Rodando como serviço (systemd)

Para manter o sistema ativo no servidor da prefeitura, crie o arquivo `/etc/systemd/system/sigep.service`:

```ini
[Unit]
Description=SIGEP - Sistema de Gestão de Processos
After=network.target

[Service]
User=www-data
WorkingDirectory=/sigep
ExecStart=/sigep/venv/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Depois ative:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sigep
sudo systemctl start sigep
```

---

## Estrutura de arquivos

```
sigep/
├── app.py            # Aplicação principal
├── sigep.db          # Banco de dados SQLite
└── requirements.txt  # Dependências Python
```

---

## Suporte

Sistema desenvolvido para uso interno da Prefeitura de Dias D'Ávila.
