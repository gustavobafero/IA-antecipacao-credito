import streamlit as st
from openai import OpenAI, RateLimitError
from datetime import datetime
import pandas as pd
import os
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="IA Crédito + Risco de Inadimplência", layout="centered")
st.title("IA para Precificação de Antecipação de Crédito")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
storage_file = "simulacoes_credito.csv"

def gerar_pdf(data_dict, explicacao):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatório de Precificação e Risco de Crédito", ln=True, align='C')
    pdf.ln(10)

    for chave, valor in data_dict.items():
        pdf.cell(200, 10, txt=f"{chave}: {valor}", ln=True)

    pdf.ln(10)
    pdf.multi_cell(200, 10, txt="Justificativa da IA: " + explicacao)
    
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

st.header("1. Informações da Operação")
with st.form("formulario_operacao"):
    nome_cliente = st.text_input("Nome do cliente")
    cnpj_cliente = st.text_input("CNPJ do cliente (opcional)")
    valor = st.number_input("Valor da operação (R$)", min_value=0.0, format="%.2f")
    data_operacao =_
