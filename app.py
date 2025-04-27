import streamlit as st
from openai import OpenAI, RateLimitError
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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
    # Página de dados básicos
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatório de Precificação e Risco de Crédito", ln=True, align='C')
    pdf.ln(10)
    for chave, valor in data_dict.items():
        pdf.cell(0, 8, txt=clean_text(f"{chave}: {valor}"), ln=True)
    pdf.ln(5)

    # Explicação infantil
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
        "Este gráfico mostra como o risco de inadimplência (eixo horizontal) se relaciona ao retorno em R$.\n"
        "- Verde (0–30%): baixo risco, retorno estável.\n"
        "- Amarelo (30–60%): risco intermediário.\n"
        "- Vermelho (60–100%): alto risco.\n"
        "O ponto azul indica seu cenário exato de risco e retorno."
    )
    pdf.multi_cell(0, 8, clean_text(texto_graf1))

    # Gráfico Fatores de Risco
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
        "Este gráfico de barras mostra a contribuição de cada fator para o risco total:\n"
        "• Score Serasa: confiabilidade de crédito.\n"
        "• Idade: maturidade de mercado.\n"
        "• Protestos: histórico de dívidas.\n"
        "• Faturamento: solidez financeira."
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
        "Histograma de 500 simulações de risco.\n"
        "A linha vertical destaca seu risco calculado, comparando-o à distribuição geral."
    )
    pdf.multi_cell(0, 8, clean_text(texto_graf3))

    # Cenários: Melhor vs. Pior Caso
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, txt="Cenários: Melhor vs. Pior Caso", ln=True)
    pdf.set_font("Arial", size=11)
    texto_cen = (
        f"Melhor caso (risco 0%): preço = {preco_melhor}.\n"
        f"Pior caso (risco 100%): preço = {preco_pior}."
    )
    pdf.multi_cell(0, 8, clean_text(texto_cen))

    # Alerta de Outlier
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, txt="Alerta de Outlier", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 8, clean_text(alerta_text))

    # Resumo Executivo e Adequação ao Apetite de Risco
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

# Streamlit Config
st.set_page_config(page_title="IA Crédito + Risco de Inadimplência", layout="centered")
st.title("IA para Precificação de Antecipação de Crédito")
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Formulário
st.header("1. Informações da Operação")
with st.form("formulario_operacao"):
    st.subheader("Dados da Operação")
    nome_cliente = st.text_input("Nome do cliente")
    cnpj_cliente = st.text_input("CNPJ (opcional)")
    valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
    data_operacao = st.date_input("Data da operação", value=datetime.today())
    data_vencimento = st.date_input("Data de vencimento")
    rating = st.slider("Rating (0 alto risco, 100 baixo)", 0, 100, 80)
    margem_desejada = st.number_input("Margem desejada (%)", min_value=0.0, value=1.0)
    custo_capital = st.number_input("Custo do capital (%)", min_value=0.0, value=1.5)
    taxa_concorrencia = st.number_input("Taxa concorrência (%)", min_value=0.0, value=4.5)
    st.markdown("---")
    st.subheader("Avaliação de Risco Manual")
    score_serasa = st.number_input("Score Serasa (0-1000)", value=750, step=1)
    idade_empresa = st.number_input("Idade empresa (anos)", value=5, step=1)
    protestos = st.selectbox("Protestos/dívidas públicas?", ["Não","Sim"])
    faturamento = st.number_input("Último faturamento (R$)", min_value=0.0)
    data_faturamento = st.date_input("Data do último faturamento")
    enviar = st.form_submit_button("Simular")

