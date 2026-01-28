import time
import json
import pandas as pd
from getpass import getpass
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys


# ==================================================
# CONFIGURAÇÕES
# ==================================================
URL_LOGIN = "https://seniorponto.puc-campinas.edu.br/gestaoponto-frontend/login"

CARGA_DIARIA_PADRAO_MINUTOS = 8 * 60  # 8 horas = 480 minutos (valor padrão)

MESES = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4,
    "MAI": 5, "JUN": 6, "JUL": 7, "AGO": 8,
    "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12
}


# ==================================================
# SELENIUM
# ==================================================
def iniciar_selenium(ver_chrome):
    options = Options()

    if not ver_chrome.lower().startswith("s"):
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")

    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


def login(driver, usuario, senha):
    driver.get(URL_LOGIN)
    time.sleep(3)

    driver.find_element(By.ID, "index-vm-username").send_keys(usuario)
    senha_input = driver.find_element(By.ID, "index-vm-password")
    senha_input.send_keys(senha)
    senha_input.send_keys(Keys.ENTER)

    time.sleep(6)


def acessar_marcacoes(driver):
    time.sleep(4)
    try:
        driver.find_element(By.CSS_SELECTOR, "div.card-employee").click()
        time.sleep(4)
    except:
        pass


def extrair_nome_usuario(driver):
    """
    Extrai o nome do usuário do elemento HTML.
    Procura por: <h2 class="employee-full-name">JOAO PEDRO DA SILVEIRA</h2>
    """
    try:
        nome_element = driver.find_element(By.CSS_SELECTOR, "h2.employee-full-name")
        nome = nome_element.text.strip()
        if nome:
            print(f"👤 Usuário: {nome}")
            return nome
    except:
        pass
    
    return "Usuário Desconhecido"


# ==================================================
# NAVEGAÇÃO DE PERÍODO
# ==================================================
def navegar_para_mes(driver, mes_alvo, ano_alvo):
    print("👉 Ajustando período...")

    for _ in range(24):
        try:
            competencia = driver.find_element(By.ID, "codCalc__competencia").text
            mes_txt, ano_txt = competencia.replace("\xa0", " ").split()

            mes_atual = MESES[mes_txt.upper()]
            ano_atual = int(ano_txt)

            if mes_atual == mes_alvo and ano_atual == ano_alvo:
                print(f"✔ Período ajustado: {competencia}")
                return

            atual = ano_atual * 12 + mes_atual
            alvo = ano_alvo * 12 + mes_alvo

            if atual > alvo:
                btn_anterior = driver.find_element(By.ID, "codCalc__navegacao_anterior")
                driver.execute_script("arguments[0].click();", btn_anterior)
            else:
                btn_proximo = driver.find_element(By.ID, "codCalc__navegacao_proximo")
                driver.execute_script("arguments[0].click();", btn_proximo)

            time.sleep(2)

        except Exception as e:
            print("Erro ao ajustar período:", e)
            time.sleep(2)

    print("⚠ Não foi possível ajustar o período automaticamente.")


