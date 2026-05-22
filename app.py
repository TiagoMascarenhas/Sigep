"""
Sistema de Controle Administrativo
Engenharia: Python + Streamlit + SQLite + RBAC
v2.0 — Inclui: Gerenciamento de Usuários, Filtros na Tabela, Exportação Excel/CSV
"""

import io
import sqlite3
import streamlit as st
import pandas as pd
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Logo da Prefeitura de Dias D'Ávila (base64 embutido)
LOGO_B64 = "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"
LOGO_DATA_URI = f"data:image/png;base64,{LOGO_B64}"


# ─────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Sistema de Controle Administrativo",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# CONSTANTES / DOMÍNIOS
# ─────────────────────────────────────────
DB_PATH = "controle_administrativo.db"

ORGAOS = [
    "Selecione...",
    "Secretaria de Fazenda",
    "Secretaria de Saúde",
    "Secretaria de Educação",
    "Secretaria de Obras",
    "Secretaria de Administração",
    "Procuradoria Geral",
    "Controladoria",
    "Outro",
]

TIPOS_PROCESSO = [
    "Selecione...",
    "Empenho",
    "Liquidação",
    "Pagamento",
    "Nota de Crédito",
    "Processo Licitatório",
    "Contrato",
    "Aditivo",
    "Outro",
]

SITUACOES = [
    "Aguardando Análise",
    "Em Análise",
    "Pendente de Documentação",
    "Aprovado",
    "Reprovado",
    "Encaminhado",
    "Arquivado",
    "Concluído",
]

FONTES = [
    "Selecione...",
    "Recurso Próprio",
    "Transferência Federal",
    "Transferência Estadual",
    "Convênio",
    "Emenda Parlamentar",
    "Outro",
]

COL_RENAME = {
    "id": "ID",
    "credor_objeto": "Credor/Objeto",
    "quant_entrada": "Qtd. Entrada",
    "data_registro": "Data Registro",
    "numero_protocolo": "Nº Protocolo",
    "orgao": "Órgão",
    "competencia": "Competência",
    "tipo_processo": "Tipo",
    "nota_fatura": "Nota/Fatura",
    "fonte": "Fonte",
    "valor": "Valor (R$)",
    "destino": "Destino",
    "situacao": "Situação",
    "data_saida": "Data Saída",
    "analista": "Analista",
    "observacoes": "Observações",
}

# ─────────────────────────────────────────
# BANCO DE DADOS
# ─────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def setup_db() -> None:
    """Inicializa o banco de dados e cria as tabelas necessárias."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                username        TEXT    NOT NULL UNIQUE,
                password_hash   TEXT    NOT NULL,
                role            TEXT    NOT NULL CHECK(role IN ('admin', 'analista'))
            )
        """)

        # Admin padrão apenas se tabela vazia
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO usuarios (username, password_hash, role) VALUES (?, ?, ?)",
                ("admin", generate_password_hash("admin123"), "admin"),
            )

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processos (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                credor_objeto       TEXT,
                quant_entrada       INTEGER,
                data_registro       DATE,
                numero_protocolo    TEXT,
                orgao               TEXT,
                competencia         TEXT,
                tipo_processo       TEXT,
                nota_fatura         TEXT,
                fonte               TEXT,
                valor               REAL,
                destino             TEXT,
                situacao            TEXT,
                data_saida          DATE,
                analista            TEXT,
                observacoes         TEXT
            )
        """)

        conn.commit()


# ─────────────────────────────────────────
# AUTENTICAÇÃO
# ─────────────────────────────────────────

def authenticate(username: str, password: str) -> dict | None:
    """Valida credenciais e retorna dados do usuário ou None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT username, password_hash, role FROM usuarios WHERE username = ?",
            (username,),
        ).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        return {"username": row["username"], "role": row["role"]}
    return None


def logout() -> None:
    """Limpa o session_state e recarrega a aplicação."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ─────────────────────────────────────────
# OPERAÇÕES — PROCESSOS
# ─────────────────────────────────────────

def insert_processo(data: dict) -> None:
    """Insere um novo processo no banco de dados."""
    sql = """
        INSERT INTO processos (
            credor_objeto, quant_entrada, data_registro, numero_protocolo,
            orgao, competencia, tipo_processo, nota_fatura, fonte, valor,
            destino, situacao, data_saida, analista, observacoes
        ) VALUES (
            :credor_objeto, :quant_entrada, :data_registro, :numero_protocolo,
            :orgao, :competencia, :tipo_processo, :nota_fatura, :fonte, :valor,
            :destino, :situacao, :data_saida, :analista, :observacoes
        )
    """
    with get_connection() as conn:
        conn.execute(sql, data)
        conn.commit()


def update_processo_analista(processo_id: int, situacao: str, observacoes: str) -> None:
    """Atualiza somente situação e observações de um processo."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE processos SET situacao = ?, observacoes = ? WHERE id = ?",
            (situacao, observacoes, processo_id),
        )
        conn.commit()


