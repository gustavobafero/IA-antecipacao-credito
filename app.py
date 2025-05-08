chat, tudo bem? Vamos continuar o processo?

import streamlit as st
from openai import OpenAI, RateLimitError
from datetime import datetime
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import PercentFormatter
from io import BytesIO
from fpdf import FPDF
import unicodedata
import tempfile
import locale
import numpy as np
import pandas as pd
import xml.etree.ElementTree as ET
import math
from twilio.rest import Client
import hashlib
import os
import sqlite3
from sqlalchemy import create\_engine, text
import streamlit as st
DATA\_PATH = "clientes.db"
from io import StringIO

# --- Configuração da página: deve ser o primeiro comando Streamlit ---

st.set\_page\_config(page\_title="Simulação Antecipação", layout="centered")

# --- Navegação inicial via simulação ---

if 'navigate' not in st.session\_state:
st.session\_state\['navigate'] = None

if st.session\_state.navigate == "register":
\# fluxo principal irá lidar com cadastro
pass
elif st.session\_state.navigate == "login":
\# fluxo principal irá lidar com login
pass
else:
\# Página Inicial (antes do login)
\# --- Estilos ---
st.markdown(""" <style>
.stApp { background-color: #FFFFFF; }
.header { font-size: 36px; font-weight: bold; text-align: center; margin-bottom: 10px; }
.subheader { font-size: 18px; text-align: center; margin-bottom: 30px; color: #555555; }
.resultado { background-color: #E3F2FD; padding: 20px; border-radius: 8px; text-align: center; margin-top: 20px; }
.cta { background-color: #0D47A1; color: white; padding: 15px; border-radius: 5px; text-align: center; margin-top: 30px; width: 100%; }
.cta\:hover { background-color: #1565C0; } </style>
""", unsafe\_allow\_html=True)

```
# --- Cabeçalho ---
st.markdown('<div class="header">Antecipe agora. Sem compromisso.</div>', unsafe_allow_html=True)
st.markdown('<div class="subheader">Envie uma nota fiscal eletrônica (.XML) e descubra agora quanto você pode antecipar.</div>', unsafe_allow_html=True)

# --- Upload de XML ---
xml_file = st.file_uploader("Escolha seu arquivo XML", type=["xml"] )
if xml_file:
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        valor_nota = float(root.find('.//nfe:vNF', ns).text.replace(',', '.'))

        # Cálculo simples
        taxa_sugerida = 2.2  # Exemplo fixo, em %
        valor_receber = valor_nota * (1 - taxa_sugerida / 100)

        # Exibição do resultado
        st.markdown('<div class="resultado">', unsafe_allow_html=True)
        st.markdown(f"**Valor da nota:** R$ {valor_nota:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), unsafe_allow_html=True)
        st.markdown(f"**Taxa sugerida:** {taxa_sugerida:.1f}%", unsafe_allow_html=True)
        st.markdown(f"**Valor a receber:** R$ {valor_receber:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Erro ao processar o XML: {e}")
else:
    st.info('Faça upload de um XML para começar a simulação.')

# --- Botões de Navegação ---
col1, col2 = st.columns(2)
with col1:
    if st.button("Assinar e continuar"):
        st.session_state.navigate = "register"
with col2:
    if st.button("Já é cliente? Faça login."):
        st.session_state.navigate = "login"

# Interrompe antes do fluxo de login/cadastro
st.stop()
```