# ==================================================
# EXTRAÇÃO
# ==================================================
def extrair_registros(driver):
    registros = []

    spans_data = driver.find_elements(By.CSS_SELECTOR, "span[id$='_data']")

    for span in spans_data:
        span_id = span.get_attribute("id")
        if not span_id.startswith("dia_"):
            continue

        data_iso = span_id[4:-5]
        
        # Removido filtro de fim de semana para capturar horas extras sábado/domingo
        # if not eh_dia_util(data_iso):
        #     continue
        
        # Formata para DD/MM/YYYY
        from datetime import datetime
        data_obj_temp = datetime.strptime(data_iso, "%Y-%m-%d")
        data_humana = data_obj_temp.strftime("%d/%m/%Y")

        # ===== EXTRAÇÃO DA CARGA HORÁRIA =====
        # Estratégia 1: Procura pelo tooltip (Horários programados)
        carga_horaria_min = 0
        horario_definido_por_escala = False
        
        try:
            # Procura o span com tooltip no contexto do dia
            parent = span.find_element(By.XPATH, "../..")
            tooltip_span = parent.find_element(By.CSS_SELECTOR, "span[data-original-title]")
            horarios_esperados = tooltip_span.get_attribute("data-original-title")
            
            # Ex: "Horário: 7493 - 07:00 12:00 13:00 16:00"
            if horarios_esperados and ":" in horarios_esperados:
                carga_temp = calcular_carga_horaria_do_dia(horarios_esperados)
                if carga_temp > 0:
                    carga_horaria_min = carga_temp
                    horario_definido_por_escala = True
                    print(f"  ✅ {data_humana}: Carga (Escala) = {minutos_para_hhmm(carga_horaria_min)}")
        except:
            pass

        # ===== VERIFICAÇÃO DE SITUAÇÃO (FÉRIAS, ATESTADO, FOLGA) =====
        # Se encontrou 'Férias' ou 'Folga', a carga esperada deve ser 0 para não gerar débito indevido
        situacao_abonada = False
        try:
            dia_row = driver.find_element(By.XPATH, f"//span[@id='dia_{data_iso}_data']/ancestor::tr")
            texto_linha = dia_row.text
            
            termos_abonados = ["Férias", "Folga", "Atestado", "Recesso", "Feriado"]
            for termo in termos_abonados:
                if termo in texto_linha:
                    print(f"  🏖️ {data_humana}: Situação '{termo}' detectada -> Carga zerada.")
                    carga_horaria_min = 0
                    situacao_abonada = True
                    break
        except:
            pass

        # Estratégia 2: Se falhar e não for abonado, procura pela situação "Trabalhando"
        if carga_horaria_min == 0 and not situacao_abonada:
            try:
                # Procura pela lista de situações no contexto do dia
                dia_row = driver.find_element(By.XPATH, f"//span[@id='dia_{data_iso}_data']/ancestor::tr")
                situacoes_spans = dia_row.find_elements(By.XPATH, ".//span[contains(text(), 'Trabalhando')]")
                
                for situacao in situacoes_spans:
                    # Ex: "08:00 - 1 Trabalhando"
                    texto = situacao.text.strip()
                    partes = texto.split(" - ")
                    if len(partes) >= 1:
                        tempo_str = partes[0].strip()
                        if ":" in tempo_str:
                            h, m = tempo_str.split(":")
                            minutos = int(h) * 60 + int(m)
                            carga_horaria_min += minutos
                
                if carga_horaria_min > 0:
                    print(f"  ✅ {data_humana}: Carga (Situação) = {minutos_para_hhmm(carga_horaria_min)}")
            except:
                pass
        
        # Fallback final: Se ainda for 0 e não for abonado, usa o padrão (mas avisa)
        if carga_horaria_min == 0 and not situacao_abonada:
            # Verifica se é dia útil antes de aplicar padrão
            if eh_dia_util(data_iso):
                carga_horaria_min = CARGA_DIARIA_PADRAO_MINUTOS
                print(f"  ⚠️  {data_humana}: Carga não detectada, usando padrão {minutos_para_hhmm(CARGA_DIARIA_PADRAO_MINUTOS)}")
            else:
                 print(f"  📅 {data_humana}: Fim de semana/Feriado sem marcação -> Carga 0")

        # ===== EXTRAÇÃO DAS MARCAÇÕES =====
        marcacoes = []
        idx = 0
        while True:
            try:
                el = driver.find_element(By.ID, f"dia_{data_iso}_marcacao_{idx}")
                marcacoes.append(el.text.strip())
                idx += 1
            except:
                break

        # ===== EXTRAÇÃO DE ABONAS (FÉRIAS, ATESTADO, ETC) =====
        abonas_min = 0
        try:
            dia_row = driver.find_element(By.XPATH, f"//span[@id='dia_{data_iso}_data']/ancestor::tr")
            
            # Procura por todos os spans que contêm horas de abono
            # Formatos esperados: "02:00 - XX Férias", "03:00 - XX Atestado"
            termos_abono_para_extrair = ["Férias", "Atestado", "Feriado"]
            
            for termo in termos_abono_para_extrair:
                situacoes_spans = dia_row.find_elements(By.XPATH, f".//span[contains(text(), '{termo}')]")
                for situacao in situacoes_spans:
                    texto = situacao.text.strip()
                    # Formato: "02:00 - XX Férias"
                    partes = texto.split(" - ")
                    if len(partes) >= 1:
                        tempo_str = partes[0].strip()
                        if ":" in tempo_str:
                            try:
                                h, m = tempo_str.split(":")
                                abonas_min += int(h) * 60 + int(m)
                                print(f"    🎁 Abono ({termo}): +{tempo_str}")
                            except:
                                pass
        except Exception as e:
            pass

        # ===== EXTRAÇÃO DO BANCO DO DIA (DIRETO DO SENIOR) =====
        banco_do_dia_min = 0
        banco_encontrado = False
        
        try:
            # Procura pela lista de situações apuradas no contexto do dia
            # Usa XPath para encontrar o elemento pai que contém as situações
            dia_row = driver.find_element(By.XPATH, f"//span[@id='dia_{data_iso}_data']/ancestor::tr")
            
            # Procura por todos os spans que contêm "Banco de Horas"
            situacoes_spans = dia_row.find_elements(By.XPATH, ".//span[contains(text(), 'Banco de Horas')]")
            
            for situacao in situacoes_spans:
                texto = situacao.text.strip()
                
                # Procura por "Banco de Horas - Crédito" ou "Banco de Horas - Débito"
                if "Banco de Horas" in texto:
                    # Formato: "00:35 - 154 Banco de Horas - Crédito (FUNC"
                    partes = texto.split(" - ")
                    if len(partes) >= 1:
                        tempo_str = partes[0].strip()  # "00:35"
                        
                        # Converte para minutos
                        if ":" in tempo_str:
                            h, m = tempo_str.split(":")
                            minutos = int(h) * 60 + int(m)
                            
                            # Verifica se é crédito ou débito
                            if "Crédito" in texto:
                                banco_do_dia_min = minutos
                                banco_encontrado = True
                                print(f"    💰 Crédito: +{tempo_str}")
                            elif "Débito" in texto:
                                banco_do_dia_min = -minutos
                                banco_encontrado = True
                                print(f"    ⚠️  Débito: -{tempo_str}")
                            
                            break
        except Exception as e:
            pass

        # Se não encontrou no site, calcula manualmente
        if not banco_encontrado:
            minutos_trabalhados = calcular_minutos_trabalhados(" | ".join(marcacoes)) if marcacoes else 0
            # IMPORTANTE: Horas creditadas = Trabalho + Abonas
            # Abonas (férias, atestado) contam como horas trabalhadas para o banco
            horas_creditadas = minutos_trabalhados + abonas_min
            
            if horas_creditadas > 0:
                banco_do_dia_min = horas_creditadas - carga_horaria_min
                if banco_do_dia_min != 0:
                    if abonas_min > 0:
                        print(f"    🔢 Calculado: {minutos_para_hhmm(minutos_trabalhados)} (trabalho) + {minutos_para_hhmm(abonas_min)} (abono) = {minutos_para_hhmm(banco_do_dia_min)}")
                    else:
                        print(f"    🔢 Calculado: {minutos_para_hhmm(banco_do_dia_min)}")

        # ===== EXTRAÇÃO DO SALDO ACUMULADO (DIRETO DO SENIOR) =====
        saldo_acumulado_min = None
        try:
            # Procura pelo saldo acumulado no contexto do dia
            dia_row = driver.find_element(By.XPATH, f"//span[@id='dia_{data_iso}_data']/ancestor::tr")
            
            # O saldo acumulado geralmente está em um elemento específico
            # Vamos procurar por elementos que contenham valores de tempo no formato HH:MM
            saldo_elements = dia_row.find_elements(By.XPATH, ".//td[contains(@class, 'saldo') or contains(@id, 'saldo')]")
            
            for elem in saldo_elements:
                texto = elem.text.strip()
                # Procura por padrão +HH:MM ou -HH:MM
                import re
                match = re.search(r'([+-])?(\d{1,2}):(\d{2})', texto)
                if match:
                    sinal = -1 if match.group(1) == '-' else 1
                    h = int(match.group(2))
                    m = int(match.group(3))
                    saldo_acumulado_min = sinal * (h * 60 + m)
                    print(f"    📊 Saldo Acumulado: {texto}")
                    break
        except Exception as e:
            pass

        # Só adiciona se tiver marcações ou se for dia útil com justificativa
        if marcacoes or situacao_abonada or (eh_dia_util(data_iso) and carga_horaria_min > 0):
            registro = {
                "Data ISO": data_iso,
                "Data": data_humana,
                "Marcações": " | ".join(marcacoes) if marcacoes else "",
                "Carga Horária (min)": carga_horaria_min,
                "Abonas (min)": abonas_min,
                "Banco do Dia (min)": banco_do_dia_min
            }
            
            # Adiciona saldo acumulado se foi extraído
            if saldo_acumulado_min is not None:
                registro["Saldo Acumulado (min)"] = saldo_acumulado_min
            
            registros.append(registro)

    return registros


