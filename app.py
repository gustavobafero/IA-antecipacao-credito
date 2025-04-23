import streamlit as st
from openai import OpenAI, RateLimitError
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from io import BytesIO
from fpdf import FPDF
import unicodedata
import tempfile

st.set_page_config(page_title="IA Crédito + Risco de Inadimplência", layout="centered")
st.title("IA para Precificação de Antecipação de Crédito")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def clean_text(text):
    return unicodedata.normalize('NFKD', text).encode('latin1', 'ignore').decode('latin1')


def gerar_pdf(data_dict, grafico_risco_bytes=None, grafico_fatores_bytes=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(200, 12, txt="Relatório de Precificação e Risco de Crédito", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    pdf.set_font("Arial", size=12)
    for chave, valor in data_dict.items():
        linha = f"{chave}: {valor}"
        pdf.cell(200, 10, txt=clean_text(linha), ln=True)

    pdf.ln(10)
    explicacao_padrao = (
        "A classificação de risco de inadimplência foi feita com base em quatro fatores principais:
"
        "1. Score Serasa – Reflete a pontuação de crédito do cliente.
"
        "2. Idade da empresa – Empresas mais jovens costumam representar maior risco.
"
        "3. Presença de protestos ou dívidas públicas – Indicadores de inadimplência recente.
"
        "4. Último faturamento declarado – Representa a capacidade financeira atual da empresa.

"
        "Cada fator recebe um peso específico na composição do risco total, e a pontuação final é classificada em:
"
        "- 🟢 Baixo risco: até 30%
"
        "- 🟡 Risco moderado: entre 31% e 60%
"
        "- 🔴 Alto risco: acima de 60%

"
        "Essa análise busca apoiar decisões de crédito com base em dados objetivos."
    )
    pdf.multi_cell(200, 10, txt=clean_text(explicacao_padrao))
    pdf.ln(5)

    if grafico_risco_bytes and grafico_fatores_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_risco:
            tmp_risco.write(grafico_risco_bytes.getvalue())
            tmp_risco_path = tmp_risco.name
        pdf.image(tmp_risco_path, w=180)
        pdf.ln(5)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_fatores:
            tmp_fatores.write(grafico_fatores_bytes.getvalue())
            tmp_fatores_path = tmp_fatores.name
        pdf.image(tmp_fatores_path, w=180)

    pdf_data = pdf.output(dest='S').encode('latin1')
    return BytesIO(pdf_data)

    st.download_button("📄 Baixar relatório em PDF", data=pdf_bytes, file_name="relatorio_credito.pdf")