def fetch_all_processos() -> pd.DataFrame:
    """Retorna todos os processos ordenados pelos mais recentes."""
    with get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM processos ORDER BY id DESC", conn)


def fetch_processo_by_id(processo_id: int) -> sqlite3.Row | None:
    """Retorna um processo pelo ID."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM processos WHERE id = ?", (processo_id,)
        ).fetchone()


# ─────────────────────────────────────────
# OPERAÇÕES — USUÁRIOS
# ─────────────────────────────────────────

def fetch_all_usuarios() -> pd.DataFrame:
    """Retorna todos os usuários (sem hash de senha)."""
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT id, username, role FROM usuarios ORDER BY id ASC", conn
        )


def insert_usuario(username: str, password: str, role: str) -> None:
    """Cria um novo usuário no banco de dados."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO usuarios (username, password_hash, role) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), role),
        )
        conn.commit()


def update_usuario_senha(username: str, new_password: str) -> None:
    """Atualiza a senha de um usuário existente."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET password_hash = ? WHERE username = ?",
            (generate_password_hash(new_password), username),
        )
        conn.commit()


def delete_usuario(username: str) -> None:
    """Remove um usuário pelo username (não permite auto-exclusão)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM usuarios WHERE username = ?", (username,))
        conn.commit()


# ─────────────────────────────────────────
# EXPORTAÇÃO
# ─────────────────────────────────────────

def _df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Serializa DataFrame para bytes .xlsx com cabeçalho formatado."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Processos")
        workbook  = writer.book
        worksheet = writer.sheets["Processos"]

        header_fmt = workbook.add_format({
            "bold": True,
            "bg_color": "#1a3a5c",
            "font_color": "#ffffff",
            "border": 1,
        })
        money_fmt = workbook.add_format({"num_format": 'R$ #,##0.00'})

        for col_num, col_name in enumerate(df.columns):
            worksheet.write(0, col_num, col_name, header_fmt)
            width = 18
            if col_name == "Valor (R$)":
                worksheet.set_column(col_num, col_num, 16, money_fmt)
            elif col_name in ("Observações", "Credor/Objeto"):
                width = 30
            else:
                worksheet.set_column(col_num, col_num, width)

    return buffer.getvalue()


def _df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Serializa DataFrame para CSV UTF-8-BOM (compatível com Excel BR)."""
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


# ─────────────────────────────────────────
# HELPERS DE UI
# ─────────────────────────────────────────

def _safe_date(value) -> date:
    """Converte string ou date para objeto date com fallback seguro."""
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            pass
    return date.today()


def _safe_index(options: list, value) -> int:
    """Retorna o índice seguro de um valor em uma lista."""
    try:
        return options.index(value)
    except (ValueError, TypeError):
        return 0


def _fmt_brl(value: float) -> str:
    """Formata um float como moeda BRL (ex: R$ 1.234,56)."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────
# SEÇÃO: TABELA COM FILTROS + EXPORTAÇÃO
# ─────────────────────────────────────────

