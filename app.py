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
import sqlite3
import hashlib
from datetime import datetime
import os
DATA_PATH = "clientes.db" 

def hash_password(password: str) -> str:
    """Retorna o SHA-256 hex digest da senha."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# 2) Conexão e criação da tabela de clientes
conn = sqlite3.connect("clientes.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS clients (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    cnpj TEXT NOT NULL,
    celular TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at TEXT NOT NULL
)
""")
conn.commit()
cursor.execute("""
CREATE TABLE IF NOT EXISTS proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_cliente   TEXT,
    cnpj           TEXT,
    valor_nota     REAL,
    taxa_ia        REAL,
    taxa_cliente   REAL,
    deseja_contato TEXT,
    created_at     TEXT
)
""")
conn.commit()
# 4) Funções de registro/autenticação usando o hash
def register_client(username, password, cnpj, celular, email):
    pwd_hash = hash_password(password)
    try:
        cursor.execute(
            "INSERT INTO clients (username, password_hash, cnpj, celular, email, created_at) VALUES (?,?,?,?,?,?)",
            (username, pwd_hash, cnpj, celular, email, datetime.now().isoformat())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Usuário já existe
        return False
    except sqlite3.Error as e:
        # Exibe o erro completo para diagnóstico
        st.error(f"Erro no banco de dados: {e}")
        return False


def authenticate_client(username, password):
    cursor.execute("SELECT password_hash FROM clients WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row and row[0] == hash_password(password):
        return True
    return False

st.set_page_config(page_title="IA de Crédito", layout="centered")
if 'role' not in st.session_state:
    st.title("🔐 Bem-vindo")
    modo = st.radio("Escolha:", ["Entrar", "Cadastrar-se"])
    if modo == "Cadastrar-se":
        with st.form("form_register"):
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            p2= st.text_input("Confirme a senha", type="password")
            cnpj = st.text_input("CNPJ")
            celular = st.text_input("Celular")
            email   = st.text_input("Email")
            ok = st.form_submit_button("Criar conta")
        if ok:
            if not all([u, p, p2, cnpj, celular, email]):
                st.error("Preencha todos os campos")
            elif p != p2:
                st.error("As senhas não coincidem")
            elif register_client(u, p, cnpj, celular, email):
                st.success("Conta criada! Faça login.")
            else:
                st.error("Usuário já existe.")
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
        rating          = st.slider("Rating do cliente", 0, 100, 80)
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

        # Cálculos
        prazo = (data_vencimento - data_operacao).days
        risco = (100 - rating) / 100
        ajuste = max(0.5 - valor / 100000, 0)
        taxa_ideal = round(custo_capital + margem_desejada + risco*2 + ajuste, 2)
        margem_estimada = round(taxa_ideal - custo_capital, 2)
        retorno_esperado = round(valor * (margem_estimada / 100), 2)
        preco_sugerido = calcular_preco_minimo(valor, risco, margem_desejada)

        st.markdown("## Resultado da Simulação")
        st.write(f"Prazo: {prazo} dias")
        st.write(f"Taxa ideal: {taxa_ideal}%")
        st.write(f"Margem estimada: {margem_estimada}%")
        st.write(f"Retorno esperado: {formatar_moeda(retorno_esperado)}")
        st.write(f"Preço sugerido: {formatar_moeda(preco_sugerido)}")
        st.markdown("---")

        # Risco (com dados manuais)
        risco_score   = 0 if score_serasa >= 800 else 0.5 if score_serasa >= 600 else 1
        risco_idade   = 0 if idade_empresa >= 5 else 0.5
        risco_protesto= 1 if protestos_bool else 0
        risco_fat     = 0 if faturamento >= 500000 else 0.5
        risco_total   = round((risco_score*0.4 + risco_idade*0.2 + risco_protesto*0.25 + risco_fat*0.15)*100, 2)
        cor = "🟢 Baixo" if risco_total <= 30 else "🟡 Moderado" if risco_total <= 60 else "🔴 Alto"
        st.write(f"Risco: {cor} ({risco_total}%)")
        st.markdown("---")

# Interface de Cotação de Crédito via XML (sem Serasa)
def exibir_interface_cliente_cotacao():
    st.header("Cotação de Antecipação de Crédito")
    st.write("Faça o upload do **XML da Nota Fiscal Eletrônica (NF-e)** para gerar sua cotação:")
    nome_cliente = st.text_input("Nome do cliente", key="xml_nome_cliente")

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
                    (nome_cliente, cnpj, valor_nota, taxa_ia, taxa_cliente, deseja_contato, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        nome_cliente,
                        cnpj_dest,
                        valor_nota,
                        taxa_ia,
                        taxa_cliente,
                        contato,                    # "SIM" ou "NÃO"
                        datetime.now().isoformat()
                    )
                )
                conn.commit()
        except Exception as e:
            st.error(f"Erro ao processar o XML: {e}")
                

# --- Roteamento pós-login ---
if st.session_state.role == 'admin':
    st.header("📋 Propostas Recebidas (Admin)")
        if os.path.exists(DATA_PATH):
        conn = sqlite3.connect(DATA_PATH, check_same_thread=False)
        df = pd.read_sql_query(
            "SELECT * FROM proposals ORDER BY created_at DESC",
            conn
        )
        st.dataframe(df)
    else:
        st.info("Ainda não há propostas.")
elif st.session_state.role == 'cliente':
    st.header("👤 Dashboard do Cliente")
    tab1, tab2 = st.tabs(["💰 Cotação de Antecipação", "⚙️ Análise de Risco"])
    with tab1:
        exibir_interface_cliente_cotacao()
    with tab2:
        exibir_interface_analise_risco()

# Configuração de localização para formatação brasileira
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')  # fallback


st.stop()