if enviar:
    # Cálculos
    prazo = (data_vencimento - data_operacao).days
    risco = (100 - rating) / 100
    ajuste = max(0.5 - valor/100000, 0)
    taxa_ideal = round(custo_capital + margem_desejada + risco*2 + ajuste, 2)
    margem_estimada = round(taxa_ideal - custo_capital, 2)
    retorno_esperado = round(valor * (margem_estimada/100), 2)
    preco_sugerido = calcular_preco_minimo(valor, risco, margem_desejada)

    st.markdown("## Resultado da Simulação")
    st.write(f"Prazo: {prazo} dias")
    st.write(f"Taxa ideal: {taxa_ideal}%")
    st.write(f"Margem estimada: {margem_estimada}%")
    st.write(f"Retorno esperado: {formatar_moeda(retorno_esperado)}")
    st.write(f"Comparação concorrência: {'Acima' if taxa_ideal>taxa_concorrencia+0.05 else 'Abaixo' if taxa_ideal<taxa_concorrencia-0.05 else 'Na média'}")
    st.markdown(f"**Preço sugerido:** {formatar_moeda(preco_sugerido)}")
    st.markdown("---")

    # Risco manual
    risco_score = 0 if score_serasa>=800 else 0.5 if score_serasa>=600 else 1
    risco_idade = 0 if idade_empresa>=5 else 0.5
    risco_protesto = 1 if protestos=='Sim' else 0
    risco_fat = 0 if faturamento>=500000 else 0.5
    risco_total = round((risco_score*0.4 + risco_idade*0.2 + risco_protesto*0.25 + risco_fat*0.15)*100,2)
    cor_risco = '🟢 Baixo' if risco_total<=30 else '🟡 Moderado' if risco_total<=60 else '🔴 Alto'
    st.write(f"Risco manual: {cor_risco} ({risco_total}%)")
    st.markdown("---")

    # Gráfico Risco x Retorno
    fig, ax = plt.subplots(figsize=(6,4))
    ax.axvspan(0,30, color='green', alpha=0.2)
    ax.axvspan(30,60, color='yellow', alpha=0.2)
    ax.axvspan(60,100, color='red', alpha=0.2)
    ax.scatter(risco_total, retorno_esperado, s=200, color='blue', edgecolor='navy', linewidth=1.5, zorder=5)
    ax.annotate(f"{risco_total:.1f}% / {formatar_moeda(retorno_esperado)}",
                (risco_total, retorno_esperado), textcoords='offset points', xytext=(10,10), ha='left', fontsize=10, color='blue')
    ax.set_xlabel('Risco (%)')
    ax.set_ylabel('Retorno (R$)')
    ax.set_xlim(0,100)
    ax.set_ylim(0, retorno_esperado*1.3)
    ax.xaxis.set_major_formatter(PercentFormatter())
    ax.grid(True, linestyle='--', alpha=0.5)
    st.pyplot(fig)
    plt.close(fig)
    st.markdown("**Explicação:** Este gráfico relaciona risco e retorno, destacando seu ponto específico.")

    # Gráfico Fatores de Risco
    fig2, ax2 = plt.subplots(figsize=(6,4))
    fatores = ['Score','Idade','Protesto','Faturamento']
    pesos = [risco_score*40, risco_idade*20, risco_protesto*25, risco_fat*15]
    bars = ax2.bar(fatores, pesos, edgecolor='black')
    for bar in bars:
        ax2.annotate(f"{bar.get_height()}%", (bar.get_x()+bar.get_width()/2, bar.get_height()), ha='center')
    ax2.yaxis.set_major_formatter(PercentFormatter())
    ax2.grid(True, linestyle='--', alpha=0.5)
    st.pyplot(fig2)
    plt.close(fig2)
    st.markdown("**Explicação:** Mostra a contribuição de cada fator para o risco total.")

    # Distribuição de Risco
    sim = np.clip(np.random.normal(rating,10,500),0,100)
    riscos = 100 - sim
    fig3, ax3 = plt.subplots(figsize=(6,3))
    ax3.hist(riscos, bins=20, edgecolor='black')
    ax3.axvline(risco_total, color='red', linestyle='--', label='Seu risco')
    ax3.set_xlabel('Risco (%)')
    ax3.set_ylabel('Frequência')
    ax3.grid(True, linestyle='--', alpha=0.5)
    st.pyplot(fig3)
    plt.close(fig3)
    st.markdown("**Explicação:** Histograma de risco em 500 simulações, destacando seu valor.")

    buf_risco = BytesIO(); fig.savefig(buf_risco, format='png', bbox_inches='tight'); buf_risco.seek(0)
    buf_fat   = BytesIO(); fig2.savefig(buf_fat,   format='png', bbox_inches='tight'); buf_fat.seek(0)
    buf_dist  = BytesIO(); fig3.savefig(buf_dist,  format='png', bbox_inches='tight'); buf_dist.seek(0)

    # Cenários e alertas
    preco_melhor = formatar_moeda(calcular_preco_minimo(valor,0, margem_desejada))
    preco_pior   = formatar_moeda(calcular_preco_minimo(valor,1, margem_desejada))
    media, desvio = riscos.mean(), riscos.std()
    alerta_text = '⚠️ Risco acima da média' if risco_total>media+2*desvio else '✅ Risco dentro da média'
    resumo = f"Cliente {nome_cliente} tem risco {risco_total}% e retorno {formatar_moeda(retorno_esperado)}."
    adequacao_text = f"Operação {'dentro' if risco_total<=50 else 'fora'} do apetite (50%)."

    # Dados para PDF
    dados = {
        'Cliente': nome_cliente,
        'CNPJ': cnpj_cliente,
        'Valor': formatar_moeda(valor),
        'Prazo': f"{prazo} dias",
        'Taxa Ideal': f"{taxa_ideal}%",
        'Margem': f"{margem_estimada}%",
        'Retorno': formatar_moeda(retorno_esperado),
        'Comparação concorrência': 'Acima' if taxa_ideal>taxa_concorrencia+0.05 else 'Abaixo' if taxa_ideal<taxa_concorrencia-
