import streamlit as st
from openai import OpenAI, RateLimitError
from datetime import datetime
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

# Configuração de localização para formatação brasileira
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')  # fallback


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

# ----------------- Função de geração de PDF atualizada ----------------- #
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
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatório de Precificação e Risco de Crédito", ln=True, align='C')
    pdf.ln(10)

    # 1) Dados principais
    for chave, valor in data_dict.items():
        pdf.cell(0, 8, txt=clean_text(f"{chave}: {valor}"), ln=True)
    pdf.ln(5)

    # 2) Explicação “para criança”
    pdf.set_font("Arial", style='I', size=11)
    texto_inf = (
        "Como a IA chegou no preço mínimo?\n"
        "- Ela considera o valor do empréstimo e protege-se do risco.\n"
        "- Adiciona uma margem de lucro para garantir rentabilidade.\n"
        "- O resultado é um preço justo, seguro e vantajoso para todos."
    )
    pdf.multi_cell(0, 8, clean_text(texto_inf))

    # 3) Gráfico Risco x Retorno
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, txt="Análise de Risco x Retorno", ln=True)
    if grafico_risco_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(grafico_risco_bytes.getvalue())
            path = tmp.name
        pdf.image(path, w=180)
        pdf.ln(5)
    pdf.set_font("Arial", size=11)
    texto_graf1 = (
        "No gráfico:\n"
        "- Zona verde (0–30%): baixo risco, ótimo retorno.\n"
        "- Zona amarela (30–60%): risco intermediário, atenção.\n"
        "- Zona vermelha (60–100%): alto risco, cuidado.\n"
        "O ponto mostra a sua simulação. Busque sempre estar na área verde!"
    )
    pdf.multi_cell(0, 8, clean_text(texto_graf1))

    # 4) Gráfico Fatores de Risco
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, txt="Fatores de Risco", ln=True)
    if grafico_fatores_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(grafico_fatores_bytes.getvalue())
            path = tmp.name
        pdf.image(path, w=180)
        pdf.ln(5)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(
        0,
        8,
        clean_text("Mostra quais indicadores mais afetam a inadimplência.")
    )

    # 5) Distribuição de Risco (histograma)
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, txt="Distribuição de Risco (Simulações)", ln=True)
    if grafico_dist_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(grafico_dist_bytes.getvalue())
            path = tmp.name
        pdf.image(path, w=180)
        pdf.ln(5)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(
        0,
        8,
        clean_text("Histograma das simulações de risco, com seu risco destacado.")
    )

    # 6) Cenários: melhor vs. pior
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, txt="Cenários: Melhor vs. Pior Caso", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, txt=clean_text(f"Melhor caso (risco 0%): Preço = {preco_melhor}"), ln=True)
    pdf.cell(0, 8, txt=clean_text(f"Pior caso   (risco 100%): Preço = {preco_pior}"), ln=True)

    # 7) Alerta de Outlier
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, txt="Alerta de Outlier", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 8, clean_text(alerta_text))

    # 8) Resumo Executivo e Adequação ao Apetite
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
# ---------------------------------------------------------------------- #

# Configuração da página Streamlit
st.set_page_config(page_title="IA Crédito + Risco de Inadimplência", layout="centered")
st.title("IA para Precificação de Antecipação de Crédito")

# Cliente OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def clean_text(text):
    """
    Normaliza texto para evitar problemas de codificação no PDF.
    """
    return unicodedata.normalize('NFKD', text).encode('latin1', 'ignore').decode('latin1')

# Formulário de entrada
st.header("1. Informações da Operação")
with st.form("formulario_operacao"):
    # ... (mantém todo o seu formulário original) ...
    enviar = st.form_submit_button("Simular")

if enviar:
    # Cálculos principais (mantém tudo igual até aqui)
    # ... (cálculos de prazo, risco, taxa_ideal, margem_estimada, retorno_esperado, preco_sugerido) ...

    # Exibição no Streamlit (mantém igual)
    # ... (st.write, st.markdown, gráficos de risco x retorno, fatores de risco, histogramas, cenários, alertas, resumo, adequação) ...

    # --- Coleta de buffers e textos para o PDF --- #
    # buffer histograma de distribuição
    buf_dist = BytesIO()
    fig_dist.savefig(buf_dist, format='png', dpi=300, bbox_inches='tight')
    buf_dist.seek(0)

    # cenários
    preco_melhor = formatar_moeda(calcular_preco_minimo(valor, 0.0, margem_desejada))
    preco_pior   = formatar_moeda(calcular_preco_minimo(valor, 1.0, margem_desejada))

    # alerta de outlier
    media = sim_risks.mean()
    desvio = sim_risks.std()
    if risco_total > media + 2*desvio:
        alerta_text = "⚠️ Seu risco está muito acima da média das simulações."
    else:
        alerta_text = "✅ Risco dentro da faixa esperada."

    # resumo executivo e adequação
    resumo = (
        f"O cliente {nome_cliente} apresenta risco de {risco_total:.1f}% "
        f"e retorno esperado de {formatar_moeda(retorno_esperado)}. "
        f"A taxa ideal sugerida é {taxa_ideal}%." 
    )
    adequacao_text = (
        f"Operação {'dentro' if risco_total <= 50 else 'fora'} do apetite "
        f"de risco ({'≤' if risco_total <= 50 else '>'} 50%)."
    )

    # dados do relatório
    dados_relatorio = {
        "Cliente": nome_cliente,
        "CNPJ": cnpj_cliente,
        "Valor da operação": formatar_moeda(valor),
        "Prazo (dias)": prazo,
        "Taxa Ideal (%)": taxa_ideal,
        "Margem (%)": margem_estimada,
        "Retorno Esperado (R$)": formatar_moeda(retorno_esperado),
        "Comparação com concorrência": ('Acima do mercado' if taxa_ideal > taxa_concorrencia + 0.05 else 'Abaixo do mercado' if taxa_ideal < taxa_concorrencia - 0.05 else 'Na média do mercado'),
        "Risco de inadimplência": f"{risco_total}% ({cor_risco})",
        "Preço mínimo sugerido pela IA": formatar_moeda(preco_sugerido),
        "Data do último faturamento": data_faturamento.strftime('%d/%m/%Y')
    }

    # geração do PDF
    pdf_bytes = gerar_pdf(
        dados_relatorio,
        buf_risco,
        buf_fat,
        buf_dist,
        preco_melhor,
        preco_pior,
        alerta_text,
        resumo,
        adequacao_text
    )
    st.download_button("📄 Baixar relatório em PDF", data=pdf_bytes, file_name="relatorio_credito.pdf")
