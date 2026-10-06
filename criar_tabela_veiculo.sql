-- =====================================================================
-- Tabela de Veículos — adicione ao banco (rode no SQL Editor do Supabase)
-- =====================================================================

CREATE TABLE IF NOT EXISTS veiculo (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    placa       VARCHAR(10) NOT NULL,
    modelo      VARCHAR(100),
    datacompra  DATE,
    kmatual     NUMERIC(10,1),
    id_usuario  BIGINT REFERENCES usuario(id),
    ativo       BOOLEAN DEFAULT TRUE,
    criado_em   TIMESTAMP DEFAULT NOW()
);

-- =====================================================================
-- Ajuste na tabela despesa: trocar o campo texto 'veiculo' por um
-- relacionamento com a tabela veiculo (id_veiculo).
-- =====================================================================

-- adiciona a coluna de relacionamento
ALTER TABLE despesa ADD COLUMN IF NOT EXISTS id_veiculo BIGINT REFERENCES veiculo(id);

-- (opcional) se quiser manter o campo texto antigo por enquanto, deixe;
-- depois de migrar, pode remover com:
-- ALTER TABLE despesa DROP COLUMN veiculo;

-- índice para consultas por veículo
CREATE INDEX IF NOT EXISTS idx_despesa_veiculo ON despesa(id_veiculo);

-- =====================================================================
-- Exemplo de veículo inicial (ajuste os dados)
-- =====================================================================
 INSERT INTO veiculo (placa, modelo, datacompra, kmatual, id_usuario)
 VALUES ('QIL1C55', 'ONIX 1.4 ACTIVE', '2021-01-01',123450, 1);
