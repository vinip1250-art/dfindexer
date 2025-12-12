"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

import re
from typing import Optional


# Detecta informações de áudio a partir do HTML da página
# Retorna: 'dual', 'português', 'legendado', ou None
def detect_audio_from_html(html_content: str) -> Optional[str]:
    """
    Detecta informações de áudio a partir do conteúdo HTML.
    
    Args:
        html_content: Conteúdo HTML onde buscar informações de áudio
        
    Returns:
        'dual': Se tem português E multi-áudio/inglês
        'português': Se tem apenas português
        'legendado': Se tem apenas legendado (sem português no áudio)
        None: Se não encontrou informações de áudio
    """
    if not html_content:
        return None
    
    # Verifica se tem "Português" no áudio/idioma
    has_portugues = re.search(r'(?i)(?:Áudio|Idioma)\s*:?\s*.*Português', html_content)
    has_multi = re.search(r'(?i)Multi-?Áudio|Multi-?Audio', html_content)
    # Verifica se tem "Inglês" no áudio/idioma (não apenas na legenda)
    has_ingles_audio = re.search(r'(?i)(?:Áudio|Idioma)\s*:?\s*.*(?:Inglês|Ingles|English)', html_content)
    has_ingles = re.search(r'(?i)Inglês|Ingles|English', html_content)
    
    # Verifica se tem "Legendado" na legenda (sem português no áudio)
    has_legenda_legendado = re.search(r'(?i)Legenda\s*:?\s*.*Legendado', html_content)
    has_legenda_ingles = re.search(r'(?i)Legenda\s*:?\s*.*(?:Inglês|Ingles|English)', html_content)
    # Verifica se tem português na legenda (PT-BR, Português, etc.)
    has_legenda_portugues = re.search(r'(?i)Legenda\s*:?\s*.*(?:PT-BR|PTBR|Português|Portugues|PT)', html_content)
    
    # Se tem português no áudio
    if has_portugues:
        if has_multi or has_ingles_audio or has_ingles:
            # Tem português E multi-áudio/inglês = DUAL
            return 'dual'
        else:
            # Apenas português
            return 'português'
    
    # Se tem inglês no áudio/idioma E legenda em português → legendado (mas também indica inglês)
    if has_ingles_audio and has_legenda_portugues:
        return 'legendado'  # Será tratado como legendado, mas add_audio_tag_if_needed detectará inglês
    
    # Se não tem português no áudio, mas tem legendado na legenda (PT-BR, Legendado, ou Inglês)
    if has_legenda_legendado or has_legenda_portugues or (has_legenda_ingles and not has_portugues):
        return 'legendado'
    
    return None


