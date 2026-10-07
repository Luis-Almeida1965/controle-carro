"""Controle de Despesas do Carro — Streamlit + Supabase.

App para registrar e acompanhar despesas do veículo (abastecimento,
manutenção, etc.), com gráficos, filtros, relatórios e login.

Executar local:  streamlit run app.py
"""
from datetime import date
import hashlib

import pandas as pd
import plotly.express as px
import streamlit as st

import db

st.set_page_config(
    page_title="Controle do Carro",
    page_icon=":car:",
    layout="wide",
)


# ===========================================================================
# Utilitários de formatação
# ===========================================================================
def moeda(v):
    try:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def num(v, casas=0):
    try:
        return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0"


# ===========================================================================
# AUTENTICAÇÃO — Login com senha
# ===========================================================================
def _hash(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()


def tela_login():
    """Exibe a tela de login e retorna True se autenticado."""
    st.markdown(
        """
        <div style='text-align:center; padding: 40px 0 10px'>
            <h1>🚗 Controle de Despesas do Carro</h1>
            <p style='color:gray'>Faça login para continuar</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_l, col_c, col_r = st.columns([1, 1, 1])
    with col_c:
        with st.form("login_form"):
            st.subheader("🔐 Login")
            usuario_login = st.text_input("Usuário", placeholder="Digite seu usuário")
            senha_login = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            entrar = st.form_submit_button("Entrar", use_container_width=True, type="primary")

        if entrar:
            if not usuario_login or not senha_login:
                st.error("Informe o usuário e a senha.")
                return False

            resultado = db.autenticar_usuario(usuario_login, _hash(senha_login))
            if resultado is not None:
                st.session_state["autenticado"] = True
                st.session_state["usuario_logado"] = resultado["nome"]
                st.session_state["usuario_id"] = resultado["id"]
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
                return False

    return False


# ===========================================================================
# Verifica autenticação antes de qualquer coisa
# ===========================================================================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    tela_login()
    st.stop()


# ===========================================================================
# App principal (só chega aqui se autenticado)
# ===========================================================================

# Barra superior com usuário logado e botão de logout
col_title, col_user = st.columns([5, 1])
with col_title:
    st.title("🚗 Controle de Despesas do Carro")
with col_user:
    st.markdown(f"<br>👤 **{st.session_state['usuario_logado']}**", unsafe_allow_html=True)
    if st.button("Sair", use_container_width=True):
        st.session_state["autenticado"] = False
        st.session_state["usuario_logado"] = ""
        st.session_state["usuario_id"] = None
        st.rerun()


# ---------------------------------------------------------------------------
# Carrega listas auxiliares com cache leve
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def carregar_auxiliares():
    usuarios = db.listar_usuarios()
    tipos = db.listar_tipos()
    veiculos = db.listar_veiculos()
    return usuarios, tipos, veiculos


# menu lateral
pagina = st.sidebar.radio(
    "Menu",
    ["Registrar despesa", "Despesas e relatórios", "Cadastros"],
)

try:
    usuarios, tipos, veiculos = carregar_auxiliares()
except Exception as e:
    st.error(f"Erro ao conectar no banco: {e}")
    st.info("Verifique as credenciais do Supabase nos secrets do Streamlit.")
    st.stop()


# ===========================================================================
# PÁGINA 1 — Registrar despesa
# ===========================================================================
if pagina == "Registrar despesa":
    st.subheader("Registrar nova despesa")

    if usuarios.empty or tipos.empty or veiculos.empty:
        st.warning("Cadastre ao menos um usuário, um tipo de despesa e um veículo na aba Cadastros.")
    else:
        with st.form("nova_despesa", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            data_desp = c1.date_input("Data", value=date.today(), format="DD/MM/YYYY")
            usuario_nome = c2.selectbox("Usuário", usuarios["nome"])
            veiculo_placa = c3.selectbox("Veículo", veiculos["placa"])

            c4, c5, c6 = st.columns(3)
            tipo_nome = c4.selectbox("Tipo de despesa", tipos["nome"])
            qtde = c5.number_input("Quantidade (litros, etc.)", min_value=0.0, step=0.1, format="%.3f")
            km = c6.number_input("KM (odômetro)", min_value=0.0, step=1.0, format="%.1f")

            # ---------------------------------------------------------------
            # Linha de valores: valor unitário, valor total (calculado auto)
            # ---------------------------------------------------------------
            c7, c8, c9 = st.columns(3)
            valor_unit = c7.number_input(
                "Valor unitário (R$)",
                min_value=0.0, step=0.01, format="%.3f",
                help="Preço por litro (abastecimento) ou por unidade",
            )
            valor = c8.number_input(
                "Valor total (R$)",
                min_value=0.0, step=1.0, format="%.2f",
                help="Valor total pago. Se informar valor unitário e quantidade, é calculado automaticamente.",
            )

            # calcula o total automaticamente quando os dois campos anteriores têm valor
            if valor_unit > 0 and qtde > 0:
                valor_calculado = round(valor_unit * qtde, 2)
                c9.metric("Total calculado", moeda(valor_calculado))
            else:
                c9.metric("Total calculado", "—")
                valor_calculado = None

            obs = st.text_input("Observação", "")
            enviar = st.form_submit_button("Salvar despesa")

        if enviar:
            # usa o valor total digitado; se for zero tenta o calculado
            valor_final = valor if valor > 0 else (valor_calculado or 0)
            if valor_final <= 0:
                st.error("Informe o valor total ou preencha o valor unitário e a quantidade.")
            else:
                id_usuario = int(usuarios.loc[usuarios["nome"] == usuario_nome, "id"].iloc[0])
                id_tipo = int(tipos.loc[tipos["nome"] == tipo_nome, "id"].iloc[0])
                id_veiculo = int(veiculos.loc[veiculos["placa"] == veiculo_placa, "id"].iloc[0])
                try:
                    db.inserir_despesa(
                        data_desp, id_usuario, id_tipo, id_veiculo,
                        qtde or None, valor_final,
                        valor_unit or None,          # ← valor unitário
                        km or None, obs or None,
                    )
                    st.success("Despesa registrada com sucesso!")
                    carregar_auxiliares.clear()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")


# ===========================================================================
# PÁGINA 2 — Despesas e relatórios
# ===========================================================================
elif pagina == "Despesas e relatórios":
    st.subheader("Despesas e relatórios")

    hoje = date.today()
    c1, c2 = st.sidebar.columns(2)
    data_ini = c1.date_input("De", value=hoje.replace(day=1), format="DD/MM/YYYY")
    data_fim = c2.date_input("Até", value=hoje, format="DD/MM/YYYY")

    if data_ini > data_fim:
        st.sidebar.error("Data inicial maior que a final.")
        st.stop()

    try:
        df = db.carregar_despesas(data_ini, data_fim)
    except Exception as e:
        st.error(f"Erro ao carregar despesas: {e}")
        st.stop()

    if df.empty:
        st.info("Nenhuma despesa no período selecionado.")
        st.stop()

    f_veiculo = st.sidebar.multiselect("Veículo", sorted(df["veiculo"].dropna().unique()))
    f_tipo = st.sidebar.multiselect("Tipo", sorted(df["tipo"].dropna().unique()))
    f_usuario = st.sidebar.multiselect("Usuário", sorted(df["usuario"].dropna().unique()))
    if f_veiculo:
        df = df[df["veiculo"].isin(f_veiculo)]
    if f_tipo:
        df = df[df["tipo"].isin(f_tipo)]
    if f_usuario:
        df = df[df["usuario"].isin(f_usuario)]

    if df.empty:
        st.info("Nenhuma despesa após os filtros.")
        st.stop()

    total = df["valor"].sum()
    n_reg = len(df)
    litros = df[df["tipo"] == "Abastecimento"]["qtde"].sum()
    k1, k2, k3 = st.columns(3)
    k1.metric("Total gasto", moeda(total))
    k2.metric("Registros", n_reg)
    k3.metric("Litros abastecidos", num(litros, 1))

    st.divider()

    aba_tabela, aba_tipo, aba_mes, aba_consumo = st.tabs(
        ["Lançamentos", "Por Tipo", "Por Mês", "Consumo"]
    )

    with aba_tabela:
        st.markdown("### Lançamentos do período")
        df_show = df.copy()
        df_show["valor"] = df_show["valor"].apply(moeda)
        if "valor_unit" in df_show.columns:
            df_show["valor_unit"] = df_show["valor_unit"].apply(
                lambda x: moeda(x) if pd.notna(x) and x > 0 else "—"
            )
        df_show["data"] = pd.to_datetime(df_show["data"]).dt.strftime("%d/%m/%Y")
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        st.download_button("Baixar CSV", csv, "despesas.csv", "text/csv")

    with aba_tipo:
        st.markdown("### Gasto por tipo de despesa")
        g = df.groupby("tipo")["valor"].sum().sort_values(ascending=False).reset_index()
        fig = px.bar(g.sort_values("valor"), x="valor", y="tipo", orientation="h", text="valor")
        fig.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
        fig.update_layout(margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True, key="g_tipo")

        fig2 = px.pie(g, names="tipo", values="valor", hole=0.4)
        st.plotly_chart(fig2, use_container_width=True, key="g_tipo_pie")

    with aba_mes:
        st.markdown("### Evolução mensal")
        df["mes"] = pd.to_datetime(df["data"]).dt.to_period("M").astype(str)
        gm = df.groupby("mes")["valor"].sum().reset_index()
        fig3 = px.bar(gm, x="mes", y="valor", text="valor")
        fig3.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
        fig3.update_layout(margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig3, use_container_width=True, key="g_mes")

    with aba_consumo:
        st.markdown("### Consumo (abastecimentos)")
        abast = df[df["tipo"] == "Abastecimento"].copy()
        if abast.empty or abast["km"].notna().sum() < 2:
            st.info("São necessários ao menos 2 abastecimentos com KM para calcular consumo.")
        else:
            abast = abast.sort_values(["veiculo", "data"])
            abast["km_rodado"] = abast.groupby("veiculo")["km"].diff()
            abast["consumo"] = abast["km_rodado"] / abast["qtde"]
            media = abast["consumo"].dropna()
            if not media.empty:
                st.metric("Consumo médio (km/litro)", num(media.mean(), 2))
            tab = abast[["data", "veiculo", "km", "qtde", "valor", "consumo"]].copy()
            tab["data"] = pd.to_datetime(tab["data"]).dt.strftime("%d/%m/%Y")
            tab["valor"] = tab["valor"].apply(moeda)
            tab["consumo"] = tab["consumo"].apply(lambda x: num(x, 2) if pd.notna(x) else "-")
            st.dataframe(tab, use_container_width=True, hide_index=True)

    st.divider()
    with st.expander("Excluir um lançamento"):
        ids = df["id"].tolist()
        id_excluir = st.selectbox("ID do lançamento", ids)
        if st.button("Excluir", type="primary"):
            try:
                db.excluir_despesa(int(id_excluir))
                st.success("Excluído. Recarregue a página para atualizar.")
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")


# ===========================================================================
# PÁGINA 3 — Cadastros
# ===========================================================================
elif pagina == "Cadastros":
    st.subheader("Cadastros")

    col_u, col_t = st.columns(2)

    with col_u:
        st.markdown("### Usuários")
        st.dataframe(usuarios, use_container_width=True, hide_index=True)
        novo_u = st.text_input("Novo usuário")
        nova_senha = st.text_input("Senha do usuário", type="password")
        if st.button("Adicionar usuário"):
            if novo_u.strip() and nova_senha.strip():
                db.adicionar_usuario(novo_u.strip(), _hash(nova_senha.strip()))
                st.success("Usuário adicionado. Recarregue a página.")
                carregar_auxiliares.clear()
            else:
                st.error("Informe o nome e a senha.")

    with col_t:
        st.markdown("### Tipos de despesa")
        st.dataframe(tipos, use_container_width=True, hide_index=True)
        novo_t = st.text_input("Novo tipo de despesa")
        if st.button("Adicionar tipo"):
            if novo_t.strip():
                db.adicionar_tipo(novo_t.strip())
                st.success("Tipo adicionado. Recarregue a página.")
                carregar_auxiliares.clear()
            else:
                st.error("Informe o nome.")

    st.divider()
    st.markdown("### Veículos")
    st.dataframe(veiculos, use_container_width=True, hide_index=True)

    with st.form("novo_veiculo", clear_on_submit=True):
        st.markdown("**Cadastrar novo veículo**")
        cv1, cv2, cv3 = st.columns(3)
        v_placa = cv1.text_input("Placa")
        v_modelo = cv2.text_input("Modelo")
        v_dono = cv3.selectbox("Proprietário", usuarios["nome"] if not usuarios.empty else [])

        cv4, cv5 = st.columns(2)
        v_datacompra = cv4.date_input("Data da compra", value=date.today(), format="DD/MM/YYYY")
        v_kmatual = cv5.number_input("KM atual", min_value=0.0, step=1.0, format="%.1f")

        add_v = st.form_submit_button("Adicionar veículo")

    if add_v:
        if not v_placa.strip():
            st.error("Informe a placa.")
        elif usuarios.empty:
            st.error("Cadastre um usuário antes.")
        else:
            id_dono = int(usuarios.loc[usuarios["nome"] == v_dono, "id"].iloc[0])
            try:
                db.adicionar_veiculo(
                    v_placa.strip().upper(), v_modelo.strip() or None,
                    v_datacompra, v_kmatual or None, id_dono,
                )
                st.success("Veículo adicionado. Recarregue a página.")
                carregar_auxiliares.clear()
            except Exception as e:
                st.error(f"Erro ao adicionar veículo: {e}")
