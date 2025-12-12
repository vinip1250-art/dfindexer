"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

import html
import re
from utils.text.constants import (
    RELEASE_CLEAN_REGEX,
    REGEX_MULTIPLE_SPACES,
    REGEX_MULTIPLE_DOTS,
    REGEX_LEADING_TRAILING_DOTS,
    REGEX_SPACE_AROUND_DOTS,
    REGEX_HTML_TAGS,
    REGEX_TITULO_TRADUZIDO_START,
    REGEX_TITULO_TRADUZIDO_MIDDLE,
    REGEX_ORDINAL_ENTITIES,
    REGEX_TEMPORADA_ORDINAL,
    REGEX_TEMPORADA_ORDINAL_ALT,
    REGEX_SEASON_EPISODE,
    REGEX_TEMPORADA_WORD,
    REGEX_TORRENT_WORD,
    REGEX_COMPLETA_NUMBER,
    REGEX_COMPLETA_WORD,
    REGEX_COMPLETA_STANDALONE,
    REGEX_AUDIO_WORDS,
    REGEX_SITE_WORDS,
)


# Remove acentos e cedilha de caracteres latinos e normaliza caracteres turcos
def remove_accents(text: str) -> str:
    replacements = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n',
        'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A', 'Ä': 'A',
        'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
        'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
        'Ó': 'O', 'Ò': 'O', 'Õ': 'O', 'Ô': 'O', 'Ö': 'O',
        'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
        'Ç': 'C', 'Ñ': 'N',
        # Caracteres turcos
        'İ': 'I',  # I maiúsculo com ponto → I maiúsculo normal
        'ı': 'i',  # i minúsculo sem ponto → i minúsculo normal
        'ş': 's', 'Ş': 'S',
        'ğ': 'g', 'Ğ': 'G',
        'ü': 'u', 'Ü': 'U',
        'ö': 'o', 'Ö': 'O'
    }
    return ''.join(replacements.get(c, c) for c in text)


# Remove tags de sites, múltiplos espaços/pontos e normaliza o título
def clean_title(title: str) -> str:
    cleaned = RELEASE_CLEAN_REGEX.sub('', title)
    cleaned = REGEX_MULTIPLE_SPACES.sub(' ', cleaned)
    cleaned = REGEX_MULTIPLE_DOTS.sub('.', cleaned)
    cleaned = REGEX_LEADING_TRAILING_DOTS.sub('', cleaned)
    cleaned = REGEX_SPACE_AROUND_DOTS.sub('.', cleaned)
    return cleaned.strip()


