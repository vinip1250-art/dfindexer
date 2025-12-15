"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

import re
import logging
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def extract_imdb_from_element(element: BeautifulSoup) -> Optional[str]:
    """
    Extrai ID do IMDB de um elemento BeautifulSoup.
    
    Busca em links <a> que contenham 'imdb.com' no href.
    
    Args:
        element: Elemento BeautifulSoup onde buscar
    
    Returns:
        ID do IMDB (ex: 'tt1234567') ou None
    """
    if not element:
        return None
    
    for a in element.select('a[href*="imdb.com"]'):
        href = a.get('href', '')
        
        # Tenta padrão /pt/title/tt
        imdb_match = re.search(r'imdb\.com/pt/title/(tt\d+)', href)
        if imdb_match:
            return imdb_match.group(1)
        
        # Tenta padrão /title/tt
        imdb_match = re.search(r'imdb\.com/title/(tt\d+)', href)
        if imdb_match:
            return imdb_match.group(1)
    
    return None


def extract_imdb_from_page(doc: BeautifulSoup, content_selectors: Optional[list] = None) -> str:
    """
    Extrai ID do IMDB de uma página HTML.
    
    Busca em múltiplos seletores de conteúdo, priorizando áreas específicas.
    
    Args:
        doc: Documento BeautifulSoup
        content_selectors: Lista de seletores CSS para buscar (opcional)
    
    Returns:
        ID do IMDB (ex: 'tt1234567') ou string vazia
    """
    if not doc:
        return ''
    
    # Seletores padrão se não fornecidos
    if not content_selectors:
        content_selectors = [
            'div#informacoes',      # rede
            'div.entry-content',    # wordpress padrão
            'div.content',          # bludv, comand
            'article',              # genérico
            'div.post',             # starck
            'main',                 # fallback
        ]
    
    imdb = ''
    
    # Busca primeiro por <strong>IMDb</strong> ou <em>IMDb:</em> seguido de link
    # Padrão usado por bludv, comand, tfilme
    imdb_strong = doc.find('strong', string=re.compile(r'IMDb', re.I))
    if imdb_strong:
        parent = imdb_strong.parent
        if parent:
            imdb = extract_imdb_from_element(parent)
            if imdb:
                return imdb
    
    imdb_em = doc.find('em', string=re.compile(r'IMDb:', re.I))
    if imdb_em:
        parent = imdb_em.parent
        if parent:
            imdb = extract_imdb_from_element(parent)
            if imdb:
                return imdb
    
    # Busca nos seletores de conteúdo
    for selector in content_selectors:
        content_div = doc.select_one(selector)
        if content_div:
            imdb = extract_imdb_from_element(content_div)
            if imdb:
                return imdb
    
    # Fallback: busca em todo o documento
    imdb = extract_imdb_from_element(doc)
    
    return imdb or ''

