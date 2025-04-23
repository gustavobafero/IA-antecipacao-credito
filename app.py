iimport streamlit as st
from openai import OpenAI, RateLimitError
from datetime import datetime
import pandas as pd
import os
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
storage_file = "simulacoes_credito.csv"

def clean_text(text):
    return unicodedata.normalize('NFKD', text).encode('latin1', 'ignore').decode('latin1')

def gerar_pdf(data_dict, explicacao, grafico_risco_bytes=None, grafico_fatores_bytes=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatorio de Precificacao e Risco de Credito", ln=True, align='C')
    pdf.ln(10)
    for chave, valor in data_dict.items():
        linha = f"{chave}: {valor}"
        pdf.cell(200, 10, txt=clean_text(linha), ln=True)
    pdf.ln(10)
    pdf.multi_cell(200, 10, txt=clean_text("Justificativa da IA: " + explicacao))

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

def gerar_justificativa_ia(prompt):
    try:
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=300
        )
        return resposta.choices[0].message.content.strip()
    except RateLimitError:
        return "A OpenAI está com excesso de requisições no momento. Tente novamente mais tarde."
    except Exception:
        return "Não foi possível gerar a justificativa neste momento. Use a análise manual como apoio."
