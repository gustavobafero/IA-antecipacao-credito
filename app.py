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
import locale

# Configura localização para formatação brasileira
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')  # fallback


def formatar_moeda(valor):
    try:
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except:
        return f"R$ {valor:.2f}".replace(".", ",")


def calcular_preco_minimo(custo_base, risco_inadimplencia, margem_desejada_percentual):
    ajuste_risco = 1 + risco_inadimplencia
    margem = 1 + (margem_desejada_percentual / 100)
    preco_final = custo_base * ajuste_risco * margem
    return preco_final

# Configuração da página
st.set_page_config(page_title="IA Crédito + Risco de Inadimplência", layout="centered")
st.title("IA para Precificação de Antecipação de Crédito")

# Cliente OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def clean_text(text):
    return unicodedata.normalize('NFKD', text).encode('latin1', 'ignore').decode('latin1')


def gerar_pdf(data_dict, grafico_risco_bytes=None, grafico_fatores_bytes=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatorio de Precificacao e Risco de Credito", ln=True, align='C')
    pdf.ln(10)

    for chave, valor in data_dict.items():
        linha = f"{chave}: {valor}"
        pdf.cell(200, 10, txt=clean_text(linha), ln=True)

    # Explicação infantil sobre o preço mínimo
    pdf.ln(5)
    pdf.set_font("Arial", style='I', size=11)
    pdf.multi_cell(0, 8, clean_text(
        "Como a IA chegou no preço mínimo? "
        "Você vai emprestar um montante que é bem valioso, correto? Você quer garantir que se não honrarem o combinado, você ainda possa se beneficiar certo? "
        "É exatamente assim que a IA pensa! Ela pega o valor do empréstimo, aumenta um pouquinho para se proteger do risco de não receber, e depois coloca um pedacinho a mais como lucro. "
        "O preço final é o mínimo justo pra que tudo fique seguro, e ainda valha a pena."))

    # Página 1: Gráfico Risco x Retorno
    pdf.add_page()
    pdf.set_font("Arial", style='I', size=11)
    if grafico_risco_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_risco:
            tmp_risco.write(grafico_risco_bytes.getvalue())
            tmp_risco_path = tmp_risco.name
        pdf.image(tmp_risco_path, w=180)
        pdf.ln(5)
    pdf.multi_cell(0, 8, clean_text(
        "Este gráfico mostra o quanto a operação pode render (retorno esperado) em relação ao risco de não receber o pagamento (risco de inadimplência). "
        "Quanto mais para cima, melhor o retorno. Quanto mais para a direita, maior o risco. O ideal é ficar no alto e à esquerda: muito retorno com pouco risco."
    ))

    # Página 2: Gráfico: Análise de Fatores de Risco
    pdf.add_page()
    pdf.set_font("Arial", style='I', size=11)
    if grafico_fatores_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_fatores:
            tmp_fatores.write(grafico_fatores_bytes.getvalue())
            tmp_fatores_path = tmp_fatores.name
        pdf.image(tmp_fatores_path, w=180)
        pdf.ln(5)
    pdf.multi_cell(0, 8, clean_text(
        "Aqui a gente vê os principais motivos que fazem o risco aumentar ou diminuir. "
        "Cada barra mostra o peso de um fator, como o score do Serasa ou a idade da empresa. "
        "Se a barra for maior, esse fator está contribuindo mais para o risco. "
        "É como montar um quebra-cabeça para entender por que uma operação pode dar errado."
    ))

    pdf_data = pdf.output(dest='S').encode('latin1')
    return BytesIO(pdf_data)


def gerar_justificativa_ia(prompt):
    st.info("🔍 Enviando solicitação à IA...")
    try:
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=300
        )
        st.success("✅ Justificativa recebida com sucesso!")
        return resposta.choices[0].message.content.strip()
    except RateLimitError:
        st.warning("⚠️ A IA está temporariamente indisponível (erro de cota). O relatório continuará sem justificativa da IA.")
        return "A OpenAI está com excesso de requisições no momento. Tente novamente mais tarde."
    except Exception:
        st.warning("⚠️ Erro inesperado ao consultar a IA. O relatório continuará sem justificativa da IA.")
        return "Não foi possível gerar a justificativa neste momento. Use a análise manual como apoio."