def clean_translated_title(translated_title: str) -> str:
    # Limpa o título traduzido removendo tags HTML, temporadas, anos e textos extras
    if not translated_title:
        return ''
    
    # Converte para string se não for
    translated_title = str(translated_title)
    
    # Remove todas as tags HTML (incluindo <strong>, <em>, <b>, <br />, <span>, <h1>, <title>, etc.)
    # Faz múltiplas passadas para garantir remoção completa
    while REGEX_HTML_TAGS.search(translated_title):
        translated_title = REGEX_HTML_TAGS.sub('', translated_title)
    
    # Remove entidades HTML (como &ordf;, &nbsp;, &amp;, etc.)
    translated_title = html.unescape(translated_title)
    
    # Remove "Título Traduzido:" se ainda estiver presente (pode estar em diferentes formatos)
    translated_title = REGEX_TITULO_TRADUZIDO_START.sub('', translated_title)
    translated_title = REGEX_TITULO_TRADUZIDO_MIDDLE.sub('', translated_title)
    
    # Remove entidades HTML específicas de temporada (&ordf;, &ordm;, etc.) ANTES de remover temporada
    translated_title = REGEX_ORDINAL_ENTITIES.sub('', translated_title)
    translated_title = html.unescape(translated_title)  # Decodifica novamente após remover entidades
    
    # Remove informações de temporada (Sxx, Temporada, etc.) - múltiplos formatos
    # Remove padrões como "1ª Temporada", "2ª Temporada", "3ª Temporada", etc.
    translated_title = REGEX_TEMPORADA_ORDINAL.sub('', translated_title)
    translated_title = REGEX_TEMPORADA_ORDINAL_ALT.sub('', translated_title)
    translated_title = REGEX_SEASON_EPISODE.sub('', translated_title)
    translated_title = REGEX_TEMPORADA_WORD.sub('', translated_title)
    
    # Remove "Torrent" após temporada (ex: "2ª Temporada Torrent")
    translated_title = REGEX_TORRENT_WORD.sub('', translated_title)
    
    # Remove "Completa" ou "Completo" do título base
    # NOTA: "Completo/Completa" só faz sentido em séries (temporadas completas), não em filmes
    # Em filmes, apenas remove do título base. Em séries, será tratado como temporada completa depois
    # Remove quando está colada a número: "2Completa" -> "2" (será tratado como temporada completa se houver temporada)
    translated_title = REGEX_COMPLETA_NUMBER.sub(r'\1', translated_title)
    # Remove quando está colada ao título: "FatehCompleto" -> "Fateh" (filme, apenas remove)
    translated_title = REGEX_COMPLETA_WORD.sub(r'\1', translated_title)
    # Remove quando está separada: "Completa" ou "Completo" (standalone)
    translated_title = REGEX_COMPLETA_STANDALONE.sub('', translated_title)
    
    # Remove palavras relacionadas a áudio/legenda que serão substituídas por tags [Brazilian], [Eng], [Leg]
    # Remove DUBLADO, DUBLADO, NACIONAL, PORTUGUES (será substituído por [Brazilian])
    translated_title = REGEX_AUDIO_WORDS.sub('', translated_title)
    # Remove LEGENDADO, LEGENDA, LEG (será substituído por [Leg])
    translated_title = re.sub(r'(?i)\b(?:Legendado|LEGENDADO|Legenda|LEGENDA|Leg|LEG)\b', '', translated_title)
    # Remove DUAL (será substituído por [Brazilian] e [Eng])
    translated_title = re.sub(r'(?i)\b(?:Dual|DUAL)\b', '', translated_title)
    
    # Remove palavras comuns de sites que não fazem parte do título
    # Remove "Download", "Assistir", "Online", "Torrent" (já removido acima, mas garante)
    translated_title = REGEX_SITE_WORDS.sub('', translated_title)
    
    # Remove anos entre parênteses (ex: (2015-2025), (2025))
    translated_title = re.sub(r'\s*\([0-9]{4}(?:-[0-9]{4})?\)\s*', '', translated_title)
    # Remove anos soltos no final (ex: "2025")
    translated_title = re.sub(r'\s+(19|20)\d{2}\s*$', '', translated_title)
    
    # Remove textos extras de sites (padrões genéricos)
    # Remove padrões como "2025 — Site Torrent – Baixe Filmes e Séries"
    translated_title = re.sub(r'(?i)\s*—\s*[^—]+Torrent\s*–\s*Baixe\s+Filmes\s+e\s+S[ée]ries\s*$', '', translated_title)
    translated_title = re.sub(r'(?i)\s*—\s*[^—]+$', '', translated_title)  # Remove "— Site Torrent – Baixe..."
    translated_title = re.sub(r'(?i)\s*–\s*[^–]+$', '', translated_title)  # Remove "– Baixe Filmes..."
    translated_title = re.sub(r'(?i)\s*Baixe\s+Filmes\s+e\s+S[ée]ries\s*', '', translated_title)
    
    # Remove campos que podem ter sido concatenados incorretamente
    # Remove "Titulo Original:" e tudo depois (com ou sem acento, com ou sem espaço antes)
    translated_title = re.sub(r'(?i).*?T[íi]tulo\s+Original:.*$', '', translated_title)
    # Remove "IMDb:" e tudo depois
    translated_title = re.sub(r'(?i).*?IMDb:.*$', '', translated_title)
    # Remove "Lançamento" e tudo depois
    translated_title = re.sub(r'(?i).*?Lançamento.*$', '', translated_title)
    
    # Remove palavras duplicadas consecutivas (ex: "FatehFateh" -> "Fateh", "Fateh Fateh" -> "Fateh")
    # Remove duplicações coladas (sem espaço)
    translated_title = re.sub(r'([A-Za-z]+)\1+', r'\1', translated_title, flags=re.IGNORECASE)
    # Remove duplicações com espaço (case-insensitive)
    words = translated_title.split()
    if len(words) > 1:
        deduplicated_words = []
        prev_word_lower = None
        for word in words:
            word_lower = word.lower()
            if word_lower != prev_word_lower:
                deduplicated_words.append(word)
                prev_word_lower = word_lower
        translated_title = ' '.join(deduplicated_words)
    
    # Remove caracteres especiais do final
    translated_title = translated_title.rstrip(' .,:;—–-')
    
    # Normaliza espaços
    translated_title = re.sub(r'\s+', ' ', translated_title).strip()
    
    return translated_title