# ==================================================
# CÁLCULOS
# ==================================================
def calcular_carga_horaria_do_dia(horarios_esperados):
    """
    Calcula a carga horária esperada a partir dos horários do tooltip.
    Exemplo: "Horário: 7493 - 07:00 12:00 13:00 16:00" -> 8 horas
    """
    if not horarios_esperados:
        return CARGA_DIARIA_PADRAO_MINUTOS
    
    try:
        # Limpa prefixo se existir
        # "Horário: 7493 - 07:00..." -> "7493 - 07:00..."
        if "Horário:" in horarios_esperados:
            horarios_esperados = horarios_esperados.replace("Horário:", "").strip()

        # Remove código e sufixo, pega só os horários
        # Formato: "7648 - 07:00 12:00 13:00 16:00 220TS"
        partes = horarios_esperados.split(" - ")
        
        horarios_texto = ""
        
        # Estratégia: Pega a parte que contém mais de um ":" (provavelmente os horários)
        for parte in partes:
            if parte.count(":") >= 2: # "07:00 12:00" tem dois :
                horarios_texto = parte.strip()
                break
            # Caso seja apenas "08:00 17:00" na string inteira sem hifens
            elif ":" in parte and len(parte.split()) >= 2:
                 horarios_texto = parte.strip()

        # Se não achou na divisão, tenta usar a string inteira buscando hora
        if not horarios_texto:
            horarios_texto = horarios_esperados

        horarios = []
        
        for parte in horarios_texto.split():
            # Ignora partes que não são horários
            if ":" in parte and len(parte) == 5:
                # Validação básica de formato HH:MM
                try:
                    datetime.strptime(parte, "%H:%M")
                    horarios.append(parte)
                except:
                    pass
        
        # Precisa ter número par de horários (entrada/saída)
        if len(horarios) % 2 != 0 or len(horarios) == 0:
            return 0 # Retorna 0 para indicar que falhou a detecção precisa
        
        # Calcula total de minutos trabalhados
        total = 0
        for i in range(0, len(horarios), 2):
            entrada = datetime.strptime(horarios[i], "%H:%M")
            saida = datetime.strptime(horarios[i + 1], "%H:%M")
            total += int((saida - entrada).total_seconds() / 60)
        
        return total
    
    except Exception as e:
        print(f"⚠ Erro ao calcular carga horária: {e}")
        return CARGA_DIARIA_PADRAO_MINUTOS


