import json

with open('dashboard/dashboard_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Converter minutos para formato HH:MM
for item in data['evolucao']:
    minutos = item['saldo']
    horas = minutos // 60
    mins = minutos % 60
    item['saldo'] = f"{horas:02d}:{mins:02d}"

with open('dashboard/dashboard_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ Convertido! Minutos → HH:MM")
