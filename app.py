
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
        "- Área verde (0–30%): baixo risco e retorno estável.\n"
        "- Área amarela (30–60%): risco intermediário; atenção ao investimento.\n"
        "- Área vermelha (60–100%): alto risco; retorno incerto.\n"
        "O ponto azul indica seu cenário: risco e retorno juntos."
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
        "Este gráfico de barras mostra a contribuição percentual de cada fator para o risco total:\n"
        "- Score Serasa: confiabilidade de crédito.\n"
        "- Idade da empresa: maturidade de mercado.\n"
        "- Protestos: histórico de dívidas.\n"
        "- Faturamento: solidez financeira."
    )
    pdf.multi_cell(0, 8, clean_text(texto_graf2))

    # Distribuição de Risco (histograma)
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
        "Histograma da frequência de risco em 500 simulações.\n"
        "A linha vertical marca seu risco, comparando-o à distribuição geral."
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

# Configuração da página Streamlit
st.set_page_config(page_title="IA Crédito + Risco de Inadimplência", layout="centered")
st.title("IA para Precificação de Antecipação de Crédito")

# Cliente OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Formulário de entrada
st.header("1. Informações da Operação")
with st.form("formulario_operacao"):
    st.subheader("1. Dados da Operação")
    nome_cliente = st.text_input("Nome do cliente")
    cnpj_cliente = st.text_input("CNPJ do cliente (opcional)")
    valor = st.number_input("Valor da operação (R$)", min_value=0.0, format="%.2f")
    data_operacao = st.date_input("Data da operação", value=datetime.today(), format="DD/MM/YYYY")
    data_vencimento = st.date_input("Data de vencimento", format="DD/MM/YYYY")
    rating = st.slider("Rating do cliente (0 = risco alto, 100 = risco baixo)", 0, 100, 80)
    margem_desejada = st.number_input("Margem desejada (%)", min_value=0.0, value=1.0)
    custo_capital = st.number_input("Custo do capital (%)", min_value=0.0, value=1.5)
    taxa_concorrencia = st.number_input("Taxa da concorrência (%)", min_value=0.0, value=4.5)
    st.markdown("---")
    st.subheader("2. Avaliação de Risco de Inadimplência (Manual)")
    score_serasa = st.number_input("Score Serasa (0 a 1000)", 0, 1000, 750)
    idade_empresa = st.number_input("Idade da empresa (anos)", 0, 100, 5)
    protestos = st.selectbox("Possui protestos ou dívidas públicas?", ["Não", "Sim"])
    faturamento = st.number_input("Último faturamento declarado (R$)", min_value=0.0, format="%.2f")
    data_faturamento = st.date_input("Data do último faturamento", format="DD/MM/YYYY")
    enviar = st.form_submit_button("Simular")