def calcular_minutos_trabalhados(marcacoes):
    if not marcacoes:
        return 0

    pontos = marcacoes.split(" | ")
    if len(pontos) % 2 != 0:
        return 0

    total = 0
    for i in range(0, len(pontos), 2):
        e = datetime.strptime(pontos[i], "%H:%M")
        s = datetime.strptime(pontos[i + 1], "%H:%M")
        total += int((s - e).total_seconds() / 60)

    return total


def minutos_para_hhmm(minutos):
    sinal = "-" if minutos < 0 else ""
    minutos = abs(minutos)
    h = minutos // 60
    m = minutos % 60
    return f"{sinal}{h:02d}:{m:02d}"


def hhmm_para_min(hhmm):
    sinal = -1 if hhmm.startswith("-") else 1
    h, m = hhmm.replace("-", "").split(":")
    return sinal * (int(h) * 60 + int(m))


# ==================================================
# Pular fins de semana
# ==================================================
def eh_dia_util(data_iso):
    data = datetime.strptime(data_iso, "%Y-%m-%d")
    return data.weekday() < 5  # 0=seg, 6=dom


def calcular_banco_do_dia(row):
    hoje = datetime.now().date()
    data = datetime.strptime(row["Data ISO"], "%Y-%m-%d").date()

    # Ignora dias futuros
    if data > hoje:
        return 0

    # Só ignora finais de semana SE não tiver trabalho
    if not eh_dia_util(row["Data ISO"]) and row["Minutos Trabalhados"] == 0:
        return 0

    # Ignora dias sem marcação
    if row["Minutos Trabalhados"] == 0:
        return 0

    # Usa a carga horária específica do dia (extraída do Senior)
    carga_esperada = row.get("Carga Horária (min)", CARGA_DIARIA_PADRAO_MINUTOS)
    return row["Minutos Trabalhados"] - carga_esperada


