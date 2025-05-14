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
from sqlalchemy import create_engine, text
import streamlit as st 
from io import StringIO
import sqlite3
import os
DATA_PATH = "clientes.db" 
# Dicionário com permissões por plano de assinatura
# Permissões por plano
PERMISSOES_POR_PLANO = {
    "Básico": ["cotacao"],
    "Intermediário": ["cotacao", "propostas"],
    "Avançado": ["cotacao", "propostas", "analise_risco", "pdf", "serasa"]
}


# — DEV: zera o .db para forçar recriação com esquema correto —
 
st.set_page_config(page_title="Simulação Antecipação", layout="centered")

if not os.path.exists(DATA_PATH):
    conn = sqlite3.connect(DATA_PATH, check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE proposals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_cliente TEXT,
        cnpj TEXT,
        valor_nota REAL,
        taxa_ia REAL,
        taxa_cliente REAL,
        deseja_contato TEXT,
        telefone_contato TEXT,
        email_contato TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        cnpj TEXT,
        celular TEXT,
        email TEXT,
        plano TEXT,
        created_at TEXT
    )
    """)

    conn.commit()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def register_client(username, password, cnpj, celular, email, plano):
    pwd_hash = hash_password(password)
    try:
        cursor.execute(
            """
            INSERT INTO clients
            (username, password_hash, cnpj, celular, email, plano, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (username, pwd_hash, cnpj, celular, email, plano, datetime.now().isoformat())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        st.error(f"Erro no banco de dados: {e}")
        return False

def authenticate_client(username, password):
    cursor.execute("SELECT password_hash FROM clients WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row and row[0] == hash_password(password):
        return True
    return False
    
    # Conexão com o banco de dados (se ainda não estiver criado)
conn = sqlite3.connect(DATA_PATH, check_same_thread=False)
cursor = conn.cursor()

# Verifica as colunas existentes da tabela 'proposals'
cursor.execute("PRAGMA table_info(proposals)")
info = cursor.fetchall()
colunas = [col[1] for col in info]  # aqui nasce a variável 'colunas'

# Adiciona 'telefone_contato' se não existir
if 'telefone_contato' not in colunas:
    try:
        cursor.execute("ALTER TABLE proposals ADD COLUMN telefone_contato TEXT")
    except sqlite3.OperationalError:
        pass  # ignora se já existir

# Adiciona 'email_contato' se não existir
if 'email_contato' not in colunas:
    try:
        cursor.execute("ALTER TABLE proposals ADD COLUMN email_contato TEXT")
    except sqlite3.OperationalError:
        pass

conn.commit()

# --- Fim da conexão SQLite ---


# --- Navegação inicial via simulação ---
if 'navigate' not in st.session_state:
    st.session_state['navigate'] = None

if st.session_state.navigate == "register":
    # fluxo principal irá lidar com cadastro
    pass
elif st.session_state.navigate == "login":
    # fluxo principal irá lidar com login
    pass
else:
    # Página Inicial (antes do login)
    # --- Estilos ---
    st.markdown("""
    <style>
      .stApp { background-color: #FFFFFF; }
      .header { font-size: 36px; font-weight: bold; text-align: center; margin-bottom: 10px; }
      .subheader { font-size: 18px; text-align: center; margin-bottom: 30px; color: #555555; }
      .resultado { background-color: #E3F2FD; padding: 20px; border-radius: 8px; text-align: center; margin-top: 20px; }
      .cta { background-color: #0D47A1; color: white; padding: 15px; border-radius: 5px; text-align: center; margin-top: 30px; width: 100%; }
      .cta:hover { background-color: #1565C0; }
    </style>
    """, unsafe_allow_html=True)

    # --- Cabeçalho ---
    st.markdown('<div class="header">Antecipe agora. Sem compromisso.</div>', unsafe_allow_html=True)
    st.markdown('<div class="subheader">Envie uma nota fiscal eletrônica (.XML) e descubra agora quanto você pode antecipar.</div>', unsafe_allow_html=True)

    # --- Upload de XML ---
    xml_files = st.file_uploader("Escolha seus arquivos XML", type=["xml"], accept_multiple_files=True)

    valor_total = 0
    if xml_files:
        for xml_file in xml_files:
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
                valor_nota = float(root.find('.//nfe:vNF', ns).text.replace(',', '.'))
                valor_receber = valor_nota * (1 - 2.2 / 100)
                valor_total += valor_nota

                st.markdown('<div class="resultado">', unsafe_allow_html=True)
                st.markdown(f"**Arquivo:** {xml_file.name}", unsafe_allow_html=True)
                st.markdown(f"**Valor da nota:** R$ {valor_nota:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), unsafe_allow_html=True)
                st.markdown(f"**Taxa sugerida:** 2,2%", unsafe_allow_html=True)
                st.markdown(f"**Valor a receber:** R$ {valor_receber:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Erro ao processar {xml_file.name}: {e}")
        valor_total_receber = valor_total * (1 - 2.2 / 100)

        st.markdown("""
        <div style='background-color:#E3F2FD; padding: 20px; border-radius: 10px; margin-top: 20px; text-align:center;'>
            <p style='font-size:22px; font-weight:bold; margin-bottom:10px;'>📄 Valor total das notas:</p>
            <p style='font-size:28px; color:#0D47A1; font-weight:bold;'>R$ {valor_total}</p>

            <p style='font-size:22px; font-weight:bold; margin-top:20px;'>📊 Taxa da IA aplicada:</p>
            <p style='font-size:26px; color:#F57C00; font-weight:bold;'>{taxa_ia}%</p>

            <p style='font-size:22px; font-weight:bold; margin-top:20px;'>💸 Valor total a receber:</p>
            <p style='font-size:28px; color:#2E7D32; font-weight:bold;'>R$ {valor_receber}</p>
        </div>
        """.format(
            valor_total=f"{valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            valor_receber=f"{valor_total_receber:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            taxa_ia=f"{taxa_ia:.2f}".replace(".", ",")
        ), unsafe_allow_html=True)



    else:
        st.info('Faça upload de um ou mais XMLs para começar a simulação.')


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

st.markdown(
    """
    <style>
      /* Botões padrão e elementos de ação */
      .stButton > button,
      button,
      [data-testid="stToolbar"],
      .css-1offfwp.edgvbvh3 {            /* classe genérica de botões */
        background-color: #0D47A1 !important;  /* azul escuro */
        color: #FFFFFF     !important;  /* texto branco */
      }

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
)



def authenticate_client(username, password):
    cursor.execute("SELECT password_hash FROM clients WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row and row[0] == hash_password(password):
        return True
    return False

ok_register = False
if 'role' not in st.session_state:
    st.title("🔐 Seja bem vindo a Confiança")
    modo = st.radio("Escolha:", ["Entrar", "Cadastrar-se"])
    if modo == "Cadastrar-se":
       with st.form("form_register"):
    # Dados de acesso e perfil
            u       = st.text_input("Usuário")
            p       = st.text_input("Senha", type="password")
            p2      = st.text_input("Confirme a senha", type="password")
            cnpj    = st.text_input("CNPJ")
            celular = st.text_input("Celular")
            email   = st.text_input("Email")

            plano = st.selectbox(
               "Preço plano de assinatura",
                [
                    "Básico – R$ 99,90",
                    "Intermediário – R$ 299,90",
                    "Avançado – R$ 499,90"
                ]
            )

            periodicidade = st.selectbox(
                "Renovação do Plano",
                ["Mensal", "Anual - 10% de desconto"]
            )

            preco_mensal = float(plano.split("R$")[1].replace(".", "").replace(",", "."))
            preco_final = preco_mensal if periodicidade == "Mensal" else preco_mensal * 12 * 0.9

            st.markdown(
                f"**Valor a pagar ({periodicidade.lower()}):** R$ {preco_final:,.2f}"
                .replace(",", "X").replace(".", ",").replace("X", "."),
                unsafe_allow_html=True
            )

    # Agora os campos de cartão de crédito estão dentro do form!
            st.subheader("Dados do Cartão de Crédito")

            cc_number = st.text_input(
                "Número do Cartão",
                placeholder="0000 0000 0000 0000",
                max_chars=19
            )
            cc_name = st.text_input("Nome impresso no cartão")

            col1, col2, col3 = st.columns([2,2,1])
            with col1:
                mes = st.selectbox("Mês de validade", [f"{m:02d}" for m in range(1,13)])
            with col2:
                ano = st.selectbox("Ano de validade", [str(y) for y in range(datetime.now().year, datetime.now().year+10)])
            with col3:
                cvv = st.text_input("CVV", type="password", max_chars=4)

            # ✅ Botão dentro do form, agora funciona perfeitamente
            ok_register = st.form_submit_button("Criar conta e pagar")
        # Extrai valor numérico do plano

   

    if ok_register:
        # aqui você deve validar todos os campos, processar o pagamento via gateway e só então:
        if not all([u, p, p2, cnpj, celular, email, cc_number, cc_name, mes, ano, cvv]):
            st.error("Preencha todos os campos do cadastro e do cartão")
        elif p != p2:
            st.error("As senhas não coincidem")
        else:
            # Exemplo: processar pagamento antes de registrar
            pagamento_sucesso = True  # <- substitua pela chamada ao seu gateway

            if pagamento_sucesso and register_client(u, p, cnpj, celular, email, plano):
                st.success(f"Conta criada! Plano: {plano} – Cobrança: {periodicidade}")

            else:
                st.error("Falha no pagamento ou usuário já existe.")

    elif modo == "Entrar":  # Entrar
        with st.form("form_login"):
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            ok_login = st.form_submit_button("Entrar")
        if ok_login:
            # admin via secrets
            if u == st.secrets["ADMIN"]["USERNAME"] and p == st.secrets["ADMIN"]["PASSWORD"]:
                st.session_state.role = 'admin'
            # cliente via DB
            elif authenticate_client(u, p):
                cursor.execute("SELECT plano FROM clients WHERE username = ?", (u,))
                row = cursor.fetchone()
                if row:
                    plano_completo = row[0]  # Ex: "Intermediário – R$ 299,90"
                    plano_limpo = plano_completo.split("–")[0].strip()  # Fica só "Intermediário"
                    st.session_state.role = 'cliente'
                    st.session_state.username = u
                    st.session_state.plano = plano_limpo
                else:
                    st.error("Plano de assinatura não encontrado.")

        else:
            st.error("Usuário ou senha inválidos")
    st.stop()
        
def formatar_moeda(valor):
    """
    Formata valor numérico como moeda brasileira.
    """
    try:
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except:
        return f"R$ {valor:.2f}".replace(".", ",")
def calcular_preco_minimo(custo_base, risco_inadimplencia, margem_desejada_percentual):
    """
    Calcula o preço mínimo com base no custo, risco e margem desejada.
    """
    ajuste_risco = 1 + risco_inadimplencia
    margem = 1 + (margem_desejada_percentual / 100)
    return custo_base * ajuste_risco * margem

def clean_text(text):
    """
    Normaliza texto para evitar problemas de codificação no PDF.
    """
    return unicodedata.normalize('NFKD', text).encode('latin1', 'ignore').decode('latin1')

def gerar_pdf(data_dict,
               grafico_risco_bytes,
               grafico_fatores_bytes,
               grafico_dist_bytes,
               preco_melhor,
               preco_pior,
               alerta_text,
               resumo,
               adequacao_text):
    pdf = FPDF()
    # Página título e dados básicos
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatório de Precificação e Risco de Crédito", ln=True, align='C')
    pdf.ln(10)
    for chave, valor in data_dict.items():
        pdf.cell(0, 8, txt=clean_text(f"{chave}: {valor}"), ln=True)
    pdf.ln(5)
    # Explicação simples
    pdf.set_font("Arial", style='I', size=11)
    texto_inf = (
        "Como a IA chegou no preço mínimo?\n"
        "- Considera o valor do empréstimo e protege-se do risco.\n"
        "- Adiciona margem de lucro para garantir rentabilidade.\n"
        "- Oferece preço justo, seguro e vantajoso para todos."
    )
    pdf.multi_cell(0, 8, clean_text(texto_inf))
    # Gráfico Risco x Retorno
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, txt="Análise de Risco x Retorno", ln=True)
    if grafico_risco_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(grafico_risco_bytes.getvalue())
            caminho = tmp.name
        pdf.image(caminho, w=180)
        pdf.ln(5)
    pdf.set_font("Arial", size=11)
    texto_graf1 = (
        "Este gráfico mostra como o risco de inadimplência (eixo horizontal) se relaciona ao retorno esperado em R$.\n"
        "- Área verde (0% a 30%): baixo risco e potencial de retorno estável.\n"
        "- Área amarela (30% a 60%): risco intermediário; atenção ao investimento.\n"
        "- Área vermelha (60% a 100%): alto risco; retorno incerto."
    )
    pdf.multi_cell(0, 8, clean_text(texto_graf1))
    # Gráfico Fatores
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, txt="Fatores de Risco", ln=True)
    if grafico_fatores_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(grafico_fatores_bytes.getvalue())
            caminho = tmp.name
        pdf.image(caminho, w=180)
        pdf.ln(5)
    pdf.set_font("Arial", size=11)
    texto_graf2 = (
        "Este gráfico de barras indica a contribuição percentual de cada fator para o risco total:\n"
        "- Rating: confiabilidade de crédito do cliente.\n"
        "- Idade da empresa: maturidade de mercado.\n"
        "- Protestos: histórico de dívidas.\n"
        "- Faturamento: solidez financeira."
    )
    pdf.multi_cell(0, 8, clean_text(texto_graf2))
    # Distribuição de Risco
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, txt="Distribuição de Risco (Simulações)", ln=True)
    if grafico_dist_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(grafico_dist_bytes.getvalue())
            caminho = tmp.name
        pdf.image(caminho, w=180)
        pdf.ln(5)
    pdf.set_font("Arial", size=11)
    texto_graf3 = (
        "Este histograma mostra a frequência dos níveis de risco em 500 simulações aleatórias.\n"
        "A linha vertical destaca o seu risco calculado, permitindo comparar com a média das simulações."
    )
    pdf.multi_cell(0, 8, clean_text(texto_graf3))
    # Cenários
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, txt="Cenários: Melhor vs. Pior Caso", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 8, clean_text(
        f"Com base no mesmo valor de operação, o melhor cenário (risco 0%) gera preço {preco_melhor}, "
        f"enquanto o pior cenário (risco 100%) gera {preco_pior}."
    ))
    # Alerta Outlier
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, txt="Alerta de Outlier", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 8, clean_text(alerta_text))
    # Resumo Executivo e Adequação
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, txt="Resumo Executivo", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 8, clean_text(resumo))
    pdf.ln(5)
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, txt="Adequação ao Apetite de Risco", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 8, clean_text(adequacao_text))
    return BytesIO(pdf.output(dest='S').encode('latin1'))

# Interface de Análise de Risco (sem Serasa)
def exibir_interface_analise_risco():
    st.header("Análise de Risco e Precificação")
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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



# Interface de Cotação de Crédito via XML (sem Serasa)
def exibir_interface_cliente_cotacao(permissoes):
    st.header("Cotação de Antecipação de Crédito")
    user_tel, user_email = "", ""
    try:
        cursor.execute("SELECT celular, email FROM clients WHERE username = ?", (st.session_state.username,))
        row = cursor.fetchone()
        if row:
            user_tel, user_email = row
    except Exception:
        pass

    st.write("Faça o upload do **XML da Nota Fiscal Eletrônica (NF-e)** para gerar sua cotação:")
    nome_cliente = st.text_input("Nome do cliente", key="xml_nome_cliente")
    xml_files = st.file_uploader("Upload de XMLs", type=["xml"], accept_multiple_files=True)

    if xml_files:
        for xml_file in xml_files:
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

                st.markdown("----")
                st.subheader(f"🧾 Nota: {xml_file.name}")
                st.write(f"Valor: {formatar_moeda(valor_nota)}")
                st.write(f"CNPJ: {cnpj_dest}")
                if data_emissao:
                    st.write(f"Data de emissão: {data_emissao}")

            except Exception as e:
                st.error(f"Erro ao processar {xml_file.name}: {e}")

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

            taxa_ia = round(risco_total * 0.1, 2)
            taxa_cliente = st.number_input(
                "Defina a taxa de antecipação (%)",
                min_value=0.0,
                max_value=10.0,
                step=0.1,
                value=taxa_ia,
                format="%.2f"
            )
            valor_receber = valor_nota * (1 - taxa_cliente/100)
            st.metric("Você receberá", f"{formatar_moeda(valor_receber)}")
            st.write("Este cálculo não leva em consideração dados de concentração de carteira e eventuais riscos que não apareçam no Serasa")

            receber_propostas = st.checkbox("Desejo receber propostas e que entrem em contato comigo")
            if receber_propostas:
                telefone_contato = st.text_input("Telefone para contato", value=user_tel, key="telefone_contato")
                email_contato = st.text_input("E-mail para contato", value=user_email, key="email_contato")
            else:
                telefone_contato = ""
                email_contato = ""

            # ✅ Aqui está o botão, agora posicionado corretamente
            if "propostas" in permissoes:
                if st.button("Solicitar proposta", key="xml_solicitar"):
                    try:
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
                            from_="whatsapp:+14155238886",
                            to=f"whatsapp:{st.secrets['ADMIN_WHATSAPP_TO']}"
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
                                telefone_contato,
                                email_contato,
                                datetime.now().isoformat()
                            )
                        )
                        conn.commit()
                    except Exception as e:
                        st.error(f"Erro ao processar a proposta: {e}")
            else:
                st.warning("⚠️ Seu plano atual não permite solicitar propostas.")

                

# --- Roteamento pós-login ---
if st.session_state.role == 'admin':
    # — DEBUG: colunas no momento do Admin —
    cursor.execute("PRAGMA table_info(proposals)")
    colunas_admin = [c[1] for c in cursor.fetchall()]

    st.header("📋 Propostas Recebidas")
    sql = """
      SELECT
        p.id                   AS "ID",
        c.username             AS "Nome da Empresa",
        p.telefone_contato     AS "Telefone",
        p.email_contato        AS "E-mail",
        p.nome_cliente         AS "Nome no XML",
        p.cnpj                 AS "CNPJ (NF-e)",
        p.valor_nota           AS "Valor NF-e",
        p.taxa_ia              AS "Taxa IA (%)",
        p.taxa_cliente         AS "Taxa Cliente (%)",
        p.deseja_contato       AS "Deseja Contato",
        p.created_at           AS "Solicitado em"
      FROM proposals p
      LEFT JOIN clients c
        ON p.cnpj = c.cnpj
      ORDER BY p.created_at DESC
    """
    try:
        df = pd.read_sql_query(sql, conn)
        st.dataframe(df)
    except Exception as e:
        st.error(f"Erro ao buscar propostas: {e}")
    else:
        st.info("Ainda não há propostas.")
elif st.session_state.role == 'cliente':
    st.header("👤 Dashboard do Cliente")
    
    plano_atual = st.session_state.get("plano", "").split("–")[0].strip()
    permissoes = PERMISSOES_POR_PLANO.get(plano_atual, [])

    st.write("Plano ativo:", plano_atual)

    abas = []
    if "cotacao" in permissoes:
        abas.append("💰 Cotação de Antecipação")
    if "analise_risco" in permissoes:
        abas.append("⚙️ Análise de Risco")

    if abas:
        tabs = st.tabs(abas)
        if "💰 Cotação de Antecipação" in abas:
            with tabs[abas.index("💰 Cotação de Antecipação")]:
                exibir_interface_cliente_cotacao(permissoes)
        if "⚙️ Análise de Risco" in abas:
            with tabs[abas.index("⚙️ Análise de Risco")]:
                exibir_interface_analise_risco()
    else:
        st.warning("Seu plano atual não dá acesso a funcionalidades. Atualize para aproveitar a plataforma.")


# Configuração de localização para formatação brasileira
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')  # fallback


st.stop()