if enviar:
    # Cálculos principais
    prazo = (data_vencimento - data_operacao).days
    risco = (100 - rating) / 100
    ajuste_valor = max(0.5 - (valor / 100000), 0)
    taxa_ideal = round(custo_capital + margem_desejada + (risco * 2.0) + ajuste_valor, 2)
    margem_estimada = round(taxa_ideal - custo_capital, 2)
    retorno_esperado = round(valor * (margem_estimada / 100), 2)
    preco_sugerido = calcular_preco_minimo(valor, risco, margem_desejada)

    # Exibição geral
    st.markdown("## Resultado da Simulação")
    st.write(f"*Prazo da operação:* {prazo} dias")
    st.write(f"*Taxa ideal sugerida:* {taxa_ideal}%")
    st.write(f"*Margem estimada:* {margem_estimada}%")
    st.write(f"*Retorno esperado:* {formatar_moeda(retorno_esperado)}")
    st.write(
        f"*Comparação com concorrência:* "
        f"{'Acima do mercado' if taxa_ideal > taxa_concorrencia + 0.05 else 'Abaixo do mercado' if taxa_ideal < taxa_concorrencia - 0.05 else 'Na média do mercado'}"
    )
    st.markdown(f"### 💰 Preço sugerido pela IA: *{formatar_moeda(preco_sugerido)}*")
    st.markdown("---")

    # Avaliação de risco manual
    risco_score = 0 if score_serasa >= 800 else 1 if score_serasa < 600 else 0.5
    risco_idade = 0 if idade_empresa >= 5 else 0.5
    risco_protesto = 1 if protestos == "Sim" else 0
    risco_faturamento = 0 if faturamento >= 500000 else 0.5
    risco_total = round((risco_score * 0.4 + risco_idade * 0.2 + risco_protesto * 0.25 + risco_faturamento * 0.15) * 100, 2)
    cor_risco = "🟢 Baixo" if risco_total <= 30 else "🟡 Moderado" if risco_total <= 60 else "🔴 Alto"
    st.write(f"*Risco de inadimplência (Manual):* {cor_risco} ({risco_total}%)")
    st.markdown("---")

    # Gráfico: Risco x Retorno com grades e anotação
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.axvspan(0, 30, color='green', alpha=0.2)
    ax.axvspan(30, 60, color='yellow', alpha=0.2)
    ax.axvspan(60, 100, color='red', alpha=0.2)
    ponto = ax.scatter(risco_total, retorno_esperado, s=200, color='blue', edgecolor='navy', linewidth=1.5, zorder=5)
    ax.annotate(f"{risco_total:.1f}% / {formatar_moeda(retorno_esperado)}",
                (risco_total, retorno_esperado),
                textcoords="offset points", xytext=(10, 10), ha='left', fontsize=10, color='blue')
    ax.set_xlabel("Risco de Inadimplência (%)", fontsize=12)
    ax.set_ylabel("Retorno Esperado (R$)", fontsize=12)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, retorno_esperado * 1.3)
    ax.xaxis.set_major_formatter(PercentFormatter())
    ax.grid(True, linestyle='--', alpha=0.5)
    st.pyplot(fig)
    plt.close(fig)
    st.markdown("**Explicação:** Este gráfico ilustra como o valor do risco de inadimplência se relaciona com o retorno esperado em reais, destacando áreas de baixo, médio e alto risco e mostrando precisamente seu cenário.")

    # Gráfico: Análise de Fatores de Risco
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    fatores = ["Score Serasa", "Idade", "Protestos", "Faturamento"]
    pesos = [risco_score * 40, risco_idade * 20, risco_protesto * 25, risco_faturamento * 15]
    bars = ax2.bar(fatores, pesos, edgecolor="black", zorder=3)
    for bar in bars:
        ax2.annotate(f"{bar.get_height()}%", (bar.get_x() + bar.get_width()/2, bar.get_height()),
                     ha='center', va='bottom')
    ax2.set_ylabel("Peso (%))", fontsize=12)
    ax2.yaxis.set_major_formatter(PercentFormatter())
    ax2.grid(True, linestyle='--', alpha=0.5)
    st.pyplot(fig2)
    plt.close(fig2)
    st.markdown("**Explicação:** Este gráfico de barras mostra a importância relativa de cada fator de risco, ajudando a entender quais indicadores mais impactam a inadimplência.")

    # Distribuição de risco
    fig3,ax3=plt.subplots(figsize=(6,3))
    sim=np.clip(np.random.normal(rating,10,500),0,100)
    riscos=100-sim
    ax3.hist(riscos,bins=20,edgecolor='black')
    ax3.axvline(risco_total,color='red',linestyle='--',label='Seu risco')
    st.pyplot(fig3)
    st.markdown("**Explicação:** O histograma apresenta a frequência dos níveis de risco em múltiplas simulações, permitindo ver onde seu risco calculado se posiciona em relação à distribuição geral.")
    plt.close(fig3)
    buf_dist=BytesIO()
    fig3.savefig(buf_dist,format='png',dpi=300,bbox_inches='tight')
    buf_dist.seek(0)
    # Cenários e alertas
    preco_melhor=formatar_moeda(calcular_preco_minimo(valor,0, margem_desejada))
    preco_pior=formatar_moeda(calcular_preco_minimo(valor,1, margem_desejada))
    media,desvio=riscos.mean(),riscos.std()
    alerta="⚠️ Risco acima da média" if risco_total>media+2*desvio else "✅ Risco dentro da média"
    resumo=f"Cliente {nome_cliente} tem risco de {risco_total}% e retorno {formatar_moeda(retorno_esperado)}. Taxa {taxa_ideal}%"
    adequacao=f"Operação {'dentro' if risco_total<=50 else 'fora'} do apetite de risco (50%)"
    # Dados PDF
    dados={
        "Cliente":nome_cliente,
        "CNPJ":cnpj_cliente,
        "Operação":formatar_moeda(valor),
        "Prazo":f"{prazo} dias",
        "Taxa Ideal":f"{taxa_ideal}%",
        "Margem":f"{margem_estimada}%",
        "Retorno":formatar_moeda(retorno_esperado),
        "Preço Sugerido":formatar_moeda(preco_sugerido),
        "Risco":f"{risco_total}%",
        "Correlação":cor
    }
    pdf_bytes=gerar_pdf(dados,buf_risco,buf_fat,buf_dist,preco_melhor,preco_pior,alerta,resumo,adequacao)
    st.download_button("📄 Baixar PDF",data=pdf_bytes,file_name="relatorio.pdf")