st.markdown(
""" <style>
/\* Botões padrão e elementos de ação */
.stButton > button,
button,
\[data-testid="stToolbar"],
.css-1offfwp.edgvbvh3 {            /* classe genérica de botões */
background-color: #0D47A1 !important;  /* azul escuro */
color: #FFFFFF     !important;  /* texto branco \*/
}

```
  /* Itens selecionados da sidebar/nav */
  [data-testid="stSidebarNav"] > div[role="button"][aria-selected="true"] {
    background-color: #0A174E !important;  /* tom ainda mais escuro */
    color: #FFFFFF       !important;
  }

  /* Cabeçalho fixo (toolbar superior) */
  [data-testid="stToolbar"] {
    background-color: #0D47A1 !important;
  }
</style>
""",
unsafe_allow_html=True,
```

)

def hash\_password(password: str) -> str:
"""Retorna o SHA-256 hex digest da senha."""
return hashlib.sha256(password.encode("utf-8")).hexdigest()

# 2) Conexão e criação da tabela de clientes

@st.cache\_resource
@st.cache\_resource
def get\_db():
\# tenta ler DATABASE\_URL, se não existir cai para sqlite local
url = st.secrets.get("DATABASE\_URL", f"sqlite:///{DATA\_PATH}")
\# se for SQLite não precisa de sslmode
connect\_args = {}
if url.startswith("postgres") or url.startswith("mysql"):
connect\_args = {"sslmode": "require"}
engine = create\_engine(url, connect\_args=connect\_args)
return engine.connect()

# conexão única e cacheada

conn = get\_db()

# define o cursor para executar SQL puros

cursor = conn.connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS clients (
username       TEXT PRIMARY KEY,
password\_hash  TEXT NOT NULL,
cnpj           TEXT NOT NULL,
celular        TEXT NOT NULL,
email          TEXT NOT NULL,
plano          TEXT NOT NULL,      -- aqui a nova coluna
created\_at     TEXT NOT NULL
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS proposals (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nome\_cliente       TEXT,
cnpj                TEXT,
valor\_nota          REAL,
taxa\_ia             REAL,
taxa\_cliente        REAL,
deseja\_contato      TEXT,
telefone\_contato    TEXT,
email\_contato       TEXT,
created\_at          TEXT
)
""")
conn.commit()

# 4) Funções de registro/autenticação usando o hash

def register\_client(username, password, cnpj, celular, email, plano):
pwd\_hash = hash\_password(password)
try:
cursor.execute(
"""
INSERT INTO clients
(username, password\_hash, cnpj, celular, email, plano, created\_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
""",
(
username,
pwd\_hash,
cnpj,
celular,
email,
plano,                        # <-- aqui
datetime.now().isoformat()
)
)
conn.commit()
return True
except sqlite3.IntegrityError:
\# Usuário já existe
return False
except sqlite3.Error as e:
st.error(f"Erro no banco de dados: {e}")
return False

def authenticate\_client(username, password):
cursor.execute("SELECT password\_hash FROM clients WHERE username = ?", (username,))
row = cursor.fetchone()
if row and row\[0] == hash\_password(password):
return True
return False

if 'role' not in st.session\_state:
st.title("🔐 Bem-vindo a All Way Capital")
modo = st.radio("Escolha:", \["Entrar", "Cadastrar-se"])
if modo == "Cadastrar-se":
with st.form("form\_register"):
\# Dados de acesso e perfil
u       = st.text\_input("Usuário")
p       = st.text\_input("Senha", type="password")
p2      = st.text\_input("Confirme a senha", type="password")
cnpj    = st.text\_input("CNPJ")
celular = st.text\_input("Celular")
email   = st.text\_input("Email")
\# --- dentro do st.form("form\_register"), logo após o selectbox de plano ---
plano = st.selectbox(
"Selecione um plano de assinatura",
\[
"Básico – R\$ 699,90",
"Intermediário – R\$ 1.299,90",
"Avançado – R\$ 1.999,90"
]
)

```
# NOVO: periodicidade de cobrança
        periodicidade = st.selectbox(
            "Periodicidade de cobrança",
            ["Mensal", "Anual (10% de desconto)"]
        )

# cálculo do preço final
        preco_mensal = float(plano.split("R$")[1].replace(".", "").replace(",", "."))
        if periodicidade == "Mensal":
            preco_final = preco_mensal
        else:
            preco_final = preco_mensal * 12 * 0.9  # 10% de desconto no anual

        st.markdown(
            f"**Valor a pagar ({periodicidade.lower()}):** "
            f"R$ {preco_final:,.2f}"
            .replace(",", "X").replace(".", ",").replace("X", ".")
        )


    st.markdown("---")
    st.subheader("Dados do Cartão de Crédito")

    # Número e nome
    cc_number = st.text_input(
        "Número do Cartão",
        placeholder="0000 0000 0000 0000",
        max_chars=19
    )
    cc_name = st.text_input("Nome impresso no cartão")

    # Validade e CVV
    col1, col2, col3 = st.columns([2,2,1])
    with col1:
        mes = st.selectbox("Mês de validade", [f"{m:02d}" for m in range(1,13)])
    with col2:
        ano = st.selectbox("Ano de validade", [str(y) for y in range(datetime.now().year, datetime.now().year+10)])
    with col3:
        cvv = st.text_input("CVV", type="password", max_chars=4)

    # Parcelamento
    parcelas = st.selectbox(
        "Número de parcelas",
        list(range(1, 13))
    )

    # Juros por faixa de parcelas (exemplo)
    juros_tabela = {
        1: 0.00, 2: 0.00, 3: 0.00,
        4: 0.015, 5: 0.020, 6: 0.025,
        7: 0.030, 8: 0.035, 9: 0.040,
        10: 0.045, 11: 0.050, 12: 0.055
    }
    juros = juros_tabela[parcelas]

    # Extrai valor numérico do plano
    preco_plano = float(plano.split("R$")[1].replace(".", "").replace(",", "."))

    total_com_juros = preco_plano * (1 + juros)
    valor_parcela = total_com_juros / parcelas

    st.write(f"**Juros:** {juros*100:.1f}%")
    st.write(f"**Total a ser cobrado:** R$ {total_com_juros:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.write(f"**{parcelas}x de:** R$ {valor_parcela:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    ok = st.form_submit_button("Criar conta e pagar")

if ok:
    # aqui você deve validar todos os campos, processar o pagamento via gateway e só então:
    if not all([u, p, p2, cnpj, celular, email, cc_number, cc_name, mes, ano, cvv]):
        st.error("Preencha todos os campos do cadastro e do cartão")
    elif p != p2:
        st.error("As senhas não coincidem")
    else:
        # Exemplo: processar pagamento antes de registrar
        pagamento_sucesso = True  # <- substitua pela chamada ao seu gateway

        if pagamento_sucesso and register_client(u, p, cnpj, celular, email, plano):
            st.success(f"Conta criada! Plano: {plano} em {parcelas}x")
        else:
            st.error("Falha no pagamento ou usuário já existe.")
st.stop()



else:  # Entrar
    with st.form("form_login"):
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        ok = st.form_submit_button("Entrar")
    if ok:
        # admin via secrets
        if u == st.secrets["ADMIN"]["USERNAME"] and p == st.secrets["ADMIN"]["PASSWORD"]:
            st.session_state.role = 'admin'
        # cliente via DB
        elif authenticate_client(u, p):
            st.session_state.role = 'cliente'
            st.session_state.username = u
        else:
            st.error("Usuário ou senha inválidos")
    st.stop()
    
```

def formatar\_moeda(valor):
"""
Formata valor numérico como moeda brasileira.
"""
try:
return f"R\$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
except:
return f"R\$ {valor:.2f}".replace(".", ",")
def calcular\_preco\_minimo(custo\_base, risco\_inadimplencia, margem\_desejada\_percentual):
"""
Calcula o preço mínimo com base no custo, risco e margem desejada.
"""
ajuste\_risco = 1 + risco\_inadimplencia
margem = 1 + (margem\_desejada\_percentual / 100)
return custo\_base \* ajuste\_risco \* margem

def clean\_text(text):
"""
Normaliza texto para evitar problemas de codificação no PDF.
"""
return unicodedata.normalize('NFKD', text).encode('latin1', 'ignore').decode('latin1')

def gerar\_pdf(data\_dict,
grafico\_risco\_bytes,
grafico\_fatores\_bytes,
grafico\_dist\_bytes,
preco\_melhor,
preco\_pior,
alerta\_text,
resumo,
adequacao\_text):
pdf = FPDF()
\# Página título e dados básicos
pdf.add\_page()
pdf.set\_font("Arial", size=12)
pdf.cell(200, 10, txt="Relatório de Precificação e Risco de Crédito", ln=True, align='C')
pdf.ln(10)
for chave, valor in data\_dict.items():
pdf.cell(0, 8, txt=clean\_text(f"{chave}: {valor}"), ln=True)
pdf.ln(5)
\# Explicação simples
pdf.set\_font("Arial", style='I', size=11)
texto\_inf = (
"Como a IA chegou no preço mínimo?\n"
"- Considera o valor do empréstimo e protege-se do risco.\n"
"- Adiciona margem de lucro para garantir rentabilidade.\n"
"- Oferece preço justo, seguro e vantajoso para todos."
)
pdf.multi\_cell(0, 8, clean\_text(texto\_inf))
\# Gráfico Risco x Retorno
pdf.add\_page()
pdf.set\_font("Arial", style='B', size=12)
pdf.cell(0, 10, txt="Análise de Risco x Retorno", ln=True)
if grafico\_risco\_bytes:
with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
tmp.write(grafico\_risco\_bytes.getvalue())
caminho = tmp.name
pdf.image(caminho, w=180)
pdf.ln(5)
pdf.set\_font("Arial", size=11)
texto\_graf1 = (
"Este gráfico mostra como o risco de inadimplência (eixo horizontal) se relaciona ao retorno esperado em R\$.\n"
"- Área verde (0% a 30%): baixo risco e potencial de retorno estável.\n"
"- Área amarela (30% a 60%): risco intermediário; atenção ao investimento.\n"
"- Área vermelha (60% a 100%): alto risco; retorno incerto."
)
pdf.multi\_cell(0, 8, clean\_text(texto\_graf1))
\# Gráfico Fatores
pdf.add\_page()
pdf.set\_font("Arial", style='B', size=12)
pdf.cell(0, 10, txt="Fatores de Risco", ln=True)
if grafico\_fatores\_bytes:
with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
tmp.write(grafico\_fatores\_bytes.getvalue())
caminho = tmp.name
pdf.image(caminho, w=180)
pdf.ln(5)
pdf.set\_font("Arial", size=11)
texto\_graf2 = (
"Este gráfico de barras indica a contribuição percentual de cada fator para o risco total:\n"
"- Rating: confiabilidade de crédito do cliente.\n"
"- Idade da empresa: maturidade de mercado.\n"
"- Protestos: histórico de dívidas.\n"
"- Faturamento: solidez financeira."
)
pdf.multi\_cell(0, 8, clean\_text(texto\_graf2))
\# Distribuição de Risco
pdf.add\_page()
pdf.set\_font("Arial", style='B', size=12)
pdf.cell(0, 10, txt="Distribuição de Risco (Simulações)", ln=True)
if grafico\_dist\_bytes:
with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
tmp.write(grafico\_dist\_bytes.getvalue())
caminho = tmp.name
pdf.image(caminho, w=180)
pdf.ln(5)
pdf.set\_font("Arial", size=11)
texto\_graf3 = (
"Este histograma mostra a frequência dos níveis de risco em 500 simulações aleatórias.\n"
"A linha vertical destaca o seu risco calculado, permitindo comparar com a média das simulações."
)
pdf.multi\_cell(0, 8, clean\_text(texto\_graf3))
\# Cenários
pdf.add\_page()
pdf.set\_font("Arial", style='B', size=12)
pdf.cell(0, 10, txt="Cenários: Melhor vs. Pior Caso", ln=True)
pdf.set\_font("Arial", size=11)
pdf.multi\_cell(0, 8, clean\_text(
f"Com base no mesmo valor de operação, o melhor cenário (risco 0%) gera preço {preco\_melhor}, "
f"enquanto o pior cenário (risco 100%) gera {preco\_pior}."
))
\# Alerta Outlier
pdf.add\_page()
pdf.set\_font("Arial", style='B', size=12)
pdf.cell(0, 10, txt="Alerta de Outlier", ln=True)
pdf.set\_font("Arial", size=11)
pdf.multi\_cell(0, 8, clean\_text(alerta\_text))
\# Resumo Executivo e Adequação
pdf.add\_page()
pdf.set\_font("Arial", style='B', size=12)
pdf.cell(0, 10, txt="Resumo Executivo", ln=True)
pdf.set\_font("Arial", size=11)
pdf.multi\_cell(0, 8, clean\_text(resumo))
pdf.ln(5)
pdf.set\_font("Arial", style='B', size=12)
pdf.cell(0, 10, txt="Adequação ao Apetite de Risco", ln=True)
pdf.set\_font("Arial", size=11)
pdf.multi\_cell(0, 8, clean\_text(adequacao\_text))
return BytesIO(pdf.output(dest='S').encode('latin1'))

# Interface de Análise de Risco (sem Serasa)

def exibir\_interface\_analise\_risco():
st.header("Análise de Risco e Precificação")
client = OpenAI(api\_key=st.secrets\["OPENAI\_API\_KEY"])

```
with st.form("form_operacao"):
    st.subheader("Dados da Operação")
    nome_cliente    = st.text_input("Nome do cliente")
    cnpj_cliente    = st.text_input("CNPJ do cliente (opcional)")
    valor           = st.number_input("Valor da operação (R$)", min_value=0.0, format="%.2f")
    data_operacao   = st.date_input("Data da operação", value=datetime.today(), format="DD/MM/YYYY")
    data_vencimento = st.date_input("Data de vencimento", format="DD/MM/YYYY")
    margem_desejada = st.number_input("Margem desejada (%)", min_value=0.0, value=1.0)
    custo_capital   = st.number_input("Custo do capital (%)", min_value=0.0, value=1.5)

    st.markdown("### Dados de Crédito (manual)")
    score_serasa   = st.number_input("Score de Crédito (0 a 1000)", 0, 1000, 750)
    idade_empresa  = st.number_input("Idade da empresa (anos)", 0, 100, 5)
    protestos_bool = st.selectbox("Protestos ou dívidas públicas?", ["Não", "Sim"]) == "Sim"
    faturamento    = st.number_input("Último faturamento (R$)", min_value=0.0, format="%.2f")

    enviar = st.form_submit_button("Simular")
    if not enviar:
        return

    # 1) Cálculo do prazo
    prazo = (data_vencimento - data_operacao).days

    # 2) Componentes de risco (mesma lógica da aba de cotação)
    risco_score = 0 if score_serasa >= 800 else 0.5 if score_serasa >= 600 else 1
    risco_idade = 0 if idade_empresa >= 5 else 0.5
    risco_protesto = 1 if protestos_bool else 0
    risco_fat = 0 if faturamento >= 500000 else 0.5

    # 3) Risco total em %, ponderado
    risco_total = round(
        (risco_score    * 0.40
       + risco_idade    * 0.20
       + risco_protesto * 0.25
       + risco_fat      * 0.15)
       * 100,
    2)

    # 4) Determinação do nível de risco
    cor = "🟢 Baixo" if risco_total <= 30 else "🟡 Moderado" if risco_total <= 60 else "🔴 Alto"

    # 5) Taxa sugerida pela IA = 10% do risco_total
    taxa_ia = round(risco_total * 0.1, 2)

    # 6) Valor a receber descontando essa taxa
    valor_receber = round(valor * (1 - taxa_ia/100), 2)

    # 7) Exibição dos resultados
    st.markdown("## Resultado da Simulação")
    st.write(f"Prazo: {prazo} dias")
    st.markdown(
        f"<p style='font-size:24px; font-weight:bold; margin:10px 0;'>"
        f"🔥 Taxa sugerida pela IA: {taxa_ia}%</p>",
        unsafe_allow_html=True
    )
    st.metric("Você receberá", formatar_moeda(valor_receber))
    st.write(f"Risco: {cor} ({risco_total}%)")
```

# Interface de Cotação de Crédito via XML (sem Serasa)

def exibir\_interface\_cliente\_cotacao():
st.header("Cotação de Antecipação de Crédito")
user\_tel, user\_email = "", ""
try:
cursor.execute("SELECT celular, email FROM clients WHERE username = ?", (st.session\_state.username,))
row = cursor.fetchone()
if row:
user\_tel, user\_email = row
except Exception:
pass
st.write("Faça o upload do **XML da Nota Fiscal Eletrônica (NF-e)** para gerar sua cotação:")
nome\_cliente = st.text\_input("Nome do cliente", key="xml\_nome\_cliente")

```
xml_file = st.file_uploader("Upload do XML", type=["xml"])
if xml_file is not None:
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

        valor_nota = float(root.find('.//nfe:vNF', ns).text.replace(",", "."))
        cnpj_dest  = root.find('.//nfe:CNPJ', ns).text
        data_emissao_tag = root.find('.//nfe:dhEmi', ns)
        data_emissao = None
        if data_emissao_tag is not None:
            raw = data_emissao_tag.text[:10]
            date_obj = datetime.strptime(raw, "%Y-%m-%d")
            data_emissao = date_obj.strftime("%d/%m/%Y")

            parcelas = []
            cobr = root.find('.//nfe:cobr', ns)
        if cobr is not None:
            for dup in cobr.findall('nfe:dup', ns):
                numero = dup.find('nfe:nDup', ns).text if dup.find('nfe:nDup', ns) is not None else None
                raw_venc = dup.find('nfe:dVenc', ns).text
                data_venc = datetime.strptime(raw_venc[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
                raw_val = dup.find('nfe:vDup', ns).text.replace(",", ".")
                valor_dup = float(raw_val)
                parcelas.append({
                    "nDup": numero,
                    "dVenc": data_venc,
                    "vDup": formatar_moeda(valor_dup)
            })

        with st.expander("Detalhes da Nota", expanded=False):
            st.write(f"**Valor da nota fiscal:** {formatar_moeda(valor_nota)}")
            st.write(f"**CNPJ do cliente:** {cnpj_dest}")
            if data_emissao:
                st.write(f"**Data de emissão:** {data_emissao}")
            if parcelas:
                st.markdown("**Parcelas e vencimentos:**")
                for p in parcelas:
                    num = f"Parcela {p['nDup']}: " if p['nDup'] else ""
                    st.write(f"- {num}{p['dVenc']} → {p['vDup']}")

        st.markdown("### Dados de Crédito (manual)")
        score_xml     = st.number_input("Score de Crédito (0 a 1000)", 0, 1000, 750, key="xml_score")
        idade_empresa = st.number_input("Idade da empresa (anos)", 0, 100, 5, key="xml_idade")
        protestos     = st.selectbox("Protestos ou dívidas públicas?", ["Não", "Sim"], key="xml_protestos")
        faturamento   = st.number_input("Último faturamento (R$)", min_value=0.0, format="%.2f", key="xml_fat")

        # Cálculo do risco total
        risco_score = round(1 / (1 + math.exp(-(600 - score_xml) / 50)), 3)
        risco_idade = round(1 / (1 + math.exp(-(5 - idade_empresa) / 1)), 3)
        risco_protesto = 1 if protestos == "Sim" else 0
        risco_fat = round(1 / (1 + math.exp(-(500_000 - faturamento) / 100_000)), 3)
        risco_total = round(
            (risco_score    * 0.40
            + risco_idade   * 0.20
            + risco_protesto* 0.25
            + risco_fat     * 0.15)
            * 100,
            2
        )

        suggested_taxa = round(risco_total, 2)
        
        taxa_ia = round(risco_total * 0.1, 2)
        st.markdown(
            f"<p style='font-size:24px; font-weight:bold; margin:10px 0;'>🔥 Taxa sugerida pela IA: {taxa_ia}%</p>",
            unsafe_allow_html=True
        )

# campo editável para o cliente definir a taxa de antecipação
        taxa_cliente = st.number_input(
            "Defina a taxa de antecipação (%)",
            min_value=0.0,
            max_value=10.0,
            step=0.1,
            value=taxa_ia,
            format="%.2f"
        )

# cálculo do valor a receber com a taxa escolhida pelo cliente
        valor_receber = valor_nota * (1 - taxa_cliente/100)
        st.metric("Você receberá", f"{formatar_moeda(valor_receber)}")

        st.write("Este cálculo não leva em consideração dados de concentração de carteira e eventuais riscos que não apareçam no Serasa")

        receber_propostas = st.checkbox(
            "Desejo receber propostas e que entrem em contato comigo"
        )

        if receber_propostas:
            telefone_contato = st.text_input(
                "Telefone para contato",
                value=user_tel,
                key="telefone_contato"
            )
            email_contato = st.text_input(
                "E-mail para contato",
                value=user_email,
                key="email_contato"
            )
        
        if st.button("Solicitar proposta", key="xml_solicitar"):
            msg_body = (
                  f"📩 *Nova solicitação de proposta*\n"
                f"• Cliente: {nome_cliente}\n"
                f"• CNPJ: {cnpj_dest}\n"
                f"• Valor da NF-e: {formatar_moeda(valor_nota)}\n"
                f"• Emissão: {data_emissao or '—'}\n"
                f"• Taxa IA sugerida: {taxa_ia}%\n"
                f"• Taxa escolhida: {taxa_cliente}%\n"
            )
            
            if parcelas:
                msg_body += "• Parcelas:\n"
                for p in parcelas:
                    num = f"{p['nDup']}. " if p['nDup'] else ""
                    msg_body += f"   – {num}{p['dVenc']} → {p['vDup']}\n"

            contato = "SIM" if receber_propostas else "NÃO"
            msg_body += f"• Deseja contato: {contato}\n"

            if receber_propostas:
                msg_body += f"• Telefone para contato: {telefone_contato}\n"
                msg_body += f"• E-mail para contato: {email_contato}\n"
            client = Client(
                st.secrets["TWILIO_ACCOUNT_SID"],
                st.secrets["TWILIO_AUTH_TOKEN"]
            )
            client.messages.create(
                body=msg_body,
                from_=f"whatsapp:{st.secrets['TWILIO_WHATSAPP_FROM']}",
                to  =f"whatsapp:{st.secrets['ADMIN_WHATSAPP_TO']}"
            )
            st.success("✅ Proposta enviada!")
            cursor.execute(
                """
                INSERT INTO proposals
                  (nome_cliente, cnpj, valor_nota, taxa_ia, taxa_cliente,
                   deseja_contato, telefone_contato, email_contato, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    nome_cliente,
                    cnpj_dest,
                    valor_nota,
                    taxa_ia,
                    taxa_cliente,
                    contato,
                    telefone_contato,   # <- adiciona aqui
                    email_contato,      # <- e aqui
                    datetime.now().isoformat()
                )
            )
            conn.commit()

    except Exception as e:
        st.error(f"Erro ao processar o XML: {e}")
            
```

# --- Roteamento pós-login ---

if st.session\_state.role == 'admin':
st.header("📋 Propostas Recebidas (Admin)")
if os.path.exists(DATA\_PATH):
conn = sqlite3.connect(DATA\_PATH, check\_same\_thread=False)
df = pd.read\_sql\_query(
"""
SELECT
p.id                   AS "ID",
c.username             AS "Nome da Empresa",
p.telefone\_contato     AS "Telefone",
p.email\_contato        AS "E-mail",
p.nome\_cliente         AS "Nome no XML",
p.cnpj                 AS "CNPJ (NF-e)",
p.valor\_nota           AS "Valor NF-e",
p.taxa\_ia              AS "Taxa IA (%)",
p.taxa\_cliente         AS "Taxa Cliente (%)",
p.deseja\_contato       AS "Deseja Contato",
p.created\_at           AS "Solicitado em"
FROM proposals p
LEFT JOIN clients c
ON p.cnpj = c.cnpj
ORDER BY p.created\_at DESC

```
        """,
        conn
    )
    st.dataframe(df)
else:
    st.info("Ainda não há propostas.")
```

elif st.session\_state.role == 'cliente':
st.header("👤 Dashboard do Cliente")
tab1, tab2 = st.tabs(\["💰 Cotação de Antecipação", "⚙️ Análise de Risco"])
with tab1:
exibir\_interface\_cliente\_cotacao()
with tab2:
exibir\_interface\_analise\_risco()

# Configuração de localização para formatação brasileira

try:
locale.setlocale(locale.LC\_ALL, 'pt\_BR.UTF-8')
except:
locale.setlocale(locale.LC\_ALL, '')  # fallback

st.stop()
