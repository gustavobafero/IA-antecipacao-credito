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

# Configuração de página
st.set_page_config(page_title="IA de Crédito", layout="centered")

# Configuração de localização para formatação brasileira
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')  # fallback

# Funções utilitárias
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

            with st.expander("Detalhes da Nota", expanded=False):
                st.write(f"**Valor da nota fiscal:** {formatar_moeda(valor_nota)}")
                st.write(f"**CNPJ do cliente:** {cnpj_dest}")
                if data_emissao:
                    st.write(f"**Data de emissão:** {data_emissao}")

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
            st.write(f"Taxa sugerida pela IA: {taxa_ia}%")

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

            if st.button("Solicitar proposta"):
                st.success("Sua solicitação foi registrada com sucesso! Em breve entraremos em contato.")
        except Exception as e:
            st.error(f"Erro ao processar o XML: {e}")

# Controle de navegação
st.title("Bem-vindo à Plataforma de Crédito Inteligente")
st.subheader("Como deseja usar a plataforma?")
opcao = st.selectbox("Escolha uma opção:", [
    "Selecione...",
    "Quero fazer uma análise de risco",
    "Quero cotar quanto vou receber"
])
if opcao == "Quero fazer uma análise de risco":
    exibir_interface_analise_risco()
elif opcao == "Quero cotar quanto vou receber":
    exibir_interface_cliente_cotacao()

st.stop()