def render_dataframe_section() -> None:
    """Exibe a tabela de processos com filtros interativos e exportação."""
    st.divider()
    st.subheader("📋 Processos Cadastrados")

    df = fetch_all_processos()

    if df.empty:
        st.info("Nenhum processo cadastrado ainda.")
        return

    # ── Filtros ──────────────────────────────────────────────────────────────
    with st.expander("🔎 Filtros", expanded=False):
        fc1, fc2, fc3 = st.columns(3)

        with fc1:
            filtro_situacao = st.selectbox(
                "Situação",
                ["Todas"] + SITUACOES,
                key="filter_situacao",
            )
        with fc2:
            filtro_orgao = st.selectbox(
                "Órgão",
                ["Todos"] + [o for o in ORGAOS if o != "Selecione..."],
                key="filter_orgao",
            )
        with fc3:
            datas_validas = pd.to_datetime(df["data_registro"], errors="coerce").dropna()
            if not datas_validas.empty:
                min_d = datas_validas.min().date()
                max_d = datas_validas.max().date()
            else:
                min_d = max_d = date.today()

            filtro_periodo = st.date_input(
                "Período (Data Registro)",
                value=(min_d, max_d),
                format="DD/MM/YYYY",
                key="filter_periodo",
            )

    # ── Aplica filtros ───────────────────────────────────────────────────────
    df_f = df.copy()

    if filtro_situacao != "Todas":
        df_f = df_f[df_f["situacao"] == filtro_situacao]

    if filtro_orgao != "Todos":
        df_f = df_f[df_f["orgao"] == filtro_orgao]

    if isinstance(filtro_periodo, (list, tuple)) and len(filtro_periodo) == 2:
        start, end = filtro_periodo
        df_f["data_registro"] = pd.to_datetime(df_f["data_registro"], errors="coerce")
        df_f = df_f[
            (df_f["data_registro"].dt.date >= start)
            & (df_f["data_registro"].dt.date <= end)
        ]

    # ── Métricas ─────────────────────────────────────────────────────────────
    m1, m2, m3 = st.columns(3)
    m1.metric("Total no banco", len(df))
    m2.metric("Registros filtrados", len(df_f))
    m3.metric("Valor total filtrado", _fmt_brl(pd.to_numeric(df_f["valor"], errors="coerce").sum()))

    # ── Tabela ────────────────────────────────────────────────────────────────
    df_display = df_f.rename(columns=COL_RENAME)
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # ── Exportação ────────────────────────────────────────────────────────────
    st.markdown("**⬇️ Exportar dados filtrados:**")
    exp1, exp2, _ = st.columns([1, 1, 4])

    with exp1:
        st.download_button(
            label="📥 Excel (.xlsx)",
            data=_df_to_excel_bytes(df_display),
            file_name=f"processos_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with exp2:
        st.download_button(
            label="📄 CSV (.csv)",
            data=_df_to_csv_bytes(df_display),
            file_name=f"processos_{date.today().isoformat()}.csv",
            mime="text/csv",
            use_container_width=True,
        )


# ─────────────────────────────────────────
# FORMULÁRIO COMPARTILHADO (Admin / Analista)
# ─────────────────────────────────────────

def render_process_form(
    disabled_all: bool = False,
    prefill: dict | None = None,
    key_prefix: str = "form",
) -> dict:
    """
    Renderiza o formulário de processo em 4 abas.

    Args:
        disabled_all: Se True, todos os campos ficam bloqueados — exceto
                      `situacao` e `observacoes`, que permanecem sempre editáveis.
        prefill: Dados para pré-preencher o formulário.
        key_prefix: Prefixo das chaves do session_state (evita conflitos).

    Returns:
        Dicionário com todos os valores do formulário.
    """
    p = prefill or {}

    tab1, tab2, tab3, tab4 = st.tabs([
        "🪪 Identificação",
        "🗂️ Classificação",
        "💰 Financeiro",
        "🔄 Tramitação",
    ])

    # ── ABA 1: Identificação ──────────────────────────────────────────────────
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            numero_protocolo = st.text_input(
                "Número do Protocolo *",
                value=p.get("numero_protocolo", ""),
                key=f"{key_prefix}_protocolo",
                disabled=disabled_all,
            )
            data_registro = st.date_input(
                "Data de Registro *",
                value=_safe_date(p.get("data_registro")),
                key=f"{key_prefix}_data_registro",
                disabled=disabled_all,
                format="DD/MM/YYYY",
            )
        with col2:
            credor_objeto = st.text_input(
                "Credor / Objeto *",
                value=p.get("credor_objeto", ""),
                key=f"{key_prefix}_credor",
                disabled=disabled_all,
            )
            quant_entrada = st.number_input(
                "Quantidade de Entrada",
                min_value=0,
                value=int(p.get("quant_entrada") or 0),
                step=1,
                key=f"{key_prefix}_quant",
                disabled=disabled_all,
            )

    # ── ABA 2: Classificação ─────────────────────────────────────────────────
    with tab2:
        col1, col2, col3 = st.columns(3)
        with col1:
            orgao = st.selectbox(
                "Órgão",
                options=ORGAOS,
                index=_safe_index(ORGAOS, p.get("orgao", "Selecione...")),
                key=f"{key_prefix}_orgao",
                disabled=disabled_all,
            )
        with col2:
            competencia = st.text_input(
                "Competência (ex: 01/2025)",
                value=p.get("competencia", ""),
                key=f"{key_prefix}_competencia",
                disabled=disabled_all,
            )
        with col3:
            tipo_processo = st.selectbox(
                "Tipo de Processo",
                options=TIPOS_PROCESSO,
                index=_safe_index(TIPOS_PROCESSO, p.get("tipo_processo", "Selecione...")),
                key=f"{key_prefix}_tipo",
                disabled=disabled_all,
            )

    # ── ABA 3: Financeiro ────────────────────────────────────────────────────
    with tab3:
        col1, col2, col3 = st.columns(3)
        with col1:
            nota_fatura = st.text_input(
                "Nota / Fatura",
                value=p.get("nota_fatura", ""),
                key=f"{key_prefix}_nota",
                disabled=disabled_all,
            )
        with col2:
            fonte = st.selectbox(
                "Fonte",
                options=FONTES,
                index=_safe_index(FONTES, p.get("fonte", "Selecione...")),
                key=f"{key_prefix}_fonte",
                disabled=disabled_all,
            )
        with col3:
            valor = st.number_input(
                "Valor (R$)",
                min_value=0.0,
                value=float(p.get("valor") or 0.0),
                step=0.01,
                format="%.2f",
                key=f"{key_prefix}_valor",
                disabled=disabled_all,
            )

    # ── ABA 4: Tramitação ────────────────────────────────────────────────────
    with tab4:
        col1, col2 = st.columns(2)
        with col1:
            destino = st.text_input(
                "Destino",
                value=p.get("destino", ""),
                key=f"{key_prefix}_destino",
                disabled=disabled_all,
            )
            # Situação: sempre editável (analista e admin)
            situacao = st.selectbox(
                "Situação",
                options=SITUACOES,
                index=_safe_index(SITUACOES, p.get("situacao", SITUACOES[0])),
                key=f"{key_prefix}_situacao",
                disabled=False,
            )
            analista = st.text_input(
                "Analista Responsável",
                value=p.get("analista", st.session_state.get("username", "")),
                key=f"{key_prefix}_analista",
                disabled=disabled_all,
            )
        with col2:
            data_saida = st.date_input(
                "Data de Saída",
                value=_safe_date(p.get("data_saida")),
                key=f"{key_prefix}_data_saida",
                disabled=disabled_all,
                format="DD/MM/YYYY",
            )
            # Observações: sempre editável (analista e admin)
            observacoes = st.text_area(
                "Observações",
                value=p.get("observacoes", ""),
                height=120,
                key=f"{key_prefix}_observacoes",
                disabled=False,
            )

    return {
        "numero_protocolo": numero_protocolo,
        "credor_objeto": credor_objeto,
        "data_registro": data_registro,
        "quant_entrada": quant_entrada,
        "orgao": orgao if orgao != "Selecione..." else "",
        "competencia": competencia,
        "tipo_processo": tipo_processo if tipo_processo != "Selecione..." else "",
        "nota_fatura": nota_fatura,
        "fonte": fonte if fonte != "Selecione..." else "",
        "valor": valor,
        "destino": destino,
        "situacao": situacao,
        "analista": analista,
        "data_saida": data_saida,
        "observacoes": observacoes,
    }


# ─────────────────────────────────────────
# VIEW: GERENCIAMENTO DE USUÁRIOS (Admin)
# ─────────────────────────────────────────

def render_user_management() -> None:
    """Tela de gerenciamento de usuários — exclusiva para administradores."""
    st.subheader("👥 Gerenciamento de Usuários")

    # ── Criar novo usuário ───────────────────────────────────────────────────
    with st.expander("➕ Criar Novo Usuário", expanded=True):
        uc1, uc2, uc3 = st.columns(3)
        with uc1:
            new_username = st.text_input("Usuário *", key="new_user_username")
        with uc2:
            new_password = st.text_input("Senha *", type="password", key="new_user_password")
        with uc3:
            new_role = st.selectbox("Perfil *", ["analista", "admin"], key="new_user_role")

        if st.button("✅ Criar Usuário", key="btn_create_user", type="primary"):
            if not new_username.strip() or not new_password.strip():
                st.error("Usuário e senha são obrigatórios.")
            else:
                try:
                    insert_usuario(new_username.strip(), new_password, new_role)
                    st.success(f"Usuário **{new_username}** criado com sucesso como **{new_role}**.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error(f"Nome de usuário **{new_username}** já existe. Escolha outro.")

    # ── Lista de usuários ────────────────────────────────────────────────────
    st.markdown("#### Usuários cadastrados")
    df_users = fetch_all_usuarios()
    st.dataframe(df_users, use_container_width=True, hide_index=True)

    # ── Redefinir senha ──────────────────────────────────────────────────────
    with st.expander("🔑 Redefinir Senha de Usuário", expanded=False):
        user_list = df_users["username"].tolist()
        if not user_list:
            st.info("Nenhum usuário cadastrado.")
        else:
            rp1, rp2, rp3 = st.columns(3)
            with rp1:
                target_user = st.selectbox("Usuário", user_list, key="reset_user_select")
            with rp2:
                new_pwd = st.text_input("Nova Senha *", type="password", key="reset_new_pwd")
            with rp3:
                confirm_pwd = st.text_input("Confirmar Senha *", type="password", key="reset_confirm_pwd")

            if st.button("🔄 Redefinir Senha", key="btn_reset_pwd"):
                if not new_pwd or not confirm_pwd:
                    st.error("Preencha os dois campos de senha.")
                elif new_pwd != confirm_pwd:
                    st.error("As senhas não coincidem.")
                else:
                    update_usuario_senha(target_user, new_pwd)
                    st.success(f"Senha de **{target_user}** redefinida com sucesso.")

    # ── Excluir usuário ──────────────────────────────────────────────────────
    with st.expander("🗑️ Excluir Usuário", expanded=False):
        current_user = st.session_state.get("username", "")
        # Impede auto-exclusão
        delete_candidates = [u for u in df_users["username"].tolist() if u != current_user]

        if not delete_candidates:
            st.info("Nenhum outro usuário disponível para exclusão.")
        else:
            del1, del2 = st.columns([2, 1])
            with del1:
                del_user = st.selectbox(
                    "Selecione o usuário para excluir",
                    delete_candidates,
                    key="del_user_select",
                )
            with del2:
                st.markdown("<br>", unsafe_allow_html=True)
                st.warning(f"⚠️ **{del_user}** será removido permanentemente.")

            if st.button("🗑️ Confirmar Exclusão", key="btn_del_user", type="secondary"):
                delete_usuario(del_user)
                st.success(f"Usuário **{del_user}** excluído.")
                st.rerun()


# ─────────────────────────────────────────
# VIEW: ADMINISTRADOR
# ─────────────────────────────────────────

def _clear_admin_form() -> None:
    """Remove as chaves do formulário de cadastro do session_state."""
    keys = [
        "form_protocolo", "form_credor", "form_data_registro", "form_quant",
        "form_orgao", "form_competencia", "form_tipo",
        "form_nota", "form_fonte", "form_valor",
        "form_destino", "form_situacao", "form_analista",
        "form_data_saida", "form_observacoes",
    ]
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]


def render_admin_view() -> None:
    """Interface completa para o perfil administrador."""
    page_tab1, page_tab2 = st.tabs(["🗂️ Cadastro de Processos", "👥 Gerenciamento de Usuários"])

    with page_tab1:
        st.header("🗂️ Cadastro de Novo Processo")

        form_data = render_process_form(disabled_all=False, key_prefix="form")

        st.markdown("")
        col_btn, _ = st.columns([1, 3])
        with col_btn:
            submitted = st.button("💾 Cadastrar Processo", type="primary", use_container_width=True)

        if submitted:
            errors = []
            if not form_data["numero_protocolo"].strip():
                errors.append("Número do Protocolo é obrigatório.")
            if not form_data["credor_objeto"].strip():
                errors.append("Credor / Objeto é obrigatório.")

            if errors:
                for err in errors:
                    st.error(err)
            else:
                insert_processo(form_data)
                st.success(f"✅ Processo **{form_data['numero_protocolo']}** cadastrado com sucesso!")
                _clear_admin_form()
                st.rerun()

        render_dataframe_section()

    with page_tab2:
        render_user_management()


# ─────────────────────────────────────────
# VIEW: ANALISTA
# ─────────────────────────────────────────

def render_analyst_view() -> None:
    """Interface restrita para o perfil analista."""
    st.header("🔍 Consultar e Atualizar Processo")

    df = fetch_all_processos()

    if df.empty:
        st.warning("Nenhum processo cadastrado. Aguarde um administrador inserir registros.")
        return

    options_map: dict[str, int] = {
        f"[{row['id']}] {row['numero_protocolo']} — {row['credor_objeto']}": int(row["id"])
        for _, row in df.iterrows()
    }

    selected_label = st.selectbox(
        "Selecione um processo:",
        options=list(options_map.keys()),
        key="analyst_selected",
    )

    if not selected_label:
        return

    processo_id = options_map[selected_label]
    row = fetch_processo_by_id(processo_id)

    if not row:
        st.error("Processo não encontrado.")
        return

    st.divider()
    st.subheader(f"Processo: {row['numero_protocolo']}")

    form_data = render_process_form(
        disabled_all=True,
        prefill=dict(row),
        key_prefix=f"analyst_{processo_id}",
    )

    st.markdown("")
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        update_btn = st.button("🔄 Atualizar Análise", type="primary", use_container_width=True)

    if update_btn:
        update_processo_analista(
            processo_id=processo_id,
            situacao=form_data["situacao"],
            observacoes=form_data["observacoes"],
        )
        st.success("✅ Análise atualizada com sucesso!")
        st.rerun()

    render_dataframe_section()


# ─────────────────────────────────────────
# TELA DE LOGIN
# ─────────────────────────────────────────

def render_header() -> None:
    """Exibe o cabeçalho institucional com logo e título do sistema."""
    st.markdown(
        f"""
        <div style="
            display: flex;
            align-items: center;
            gap: 18px;
            padding: 0.75rem 1.25rem;
            background: #0057A8;
            border-radius: 10px;
            margin-bottom: 1.5rem;
        ">
            <img src="{LOGO_DATA_URI}"
                 style="height: 56px; width: 56px; object-fit: contain; border-radius: 6px;"
                 alt="Logo Prefeitura de Dias D'Ávila">
            <div>
                <div style="font-size: 1.15rem; font-weight: 700; color: #ffffff; letter-spacing: 0.03em;">
                    PMDD — Prefeitura Municipal de Dias D'Ávila
                </div>
                <div style="font-size: 0.82rem; color: #cce3f7; margin-top: 2px; letter-spacing: 0.02em;">
                    Sistema de Controle Administrativo · Secretaria de Administração
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login() -> None:
    """Exibe a tela centralizada de login."""
    st.markdown(
        """
        <style>
            .login-title {
                text-align: center;
                font-size: 1.6rem;
                font-weight: 700;
                margin-bottom: 0.3rem;
                color: #1a1f36;
            }
            .login-subtitle {
                text-align: center;
                color: #6b7280;
                font-size: 0.9rem;
                margin-bottom: 1.8rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    render_header()
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown('<div class="login-title">🗂️ Controle Administrativo</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Faça login para acessar o sistema</div>', unsafe_allow_html=True)
        st.divider()

        username = st.text_input("👤 Usuário", placeholder="Digite seu usuário", key="login_user")
        password = st.text_input("🔒 Senha", placeholder="Digite sua senha", type="password", key="login_pass")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Entrar", type="primary", use_container_width=True):
            if not username or not password:
                st.error("Preencha usuário e senha.")
            else:
                user = authenticate(username, password)
                if user:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = user["username"]
                    st.session_state["role"] = user["role"]
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos.")


# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────

def render_sidebar() -> None:
    """Renderiza informações do usuário logado e botão de logout."""
    with st.sidebar:
        st.markdown(
            f'''<div style="text-align:center; margin-bottom:0.5rem;">
                <img src="{LOGO_DATA_URI}"
                     style="height:52px; object-fit:contain; border-radius:6px;"
                     alt="Logo PMDD">
            </div>''',
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style=\'text-align:center; font-size:12px; font-weight:600;"
            " color:#0057A8; margin-bottom:4px;\'>PMDD — Dias D\'Ávila</div>",
            unsafe_allow_html=True,
        )
        st.divider()

        role_icon  = "🛡️" if st.session_state["role"] == "admin" else "🔬"
        role_label = "Administrador" if st.session_state["role"] == "admin" else "Analista"

        st.markdown(f"**Usuário:** {st.session_state['username']}")
        st.markdown(f"**Perfil:** {role_icon} {role_label}")
        st.divider()

        if st.button("🚪 Sair do Sistema", use_container_width=True, type="secondary"):
            logout()


# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────

def main() -> None:
    setup_db()

    if not st.session_state.get("logged_in"):
        render_login()
        return

    render_sidebar()
    render_header()

    role = st.session_state.get("role")
    if role == "admin":
        render_admin_view()
    elif role == "analista":
        render_analyst_view()
    else:
        st.error("Perfil de acesso não reconhecido. Faça login novamente.")
        logout()


if __name__ == "__main__":
    main()