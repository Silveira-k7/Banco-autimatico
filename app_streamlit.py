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
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#0066cc'), spaceAfter=12, alignment=1)
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, spaceAfter=6)
    
    elements.append(Paragraph(f"📊 Relatório de Banco de Horas", title_style))
    elements.append(Paragraph(f"<b>Usuário:</b> {nome_usuario}", normal_style))
    elements.append(Paragraph(f"<b>Período:</b> {periodo_inicio} a {periodo_fim}", normal_style))
    elements.append(Paragraph(f"<b>Gerado em:</b> {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}", normal_style))
    elements.append(Spacer(1, 12))
    
    data = [["Data", "Entrada", "Saída Almoço", "Volta Almoço", "Saída", "Trabalhadas", "Abonas", "Carga", "Banco do Dia", "Saldo Acum."]]
    
    for _, row in df.iterrows():
        marcacoes_str = row["Marcações"] if pd.notna(row["Marcações"]) else ""
        marcacoes = marcacoes_str.split(" | ") if marcacoes_str else []
        while len(marcacoes) < 4:
            marcacoes.append("")
        
        data.append([row["Data"], marcacoes[0] if len(marcacoes) > 0 else "", marcacoes[1] if len(marcacoes) > 1 else "", marcacoes[2] if len(marcacoes) > 2 else "", marcacoes[3] if len(marcacoes) > 3 else "", row["Horas Trabalhadas"], row["Abonas"], row["Carga Horária"], row["Banco do Dia"], row["Saldo Acumulado"]])
    
    table = Table(data, colWidths=[0.8*inch, 0.9*inch, 1.1*inch, 1.1*inch, 0.9*inch, 0.85*inch, 0.75*inch, 0.75*inch, 0.9*inch, 0.9*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
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
        * { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        html, body, [data-testid="stAppViewContainer"] { background: #0f0f0f !important; }
        [data-testid="stSidebar"] { background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%) !important; }
        [data-testid="stSidebar"] * { color: #ffffff !important; }
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBg"] { background: transparent !important; }
        
        /* Menu Radio Minimalista */
        [data-testid="stSidebar"] .stRadio > div { gap: 0px !important; }
        [data-testid="stSidebar"] .stRadio > div > label { 
            background: transparent !important; 
            border: none !important; 
            padding: 10px 16px !important; 
            border-radius: 6px !important;
            transition: background 0.2s !important;
            margin: 2px 0 !important;
        }
        [data-testid="stSidebar"] .stRadio > div > label:hover { 
            background: rgba(255, 255, 255, 0.05) !important; 
        }
        [data-testid="stSidebar"] .stRadio > div > label[data-baseweb="radio"] > div:first-child {
            display: none !important;
        }
        [data-testid="stSidebar"] .stRadio > div > label > div:last-child {
            font-size: 14px !important;
            font-weight: 500 !important;
            color: rgba(255, 255, 255, 0.8) !important;
        }
        [data-testid="stSidebar"] .stRadio > div > label[aria-checked="true"] {
            background: rgba(0, 102, 204, 0.15) !important;
        }
        [data-testid="stSidebar"] .stRadio > div > label[aria-checked="true"] > div:last-child {
            color: #66b3ff !important;
            font-weight: 600 !important;
        }
        
        .stButton > button {
            background: linear-gradient(135deg, #0066cc 0%, #0052a3 100%) !important;
            color: white !important; border: none !important; border-radius: 8px !important;
            font-weight: 600 !important; font-size: 15px !important; padding: 12px 24px !important;
            box-shadow: 0 2px 8px rgba(0, 102, 204, 0.2) !important; transition: all 0.2s !important;
        }
        .stButton > button:hover { transform: translateY(-1px) !important; box-shadow: 0 4px 12px rgba(0, 102, 204, 0.3) !important; }
        
        .stTextInput > div > div > input, .stSelectbox > div > div > select {
            border: 1px solid #333333 !important; border-radius: 6px !important;
            font-size: 14px !important; padding: 10px 12px !important; background: #1a1a1a !important; color: #ffffff !important;
        }
        .stTextInput > div > div > input:focus, .stSelectbox > div > div > select:focus {
            border-color: #0066cc !important; box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.2) !important;
        }
        
        .stCheckbox label { color: #ffffff !important; font-weight: 500 !important; font-size: 14px !important; }
        
        h1 { color: #ffffff !important; font-size: 2.2em !important; font-weight: 600 !important; margin-bottom: 4px !important; }
        h2 { color: #ffffff !important; font-size: 1.3em !important; font-weight: 600 !important; margin: 0 !important; }
        h3 { color: #ffffff !important; font-weight: 600 !important; }
        p { color: #cccccc; }
        
        .card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.5); }
        .card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #2a2a2a; }
        .card-icon { width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 20px; background: #2a2a2a; }
        
        .metric { background: #1a1a1a; padding: 20px; border-radius: 8px; border: 1px solid #2a2a2a; text-align: center; }
        .metric-value { font-size: 28px; font-weight: 700; color: #0088ff; margin: 8px 0; }
        .metric-label { font-size: 12px; color: #888888; text-transform: uppercase; letter-spacing: 0.5px; }
        
        .info-box { background: rgba(0, 102, 204, 0.15); border-left: 4px solid #0066cc; border-radius: 4px; padding: 12px 16px; margin: 16px 0; font-size: 13px; color: #66b3ff; }
        
        .stDownloadButton > button { background: #27ae60 !important; color: white !important; border-radius: 6px !important; }
        .stDownloadButton > button:hover { background: #229954 !important; }
        
        /* Dark Theme para Tabelas */
        [data-testid="stDataFrame"] { background: #1a1a1a !important; }
        [data-testid="stDataFrame"] table { background: #1a1a1a !important; }
        [data-testid="stDataFrame"] th { background: #2a2a2a !important; color: #ffffff !important; border-color: #333333 !important; }
        [data-testid="stDataFrame"] td { background: #1a1a1a !important; color: #e0e0e0 !important; border-color: #333333 !important; }
        [data-testid="stDataFrame"] tr:hover td { background: #252525 !important; }
        
        /* Dark Theme para Gráficos */
        [data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"] { background: #1a1a1a !important; border-radius: 8px !important; }
        
        /* Dark Theme para Expanders */
        [data-testid="stExpander"] { background: #1a1a1a !important; border: 1px solid #2a2a2a !important; border-radius: 8px !important; }
        [data-testid="stExpander"] [data-testid="stExpanderDetails"] { background: #1a1a1a !important; color: #e0e0e0 !important; }
        
        /* Dark Theme para Status/Alert boxes */
        .stAlert { background: #1a1a1a !important; border: 1px solid #2a2a2a !important; color: #e0e0e0 !important; }
        
        .dev-credit {
            background: linear-gradient(135deg, #0066cc 0%, #0052a3 100%);
            color: white; padding: 24px; border-radius: 8px; text-align: center; margin-top: 30px;
        }
        .dev-credit h3 { color: white !important; font-size: 11px !important; text-transform: uppercase !important; letter-spacing: 1px !important; margin-bottom: 8px !important; opacity: 0.9 !important; }
        .dev-credit h2 { color: white !important; font-size: 1.4em !important; margin: 0 0 8px 0 !important; }
        .dev-credit p { color: rgba(255, 255, 255, 0.9) !important; margin: 0; font-size: 13px !important; }
        
        /* Remover linhas extras */
        [data-testid="stSidebar"] hr { display: none !important; }
        [data-testid="stSidebar"] .css-1544g2n { border: none !important; }
    </style>
""", unsafe_allow_html=True)

# ============ SIDEBAR ============
with st.sidebar:
    st.markdown("""
        <div style='padding: 20px 0 16px 0; margin-bottom: 20px;'>
            <h3 style='margin: 0; font-size: 16px; font-weight: 600; color: white; letter-spacing: 0.3px;'>Banco de Horas</h3>
        </div>
    """, unsafe_allow_html=True)
    
    pagina = st.radio("Menu", ["Inicial", "Dashboard", "Extração", "Dados", "Configurações"], label_visibility="collapsed")
    
    st.markdown("""
        <div style='position: fixed; bottom: 20px; left: 16px; right: 16px;'>
            <div style='border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 16px;'>
                <p style='font-size: 10px; color: rgba(255, 255, 255, 0.5); margin: 0 0 4px 0;'>v2.1</p>
                <p style='font-size: 11px; color: rgba(255, 255, 255, 0.6); margin: 0;'>João Pedro da Silveira</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ============ PÁGINA INICIAL ============
if pagina == "Inicial":
    st.markdown("# Automação de Extração")
    st.markdown("*Configure suas credenciais e o período para atualizar seu banco de horas.*")
    st.markdown("---")
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header"><div class="card-icon">🔐</div><h2>Credenciais de Acesso</h2></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<label style='font-weight: 600; color: #333; font-size: 13px; display: block; margin-bottom: 6px;'>👤 Usuário</label>", unsafe_allow_html=True)
        usuario = st.text_input("login", placeholder="Digite seu usuário", label_visibility="collapsed")
    with col2:
        st.markdown("<label style='font-weight: 600; color: #333; font-size: 13px; display: block; margin-bottom: 6px;'>🔑 Senha</label>", unsafe_allow_html=True)
        senha = st.text_input("password", placeholder="Digite sua senha", type="password", label_visibility="collapsed")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header"><div class="card-icon">📅</div><h2>Período de Extração</h2></div>', unsafe_allow_html=True)
    
    agora = datetime.now()
    st.markdown(f'<div class="info-box"><strong>📌 Data de Referência:</strong> {agora.month:02d}/{agora.year}</div>', unsafe_allow_html=True)
    
    st.markdown("<label style='font-weight: 600; color: #333; font-size: 13px; display: block; margin-bottom: 6px;'>Extrair até o Mês:</label>", unsafe_allow_html=True)
    mes_fim = st.selectbox("mes", range(1, 13), index=agora.month-2 if agora.month > 2 else 0, label_visibility="collapsed")
    
    st.markdown("<label style='font-weight: 600; color: #333; font-size: 13px; display: block; margin-bottom: 6px; margin-top: 12px;'>Até o Ano:</label>", unsafe_allow_html=True)
    ano_fim = st.selectbox("ano", range(2020, 2027), index=agora.year-2020, label_visibility="collapsed")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header"><div class="card-icon">⚙️</div><h2>Opções Avançadas</h2></div>', unsafe_allow_html=True)
    
    mostrar_chrome = st.checkbox("Mostrar navegador durante a execução", value=False)
    st.markdown("<p style='font-size: 12px; color: #999; margin-top: 8px;'><em>Aumenta o tempo, útil apenas para depuração</em></p>", unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.button("🚀 PROCESSAR EXTRAÇÃO", use_container_width=True, key="processar_main"):
        if not usuario or not senha:
            st.error("❌ Usuário e senha são obrigatórios!")
        else:
            try:
                progresso = st.progress(0)
                status = st.status("Iniciando processamento...", expanded=True)
                
                status.write("👉 Iniciando navegador...")
                ver_chrome = "s" if mostrar_chrome else "n"
                driver = iniciar_selenium(ver_chrome)
                progresso.progress(10)
                
                status.write("👉 Fazendo login...")
                login(driver, usuario, senha)
                progresso.progress(20)
                
                status.write("👉 Acessando marcações...")
                acessar_marcacoes(driver)
                progresso.progress(30)
                
                status.write("👉 Extraindo nome do usuário...")
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
                    status.write(f"[{mes_processado}/{total_meses}] 📅 Processando {mes:02d}/{ano}...")
                    
                    navegar_para_mes(driver, mes, ano)
                    registros_mes = extrair_registros(driver)
                    registros.extend(registros_mes)
                    
                    progresso.progress(35 + int((mes_processado / total_meses) * 50))
                    
                    mes -= 1
                    if mes < 1:
                        mes = 12
                        ano -= 1
                
                driver.quit()
                status.write("👉 Organizando dados...")
                registros = sorted(registros, key=lambda x: x["Data ISO"])
                progresso.progress(85)
                
                status.write("👉 Gerando planilha e dashboard...")
                gerar_planilha(registros, nome_usuario)
                progresso.progress(95)
                
                status.write("✅ Processamento concluído!")
                progresso.progress(100)
                
                st.success(f"✅ Sucesso! {len(registros)} registros processados para **{nome_usuario}**")
                st.info("📊 Vá para **Dashboard** para visualizar seus dados!")
                
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
    
    st.markdown("<div style='text-align: center; font-size: 12px; color: #999; margin-top: 24px;'>✓ Seus dados são processados localmente</div>", unsafe_allow_html=True)

# ============ PÁGINA DASHBOARD ============
elif pagina == "Dashboard":
    st.markdown("# Dashboard")
    st.markdown("*Visualize seus dados de banco de horas*")
    st.markdown("---")
    
    if not os.path.exists("dashboard/dashboard_data.json"):
        st.warning("⚠️ Nenhum dado processado ainda. Vá para **Inicial** e processe seus dados.")
    else:
        with open("dashboard/dashboard_data.json") as f:
            data = json.load(f)
        
        st.markdown(f"### 👤 {data.get('usuario', 'Usuário')}")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f'<div class="metric"><div class="metric-label">Saldo Acumulado</div><div class="metric-value">{data["kpis"]["saldo_atual"]}</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric"><div class="metric-label">Dias Trabalhados</div><div class="metric-value">{data["kpis"]["dias_trabalhados"]}</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric"><div class="metric-label">Horas Crédito</div><div class="metric-value">{data["kpis"]["dias_credito"]}</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="metric"><div class="metric-label">Horas Débito</div><div class="metric-value">{data["kpis"]["dias_debito"]}</div></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown("### 📈 Evolução do Saldo")
        df_evolucao = pd.DataFrame(data["evolucao"])
        st.line_chart(df_evolucao.set_index("data")["saldo"])
        
        st.markdown("---")
        st.markdown("### 📋 Detalhes Diários")
        df_detalhes = pd.DataFrame(data["detalhes"])
        st.dataframe(df_detalhes, use_container_width=True)
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if os.path.exists("controle_banco_horas.xlsx"):
                df = pd.read_excel("controle_banco_horas.xlsx")
                csv = df.to_csv(index=False)
                st.download_button("📥 Baixar CSV", csv, f"banco_horas_{data.get('usuario', 'relatorio').replace(' ', '_')}.csv", "text/csv")
        
        with col2:
            if os.path.exists("controle_banco_horas.xlsx"):
                with open("controle_banco_horas.xlsx", "rb") as f:
                    excel_data = f.read()
                st.download_button("📄 Baixar Excel", excel_data, f"banco_horas_{data.get('usuario', 'relatorio').replace(' ', '_')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        with col3:
            if os.path.exists("controle_banco_horas.xlsx"):
                df = pd.read_excel("controle_banco_horas.xlsx")
                periodo_inicio = df["Data"].min() if not df.empty else "N/A"
                periodo_fim = df["Data"].max() if not df.empty else "N/A"
                pdf_data = gerar_pdf(df, data.get('usuario', 'Usuário'), periodo_inicio, periodo_fim)
                st.download_button("📊 Baixar PDF", pdf_data, f"banco_horas_{data.get('usuario', 'relatorio').replace(' ', '_')}.pdf", "application/pdf")

# ============ PÁGINA EXTRAÇÃO ============
elif pagina == "Extração":
    st.markdown("# Automação de Extração")
    st.info("Acesse a aba **Inicial** para começar uma nova extração de dados")

# ============ PÁGINA DADOS ============
elif pagina == "Dados":
    st.markdown("# Dados Processados")
    
    if not os.path.exists("controle_banco_horas.xlsx"):
        st.warning("⚠️ Nenhum dado processado ainda.")
    else:
        df = pd.read_excel("controle_banco_horas.xlsx")
        
        if os.path.exists("dashboard/dashboard_data.json"):
            with open("dashboard/dashboard_data.json") as f:
                data = json.load(f)
                st.markdown(f"### 👤 {data.get('usuario', 'Usuário')}")
        
        st.markdown("### 📊 Tabela Completa")
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        usuario = data.get('usuario', 'relatorio').replace(' ', '_') if 'data' in locals() else 'relatorio'
        
        with col1:
            csv = df.to_csv(index=False)
            st.download_button("📥 Baixar CSV", csv, f"banco_horas_{usuario}.csv", "text/csv")
        
        with col2:
            with open("controle_banco_horas.xlsx", "rb") as f:
                excel_data = f.read()
            st.download_button("📄 Baixar Excel", excel_data, f"banco_horas_{usuario}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        with col3:
            periodo_inicio = df["Data"].min() if not df.empty else "N/A"
            periodo_fim = df["Data"].max() if not df.empty else "N/A"
            usuario_display = data.get('usuario', 'Usuário') if 'data' in locals() else 'Usuário'
            pdf_data = gerar_pdf(df, usuario_display, periodo_inicio, periodo_fim)
            st.download_button("📊 Baixar PDF", pdf_data, f"banco_horas_{usuario}.pdf", "application/pdf")

# ============ PÁGINA CONFIGURAÇÕES ============
elif pagina == "Configurações":
    st.markdown("# Configurações")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📝 Sistema")
        st.info("**Sistema:** Senior Ponto\n\n**Versão:** 2.1 Web\n\n**Status:** ✅ Operacional\n\n**Framework:** Streamlit")
    
    with col2:
        st.markdown("### 🛠️ Tecnologias")
        st.info("**Python:** 3.8+\n\n**Selenium:** Automação Web\n\n**Pandas:** Processamento\n\n**Reportlab:** PDF")
    
    st.markdown("---")
    
    with st.expander("📖 Como Usar"):
        st.markdown("1. Vá para **Inicial**\n2. Insira suas credenciais do Senior\n3. Escolha o período de extração\n4. Clique em **PROCESSAR EXTRAÇÃO**\n5. Acompanhe o progresso em tempo real\n6. Visualize no **Dashboard**")
    
    with st.expander("🔒 Segurança"):
        st.markdown("- ✅ Processamento 100% local\n- ✅ Sem armazenamento em nuvem\n- ✅ Senha usada apenas na autenticação\n- ✅ Dados privados e seguros")
    
    st.markdown("---")
    
    st.markdown("""
        <div class="dev-credit">
            <h3>🎯 Desenvolvido por</h3>
            <h2>João Pedro da Silveira</h2>
            <p>Sistema de Extração Automática de Banco de Horas</p>
            <p style='margin-top: 12px; opacity: 0.8;'>v2.1 - 2026</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='text-align: center; font-size: 12px; color: #999; margin-top: 30px; padding-top: 20px; border-top: 1px solid #f0f0f0;'>⚙️ Gerado automaticamente • Controle de Banco de Horas</div>", unsafe_allow_html=True)
