-- =====================================================================
-- Controle de Despesas do Carro — estrutura das tabelas (PostgreSQL / Supabase)
-- Rode este script no SQL Editor do Supabase (uma vez).
-- =====================================================================

-- Tabela de usuários
CREATE TABLE IF NOT EXISTS usuario (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome        VARCHAR(100) NOT NULL,
    ativo       BOOLEAN DEFAULT TRUE,
    criado_em   TIMESTAMP DEFAULT NOW()
);

-- Tabela de tipos de despesa (abastecimento, manutenção, pneu, etc.)
CREATE TABLE IF NOT EXISTS tipo_despesa (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome        VARCHAR(50) NOT NULL,
    ativo       BOOLEAN DEFAULT TRUE
);

-- Tabela principal de despesas
CREATE TABLE IF NOT EXISTS despesa (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    data            DATE NOT NULL,
    id_usuario      BIGINT REFERENCES usuario(id),
    id_tipo         BIGINT REFERENCES tipo_despesa(id),
    veiculo         VARCHAR(50),          -- placa ou nome do carro (opcional)
    qtde            NUMERIC(10,3),         -- litros (no abastecimento) ou quantidade
    valor           NUMERIC(10,2) NOT NULL,
    km              NUMERIC(10,1),         -- odômetro no momento
    observacao      VARCHAR(300),
    criado_em       TIMESTAMP DEFAULT NOW()
);

-- índices para consultas por data e tipo
CREATE INDEX IF NOT EXISTS idx_despesa_data ON despesa(data);
CREATE INDEX IF NOT EXISTS idx_despesa_tipo ON despesa(id_tipo);

-- =====================================================================
-- Dados iniciais
-- =====================================================================

-- usuários (ajuste os nomes da família)
INSERT INTO usuario (nome) VALUES ('Luis') ON CONFLICT DO NOTHING;

-- tipos de despesa comuns
INSERT INTO tipo_despesa (nome) VALUES
    ('Abastecimento'),
    ('Manutenção'),
    ('Pneu'),
    ('Seguro'),
    ('IPVA/Licenciamento'),
    ('Lavagem'),
    ('Estacionamento'),
    ('Multa'),
    ('Outros')
ON CONFLICT DO NOTHING;