# ==================================================
# PLANILHA + DASHBOARD
# ==================================================
def gerar_dashboard_json(df, nome_usuario="Usuário"):
    # Garante que o DataFrame está ordenado cronologicamente
    df = df.sort_values("Data ISO").reset_index(drop=True)
    
    # converte Banco do Dia para minutos
    df["Banco_min"] = df["Banco do Dia"].apply(hhmm_para_min)

    credito_min = df[df["Banco_min"] > 0]["Banco_min"].sum()
    debito_min = df[df["Banco_min"] < 0]["Banco_min"].sum()

    # Prepara dados detalhados para o PDF
    detalhes = []
    for _, row in df.iterrows():
        # Separa as marcações
        marcacoes = row["Marcações"].split(" | ")
        
        # Preenche com vazio se não tiver 4 marcações
        while len(marcacoes) < 4:
            marcacoes.append("")
        
        detalhes.append({
            "data": row["Data"],
            "entrada": marcacoes[0] if len(marcacoes) > 0 else "",
            "saida_almoco": marcacoes[1] if len(marcacoes) > 1 else "",
            "volta_almoco": marcacoes[2] if len(marcacoes) > 2 else "",
            "saida": marcacoes[3] if len(marcacoes) > 3 else "",
            "banco_dia": row["Banco do Dia"]
        })

    data = {
        "usuario": nome_usuario,
        "data_relatorio": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "kpis": {
            "saldo_atual": df["Saldo Acumulado"].iloc[-1],
            "dias_credito": minutos_para_hhmm(int(credito_min)),
            "dias_debito": minutos_para_hhmm(int(abs(debito_min))),
            "dias_trabalhados": int(len(df))
        },
        "evolucao": [
            {"data": d, "saldo": hhmm_para_min(s)}
            for d, s in zip(df["Data"], df["Saldo Acumulado"])
        ],
        "detalhes": detalhes
    }

    with open("dashboard/dashboard_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("📊 JSON do dashboard (horas reais) gerado!")



def gerar_planilha(registros, nome_usuario="Usuário"):
    df = pd.DataFrame(registros)

    if df.empty:
        print("⚠ Nenhuma marcação encontrada.")
        return

    df["Minutos Trabalhados"] = df["Marcações"].apply(calcular_minutos_trabalhados)
    
    # Garante que coluna de abonas existe
    if "Abonas (min)" not in df.columns:
        df["Abonas (min)"] = 0
    
    # NÃO REMOVER DIAS SEM MARCAÇÃO! 
    # Isso escondia as faltas (dias com 0 trabalhado e carga > 0).
    # O filtro abaixo foi removido:
    # df = df[df["Minutos Trabalhados"] > 0].copy()

    # GARANTE A ORDENAÇÃO CRONOLÓGICA ANTES DE QUALQUER CÁLCULO ACUMULADO
    df = df.sort_values("Data ISO").reset_index(drop=True)

    # 👉 USA O BANCO DO DIA EXTRAÍDO DO SENIOR (não calcula!)
    # Se não tiver banco do dia extraído, calcula
    if "Banco do Dia (min)" not in df.columns:
        # Calcula considerando: Horas Creditadas = Trabalhado + Abonas
        df["Banco do Dia (min)"] = df.apply(
            lambda row: (row["Minutos Trabalhados"] + row["Abonas (min)"]) - row.get("Carga Horária (min)", CARGA_DIARIA_PADRAO_MINUTOS),
            axis=1
        )
    
    # 👉 USA O SALDO ACUMULADO EXTRAÍDO DO SENIOR
    # Se não tiver saldo acumulado extraído, calcula com cumsum
    if "Saldo Acumulado (min)" not in df.columns:
        df["Saldo Acumulado (min)"] = df["Banco do Dia (min)"].cumsum()
        print("⚠️  Saldo acumulado calculado (não extraído do Senior)")
    else:
        print("✅ Saldo acumulado extraído do Senior!")

    df["Horas Trabalhadas"] = df["Minutos Trabalhados"].apply(minutos_para_hhmm)
    df["Abonas"] = df["Abonas (min)"].apply(minutos_para_hhmm)
    df["Carga Horária"] = df["Carga Horária (min)"].apply(minutos_para_hhmm)
    df["Banco do Dia"] = df["Banco do Dia (min)"].apply(minutos_para_hhmm)
    df["Saldo Acumulado"] = df["Saldo Acumulado (min)"].apply(minutos_para_hhmm)

    df_final = df.drop(columns=[
        "Minutos Trabalhados",
        "Abonas (min)",
        "Carga Horária (min)",
        "Banco do Dia (min)",
        "Saldo Acumulado (min)"
    ])

    df_final.to_excel("controle_banco_horas.xlsx", index=False)
    gerar_dashboard_json(df_final, nome_usuario)

    print("📊 Planilha e dashboard gerados com dados REAIS do Senior!")



# ==================================================
# MAIN (Para uso direto em terminal)
# ==================================================
def main_cli():
    print("\n=== Senior Ponto → Controle de Banco de Horas ===")

    usuario = input("Usuário: ")
    senha = getpass("Senha: ")
    ver = input("Mostrar Chrome? (s/n): ")

    mes_inicio = int(input("Mês inicial (1-12): "))
    ano_inicio = int(input("Ano inicial: "))

    # Pega o mês e ano atual
    agora = datetime.now()
    mes_atual = agora.month
    ano_atual = agora.year

    driver = iniciar_selenium(ver)

    print("👉 Entrando no Senior...")
    login(driver, usuario, senha)

    print("👉 Acessando marcações...")
    acessar_marcacoes(driver)

    # Loop para extrair registros de todos os meses até o mês atual
    registros = []
    mes = mes_inicio
    ano = ano_inicio

    while ano < ano_atual or (ano == ano_atual and mes <= mes_atual):
        print(f"\n📅 Processando {mes:02d}/{ano}...")
        navegar_para_mes(driver, mes, ano)
        
        print("👉 Extraindo registros...")
        registros.extend(extrair_registros(driver))
        
        # Avança para o próximo mês
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1

    driver.quit()

    print("👉 Gerando planilha final...")
    gerar_planilha(registros)


if __name__ == "__main__":
    main_cli()
