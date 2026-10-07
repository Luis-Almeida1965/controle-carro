"""Conexão com o Supabase (PostgreSQL) e funções de acesso aos dados."""
import pandas as pd
import psycopg2
import psycopg2.extras
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
    """Retorna dict com id e nome se autenticado, ou None."""
    df = consultar(
        "SELECT id, nome FROM usuario WHERE nome = %s AND senha = %s AND ativo = TRUE",
        (nome, senha_hash),
    )
    if df.empty:
        return None
    return {"id": int(df.iloc[0]["id"]), "nome": str(df.iloc[0]["nome"])}


# ---------------------------------------------------------------------------
# Usuários, tipos e veículos
# ---------------------------------------------------------------------------
def listar_usuarios() -> pd.DataFrame:
    return consultar("SELECT id, nome FROM usuario WHERE ativo = TRUE ORDER BY nome")


def listar_tipos() -> pd.DataFrame:
    return consultar("SELECT id, nome FROM tipo_despesa WHERE ativo = TRUE ORDER BY nome")


def listar_veiculos() -> pd.DataFrame:
    return consultar(
        """SELECT v.id, v.placa, v.modelo, v.datacompra, v.kmatual,
                  v.id_usuario, u.nome AS usuario
             FROM veiculo v
             LEFT JOIN usuario u ON u.id = v.id_usuario
            WHERE v.ativo = TRUE
            ORDER BY v.placa"""
    )


# ---------------------------------------------------------------------------
# Despesas
# ---------------------------------------------------------------------------
def inserir_despesa(data, id_usuario, id_tipo, id_veiculo, qtde, valor, valor_unit, km, obs):
    executar(
        """INSERT INTO despesa
           (data, id_usuario, id_tipo, id_veiculo, qtde, valor, valor_unit, km, observacao)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (data, id_usuario, id_tipo, id_veiculo, qtde, valor, valor_unit, km, obs),
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
                  v.placa AS veiculo, d.qtde, d.valor_unit, d.valor, d.km,
                  d.observacao, d.id_veiculo
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


def adicionar_usuario(nome, senha_hash):
    executar("INSERT INTO usuario (nome, senha) VALUES (%s, %s)", (nome, senha_hash))


def trocar_senha(id_usuario, nova_senha_hash):
    executar(
        "UPDATE usuario SET senha = %s WHERE id = %s",
        (nova_senha_hash, id_usuario)
    )


def adicionar_tipo(nome):
    executar("INSERT INTO tipo_despesa (nome) VALUES (%s)", (nome,))


def adicionar_veiculo(placa, modelo, datacompra, kmatual, id_usuario):
    executar(
        """INSERT INTO veiculo (placa, modelo, datacompra, kmatual, id_usuario)
           VALUES (%s, %s, %s, %s, %s)""",
        (placa, modelo, datacompra, kmatual, id_usuario),
    )
