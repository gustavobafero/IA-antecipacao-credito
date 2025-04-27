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


def gerar_pdf(data_dict, grafico_risco_bytes=None, grafico_fatores_bytes=None):
    """
    Gera um PDF com relatório de precificação e riscos, incluindo gráficos.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatório de Precificação e Risco de Crédito", ln=True, align='C')
    pdf.ln(10)

    # Insere dados
    for chave, valor in data_dict.items():
        pdf.cell(0, 8, txt=clean_text(f"{chave}: {valor}"), ln=True)
    pdf.ln(5)

    # Explicação infantil
    pdf.set_font("Arial", style='I', size=11)
    texto_inf = (
        "Como a IA chegou no preço mínimo?\n"
        "- Ela considera o valor do empréstimo e protege-se do risco.\n"
        "- Adiciona uma margem de lucro para garantir rentabilidade.\n"
        "- O resultado é um preço justo, seguro e vantajoso para todos."
    )
    pdf.multi_cell(0, 8, clean_text(texto_inf))

    # Gráfico Risco x Retorno
    pdf.add_page()
    if grafico_risco_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(grafico_risco_bytes.getvalue())
            path = tmp.name
        pdf.image(path, w=180)
        pdf.ln(5)
    texto_graf1 = (
        "No gráfico:\n"
        "- Zona verde (0-30%): baixo risco, ótimo retorno.\n"
        "- Zona amarela (30-60%): risco intermediário, atenção.\n"
        "- Zona vermelha (60-100%): alto risco, cuidado.\n"
        "O ponto mostra a sua simulação. Busque sempre estar na área verde!"
    )
    pdf.multi_cell(0, 8, clean_text(texto_graf1))

    # Gráfico Fatores de Risco
    pdf.add_page()
    if grafico_fatores_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(grafico_fatores_bytes.getvalue())
            path = tmp.name
        pdf.image(path, w=180)
        pdf.ln(5)
    pdf.multi_cell(
        0,
        8,
        clean_text("Fatores de risco: mostra quais indicadores mais afetam a inadimplência.")
    )

    return BytesIO(pdf.output(dest='S').encode('latin1'))

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

    # Risco manual
    st.subheader("Avaliação de Risco de Inadimplência (Manual)")
    risco_score = 0 if score_serasa >= 800 else 1 if score_serasa < 600 else 0.5
    risco_idade = 0 if idade_empresa >= 5 else 0.5
    risco_protesto = 1 if protestos == "Sim" else 0
    risco_faturamento = 0 if faturamento >= 500000 else 0.5
    risco_total = round((risco_score * 0.4 + risco_idade * 0.2 + risco_protesto * 0.25 + risco_faturamento * 0.15) * 100, 2)
    cor_risco = "🟢 Baixo" if risco_total <= 30 else "🟡 Moderado" if risco_total <= 60 else "🔴 Alto"
    st.write(f"*Risco de inadimplência (Manual):* {cor_risco} ({risco_total}%)")
    st.markdown("---")

    # Gráfico: Risco x Retorno com zonas coloridas
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.axvspan(0, 30, color='green', alpha=0.2, label='Baixo Risco')
    ax.axvspan(30, 60, color='yellow', alpha=0.2, label='Risco Intermediário')
    ax.axvspan(60, 100, color='red', alpha=0.2, label='Alto Risco')
    # Ponto da simulação
    ax.scatter(risco_total, retorno_esperado, s=200, color='blue', edgecolor='navy', linewidth=1.5, zorder=5)
    # Anotação do ponto: risco e retorno
    ax.annotate(f"{risco_total:.1f}% / {formatar_moeda(retorno_esperado)}",
                (risco_total, retorno_esperado),
                textcoords="offset points", xytext=(10, 10), ha='left', fontsize=10, color='blue')
    # Configurações dos eixos
    ax.set_xlabel("Risco de Inadimplência (%)", fontsize=12)
    ax.set_ylabel("Retorno Esperado (R$)", fontsize=12)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, retorno_esperado * 1.3)
    ax.xaxis.set_major_formatter(PercentFormatter())
    ax.grid(True, linestyle="--", alpha=0.5, zorder=3)
    # Título e legenda explicativa
    ax.set_title("Análise de Risco x Retorno", fontsize=14, fontweight='bold', pad=10)
    ax.legend(loc='upper right', fontsize=9)
    # Captura buffer para PDF
    buf_risco = BytesIO()
    fig.savefig(buf_risco, format='png', dpi=300, bbox_inches='tight')
    buf_risco.seek(0)
    st.pyplot(fig)
    plt.close(fig)

    # Gráfico: Análise de Fatores de Risco
    st.subheader("Análise de Fatores de Risco")
    fatores = ["Score Serasa", "Idade da Empresa", "Protestos", "Faturamento"]
    pesos = [risco_score * 0.4, risco_idade * 0.2, risco_protesto * 0.25, risco_faturamento * 0.15]
    pesos = [p * 100 for p in pesos]
    fig_fat, ax_fat = plt.subplots(figsize=(6, 4))
    bars = ax_fat.bar(fatores, pesos, edgecolor="black", zorder=3)
    for bar in bars:
        height = bar.get_height()
        ax_fat.annotate(
            f"{height:.1f}%",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 5),
            textcoords="offset points",
            ha='center', va='bottom', fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.7)
        )
    ax_fat.set_ylabel("Peso na Composição do Risco (%)", fontsize=12)
    ax_fat.yaxis.set_major_formatter(PercentFormatter())
    ax_fat.grid(True, linestyle="--", alpha=0.6, zorder=0)
    buf_fat = BytesIO()
    fig_fat.savefig(buf_fat, format='png', dpi=300, bbox_inches='tight')
    buf_fat.seek(0)
    st.pyplot(fig_fat)
    plt.close(fig_fat)


    # 1) DISTRIBUIÇÃO DE RISCO
    st.subheader("Distribuição de Risco (Simulações)")
    sim_ratings = np.clip(np.random.normal(rating, 10, 500), 0, 100)
    sim_risks = (100 - sim_ratings)  # em %
    fig_dist, ax_dist = plt.subplots(figsize=(6, 3))
    ax_dist.hist(sim_risks, bins=20, edgecolor='black')
    ax_dist.axvline(risco_total, color='red', linestyle='--', label='Seu risco')
    ax_dist.set_xlabel('Risco (%)')
    ax_dist.set_ylabel('Frequência')
    ax_dist.set_title('Histograma de Risco')
    ax_dist.legend()
    st.pyplot(fig_dist)
    plt.close(fig_dist)

    # 4) CENÁRIOS: MELHOR E PIOR CASO
    st.subheader("Cenários: Melhor vs. Pior Caso")
    preco_melhor = calcular_preco_minimo(valor, 0.0, margem_desejada)
    preco_pior   = calcular_preco_minimo(valor, 1.0, margem_desejada)
    st.write(f"**Melhor caso (risco 0%):** Preço = {formatar_moeda(preco_melhor)}")
    st.write(f"**Pior caso   (risco 100%):** Preço = {formatar_moeda(preco_pior)}")

    # 6) HEATMAP DE CORRELAÇÕES
    df_corr = pd.DataFrame({
        'rating':          [rating],
        'score_serasa':    [score_serasa],
        'idade_empresa':   [idade_empresa],
        'faturamento':     [faturamento],
        'risco_total (%)': [risco_total],
        'retorno (R$)':    [retorno_esperado]
    }).corr()


    # monta o DataFrame e corrige colunas
    st.subheader("Heatmap de Correlação (Rating vs. Risco)")

    # monta DataFrame de simulação
    sim_df = pd.DataFrame({
        'Rating (0–100)': sim_ratings,
        'Risco (%)':      sim_risks
    })

    # calcula correlação
    df_corr_sim = sim_df.corr()

    # plota o heatmap
    fig_corr, ax_corr = plt.subplots(figsize=(4, 4))
    cax = ax_corr.imshow(df_corr_sim.values, interpolation='nearest', cmap='coolwarm')
    fig_corr.colorbar(cax, ax=ax_corr, fraction=0.046, pad=0.04)

    # configurações de ticks
    ax_corr.set_xticks([0, 1])
    ax_corr.set_yticks([0, 1])
    ax_corr.set_xticklabels(df_corr_sim.columns, rotation=45, ha='right')
    ax_corr.set_yticklabels(df_corr_sim.columns)

    # anota valores
    for (i, j), val in np.ndenumerate(df_corr_sim.values):
        ax_corr.text(j, i, f"{val:.2f}", ha='center', va='center', fontsize=10)

    ax_corr.set_title("Correl(Rating, Risco)")
    plt.tight_layout()

    st.pyplot(fig_corr)



    # 8) ALERTA DE OUTLIER
    st.subheader("Alerta de Outlier")
    media = sim_risks.mean()
    desvio = sim_risks.std()
    if risco_total > media + 2*desvio:
        st.warning("⚠️ Seu risco está muito acima da média das simulações.")
    else:
        st.success("✅ Risco dentro da faixa esperada.")

    # 9) RESUMO EXECUTIVO
    st.subheader("Resumo Executivo")
    resumo = (
        f"O cliente {nome_cliente} apresenta risco de {risco_total:.1f}% "
        f"e retorno esperado de {formatar_moeda(retorno_esperado)}. "
        f"A taxa ideal sugerida é {taxa_ideal}%."
    )
    st.info(resumo)

    # 10) ADEQUAÇÃO AO APETITE DE RISCO
    st.subheader("Adequação ao Apetite de Risco")
    risco_limite = 50
    if risco_total <= risco_limite:
        st.success(f"👍 Operação dentro do apetite de risco (≤ {risco_limite}%).")
    else:
        st.error(f"⚠️ Operação fora do apetite de risco (> {risco_limite}%).")


    # Geração e download do PDF
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
    pdf_bytes = gerar_pdf(dados_relatorio, buf_risco, buf_fat)
    st.download_button("📄 Baixar relatório em PDF", data=pdf_bytes, file_name="relatorio_credito.pdf")
