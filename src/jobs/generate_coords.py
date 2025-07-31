# generate_coords.py
import requests
import json
import time

print("Iniciando a geração do arquivo de coordenadas. Este processo é lento e será executado apenas uma vez.")

IBGE_API_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/MG/municipios"
GEOCODING_URL = "https://nominatim.openstreetmap.org/search"

# 1. Buscar municípios de MG no IBGE
print("🏛️  Buscando lista de municípios de MG na API do IBGE..." )
try:
    response = requests.get(IBGE_API_URL, timeout=60)
    response.raise_for_status()
    ibge_municipalities = response.json()
    print(f"✅ Encontrados {len(ibge_municipalities)} municípios.")
except Exception as e:
    print(f"❌ Falha crítica ao buscar dados do IBGE: {e}")
    exit()

# 2. Geocodificar cada município usando Nominatim
geocoded_list = []
print(f"🌍 Iniciando geocodificação com Nominatim para {len(ibge_municipalities)} municípios...")
for i, muni in enumerate(ibge_municipalities):
    muni_name = muni["nome"]
    query = {'q': f'{muni_name}, MG, Brazil', 'format': 'json', 'limit': 1}
    headers = {'User-Agent': 'ArbovirosesApp/1.0 (Data Generation Script)'}
    
    print(f"   ({i+1}/{len(ibge_municipalities)}) Geocodificando '{muni_name}'...")
    
    try:
        geo_response = requests.get(GEOCODING_URL, params=query, headers=headers, timeout=10)
        geo_response.raise_for_status()
        geo_data = geo_response.json()

        if geo_data and len(geo_data) > 0:
            location = geo_data[0]
            geocoded_list.append({
                "code": str(muni["id"]),
                "name": muni_name,
                "state": "MG",
                "lat": float(location["lat"]),
                "lon": float(location["lon"])
            })
        else:
            print(f"   ⚠️  Coordenadas não encontradas para '{muni_name}'")
        
        time.sleep(1) # Respeitar a política de uso da API

    except Exception as e:
        print(f"   ❌ Erro na geocodificação de '{muni_name}': {e}")

# 3. Salvar a lista em um arquivo JSON
output_filename = "municipalities_with_coords.json"
with open(output_filename, 'w', encoding='utf-8') as f:
    json.dump(geocoded_list, f, ensure_ascii=False, indent=2)

print(f"\n🎉 Processo concluído! A lista de {len(geocoded_list)} municípios com coordenadas foi salva em '{output_filename}'.")
print("Agora, mova este arquivo para 'src/data/' e atualize o ClimateCollector.py para lê-lo.")
