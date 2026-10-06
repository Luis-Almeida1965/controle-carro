# Controle de Despesas do Carro

App Streamlit + Supabase para registrar e acompanhar despesas do veículo.

## Passos para colocar no ar

### 1. Criar as tabelas no Supabase
- Entre no seu projeto Supabase → SQL Editor
- Cole e execute o conteúdo de `criar_tabelas.sql`

### 2. Pegar as credenciais do banco
- No Supabase: Project Settings → Database → Connection info
- Anote: host, port (5432), database (postgres), user (postgres), password

### 3. Testar local (opcional)
- Crie `.streamlit/secrets.toml` a partir do `.streamlit/secrets.toml.example`
- Preencha com as credenciais
- `pip install -r requirements.txt`
- `streamlit run app.py`

### 4. Subir no GitHub
- Crie um repositório e suba todos os arquivos
- IMPORTANTE: NÃO suba o `secrets.toml` (só o .example)

### 5. Deploy no Streamlit Cloud
- Acesse share.streamlit.io
- Conecte o repositório do GitHub
- Em Advanced settings → Secrets, cole as credenciais (formato do secrets.toml)
- Deploy!

### 6. Acessar
- O app fica em uma URL tipo `seuapp.streamlit.app`
- Acessível de qualquer lugar (celular, PC)
