#!/usr/bin/env python3
"""Script para mostrar dados extraídos usando a API"""

import requests
import json
import time
from datetime import datetime

# Configuração do servidor
API_BASE_URL = "http://172.30.0.254:7006"

# URLs específicas para teste - mapeia para queries de busca
#TEST_QUERIES = {
#   'starck': '忍者と極道',
#   'tfilme': '忍者と極道',
#   'baixafilmes': '忍者と極道',
#   #'comand': '忍者と極道',
#   'bludv': '忍者と極道',
#   'nerd': '忍者と極道',
#}

TEST_QUERIES = {
    'starck': 'Dünya',
    'tfilme': 'Dünya',
    'baixafilmes': 'Dünya',
    #'comand': 'Dünya',
    'bludv': 'Dünya',
    'nerd': 'Dünya',
}

def show_scraper_data_api(scraper_type: str, query: str):
    """Mostra dados de um scraper usando a API"""
    try:
        # Faz requisição à API
        url = f"{API_BASE_URL}/indexers/{scraper_type}"
        params = {}
        if query:
            params['q'] = query
        # Usa FlareSolverr apenas para o scraper "comand"
        if scraper_type == 'comand':
            params['use_flaresolverr'] = 'true'
        
        # Timeout maior para scrapers que usam links protegidos (bludv)
        timeout = 120 if scraper_type in ['bludv'] else 30
        
        # Mede o tempo de resposta para estimar origem dos dados
        start_time = time.time()
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            elapsed_time = time.time() - start_time
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Erro na requisição: {e}")
            return
        
        results = data.get('results', [])
        count = data.get('count', 0)
        
        if not results:
            print(f"  ❌ Nenhum resultado encontrado")
            return
        
        # Estima origem baseado no tempo de resposta
        # < 0.5s = provável cache, > 2s = provável site, entre = misto
        if elapsed_time < 0.5:
            data_origin = "Redis (Cache)"
        elif elapsed_time >= 2.0:
            data_origin = "Site (Novo)"
        else:
            data_origin = "Misto (Cache/Site)"
        
        # Pega apenas o primeiro resultado
        first_result = results[0]
        
        # Extrai display_name do magnet link
        magnet_link = first_result.get('magnet', '') or first_result.get('magnet_link', '')
        release_title_magnet = ''
        if magnet_link:
            try:
                from magnet.parser import MagnetParser
                magnet_data = MagnetParser.parse(magnet_link)
                release_title_magnet = magnet_data.get('display_name', '')
            except Exception as e:
                release_title_magnet = f"Erro ao parsear: {e}"
        
        # Cria tabela com os campos solicitados
        print(f"\n  📊 {scraper_type}")
        print(f"  {'='*150}")
        print(f"  {'Campo':<25} {'Valor':<80} {'Origem':<45}")
        print(f"  {'-'*150}")
        
        # Prepara valores para exibição (trunca se muito longo)
        def truncate(value, max_len=80):
            if not value:
                return 'N/A'
            str_value = str(value)
            return str_value[:max_len] + '...' if len(str_value) > max_len else str_value
        
        # Determina origem de cada campo
        # Campos que vêm do HTML da página
        html_origin_base = data_origin if elapsed_time < 0.5 else ("Site (Novo)" if elapsed_time >= 2.0 else "Misto")
        # Campos que vêm do magnet (sempre do site, mas HTML pode estar em cache)
        magnet_origin = "Site (Magnet)" if release_title_magnet else "N/A"
        # Campos processados (baseados nos dados acima)
        processed_origin = "Processado"
        
        # Verifica se os campos existem para determinar origem correta
        original_title = first_result.get('original_title', '')
        translated_title = first_result.get('translated_title', '')
        imdb = first_result.get('imdb', '')
        
        original_title_origin = html_origin_base if original_title else "N/A"
        translated_title_origin = html_origin_base if translated_title else "N/A"
        imdb_origin = html_origin_base if imdb else "N/A"
        
        print(f"  {'original_title_html':<25} {truncate(original_title):<80} {original_title_origin:<45}")
        print(f"  {'release_title_magnet':<25} {truncate(release_title_magnet):<80} {magnet_origin:<45}")
        print(f"  {'translated_title_html':<25} {truncate(translated_title):<80} {translated_title_origin:<45}")
        print(f"  {'title (finalizado)':<25} {truncate(first_result.get('title', '')):<80} {processed_origin:<45}")
        print(f"  {'info_hash':<25} {truncate(first_result.get('info_hash', '')):<80} {magnet_origin:<45}")
        print(f"  {'details':<25} {truncate(first_result.get('details', '')):<80} {'URL (Sempre)':<45}")
        print(f"  {'imdb':<25} {truncate(imdb):<80} {imdb_origin:<45}")
        print(f"  {'='*150}")
        print(f"  ⚠️  Nota: Origem estimada baseada no tempo de resposta ({elapsed_time:.2f}s)")
        
    except Exception as e:
        print(f"  ❌ Erro: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Testa todos os scrapers usando a API"""
    for scraper_type, query in TEST_QUERIES.items():
        try:
            show_scraper_data_api(scraper_type, query)
        except Exception as e:
            print(f"\n❌ Erro ao processar {scraper_type}: {e}")

if __name__ == "__main__":
    main()

