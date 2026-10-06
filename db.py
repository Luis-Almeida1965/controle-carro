"""Conexão com o Supabase (PostgreSQL) e funções de acesso aos dados.

As credenciais vêm dos secrets do Streamlit (st.secrets), configurados no
Streamlit Cloud ou no arquivo .streamlit/secrets.toml local.
"""
import pandas as pd
import psycopg2
import psycopg2.extras
import streamlit as st


def _conectar():
    """Abre conexão com o Supabase usando os secrets do Streamlit."""
    return psycopg2.connect(
        host=st.secrets["db_host"],
        port=st.secrets["db_port"],
        dbname=st.secrets["db_name"],
        user=st.secrets["db_user"],
        password=st.secrets["db_password"],
    )


def consultar(sql, params=None) -> pd.DataFrame:
    """Executa um SELECT e devolve um DataFrame."""
    with _conectar() as cn:
        return pd.read_sql(sql, cn, params=params)


def executar(sql, params=None):
    """Executa um INSERT/UPDATE/DELETE."""
    with _conectar() as cn:
        cur = cn.cursor()
        cur.execute(sql, params or ())
        cn.commit()


# ---------------------------------------------------------------------------
# Funções específicas do domínio
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


def inserir_despesa(data, id_usuario, id_tipo, id_veiculo, qtde, valor, km, obs):
    executar(
        """INSERT INTO despesa
           (data, id_usuario, id_tipo, id_veiculo, qtde, valor, km, observacao)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (data, id_usuario, id_tipo, id_veiculo, qtde, valor, km, obs),
    )
    # atualiza o km atual do veículo, se o km informado for maior
    if id_veiculo and km:
        executar(
            """UPDATE veiculo SET kmatual = %s
                WHERE id = %s AND (kmatual IS NULL OR kmatual < %s)""",
            (km, id_veiculo, km),
        )


def carregar_despesas(data_ini, data_fim) -> pd.DataFrame:
    """Carrega as despesas do período com os nomes de tipo, usuário e veículo."""
    return consultar(
        """SELECT d.id, d.data, u.nome AS usuario, t.nome AS tipo,
                  v.placa AS veiculo, d.qtde, d.valor, d.km, d.observacao,
                  d.id_veiculo
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


def adicionar_usuario(nome):
    executar("INSERT INTO usuario (nome) VALUES (%s)", (nome,))


def adicionar_tipo(nome):
    executar("INSERT INTO tipo_despesa (nome) VALUES (%s)", (nome,))


def adicionar_veiculo(placa, modelo, datacompra, kmatual, id_usuario):
    executar(
        """INSERT INTO veiculo (placa, modelo, datacompra, kmatual, id_usuario)
           VALUES (%s, %s, %s, %s, %s)""",
        (placa, modelo, datacompra, kmatual, id_usuario),
    )
