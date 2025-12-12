"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

import re
import html
import logging
from typing import Optional, Dict, List
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class AudioLanguageParser:
    """
    Parser reutilizável para extrair informações de áudio/idioma/legenda de HTML.
    Centraliza a lógica de parsing que era duplicada em vários scrapers.
    """
    
    @staticmethod
    def extract_from_html(html_content: str, page_html: Optional[BeautifulSoup] = None) -> Dict[str, Optional[str]]:
        """
        Extrai informações de áudio, idioma e legenda do HTML.
        
        Args:
            html_content: HTML como string (pode ser de um parágrafo específico)
            page_html: BeautifulSoup da página completa (opcional, para busca adicional)
            
        Returns:
            Dict com 'audio_info', 'idioma', 'legenda'
        """
        result = {
            'audio_info': None,
            'idioma': '',
            'legenda': ''
        }
        
        # Detecta áudio via função existente
        from utils.text.audio import detect_audio_from_html
        result['audio_info'] = detect_audio_from_html(html_content)
        
        # Extrai idioma
        idioma_patterns = [
            r'(?i)Idioma\s*:\s*([^<\n\r]+?)(?:<br|</div|</p|Legendas?|Qualidade|Duração|Formato|Vídeo|Nota|Tamanho|$)',
            r'(?i)<[^>]*>Idioma\s*:\s*</[^>]*>([^<\n\r]+?)(?:<br|</div|</p|Legendas?|$)',
        ]
        
        for pattern in idioma_patterns:
            match = re.search(pattern, html_content, re.DOTALL)
            if match:
                idioma = match.group(1).strip()
                idioma = html.unescape(idioma)
                idioma = re.sub(r'<[^>]+>', '', idioma).strip()
                idioma = re.sub(r'\s+', ' ', idioma).strip()
                if idioma:
                    result['idioma'] = idioma
                    break
        
        # Extrai legenda
        legenda_patterns = [
            r'(?i)<strong>Legendas?\s*:\s*</strong>\s*(?:<br\s*/?>)?\s*\n\s*([^<\n\r]+?)(?:<br|</div|</p|</strong|Nota|Tamanho|$)',
            r'(?i)<strong>Legendas?\s*:\s*</strong>\s*([^<\n\r]+?)(?:<br|</div|</p|</strong|Nota|Tamanho|$)',
            r'(?i)<b>Legendas?\s*:</b>\s*([^<]+?)(?:<br|</div|</p|</b|Nota|Tamanho|$)',
            r'(?i)Legendas?\s*:\s*([^<\n\r]+?)(?:<br|</div|</p|Nota|Tamanho|Imdb|$)',
            r'(?i)<[^>]*>Legendas?\s*:\s*</[^>]*>([^<\n\r]+?)(?:<br|</div|</p|$)',
        ]
        
        for pattern in legenda_patterns:
            match = re.search(pattern, html_content, re.DOTALL)
            if match:
                legenda = match.group(1).strip()
                legenda = html.unescape(legenda)
                legenda = re.sub(r'<[^>]+>', '', legenda).strip()
                legenda = re.sub(r'\s+', ' ', legenda).strip()
                
                # Remove palavras de parada
                stop_words = ['Nota', 'Tamanho', 'Imdb', 'Vídeo', 'Áudio']
                for stop_word in stop_words:
                    if stop_word in legenda:
                        idx = legenda.index(stop_word)
                        legenda = legenda[:idx].strip()
                        break
                
                if legenda:
                    result['legenda'] = legenda
                    break
        
        return result
    
    @staticmethod
    def determine_audio_tag(idioma: str, legenda: str) -> Optional[str]:
        """
        Determina a tag de áudio baseado em idioma e legenda extraídos.
        
        Args:
            idioma: Idioma extraído
            legenda: Legenda extraída
            
        Returns:
            'dual', 'português', 'legendado' ou None
        """
        if not idioma and not legenda:
            return None
        
        idioma_lower = idioma.lower() if idioma else ''
        legenda_lower = legenda.lower() if legenda else ''
        
        # Verifica se tem português no idioma (áudio)
        has_portugues_audio = 'português' in idioma_lower or 'portugues' in idioma_lower
        # Verifica se tem português na legenda
        has_portugues_legenda = 'português' in legenda_lower or 'portugues' in legenda_lower
        # Verifica se tem Inglês no idioma (áudio)
        has_ingles_audio = 'inglês' in idioma_lower or 'ingles' in idioma_lower or 'english' in idioma_lower
        # Verifica se tem Inglês em qualquer lugar
        has_ingles = has_ingles_audio or 'inglês' in legenda_lower or 'ingles' in legenda_lower or 'english' in legenda_lower
        
        # Lógica: Se tem português E inglês no idioma → DUAL
        if has_portugues_audio and has_ingles_audio:
            return 'dual'
        # Se tem apenas português no idioma → português
        elif has_portugues_audio:
            return 'português'
        # Se tem legenda com português OU tem Inglês → legendado
        elif has_portugues_legenda or has_ingles:
            return 'legendado'
        
        return None


