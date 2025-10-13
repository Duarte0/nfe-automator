from datetime import datetime, timedelta

def obter_periodo_mes_anterior():
    hoje = datetime.now()
    
    primeiro_dia_mes_atual = hoje.replace(day=1)
    
    ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
    
    primeiro_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)
    
    data_inicio = primeiro_dia_mes_anterior.strftime("%d/%m/%Y")
    data_fim = ultimo_dia_mes_anterior.strftime("%d/%m/%Y")
    
    return data_inicio, data_fim

data_inicio, data_fim = obter_periodo_mes_anterior()

CONFIG = {
    'usuario': '000.000.000-00',           # CPF com pontos e traço
    'senha': 'sua_senha_aqui',             # Senha do portal
    'inscricao_estadual': '000000000',     # IE apenas números
    'data_inicio': data_inicio,            # Primeiro dia do mês anterior (automático)
    'data_fim': data_fim                   # Último dia do mês anterior (automático)
}