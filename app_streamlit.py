import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os
from senior_aut import (
    iniciar_selenium, login, acessar_marcacoes, navegar_para_mes,
    extrair_registros, gerar_planilha, extrair_nome_usuario
)
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch


def gerar_pdf(df, nome_usuario, periodo_inicio, periodo_fim):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=40, bottomMargin=20)
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1a1a1a'), spaceAfter=12, alignment=1)
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, spaceAfter=6)

    elements.append(Paragraph(f"Relatorio de Banco de Horas", title_style))
    elements.append(Paragraph(f"<b>Usuario:</b> {nome_usuario}", normal_style))
    elements.append(Paragraph(f"<b>Periodo:</b> {periodo_inicio} a {periodo_fim}", normal_style))
    elements.append(Paragraph(f"<b>Gerado em:</b> {datetime.now().strftime('%d/%m/%Y as %H:%M:%S')}", normal_style))
    elements.append(Spacer(1, 12))

    data = [["Data", "Entrada", "Saida Almoco", "Volta Almoco", "Saida", "Trabalhadas", "Abonas", "Carga", "Banco do Dia", "Saldo Acum."]]

    for _, row in df.iterrows():
        marcacoes_str = row["Marcacoes"] if pd.notna(row["Marcacoes"]) else ""
        marcacoes = marcacoes_str.split(" | ") if marcacoes_str else []
        while len(marcacoes) < 4:
            marcacoes.append("")

        data.append([row["Data"], marcacoes[0] if len(marcacoes) > 0 else "", marcacoes[1] if len(marcacoes) > 1 else "", marcacoes[2] if len(marcacoes) > 2 else "", marcacoes[3] if len(marcacoes) > 3 else "", row["Horas Trabalhadas"], row["Abonas"], row["Carga Horaria"], row["Banco do Dia"], row["Saldo Acumulado"]])

    table = Table(data, colWidths=[0.8*inch, 0.9*inch, 1.1*inch, 1.1*inch, 0.9*inch, 0.85*inch, 0.75*inch, 0.75*inch, 0.9*inch, 0.9*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f5f5')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


st.set_page_config(page_title="Banco de Horas", page_icon="⏱️", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        /* Background limpo */
        html, body, [data-testid="stAppViewContainer"] {
            background: #fafafa !important;
        }

        [data-testid="stAppViewContainer"] > div:first-child {
            background: #fafafa !important;
        }

        /* Sidebar minimalista */
        [data-testid="stSidebar"] {
            background: #ffffff !important;
            border-right: 1px solid #e5e5e5 !important;
            padding-top: 2rem !important;
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: #525252 !important;
        }

        /* Menu limpo sem radio buttons */
        [data-testid="stSidebar"] .stRadio > div {
            gap: 4px !important;
        }

        [data-testid="stSidebar"] .stRadio > div > label {
            background: transparent !important;
            border: none !important;
            padding: 12px 20px !important;
            border-radius: 8px !important;
            transition: all 0.12s ease !important;
            cursor: pointer !important;
        }

        [data-testid="stSidebar"] .stRadio > div > label:hover {
            background: #f5f5f5 !important;
        }

        /* Esconde radio button original */
        [data-testid="stSidebar"] .stRadio > div > label > div:first-child {
            display: none !important;
        }

        [data-testid="stSidebar"] .stRadio > div > label > div:last-child {
            font-size: 15px !important;
            font-weight: 500 !important;
            color: #737373 !important;
        }

        [data-testid="stSidebar"] .stRadio > div > label[aria-checked="true"] {
            background: #f5f5f5 !important;
        }

        [data-testid="stSidebar"] .stRadio > div > label[aria-checked="true"] > div:last-child {
            color: #171717 !important;
            font-weight: 600 !important;
        }

        /* Tipografia minimalista */
        h1 {
            color: #171717 !important;
            font-size: 28px !important;
            font-weight: 600 !important;
            margin-bottom: 8px !important;
            letter-spacing: -0.02em !important;
        }

        h2 {
            color: #171717 !important;
            font-size: 18px !important;
            font-weight: 600 !important;
            margin: 0 !important;
            letter-spacing: -0.01em !important;
        }

        h3 {
            color: #404040 !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            margin-bottom: 12px !important;
        }

        p, div, span {
            color: #737373 !important;
            font-size: 14px !important;
            line-height: 1.6 !important;
        }

        /* Inputs minimalistas */
        .stTextInput > div > div > input,
        .stSelectbox > div > div > select {
            border: 1px solid #e5e5e5 !important;
            border-radius: 8px !important;
            font-size: 14px !important;
            padding: 12px 14px !important;
            background: #ffffff !important;
            color: #171717 !important;
            transition: border 0.15s !important;
        }

        .stTextInput > div > div > input:focus,
        .stSelectbox > div > div > select:focus {
            border-color: #a3a3a3 !important;
            box-shadow: 0 0 0 1px #a3a3a3 !important;
            outline: none !important;
        }

        .stTextInput label, .stSelectbox label {
            color: #525252 !important;
            font-size: 13px !important;
            font-weight: 500 !important;
        }

        /* Checkbox simples */
        .stCheckbox label {
            color: #525252 !important;
            font-weight: 400 !important;
            font-size: 14px !important;
        }

        /* Botao principal minimalista */
        .stButton > button {
            background: #171717 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            font-size: 14px !important;
            padding: 12px 24px !important;
            transition: all 0.15s !important;
            letter-spacing: 0 !important;
        }

        .stButton > button:hover {
            background: #404040 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
        }

        /* Botoes de download */
        .stDownloadButton > button {
            background: #ffffff !important;
            color: #171717 !important;
            border: 1px solid #e5e5e5 !important;
            border-radius: 8px !important;
            padding: 10px 20px !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            transition: all 0.15s !important;
        }

        .stDownloadButton > button:hover {
            border-color: #a3a3a3 !important;
            background: #fafafa !important;
        }

        /* Cards minimalistas */
        .card {
            background: #ffffff;
            border: 1px solid #e5e5e5;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }

        /* Metricas limpas */
        .metric-card {
            background: #ffffff;
            border: 1px solid #e5e5e5;
            border-radius: 12px;
            padding: 20px;
        }

        .metric-label {
            font-size: 12px;
            color: #a3a3a3;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }

        .metric-value {
            font-size: 32px;
            font-weight: 600;
            color: #171717;
            letter-spacing: -0.02em;
            line-height: 1;
        }

        /* Tabelas limpas */
        [data-testid="stDataFrame"] {
            background: #ffffff !important;
            border: 1px solid #e5e5e5 !important;
            border-radius: 12px !important;
            overflow: hidden !important;
        }

        [data-testid="stDataFrame"] table {
            background: #ffffff !important;
        }

        [data-testid="stDataFrame"] th {
            background: #fafafa !important;
            color: #525252 !important;
            border-color: #e5e5e5 !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            text-transform: uppercase !important;
            letter-spacing: 0.03em !important;
        }

        [data-testid="stDataFrame"] td {
            background: #ffffff !important;
            color: #171717 !important;
            border-color: #f5f5f5 !important;
            font-size: 14px !important;
        }

        [data-testid="stDataFrame"] tr:hover td {
            background: #fafafa !important;
        }

        /* Alerts minimalistas */
        .stAlert {
            background: #fafafa !important;
            border: 1px solid #e5e5e5 !important;
            border-left: 3px solid #171717 !important;
            color: #525252 !important;
            border-radius: 8px !important;
        }

        .stSuccess {
            background: #f0fdf4 !important;
            border: 1px solid #bbf7d0 !important;
            border-left: 3px solid #22c55e !important;
            color: #166534 !important;
        }

        .stError {
            background: #fef2f2 !important;
            border: 1px solid #fecaca !important;
            border-left: 3px solid #ef4444 !important;
            color: #991b1b !important;
        }

        .stWarning {
            background: #fffbeb !important;
            border: 1px solid #fde68a !important;
            border-left: 3px solid #f59e0b !important;
            color: #92400e !important;
        }

        .stInfo {
            background: #eff6ff !important;
            border: 1px solid #bfdbfe !important;
            border-left: 3px solid #3b82f6 !important;
            color: #1e3a8a !important;
        }

        /* Progress bar limpa */
        .stProgress > div > div > div > div {
            background: #171717 !important;
        }

        /* Graficos */
        [data-testid="stVegaLiteChart"],
        [data-testid="stArrowVegaLiteChart"] {
            background: #ffffff !important;
            border: 1px solid #e5e5e5 !important;
            border-radius: 12px !important;
            padding: 16px !important;
        }

        /* Expander limpo */
        [data-testid="stExpander"] {
            background: #ffffff !important;
            border: 1px solid #e5e5e5 !important;
            border-radius: 8px !important;
        }

        [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
            background: #fafafa !important;
            color: #525252 !important;
        }

        /* Status widget */
        [data-testid="stStatusWidget"] {
            background: #ffffff !important;
            border: 1px solid #e5e5e5 !important;
            border-radius: 12px !important;
        }

        /* Remover elementos desnecessarios */
        [data-testid="stSidebar"] hr {
            display: none !important;
        }

        #MainMenu {
            visibility: hidden !important;
        }

        footer {
            visibility: hidden !important;
        }
    </style>
""", unsafe_allow_html=True)

# SIDEBAR
with st.sidebar:
    st.markdown("<div style='padding: 0 0 24px 0; margin-bottom: 20px;'><h2 style='margin: 0; font-size: 18px; font-weight: 600; color: #171717;'>Banco de Horas</h2></div>", unsafe_allow_html=True)

    pagina = st.radio("Menu", ["Inicial", "Dashboard", "Dados", "Sobre"], label_visibility="collapsed")

    st.markdown("""
        <div style='position: fixed; bottom: 24px; left: 16px; right: 16px;'>
            <div style='border-top: 1px solid #f5f5f5; padding-top: 16px;'>
                <p style='font-size: 11px; color: #a3a3a3; margin: 0;'>Versao 2.2</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

# PAGINA INICIAL
if pagina == "Inicial":
    st.markdown("# Processar Dados")
    st.markdown("<p style='margin-bottom: 32px;'>Configure suas credenciais e periodo para extrair os dados do Senior Ponto</p>", unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("<label style='display: block; margin-bottom: 8px; font-size: 13px; font-weight: 500; color: #525252;'>Usuario</label>", unsafe_allow_html=True)
        usuario = st.text_input("usuario", placeholder="Seu usuario do Senior", label_visibility="collapsed", key="user_input")

    with col2:
        st.markdown("<label style='display: block; margin-bottom: 8px; font-size: 13px; font-weight: 500; color: #525252;'>Senha</label>", unsafe_allow_html=True)
        senha = st.text_input("senha", placeholder="Sua senha", type="password", label_visibility="collapsed", key="pass_input")

    st.markdown("<div style='margin: 32px 0;'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    agora = datetime.now()

    with col1:
        st.markdown("<label style='display: block; margin-bottom: 8px; font-size: 13px; font-weight: 500; color: #525252;'>Mes ate</label>", unsafe_allow_html=True)
        mes_fim = st.selectbox("mes", range(1, 13), index=agora.month-2 if agora.month > 2 else 0, label_visibility="collapsed")

    with col2:
        st.markdown("<label style='display: block; margin-bottom: 8px; font-size: 13px; font-weight: 500; color: #525252;'>Ano ate</label>", unsafe_allow_html=True)
        ano_fim = st.selectbox("ano", range(2020, 2027), index=agora.year-2020, label_visibility="collapsed")

    st.markdown("<div style='margin: 32px 0;'></div>", unsafe_allow_html=True)

    mostrar_chrome = st.checkbox("Mostrar navegador durante processamento", value=False)

    st.markdown("<div style='margin: 32px 0;'></div>", unsafe_allow_html=True)

    if st.button("Processar", use_container_width=True, key="processar_main"):
        if not usuario or not senha:
            st.error("Usuario e senha sao obrigatorios")
        else:
            try:
                progresso = st.progress(0)
                status = st.status("Processando...", expanded=True)

                status.write("Iniciando navegador...")
                ver_chrome = "s" if mostrar_chrome else "n"
                driver = iniciar_selenium(ver_chrome)
                progresso.progress(10)

                status.write("Fazendo login...")
                login(driver, usuario, senha)
                progresso.progress(20)

                status.write("Acessando marcacoes...")
                acessar_marcacoes(driver)
                progresso.progress(30)

                status.write("Extraindo dados do usuario...")
                nome_usuario = extrair_nome_usuario(driver)
                progresso.progress(35)

                registros = []
                mes, ano = agora.month, agora.year

                mes_temp, ano_temp = mes, ano
                total_meses = 0
                while ano_temp > ano_fim or (ano_temp == ano_fim and mes_temp >= mes_fim):
                    total_meses += 1
                    mes_temp -= 1
                    if mes_temp < 1:
                        mes_temp = 12
                        ano_temp -= 1

                mes_processado = 0
                while ano > ano_fim or (ano == ano_fim and mes >= mes_fim):
                    mes_processado += 1
                    status.write(f"Processando mes {mes:02d}/{ano} ({mes_processado}/{total_meses})")

                    navegar_para_mes(driver, mes, ano)
                    registros_mes = extrair_registros(driver)
                    registros.extend(registros_mes)

                    progresso.progress(35 + int((mes_processado / total_meses) * 50))

                    mes -= 1
                    if mes < 1:
                        mes = 12
                        ano -= 1

                driver.quit()
                status.write("Organizando dados...")
                registros = sorted(registros, key=lambda x: x["Data ISO"])
                progresso.progress(85)

                status.write("Gerando planilha...")
                gerar_planilha(registros, nome_usuario)
                progresso.progress(100)

                status.write("Concluido")
                st.success(f"{len(registros)} registros processados para {nome_usuario}")

            except Exception as e:
                st.error(f"Erro: {str(e)}")

# PAGINA DASHBOARD
elif pagina == "Dashboard":
    st.markdown("# Dashboard")
    st.markdown("<p style='margin-bottom: 32px;'>Visualize seus dados de banco de horas</p>", unsafe_allow_html=True)

    if not os.path.exists("dashboard/dashboard_data.json"):
        st.info("Nenhum dado processado ainda. Va para a pagina Inicial para processar seus dados.")
    else:
        with open("dashboard/dashboard_data.json") as f:
            data = json.load(f)

        st.markdown(f"<p style='margin-bottom: 24px; font-weight: 600; color: #171717;'>{data.get('usuario', 'Usuario')}</p>", unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Saldo Atual</div><div class="metric-value">{data["kpis"]["saldo_atual"]}</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Dias Trabalhados</div><div class="metric-value">{data["kpis"]["dias_trabalhados"]}</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Horas Credito</div><div class="metric-value">{data["kpis"]["dias_credito"]}</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Horas Debito</div><div class="metric-value">{data["kpis"]["dias_debito"]}</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='margin: 40px 0;'></div>", unsafe_allow_html=True)

        st.markdown("### Evolucao do Saldo")
        df_evolucao = pd.DataFrame(data["evolucao"])
        st.line_chart(df_evolucao.set_index("data")["saldo"], height=300)

        st.markdown("<div style='margin: 40px 0;'></div>", unsafe_allow_html=True)

        st.markdown("### Detalhes Diarios")
        df_detalhes = pd.DataFrame(data["detalhes"])
        st.dataframe(df_detalhes, use_container_width=True, height=400)

        st.markdown("<div style='margin: 32px 0;'></div>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            if os.path.exists("controle_banco_horas.xlsx"):
                df = pd.read_excel("controle_banco_horas.xlsx")
                csv = df.to_csv(index=False)
                st.download_button("Baixar CSV", csv, f"banco_horas_{data.get('usuario', 'relatorio').replace(' ', '_')}.csv", "text/csv", use_container_width=True)

        with col2:
            if os.path.exists("controle_banco_horas.xlsx"):
                with open("controle_banco_horas.xlsx", "rb") as f:
                    excel_data = f.read()
                st.download_button("Baixar Excel", excel_data, f"banco_horas_{data.get('usuario', 'relatorio').replace(' ', '_')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

        with col3:
            if os.path.exists("controle_banco_horas.xlsx"):
                df = pd.read_excel("controle_banco_horas.xlsx")
                periodo_inicio = df["Data"].min() if not df.empty else "N/A"
                periodo_fim = df["Data"].max() if not df.empty else "N/A"
                pdf_data = gerar_pdf(df, data.get('usuario', 'Usuario'), periodo_inicio, periodo_fim)
                st.download_button("Baixar PDF", pdf_data, f"banco_horas_{data.get('usuario', 'relatorio').replace(' ', '_')}.pdf", "application/pdf", use_container_width=True)

# PAGINA DADOS
elif pagina == "Dados":
    st.markdown("# Dados Completos")
    st.markdown("<p style='margin-bottom: 32px;'>Visualize e baixe todos os seus dados processados</p>", unsafe_allow_html=True)

    if not os.path.exists("controle_banco_horas.xlsx"):
        st.info("Nenhum dado processado ainda.")
    else:
        df = pd.read_excel("controle_banco_horas.xlsx")

        if os.path.exists("dashboard/dashboard_data.json"):
            with open("dashboard/dashboard_data.json") as f:
                data = json.load(f)
                st.markdown(f"<p style='margin-bottom: 24px; font-weight: 600; color: #171717;'>{data.get('usuario', 'Usuario')}</p>", unsafe_allow_html=True)

        st.dataframe(df, use_container_width=True, height=500)

        st.markdown("<div style='margin: 32px 0;'></div>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        usuario = data.get('usuario', 'relatorio').replace(' ', '_') if 'data' in locals() else 'relatorio'

        with col1:
            csv = df.to_csv(index=False)
            st.download_button("Baixar CSV", csv, f"banco_horas_{usuario}.csv", "text/csv", use_container_width=True)

        with col2:
            with open("controle_banco_horas.xlsx", "rb") as f:
                excel_data = f.read()
            st.download_button("Baixar Excel", excel_data, f"banco_horas_{usuario}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

        with col3:
            periodo_inicio = df["Data"].min() if not df.empty else "N/A"
            periodo_fim = df["Data"].max() if not df.empty else "N/A"
            usuario_display = data.get('usuario', 'Usuario') if 'data' in locals() else 'Usuario'
            pdf_data = gerar_pdf(df, usuario_display, periodo_inicio, periodo_fim)
            st.download_button("Baixar PDF", pdf_data, f"banco_horas_{usuario}.pdf", "application/pdf", use_container_width=True)

# PAGINA SOBRE
elif pagina == "Sobre":
    st.markdown("# Sobre o Sistema")
    st.markdown("<p style='margin-bottom: 32px;'>Informacoes sobre o sistema de banco de horas</p>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="card"><h3>Sistema</h3><p style="margin: 0;">Senior Ponto</p><p style="margin: 4px 0 0 0;">Versao 2.2</p></div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card"><h3>Tecnologia</h3><p style="margin: 0;">Python 3.8+</p><p style="margin: 4px 0 0 0;">Streamlit • Selenium • Pandas</p></div>', unsafe_allow_html=True)

    st.markdown("<div style='margin: 32px 0;'></div>", unsafe_allow_html=True)

    with st.expander("Como usar"):
        st.markdown("""
        1. Acesse a pagina Inicial
        2. Insira suas credenciais do Senior Ponto
        3. Selecione o periodo desejado
        4. Clique em Processar
        5. Aguarde o processamento
        6. Visualize os dados no Dashboard
        """)

    with st.expander("Seguranca"):
        st.markdown("""
        - Processamento 100% local
        - Sem armazenamento em nuvem
        - Credenciais nao sao salvas
        - Dados privados e seguros
        """)

    st.markdown("<div style='margin: 48px 0;'></div>", unsafe_allow_html=True)

    st.markdown("""
        <div style='background: #ffffff; border: 1px solid #e5e5e5; border-radius: 12px; padding: 32px; text-align: center;'>
            <p style='font-size: 12px; color: #a3a3a3; margin: 0 0 8px 0; text-transform: uppercase; letter-spacing: 0.05em;'>Desenvolvido por</p>
            <h2 style='margin: 0 0 12px 0; font-size: 24px;'>Joao Pedro da Silveira</h2>
            <p style='margin: 0; color: #737373;'>Sistema de Extracao Automatica de Banco de Horas</p>
        </div>
    """, unsafe_allow_html=True)
