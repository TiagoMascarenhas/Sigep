# 🗂️ Sistema de Controle Administrativo

Sistema web desenvolvido em **Python + Streamlit** para substituir planilhas de controle administrativo por uma interface segura, com autenticação e controle de acesso baseado em funções (RBAC). Utiliza banco de dados **SQLite local** — sem necessidade de infraestrutura externa.

---

## ✨ Funcionalidades

| Recurso | Admin | Analista |
|---|:---:|:---:|
| Login seguro com hash de senha | ✅ | ✅ |
| Cadastrar novos processos | ✅ | ❌ |
| Visualizar todos os processos | ✅ | ✅ |
| Editar situação e observações | ✅ | ✅ |
| Filtros por situação, órgão e período | ✅ | ✅ |
| Exportar tabela em Excel (.xlsx) | ✅ | ✅ |
| Exportar tabela em CSV (.csv) | ✅ | ✅ |
| Criar / excluir usuários | ✅ | ❌ |
| Redefinir senha de usuários | ✅ | ❌ |

---

## 🗂️ Estrutura do projeto

```
.
├── app.py               # Código principal da aplicação
├── requirements.txt     # Dependências Python
├── README.md            # Este arquivo
└── controle_administrativo.db   # Banco SQLite (gerado automaticamente)
```

---

## ⚙️ Pré-requisitos

- **Python 3.11+** — [download](https://www.python.org/downloads/)
- **pip** (já incluso com Python)
- Terminal (Prompt de Comando, PowerShell, bash ou zsh)

---

## 🚀 Instalação e execução

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/controle-administrativo.git
cd controle-administrativo
```

### 2. Crie e ative um ambiente virtual (recomendado)

**Linux / macOS**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (Prompt de Comando)**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Execute a aplicação

```bash
streamlit run app.py
```

O navegador abrirá automaticamente em `http://localhost:8501`.

---

## 🔐 Acesso inicial

Na primeira execução o banco de dados é criado automaticamente com um usuário administrador padrão:

| Campo | Valor |
|---|---|
| Usuário | `admin` |
| Senha | `admin123` |

> **Importante:** troque a senha do admin imediatamente após o primeiro acesso, pela tela **Gerenciamento de Usuários → Redefinir Senha**.

---

## 🖥️ Guia de uso

### Perfil Administrador

1. Faça login com as credenciais acima.
2. Na aba **Cadastro de Processos**, preencha os dados nas quatro abas do formulário:
   - **Identificação** — protocolo, credor/objeto, data, quantidade
   - **Classificação** — órgão, competência, tipo de processo
   - **Financeiro** — nota/fatura, fonte, valor
   - **Tramitação** — destino, situação, analista, data de saída, observações
3. Clique em **Cadastrar Processo**. O registro aparecerá imediatamente na tabela abaixo.
4. Na aba **Gerenciamento de Usuários** você pode:
   - Criar analistas informando usuário, senha e perfil
   - Redefinir a senha de qualquer usuário
   - Excluir usuários (exceto o próprio usuário logado)

### Perfil Analista

1. Faça login com as credenciais criadas pelo administrador.
2. Selecione um processo no menu **Selecione um processo**.
3. O formulário será exibido com todos os campos bloqueados, exceto **Situação** e **Observações**.
4. Atualize os campos liberados e clique em **Atualizar Análise**.

### Tabela de processos (ambos os perfis)

- Use o painel **🔎 Filtros** para filtrar por situação, órgão e período de registro.
- As métricas acima da tabela atualizam automaticamente conforme os filtros.
- Clique em **Excel (.xlsx)** ou **CSV (.csv)** para exportar os dados filtrados.

---

## 🏗️ Arquitetura do código

O arquivo `app.py` é organizado em camadas com responsabilidades separadas:

```
app.py
│
├── Configuração          set_page_config, constantes de domínio
├── Banco de dados        get_connection(), setup_db()
├── Autenticação          authenticate(), logout()
├── Repositório           insert_processo(), update_processo_analista(),
│                         fetch_all_processos(), fetch_processo_by_id()
├── Repositório usuários  insert_usuario(), update_usuario_senha(),
│                         delete_usuario(), fetch_all_usuarios()
├── Exportação            _df_to_excel_bytes(), _df_to_csv_bytes()
├── Componentes UI        render_process_form(), render_dataframe_section()
├── Views                 render_admin_view(), render_analyst_view(),
│                         render_user_management()
├── Shell                 render_login(), render_sidebar()
└── Entry point           main()
```

---

## 🔒 Segurança

- Senhas armazenadas com hash **PBKDF2-SHA256** via `werkzeug.security` — nunca em texto puro.
- Sessão gerenciada pelo `st.session_state` do Streamlit; logout limpa todas as chaves.
- Analistas não conseguem acessar rotas de criação ou gerenciamento de usuários — o controle é feito no `main()` antes de qualquer renderização.
- Auto-exclusão de usuário bloqueada no backend e na interface.

---

## 📦 Dependências

| Pacote | Uso |
|---|---|
| `streamlit` | Framework web e interface |
| `pandas` | Manipulação de dados e leitura do SQLite |
| `werkzeug` | Hash seguro de senhas |
| `xlsxwriter` | Geração de arquivos Excel formatados |
| `sqlite3` | Banco de dados local (embutido no Python) |

---

## 🤝 Contribuindo

1. Faça um fork do projeto
2. Crie uma branch: `git checkout -b feature/minha-feature`
3. Commit suas alterações: `git commit -m 'feat: adiciona minha feature'`
4. Push para a branch: `git push origin feature/minha-feature`
5. Abra um Pull Request

---

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.
