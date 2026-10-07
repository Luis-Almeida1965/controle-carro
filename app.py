"""Controle de Despesas do Carro — Streamlit + Supabase.

App para registrar e acompanhar despesas do veículo (abastecimento,
manutenção, etc.), com gráficos, filtros, relatórios, login e alertas.

Executar local:  streamlit run app.py
"""
from datetime import date, timedelta
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
# AUTENTICAÇÃO
# ===========================================================================
def _hash(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()


def tela_login():
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


if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    tela_login()
    st.stop()


# ===========================================================================
# App principal
# ===========================================================================
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


@st.cache_data(ttl=300)
def carregar_auxiliares():
    usuarios = db.listar_usuarios()
    tipos    = db.listar_tipos()
    veiculos = db.listar_veiculos()
    return usuarios, tipos, veiculos


pagina = st.sidebar.radio(
    "Menu",
    ["🏠 Dashboard", "📝 Registrar despesa", "📊 Despesas e relatórios", "⚙️ Cadastros"],
)

try:
    usuarios, tipos, veiculos = carregar_auxiliares()
except Exception as e:
    st.error(f"Erro ao conectar no banco: {e}")
    st.stop()


# ===========================================================================
# PÁGINA 0 — Dashboard
# ===========================================================================
if pagina == "🏠 Dashboard":
    st.subheader("Dashboard")

    hoje = date.today()
    mes_ini = hoje.replace(day=1)

    # KPIs do mês
    try:
        df_mes = db.carregar_despesas(mes_ini, hoje)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()

    total_mes   = df_mes["valor"].sum() if not df_mes.empty else 0
    n_reg       = len(df_mes)
    litros_mes  = df_mes[df_mes["tipo"] == "Abastecimento"]["qtde"].sum() if not df_mes.empty else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("💰 Gasto no mês", moeda(total_mes))
    k2.metric("📋 Registros no mês", n_reg)
    k3.metric("⛽ Litros abastecidos", num(litros_mes, 1))

    st.divider()

    # -------------------------------------------------------------------
    # PAINEL DE ALERTAS
    # -------------------------------------------------------------------
    st.markdown("### 🔔 Alertas de manutenção")

    try:
        alertas = db.buscar_alertas()
    except Exception as e:
        st.error(f"Erro ao carregar alertas: {e}")
        alertas = pd.DataFrame()

    if alertas.empty:
        st.success("✅ Nenhum alerta pendente. Tudo em dia!")
    else:
        for _, row in alertas.iterrows():
            veiculo_info = f"**{row['placa']}** — {row['modelo'] or ''}"
            tipo_info    = row.get("tipo", "Manutenção")

            # determina status por KM
            status_km = None
            msg_km = ""
            if pd.notna(row.get("km_proximo")) and pd.notna(row.get("km_atual")):
                diff_km = float(row["km_proximo"]) - float(row["km_atual"])
                if diff_km <= 0:
                    status_km = "vencido"
                    msg_km = f"KM vencido há {num(abs(diff_km), 0)} km"
                elif diff_km <= 500:
                    status_km = "proximo"
                    msg_km = f"Faltam {num(diff_km, 0)} km"
                else:
                    status_km = "ok"
                    msg_km = f"Próxima troca em {num(row['km_proximo'], 0)} km"

            # determina status por data
            status_data = None
            msg_data = ""
            if pd.notna(row.get("data_proxima")):
                data_prox = pd.to_datetime(row["data_proxima"]).date()
                diff_dias = (data_prox - hoje).days
                if diff_dias < 0:
                    status_data = "vencido"
                    msg_data = f"Data vencida há {abs(diff_dias)} dias"
                elif diff_dias <= 30:
                    status_data = "proximo"
                    msg_data = f"Faltam {diff_dias} dias ({data_prox.strftime('%d/%m/%Y')})"
                else:
                    status_data = "ok"
                    msg_data = f"Próxima troca em {data_prox.strftime('%d/%m/%Y')}"

            # status geral = o mais crítico entre km e data
            status_final = "ok"
            for s in [status_km, status_data]:
                if s == "vencido":
                    status_final = "vencido"
                    break
                elif s == "proximo" and status_final != "vencido":
                    status_final = "proximo"

            icone = {"vencido": "🔴", "proximo": "🟡", "ok": "🟢"}.get(status_final, "⚪")

            msgs = []
            if msg_km:
                msgs.append(msg_km)
            if msg_data:
                msgs.append(msg_data)

            with st.container(border=True):
                col_ic, col_info = st.columns([1, 8])
                col_ic.markdown(f"## {icone}")
                col_info.markdown(f"{veiculo_info} — **{tipo_info}**")
                col_info.caption(" | ".join(msgs))

    st.divider()

    # Gráfico rápido dos últimos 6 meses
    st.markdown("### 📈 Evolução dos gastos (últimos 6 meses)")
    try:
        df_6m = db.carregar_despesas(hoje - timedelta(days=180), hoje)
        if not df_6m.empty:
            df_6m["mes"] = pd.to_datetime(df_6m["data"]).dt.to_period("M").astype(str)
            gm = df_6m.groupby("mes")["valor"].sum().reset_index()
            fig = px.bar(gm, x="mes", y="valor", text="valor")
            fig.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados nos últimos 6 meses.")
    except Exception as e:
        st.error(f"Erro ao carregar gráfico: {e}")


# ===========================================================================
# PÁGINA 1 — Registrar despesa
# ===========================================================================
elif pagina == "📝 Registrar despesa":
    st.subheader("Registrar nova despesa")

    if usuarios.empty or tipos.empty or veiculos.empty:
        st.warning("Cadastre ao menos um usuário, um tipo de despesa e um veículo na aba Cadastros.")
    else:
        with st.form("nova_despesa", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            data_desp    = c1.date_input("Data", value=date.today(), format="DD/MM/YYYY")
            usuario_nome = c2.selectbox("Usuário", usuarios["nome"])
            veiculo_placa = c3.selectbox("Veículo", veiculos["placa"])

            c4, c5, c6 = st.columns(3)
            tipo_nome = c4.selectbox("Tipo de despesa", tipos["nome"])
            qtde      = c5.number_input("Quantidade (litros, etc.)", min_value=0.0, step=0.1, format="%.3f")
            km        = c6.number_input("KM (odômetro)", min_value=0.0, step=1.0, format="%.1f")

            c7, c8, c9 = st.columns(3)
            valor_unit = c7.number_input(
                "Valor unitário (R$)", min_value=0.0, step=0.01, format="%.3f",
                help="Preço por litro ou por unidade",
            )
            valor = c8.number_input(
                "Valor total (R$)", min_value=0.0, step=1.0, format="%.2f",
                help="Valor total pago",
            )
            if valor_unit > 0 and qtde > 0:
                valor_calculado = round(valor_unit * qtde, 2)
                c9.metric("Total calculado", moeda(valor_calculado))
            else:
                valor_calculado = None
                c9.metric("Total calculado", "—")

            obs = st.text_input("Observação", "")

            # -----------------------------------------------------------
            # Alerta de manutenção
            # -----------------------------------------------------------
            st.divider()
            gera_alerta = st.checkbox(
                "🔔 Gerar alerta de próxima manutenção para esta despesa",
                value=False,
            )

            km_proximo    = None
            data_proxima  = None

            if gera_alerta:
                # busca os intervalos configurados no veículo selecionado
                v_row = veiculos[veiculos["placa"] == veiculo_placa]
                int_km  = int(v_row["intervalo_km_oleo"].iloc[0])  if not v_row.empty and pd.notna(v_row["intervalo_km_oleo"].iloc[0])  else 5000
                int_mes = int(v_row["intervalo_meses_oleo"].iloc[0]) if not v_row.empty and pd.notna(v_row["intervalo_meses_oleo"].iloc[0]) else 6

                ca1, ca2 = st.columns(2)
                km_proximo = ca1.number_input(
                    "KM da próxima manutenção",
                    min_value=0.0, step=100.0, format="%.0f",
                    value=float(km + int_km) if km > 0 else float(int_km),
                    help=f"Intervalo configurado no veículo: {int_km} km",
                )
                data_sugerida = data_desp + timedelta(days=int_mes * 30)
                data_proxima = ca2.date_input(
                    "Data da próxima manutenção",
                    value=data_sugerida,
                    format="DD/MM/YYYY",
                    help=f"Intervalo configurado no veículo: {int_mes} meses",
                )

            enviar = st.form_submit_button("Salvar despesa")

        if enviar:
            valor_final = valor if valor > 0 else (valor_calculado or 0)
            if valor_final <= 0:
                st.error("Informe o valor total ou preencha o valor unitário e a quantidade.")
            else:
                id_usuario = int(usuarios.loc[usuarios["nome"] == usuario_nome, "id"].iloc[0])
                id_tipo    = int(tipos.loc[tipos["nome"] == tipo_nome, "id"].iloc[0])
                id_veiculo = int(veiculos.loc[veiculos["placa"] == veiculo_placa, "id"].iloc[0])
                try:
                    db.inserir_despesa(
                        data_desp, id_usuario, id_tipo, id_veiculo,
                        qtde or None, valor_final, valor_unit or None,
                        km or None, obs or None,
                        gera_alerta,
                        float(km_proximo) if gera_alerta and km_proximo else None,
                        data_proxima if gera_alerta else None,
                    )
                    st.success("Despesa registrada com sucesso!")
                    carregar_auxiliares.clear()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")


# ===========================================================================
# PÁGINA 2 — Despesas e relatórios
# ===========================================================================
elif pagina == "📊 Despesas e relatórios":
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
    f_tipo    = st.sidebar.multiselect("Tipo", sorted(df["tipo"].dropna().unique()))
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

    total  = df["valor"].sum()
    n_reg  = len(df)
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
            abast["consumo"]   = abast["km_rodado"] / abast["qtde"]
            media = abast["consumo"].dropna()
            if not media.empty:
                st.metric("Consumo médio (km/litro)", num(media.mean(), 2))
            tab = abast[["data", "veiculo", "km", "qtde", "valor", "consumo"]].copy()
            tab["data"]    = pd.to_datetime(tab["data"]).dt.strftime("%d/%m/%Y")
            tab["valor"]   = tab["valor"].apply(moeda)
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
elif pagina == "⚙️ Cadastros":
    st.subheader("Cadastros")

    col_u, col_t = st.columns(2)

    with col_u:
        st.markdown("### Usuários")
        st.dataframe(usuarios, use_container_width=True, hide_index=True)
        novo_u    = st.text_input("Novo usuário")
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
    st.markdown("### 🚗 Veículos")
    st.dataframe(veiculos, use_container_width=True, hide_index=True)

    aba_add_v, aba_edit_v, aba_del_v = st.tabs(["➕ Incluir", "✏️ Alterar", "🗑️ Excluir"])

    with aba_add_v:
        with st.form("novo_veiculo", clear_on_submit=True):
            st.markdown("**Cadastrar novo veículo**")
            cv1, cv2, cv3 = st.columns(3)
            v_placa  = cv1.text_input("Placa")
            v_modelo = cv2.text_input("Modelo")
            v_dono   = cv3.selectbox("Proprietário", usuarios["nome"] if not usuarios.empty else [])

            cv4, cv5 = st.columns(2)
            v_datacompra = cv4.date_input("Data da compra", value=date.today(), format="DD/MM/YYYY")
            v_kmatual    = cv5.number_input("KM atual", min_value=0.0, step=1.0, format="%.1f")

            st.markdown("**Intervalos de manutenção**")
            ci1, ci2 = st.columns(2)
            v_int_km  = ci1.number_input("Intervalo troca de óleo (km)",  min_value=0, step=500, value=5000)
            v_int_mes = ci2.number_input("Intervalo troca de óleo (meses)", min_value=0, step=1,   value=6)

            add_v = st.form_submit_button("Adicionar veículo", type="primary")

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
                        v_int_km, v_int_mes,
                    )
                    st.success("Veículo adicionado. Recarregue a página.")
                    carregar_auxiliares.clear()
                except Exception as e:
                    st.error(f"Erro ao adicionar veículo: {e}")

    with aba_edit_v:
        if veiculos.empty:
            st.info("Nenhum veículo cadastrado.")
        else:
            v_sel_placa = st.selectbox("Veículo", veiculos["placa"], key="sel_veiculo_editar")
            v_sel = veiculos[veiculos["placa"] == v_sel_placa].iloc[0]

            with st.form("editar_veiculo", clear_on_submit=False):
                ec1, ec2, ec3 = st.columns(3)
                e_placa  = ec1.text_input("Placa", value=v_sel["placa"])
                e_modelo = ec2.text_input("Modelo", value=v_sel["modelo"] or "")
                e_dono_atual = v_sel["usuario"] if v_sel["usuario"] else usuarios["nome"].iloc[0]
                e_dono = ec3.selectbox(
                    "Proprietário", usuarios["nome"],
                    index=int(usuarios["nome"].tolist().index(e_dono_atual))
                    if e_dono_atual in usuarios["nome"].tolist() else 0,
                )

                ec4, ec5 = st.columns(2)
                e_datacompra = ec4.date_input(
                    "Data da compra",
                    value=pd.to_datetime(v_sel["datacompra"]).date()
                    if v_sel["datacompra"] is not None else date.today(),
                    format="DD/MM/YYYY",
                )
                e_kmatual = ec5.number_input(
                    "KM atual", min_value=0.0, step=1.0, format="%.1f",
                    value=float(v_sel["kmatual"]) if v_sel["kmatual"] else 0.0,
                )

                st.markdown("**Intervalos de manutenção**")
                ei1, ei2 = st.columns(2)
                e_int_km  = ei1.number_input(
                    "Intervalo troca de óleo (km)", min_value=0, step=500,
                    value=int(v_sel["intervalo_km_oleo"]) if pd.notna(v_sel.get("intervalo_km_oleo")) else 5000,
                )
                e_int_mes = ei2.number_input(
                    "Intervalo troca de óleo (meses)", min_value=0, step=1,
                    value=int(v_sel["intervalo_meses_oleo"]) if pd.notna(v_sel.get("intervalo_meses_oleo")) else 6,
                )

                salvar_v = st.form_submit_button("Salvar alterações", type="primary")

            if salvar_v:
                if not e_placa.strip():
                    st.error("Informe a placa.")
                else:
                    id_dono_e = int(usuarios.loc[usuarios["nome"] == e_dono, "id"].iloc[0])
                    try:
                        db.alterar_veiculo(
                            int(v_sel["id"]),
                            e_placa.strip().upper(), e_modelo.strip() or None,
                            e_datacompra, e_kmatual or None, id_dono_e,
                            e_int_km, e_int_mes,
                        )
                        st.success("Veículo atualizado! Recarregue a página.")
                        carregar_auxiliares.clear()
                    except Exception as e:
                        st.error(f"Erro ao alterar veículo: {e}")

    with aba_del_v:
        if veiculos.empty:
            st.info("Nenhum veículo cadastrado.")
        else:
            v_del_placa = st.selectbox("Veículo", veiculos["placa"], key="sel_veiculo_excluir")
            v_del = veiculos[veiculos["placa"] == v_del_placa].iloc[0]
            st.warning(
                f"Você está prestes a excluir o veículo **{v_del_placa}** "
                f"({v_del['modelo'] or ''}). Esta ação não pode ser desfeita."
            )
            if st.button("Excluir veículo", type="primary", key="btn_excluir_veiculo"):
                try:
                    db.excluir_veiculo(int(v_del["id"]))
                    st.success("Veículo excluído. Recarregue a página.")
                    carregar_auxiliares.clear()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")

    # -----------------------------------------------------------------------
    # Trocar senha
    # -----------------------------------------------------------------------
    st.divider()
    st.markdown("### 🔑 Trocar minha senha")
    st.caption(f"Usuário logado: **{st.session_state['usuario_logado']}**")

    with st.form("trocar_senha", clear_on_submit=True):
        senha_atual    = st.text_input("Senha atual", type="password")
        nova_senha     = st.text_input("Nova senha", type="password")
        confirma_senha = st.text_input("Confirmar nova senha", type="password")
        trocar = st.form_submit_button("Salvar nova senha", type="primary")

    if trocar:
        if not senha_atual or not nova_senha or not confirma_senha:
            st.error("Preencha todos os campos.")
        elif nova_senha != confirma_senha:
            st.error("A nova senha e a confirmação não coincidem.")
        elif len(nova_senha) < 4:
            st.error("A nova senha deve ter ao menos 4 caracteres.")
        else:
            resultado = db.autenticar_usuario(
                st.session_state["usuario_logado"], _hash(senha_atual)
            )
            if resultado is None:
                st.error("Senha atual incorreta.")
            else:
                try:
                    db.trocar_senha(st.session_state["usuario_id"], _hash(nova_senha))
                    st.success("Senha alterada com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao trocar senha: {e}")