# Acrescenta tags de idioma [Brazilian], [Eng], [Jap] e/ou [Leg] quando detectadas no release, metadata ou HTML
def add_audio_tag_if_needed(title: str, release_title_magnet: str, info_hash: Optional[str] = None, skip_metadata: bool = False, audio_info_from_html: Optional[str] = None, audio_html_content: Optional[str] = None) -> str:
    # Remove apenas as tags que queremos usar antes de processar
    title = title.replace('[Brazilian]', '').replace('[Eng]', '').replace('[Jap]', '').replace('[Leg]', '')
    title = re.sub(r'\s+', ' ', title).strip()
    
    # Verifica se já tem as tags corretas no título
    has_brazilian = '[Brazilian]' in title
    has_eng = '[Eng]' in title
    has_jap = '[Jap]' in title
    has_leg = '[Leg]' in title
    
    # Tenta detectar áudio no release_title_magnet primeiro
    has_brazilian_audio = False
    has_legendado = False
    has_dual = False
    has_japones_audio = False
    
    if release_title_magnet:
        release_lower = release_title_magnet.lower()
        # Detecta DUAL (português + inglês)
        if 'dual' in release_lower:
            has_dual = True
            has_brazilian_audio = True  # DUAL também indica português
        # Detecta português (DUBLADO, NACIONAL, PORTUGUES, PORTUGUÊS)
        elif 'dublado' in release_lower or 'nacional' in release_lower or 'portugues' in release_lower or 'português' in release_lower:
            has_brazilian_audio = True
        # Detecta japonês (JAPONÊS, JAPONES, JAPANESE, JAP)
        if 'japonês' in release_lower or 'japones' in release_lower or 'japanese' in release_lower or re.search(r'\bjap\b', release_lower):
            has_japones_audio = True
        # Detecta legendado (LEGENDADO, LEGENDA, LEG)
        if 'legendado' in release_lower or 'legenda' in release_lower or re.search(r'\bleg\b', release_lower):
            has_legendado = True
    
    # Se não encontrou no release_title_magnet e temos info_hash, tenta buscar no cross_data primeiro (evita consulta desnecessária ao metadata)
    if info_hash and not skip_metadata:
        try:
            from utils.text.cross_data import get_cross_data_from_redis
            cross_data = get_cross_data_from_redis(info_hash)
            if cross_data and cross_data.get('release_title_magnet'):
                cross_release = cross_data.get('release_title_magnet')
                if cross_release and cross_release != 'N/A':
                    cross_release_lower = str(cross_release).lower()
                    # Detecta DUAL no cross_data
                    if not has_dual and 'dual' in cross_release_lower:
                        has_dual = True
                        has_brazilian_audio = True  # DUAL também indica português
                    # Detecta português no cross_data (DUBLADO, NACIONAL, PORTUGUES, PORTUGUÊS)
                    elif not has_brazilian_audio and ('dublado' in cross_release_lower or 'nacional' in cross_release_lower or 'portugues' in cross_release_lower or 'português' in cross_release_lower):
                        has_brazilian_audio = True
                    # Detecta japonês no cross_data
                    if not has_japones_audio and ('japonês' in cross_release_lower or 'japones' in cross_release_lower or 'japanese' in cross_release_lower or re.search(r'\bjap\b', cross_release_lower)):
                        has_japones_audio = True
                    # Detecta legendado no cross_data
                    if not has_legendado and ('legendado' in cross_release_lower or 'legenda' in cross_release_lower or re.search(r'\bleg\b', cross_release_lower)):
                        has_legendado = True
        except Exception:
            pass
            
        # Só busca no metadata se ainda não encontrou todas as informações necessárias
        if not has_dual and not has_brazilian_audio and not has_japones_audio and not has_legendado:
            try:
                from magnet.metadata import fetch_metadata_from_itorrents
                metadata = fetch_metadata_from_itorrents(info_hash)
                if metadata and metadata.get('name'):
                    metadata_name = metadata.get('name', '').lower()
                    # Detecta DUAL no metadata
                    if not has_dual and 'dual' in metadata_name:
                        has_dual = True
                        has_brazilian_audio = True  # DUAL também indica português
                    # Detecta português no metadata (DUBLADO, NACIONAL, PORTUGUES, PORTUGUÊS)
                    elif not has_brazilian_audio and ('dublado' in metadata_name or 'nacional' in metadata_name or 'portugues' in metadata_name or 'português' in metadata_name):
                        has_brazilian_audio = True
                    # Detecta japonês no metadata
                    if not has_japones_audio and ('japonês' in metadata_name or 'japones' in metadata_name or 'japanese' in metadata_name or re.search(r'\bjap\b', metadata_name)):
                        has_japones_audio = True
                    # Detecta legendado no metadata
                    if not has_legendado and ('legendado' in metadata_name or 'legenda' in metadata_name or re.search(r'\bleg\b', metadata_name)):
                        has_legendado = True
            except Exception:
                pass
    
    # Processa detecção via HTML (audio_info_from_html)
    # [Eng] só é adicionada quando detectado via HTML como 'dual' ou quando detecta DUAL em qualquer fonte
    has_eng_from_html = False
    if audio_info_from_html == 'dual':
        has_dual = True
        has_brazilian_audio = True  # DUAL também indica português
    
    # Verifica diretamente no HTML para tags independentes
    # Se há "Idioma: Inglês" no HTML → adiciona [Eng] (independente de ter legenda ou não)
    # Se há "Áudio: Japonês" no HTML → adiciona [Jap] (independente de ter legenda ou não)
    # Se há "Legenda: PT-BR" no HTML → adiciona [Leg] (independente de ter inglês ou não)
    if audio_html_content:
        # Verifica se há inglês no áudio/idioma
        has_ingles_audio_html = re.search(r'(?i)(?:Áudio|Idioma)\s*:?\s*.*(?:Inglês|Ingles|English)', audio_html_content)
        if has_ingles_audio_html:
            has_eng_from_html = True
        
        # Verifica se há japonês no áudio/idioma
        has_japones_audio_html = re.search(r'(?i)(?:Áudio|Idioma)\s*:?\s*.*(?:Japonês|Japones|Japanese)', audio_html_content)
        if has_japones_audio_html:
            has_japones_audio = True
        
        # Verifica se há legenda PT-BR
        has_legenda_portugues_html = re.search(r'(?i)Legenda\s*:?\s*.*(?:PT-BR|PTBR|Português|Portugues|PT)', audio_html_content)
        if has_legenda_portugues_html:
            has_legendado = True
    
    # Se detectado via HTML como 'legendado' (fallback quando não tem audio_html_content)
    if audio_info_from_html == 'legendado' and not has_legendado:
        has_legendado = True
        # Se não tem audio_html_content, tenta detectar inglês no release_title
        if not audio_html_content and not has_eng_from_html:
            if release_title_magnet:
                release_lower = release_title_magnet.lower()
                # Se não tem português/dublado/nacional no release_title, assume inglês quando há legenda PT-BR via HTML
                if ('português' not in release_lower and 'dublado' not in release_lower and 'nacional' not in release_lower and 
                    'portugues' not in release_lower):
                    has_eng_from_html = True
            else:
                # Se não tem release_title, assume inglês quando há legenda PT-BR via HTML
                has_eng_from_html = True
    
    # Se detectado via HTML como 'português', adiciona [Brazilian]
    if audio_info_from_html == 'português':
        has_brazilian_audio = True
    
    # Se detectado via HTML como 'japonês', adiciona [Jap]
    if audio_info_from_html == 'japonês':
        has_japones_audio = True
    
    # Se detectou DUAL (via HTML, release_title ou metadata), adiciona [Eng]
    if has_dual:
        has_eng_from_html = True
    
    # Adiciona tags conforme detectado
    tags_to_add = []
    if has_brazilian_audio and not has_brazilian:
        tags_to_add.append('[Brazilian]')
    if has_eng_from_html and not has_eng:
        tags_to_add.append('[Eng]')
    if has_japones_audio and not has_jap:
        tags_to_add.append('[Jap]')
    if has_legendado and not has_leg:
        tags_to_add.append('[Leg]')
    
    # Remove DUAL, DUBLADO, NACIONAL, PORTUGUES, LEGENDADO do título se as tags correspondentes foram adicionadas
    # (não precisa manter no título se a tag já indica o tipo de áudio)
    if tags_to_add:
        # Remove DUAL se [Brazilian] ou [Eng] foi adicionado
        if '[Brazilian]' in tags_to_add or '[Eng]' in tags_to_add:
            # Remove DUAL (case insensitive, com pontos antes/depois)
            title = re.sub(r'\.?\.?DUAL\.?\.?', '.', title, flags=re.IGNORECASE)
            title = re.sub(r'\.{2,}', '.', title)  # Remove pontos duplicados
            title = title.strip('.')
        # Remove DUBLADO, NACIONAL, PORTUGUES se [Brazilian] foi adicionado
        if '[Brazilian]' in tags_to_add:
            title = re.sub(r'\.?\.?DUBLADO\.?\.?', '.', title, flags=re.IGNORECASE)
            title = re.sub(r'\.?\.?NACIONAL\.?\.?', '.', title, flags=re.IGNORECASE)
            title = re.sub(r'\.?\.?PORTUGUES\.?\.?', '.', title, flags=re.IGNORECASE)
            title = re.sub(r'\.?\.?PORTUGUÊS\.?\.?', '.', title, flags=re.IGNORECASE)
            title = re.sub(r'\.{2,}', '.', title)
            title = title.strip('.')
        # Remove JAPONÊS, JAPONES, JAPANESE, JAP se [Jap] foi adicionado
        if '[Jap]' in tags_to_add:
            title = re.sub(r'\.?\.?JAPONÊS\.?\.?', '.', title, flags=re.IGNORECASE)
            title = re.sub(r'\.?\.?JAPONES\.?\.?', '.', title, flags=re.IGNORECASE)
            title = re.sub(r'\.?\.?JAPANESE\.?\.?', '.', title, flags=re.IGNORECASE)
            title = re.sub(r'\.?\.?JAP\.?\.?', '.', title, flags=re.IGNORECASE)
            title = re.sub(r'\.{2,}', '.', title)
            title = title.strip('.')
        # Remove LEGENDADO se [Leg] foi adicionado
        if '[Leg]' in tags_to_add:
            title = re.sub(r'\.?\.?LEGENDADO\.?\.?', '.', title, flags=re.IGNORECASE)
            title = re.sub(r'\.?\.?LEGENDA\.?\.?', '.', title, flags=re.IGNORECASE)
            title = re.sub(r'\.?\.?LEG\.?\.?', '.', title, flags=re.IGNORECASE)
            title = re.sub(r'\.{2,}', '.', title)
            title = title.strip('.')
        
        title = title.rstrip()
        title = f"{title} {' '.join(tags_to_add)}"

    result = title
    return result