# 1. Informações da Operação
st.header("1. Informações da Operação")
form = st.form("formulario_operacao")
with form:
    nome_cliente = st.text_input("Nome do cliente")
    cnpj_cliente = st.text_input("CNPJ do cliente (opcional)")
    valor = st.number_input("Valor da operação (R$)", min_value=0.0, format="%.2f")
    data_operacao = st.date_input("Data da operação", value=datetime.today(), format="DD/MM/YYYY")
    data_vencimento = st.date_input("Data de vencimento", format="DD/MM/YYYY")
    rating = st.slider("Rating do cliente (0 = risco alto, 100 = risco baixo)", 0, 100, 80)
    margem_desejada = st.number_input("Margem desejada (%)", min_value=0.0, value=1.0)
    custo_capital = st.number_input("Custo do capital (%)", min_value=0.0, value=1.5)
    taxa_concorrencia = st.number_input("Taxa da concorrência (%)", min_value=0.0, value=4.5)

    st.subheader("2. Avaliação de Risco de Inadimplência (manual)")

    score_serasa = st.number_input("Score Serasa (0 a 1000)", min_value=0, max_value=1000, value=750)
    idade_empresa = st.number_input("Idade da empresa (anos)", min_value=0, value=5)
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

    # Status concorrência
    if taxa_ideal > taxa_concorrencia + 0.05:
        status = "Acima do mercado"
    elif taxa_ideal < taxa_concorrencia - 0.05:
        status = "Abaixo do mercado"
    else:
        status = "Na média do mercado"

    # Risco manual detalhado
    risco_score = 0 if score_serasa >= 800 else 1 if score_serasa < 600 else 0.5
    risco_idade = 0 if idade_empresa >= 5 else 0.5
    risco_protesto = 1 if protestos == "Sim" else 0
    risco_faturamento = 0 if faturamento >= 500000 else 0.5
    risco_total = round((risco_score * 0.4 + risco_idade * 0.2 + risco_protesto * 0.25 + risco_faturamento * 0.15) * 100, 2)
    cor_risco = "🟢 Baixo" if risco_total <= 30 else "🟡 Moderado" if risco_total <= 60 else "🔴 Alto"

    # Novo: preco sugerido pela IA
    preco_sugerido = calcular_preco_minimo(valor, risco, margem_desejada)

    # Exibição dos resultados
    st.markdown("## Resultado da Simulação")
    st.write(f"**Prazo da operação:** {prazo} dias")
    st.write(f"**Taxa ideal sugerida:** {taxa_ideal}%")
    st.write(f"**Margem estimada:** {margem_estimada}%")
    st.write(f"**Retorno esperado:** {formatar_moeda(retorno_esperado)}")
    st.write(f"**Comparação com concorrência:** {status}")
    st.write(f"**Classificação de risco (IA):** {'Baixo' if rating >= 80 else 'Moderado' if rating >= 60 else 'Alto'}")
    st.write(f"**Risco de inadimplência (manual):** {cor_risco} ({risco_total}%)")

    # Exibe o preço sugerido pela IA
    st.markdown(f"### 💰 Preço sugerido pela IA: **{formatar_moeda(preco_sugerido)}**")

    # Bloco explicativo dinâmico
    st.markdown("""
    ---
    ### 💡 Como esse preço foi calculado?

    A IA leva em conta três fatores principais:

    - **Risco de inadimplência:** quanto maior o risco, maior o retorno necessário para compensar.
    - **Margem desejada:** é o lucro mínimo que você espera ganhar com essa operação.
    - **Concorrência:** se outras empresas oferecem melhores condições, a IA ajusta o preço pra manter você competitivo.

    **Exemplo didático:**  
    Se a operação é de **R$ 10.000** e a IA sugeriu **2,8%**, isso significa que ela calculou um risco médio, considerou sua margem desejada, e chegou nesse retorno ideal:

    **R$ 10.000 x 2,8% = R$ 280,00 de retorno esperado**
    ---
    """)

    # Gráfico de Risco x Retorno
    fig, ax = plt.subplots(figsize=(6, 4))

    # ... seus comandos de eixo, scatter, grid, anotação etc. ...

    # Título principal centralizado, moderno e sofisticado
    fig.suptitle("Análise de Risco x Retorno", 
                 fontsize=16, fontweight='bold', color='#333333', y=1.02)

    # “Subtítulo” com a fórmula estilizada
    formula = f"{formatar_moeda(valor)} × {margem_estimada:.1f}% = {formatar_moeda(retorno_esperado)} de retorno"
    fig.text(0.5, 0.95, formula, ha='center', fontsize=12, color='#555555')

    # Ajuste de layout para não cortar títulos
    fig.tight_layout(rect=[0, 0, 1, 0.9])

    # Salva e exibe
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
    buffer.seek(0)
    st.image(buffer, caption="")
    plt.close(fig)


    # Gráfico de Análise de Fatores de Risco
    st.markdown("### Análise de Fatores de Risco")
    fatores = ["Score Serasa", "Idade da Empresa", "Protestos", "Faturamento"]
    pesos = [risco_score * 0.4, risco_idade * 0.2, risco_protesto * 0.25, risco_faturamento * 0.15]
    pesos = [p * 100 for p in pesos]
    fig_risco, ax_risco = plt.subplots(figsize=(6, 4))
    bars = ax_risco.bar(fatores, pesos, edgecolor="black", zorder=3)
    for bar in bars:
    height = bar.get_height()
    ax_risco.annotate(f'{height:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 5),
                        textcoords="offset points",
                        ha='center', va='bottom',
                        fontsize=10,
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.7))
    ax_risco.set_ylabel("Peso na Composição do Risco (%)", fontsize=12)
    ax_risco.set_title("Análise de Fatores de Risco", fontsize=13, fontweight='bold')
    ax_risco.yaxis.set_major_formatter(PercentFormatter())
    ax_risco.grid(True, linestyle="--", alpha=0.6, zorder=0)
    buffer_risco = BytesIO()
    fig_risco.savefig(buffer_risco, format="png", dpi=300, bbox_inches="tight")
    buffer_risco.seek(0)
    st.image(buffer_risco, caption="Análise de Fatores de Risco")
    plt.close(fig_risco)

    # Geração e download do PDF
    dados_relatorio = {
        "Cliente": nome_cliente,
        "CNPJ": cnpj_cliente,
        "Valor da operação": formatar_moeda(valor),
        "Prazo (dias)": prazo,
        "Taxa Ideal (%)": taxa_ideal,
        "Margem (%)": margem_estimada,
        "Retorno Esperado (R$)": formatar_moeda(retorno_esperado),
        "Status Concorrência": status,
        "Risco de inadimplência": f"{risco_total}% ({cor_risco})",
        "Preço mínimo sugerido pela IA": formatar_moeda(preco_sugerido),
        "Data do último faturamento": data_faturamento.strftime('%d/%m/%Y')
    }

    pdf_bytes = gerar_pdf(dados_relatorio, buffer, buffer_risco)
    st.download_button("📄 Baixar relatório em PDF", data=pdf_bytes, file_name="relatorio_credito.pdf")