class TitleParser:
    """
    Parser reutilizável para extrair títulos (original e traduzido) de HTML.
    Centraliza a lógica de parsing que era duplicada em vários scrapers.
    """
    
    @staticmethod
    def extract_original_title(soup: BeautifulSoup, patterns: Optional[List[str]] = None) -> str:
        """
        Extrai título original do HTML usando padrões configuráveis.
        
        Args:
            soup: BeautifulSoup da página
            patterns: Lista de padrões regex opcionais (usa padrões default se None)
            
        Returns:
            Título original extraído ou string vazia
        """
        if patterns is None:
            patterns = [
                r'Título Original:\s*([^\n\r]{1,200}?)(?:\s*(?:Gênero|Ano|Duração|Direção|Elenco|Sinopse|$))',
                r'Nome Original:\s*([^\n\r]{1,200}?)(?:\s*(?:Gênero|Ano|Duração|Direção|Elenco|Sinopse|$))',
            ]
        
        # Busca em todos os parágrafos
        for p in soup.select('p'):
            text = p.get_text()
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    title = match.group(1).strip()
                    title = title.rstrip(' .,:;-')
                    if title:
                        return title
        
        return ''
    
    @staticmethod
    def extract_translated_title(soup: BeautifulSoup, patterns: Optional[List[str]] = None) -> str:
        """
        Extrai título traduzido do HTML usando padrões configuráveis.
        
        Args:
            soup: BeautifulSoup da página
            patterns: Lista de padrões regex opcionais (usa padrões default se None)
            
        Returns:
            Título traduzido extraído ou string vazia
        """
        if patterns is None:
            patterns = [
                r'Título Traduzido:\s*([^\n\r]{1,200}?)(?:\s*(?:Gênero|Ano|Duração|Direção|Elenco|Sinopse|Título Original|$))',
                r'Titulo Traduzido:\s*([^\n\r]{1,200}?)(?:\s*(?:Gênero|Ano|Duração|Direção|Elenco|Sinopse|Título Original|$))',
            ]
        
        # Busca em todos os parágrafos
        for p in soup.select('p'):
            # Remove tags HTML internas
            for tag in p.find_all(['strong', 'em', 'b', 'i']):
                tag.unwrap()
            
            text = p.get_text()
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    title = match.group(1).strip()
                    title = html.unescape(title)
                    title = re.sub(r'<[^>]+>', '', title)  # Remove HTML residual
                    title = title.rstrip(' .,:;-')
                    
                    # Limpeza adicional
                    from utils.text.cleaning import clean_translated_title
                    title = clean_translated_title(title)
                    
                    if title:
                        return title
        
        return ''
    
    @staticmethod
    def extract_imdb_id(soup: BeautifulSoup, priority_div_id: Optional[str] = None) -> str:
        """
        Extrai IMDB ID do HTML.
        
        Args:
            soup: BeautifulSoup da página
            priority_div_id: ID de div com prioridade para busca (opcional)
            
        Returns:
            IMDB ID (ex: 'tt1234567') ou string vazia
        """
        # Busca prioritária em div específica
        if priority_div_id:
            priority_div = soup.find('div', id=priority_div_id)
            if priority_div:
                for a in priority_div.select('a'):
                    href = a.get('href', '')
                    if 'imdb.com' in href:
                        # Tenta padrão /pt/title/tt
                        match = re.search(r'imdb\.com/pt/title/(tt\d+)', href)
                        if match:
                            return match.group(1)
                        # Tenta padrão /title/tt
                        match = re.search(r'imdb\.com/title/(tt\d+)', href)
                        if match:
                            return match.group(1)
        
        # Busca em toda a página
        for a in soup.select('a'):
            href = a.get('href', '')
            if 'imdb.com' in href:
                # Tenta padrão /pt/title/tt
                match = re.search(r'imdb\.com/pt/title/(tt\d+)', href)
                if match:
                    return match.group(1)
                # Tenta padrão /title/tt
                match = re.search(r'imdb\.com/title/(tt\d+)', href)
                if match:
                    return match.group(1)
        
        return ''


class MagnetLinkExtractor:
    """
    Extrator reutilizável de links magnet de HTML.
    Centraliza a lógica de extração e resolução de links protegidos.
    """
    
    @staticmethod
    def extract_all_magnets(soup: BeautifulSoup, resolve_func) -> List[str]:
        """
        Extrai todos os links magnet de um BeautifulSoup.
        
        Args:
            soup: BeautifulSoup da página
            resolve_func: Função para resolver links (magnet direto ou protegido)
            
        Returns:
            Lista de magnet links únicos
        """
        magnet_links = []
        
        for link in soup.select('a[href]'):
            href = link.get('href', '')
            if not href:
                continue
            
            # Resolve automaticamente (magnet direto ou protegido)
            resolved_magnet = resolve_func(href)
            if resolved_magnet and resolved_magnet.startswith('magnet:') and resolved_magnet not in magnet_links:
                magnet_links.append(resolved_magnet)
        
        return magnet_links

