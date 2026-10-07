"""Conexão com o Supabase (PostgreSQL) e funções de acesso aos dados."""
import pandas as pd
import psycopg2
import streamlit as st


def _conectar():
    return psycopg2.connect(
        host=st.secrets["db_host"],
        port=st.secrets["db_port"],
        dbname=st.secrets["db_name"],
        user=st.secrets["db_user"],
        password=st.secrets["db_password"],
    )


def consultar(sql, params=None) -> pd.DataFrame:
    with _conectar() as cn:
        return pd.read_sql(sql, cn, params=params)


def executar(sql, params=None):
    with _conectar() as cn:
        cur = cn.cursor()
        cur.execute(sql, params or ())
        cn.commit()


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------
def autenticar_usuario(nome: str, senha_hash: str):
    df = consultar(
        "SELECT id, nome FROM usuario WHERE nome = %s AND senha = %s AND ativo = TRUE",
        (nome, senha_hash),
    )
    if df.empty:
        return None
    return {"id": int(df.iloc[0]["id"]), "nome": str(df.iloc[0]["nome"])}


def trocar_senha(id_usuario, nova_senha_hash):
    executar("UPDATE usuario SET senha = %s WHERE id = %s", (nova_senha_hash, id_usuario))


# ---------------------------------------------------------------------------
# Usuários e tipos
# ---------------------------------------------------------------------------
def listar_usuarios() -> pd.DataFrame:
    return consultar("SELECT id, nome FROM usuario WHERE ativo = TRUE ORDER BY nome")


def listar_tipos() -> pd.DataFrame:
    return consultar("SELECT id, nome FROM tipo_despesa WHERE ativo = TRUE ORDER BY nome")


def adicionar_usuario(nome, senha_hash):
    executar("INSERT INTO usuario (nome, senha) VALUES (%s, %s)", (nome, senha_hash))


def adicionar_tipo(nome):
    executar("INSERT INTO tipo_despesa (nome) VALUES (%s)", (nome,))


# ---------------------------------------------------------------------------
# Veículos
# ---------------------------------------------------------------------------
def listar_veiculos() -> pd.DataFrame:
    return consultar(
        """SELECT v.id, v.placa, v.modelo, v.datacompra, v.kmatual,
                  v.intervalo_km_oleo, v.intervalo_meses_oleo,
                  v.id_usuario, u.nome AS usuario
             FROM veiculo v
             LEFT JOIN usuario u ON u.id = v.id_usuario
            WHERE v.ativo = TRUE
            ORDER BY v.placa"""
    )


def adicionar_veiculo(placa, modelo, datacompra, kmatual, id_usuario, int_km=5000, int_mes=6):
    executar(
        """INSERT INTO veiculo
           (placa, modelo, datacompra, kmatual, id_usuario,
            intervalo_km_oleo, intervalo_meses_oleo)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (placa, modelo, datacompra, kmatual, id_usuario, int_km, int_mes),
    )


def alterar_veiculo(id_veiculo, placa, modelo, datacompra, kmatual, id_usuario, int_km=5000, int_mes=6):
    executar(
        """UPDATE veiculo
              SET placa = %s, modelo = %s, datacompra = %s, kmatual = %s,
                  id_usuario = %s, intervalo_km_oleo = %s, intervalo_meses_oleo = %s
            WHERE id = %s""",
        (placa, modelo, datacompra, kmatual, id_usuario, int_km, int_mes, id_veiculo),
    )


def excluir_veiculo(id_veiculo):
    executar("UPDATE veiculo SET ativo = FALSE WHERE id = %s", (id_veiculo,))


# ---------------------------------------------------------------------------
# Despesas
# ---------------------------------------------------------------------------
def inserir_despesa(data, id_usuario, id_tipo, id_veiculo, qtde, valor,
                    valor_unit, km, obs, gera_alerta=False,
                    km_proximo=None, data_proxima=None):
    executar(
        """INSERT INTO despesa
           (data, id_usuario, id_tipo, id_veiculo, qtde, valor, valor_unit,
            km, observacao, gera_alerta, km_proximo, data_proxima)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (data, id_usuario, id_tipo, id_veiculo, qtde, valor, valor_unit,
         km, obs, gera_alerta, km_proximo, data_proxima),
    )
    if id_veiculo and km:
        executar(
            """UPDATE veiculo SET kmatual = %s
                WHERE id = %s AND (kmatual IS NULL OR kmatual < %s)""",
            (km, id_veiculo, km),
        )


def carregar_despesas(data_ini, data_fim) -> pd.DataFrame:
    return consultar(
        """SELECT d.id, d.data, u.nome AS usuario, t.nome AS tipo,
                  v.placa AS veiculo, d.qtde, d.valor_unit, d.valor,
                  d.km, d.observacao, d.gera_alerta,
                  d.km_proximo, d.data_proxima, d.id_veiculo
             FROM despesa d
             LEFT JOIN usuario u ON u.id = d.id_usuario
             LEFT JOIN tipo_despesa t ON t.id = d.id_tipo
             LEFT JOIN veiculo v ON v.id = d.id_veiculo
            WHERE d.data BETWEEN %s AND %s
            ORDER BY d.data DESC, d.id DESC""",
        (data_ini, data_fim),
    )


def excluir_despesa(id_despesa):
    executar("DELETE FROM despesa WHERE id = %s", (id_despesa,))


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------
def buscar_alertas() -> pd.DataFrame:
    """Retorna despesas com alerta ativo, junto com o km atual do veículo."""
    return consultar(
        """SELECT d.id, d.data, t.nome AS tipo,
                  v.placa, v.modelo, v.kmatual AS km_atual,
                  d.km_proximo, d.data_proxima
             FROM despesa d
             LEFT JOIN tipo_despesa t ON t.id = d.id_tipo
             LEFT JOIN veiculo v      ON v.id = d.id_veiculo
            WHERE d.gera_alerta = TRUE
              AND v.ativo = TRUE
              AND (
                    d.data_proxima IS NOT NULL
                 OR d.km_proximo   IS NOT NULL
              )
            ORDER BY d.data_proxima ASC NULLS LAST, d.km_proximo ASC NULLS LAST"""
    )
