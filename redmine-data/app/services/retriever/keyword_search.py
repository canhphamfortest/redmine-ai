"""Full-text search với PostgreSQL.

Module này cung cấp keyword search sử dụng PostgreSQL full-text search:
- STOPWORDS: Danh sách stopwords tiếng Việt và tiếng Anh
- remove_stopwords: Loại bỏ stopwords từ query, sử dụng underthesea để extract keywords
- build_fts_query: Build OR query cho PostgreSQL tsquery
- keyword_search: Thực hiện full-text search và trả về kết quả

Sử dụng GIN index với to_tsvector('simple', text_content) để tìm kiếm nhanh.
Sử dụng underthesea để:
- Tách từ tiếng Việt chính xác (word_tokenize)
- Phân tích POS tags (N, V, A, Np) để ưu tiên từ quan trọng
- Nhận diện tên riêng (NER: PER, LOC, ORG) để tăng điểm

Không sử dụng AI model (sentence-transformers) vì underthesea + heuristic đã đủ tốt,
nhanh hơn và nhẹ hơn.
"""
import logging
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Lazy loading cho underthesea
_underthesea_available = None


# Stopwords - các từ phổ biến không mang ý nghĩa search
# Có thể mở rộng dựa trên thực tế sử dụng
STOPWORDS = {
    # Tiếng Việt - các từ phổ biến không mang ý nghĩa search
    'tìm', 'kiếm', 'các', 'của', 'và', 'là', 'có', 'được', 'trong',
    'cho', 'với', 'này', 'đó', 'thì', 'mà', 'để', 'từ', 'đến', 'về',
    'như', 'khi', 'nếu', 'nhưng', 'hay', 'hoặc', 'vì', 'bởi', 'theo',
    'những', 'một', 'nhiều', 'ít', 'ra', 'vào', 'lên', 'xuống',
    'trên', 'dưới', 'ngoài', 'sau', 'trước', 'giữa', 'đã', 'đang',
    'sẽ', 'còn', 'nên', 'cần', 'phải', 'bị', 'làm', 'gì', 'nào',
    'sao', 'ai', 'đâu', 'bao', 'lại', 'cũng', 'vẫn', 'chỉ', 'rồi',
    'mới', 'đều', 'hết', 'rất', 'quá', 'lắm', 'nhất',
    'tôi', 'ta', 'mình', 'bạn', 'anh', 'chị', 'em', 'ông', 'bà',
    'muốn', 'cần', 'phải', 'nên', 'sẽ', 'đang', 'đã',
    'thuộc', 'nó', 'dùng',  # Thêm các từ còn thiếu
    # Tiếng Anh
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'to', 'of', 'for', 'with', 'in', 'on', 'at', 'by', 'from',
    'or', 'and', 'not', 'this', 'that', 'these', 'those',
    'it', 'its', 'as', 'so', 'if', 'then', 'than', 'but',
    'find', 'search', 'get', 'show', 'list', 'all', 'any', 'some',
    'has', 'have', 'had', 'do', 'does', 'did', 'will', 'would',
    'can', 'could', 'may', 'might', 'must', 'shall', 'should',
    'what', 'which', 'who', 'whom', 'where', 'when', 'why', 'how',
}

# POS tags quan trọng từ underthesea (ưu tiên cao)
# N: Danh từ, V: Động từ, A: Tính từ, Np: Tên riêng
IMPORTANT_POS_TAGS = {'N', 'V', 'A', 'Np'}

# NER tags quan trọng (tên riêng - rất quan trọng trong search)
# PER: Person, LOC: Location, ORG: Organization
IMPORTANT_NER_TAGS = {'B-PER', 'I-PER', 'B-LOC', 'I-LOC', 'B-ORG', 'I-ORG'}


def _ensure_underthesea():
    """Đảm bảo underthesea đã được import và khả dụng.
    
    Returns:
        tuple: (word_tokenize, pos_tag, ner) hoặc (None, None, None) nếu không khả dụng
    """
    global _underthesea_available
    
    if _underthesea_available is None:
        try:
            from underthesea import word_tokenize, pos_tag, ner
            _underthesea_available = {
                'word_tokenize': word_tokenize,
                'pos_tag': pos_tag,
                'ner': ner
            }
            logger.debug("Underthesea loaded successfully")
        except ImportError:
            logger.debug("Underthesea not available, using regex fallback")
            _underthesea_available = False
        except Exception as e:
            logger.warning(f"Failed to load underthesea: {e}, using regex fallback")
            _underthesea_available = False
    
    if _underthesea_available is False:
        return None, None, None
    
    return (
        _underthesea_available.get('word_tokenize'),
        _underthesea_available.get('pos_tag'),
        _underthesea_available.get('ner')
    )


def _tokenize_with_underthesea(text: str) -> List[str]:
    """Tokenize text sử dụng underthesea.word_tokenize, fallback về regex.
    
    Args:
        text: Chuỗi text cần tokenize
    
    Returns:
        List[str]: Danh sách các từ đã được tách (bao gồm cả từ có dấu gạch ngang)
    """
    word_tokenize_func, _, _ = _ensure_underthesea()
    
    if word_tokenize_func:
        try:
            tokens = word_tokenize_func(text)
            # Underthesea trả về list, filter các token hợp lệ
            words = []
            for token in tokens:
                token = token.strip()
                if token and len(token) > 0:
                    # Cho phép chữ cái, số, ký tự tiếng Việt, và dấu gạch ngang (cho từ ghép như "sub-issue")
                    # Pattern: chữ cái/số/tiếng Việt, có thể có dấu gạch ngang ở giữa
                    if re.match(r'^[\w\u00C0-\u1EF9]+(-[\w\u00C0-\u1EF9]+)*$', token, re.UNICODE):
                        words.append(token)
            return words
        except Exception as e:
            logger.debug(f"Underthesea tokenization failed: {e}, using regex fallback")
    
    # Fallback: sử dụng regex - cải thiện để giữ từ có dấu gạch ngang
    # Tìm các từ có thể có dấu gạch ngang: word, word-word, word-word-word, etc.
    return re.findall(r'\b[\w\u00C0-\u1EF9]+(?:-[\w\u00C0-\u1EF9]+)+\b|\b[\w\u00C0-\u1EF9]+\b', text, re.UNICODE)


def _get_pos_tags(text: str) -> Dict[str, str]:
    """Lấy POS tags cho các từ trong text sử dụng underthesea.
    
    Args:
        text: Chuỗi text cần phân tích
    
    Returns:
        Dict[str, str]: Dictionary mapping từ/cụm từ -> POS tag
    """
    _, pos_tag_func, _ = _ensure_underthesea()
    
    if pos_tag_func:
        try:
            pos_tags = pos_tag_func(text)
            # pos_tag trả về list of tuples: [('từ', 'POS'), ...]
            # Có thể là từ đơn hoặc cụm từ (ví dụ: 'nổi tiếng', 'Sài Gòn')
            result = {}
            for word, tag in pos_tags:
                word_lower = word.lower()
                # Lưu tag của từ/cụm từ (nếu có nhiều từ cùng, lấy tag đầu tiên)
                if word_lower not in result:
                    result[word_lower] = tag
                
                # Nếu là cụm từ, cũng lưu tag cho từng từ đơn trong cụm từ
                if ' ' in word:
                    for single_word in word.split():
                        single_word_lower = single_word.lower()
                        if single_word_lower not in result:
                            result[single_word_lower] = tag
            return result
        except Exception as e:
            logger.debug(f"Underthesea POS tagging failed: {e}")
    
    return {}


def _get_ner_entities(text: str) -> Dict[str, str]:
    """Lấy Named Entity Recognition tags cho các từ trong text.
    
    Args:
        text: Chuỗi text cần phân tích
    
    Returns:
        Dict[str, str]: Dictionary mapping từ/cụm từ -> NER tag (PER, LOC, ORG, etc.)
    """
    _, _, ner_func = _ensure_underthesea()
    
    if ner_func:
        try:
            ner_tags = ner_func(text)
            # ner trả về list of tuples: [('từ', 'POS', 'Chunk', 'NER'), ...]
            # Có thể là từ đơn hoặc cụm từ (ví dụ: 'Việt Nam', 'Donald Trump')
            result = {}
            for word, pos, chunk, ner_tag in ner_tags:
                word_lower = word.lower()
                # Lưu NER tag của từ/cụm từ (nếu có nhiều từ cùng, lấy tag đầu tiên)
                if word_lower not in result and ner_tag != 'O':
                    result[word_lower] = ner_tag
                
                # Nếu là cụm từ có NER tag, cũng lưu tag cho từng từ đơn trong cụm từ
                if ' ' in word and ner_tag != 'O':
                    for single_word in word.split():
                        single_word_lower = single_word.lower()
                        if single_word_lower not in result:
                            result[single_word_lower] = ner_tag
            return result
        except Exception as e:
            logger.debug(f"Underthesea NER failed: {e}")
    
    return {}


def remove_stopwords(query: str, max_words: int = 10) -> List[str]:
    """Loại bỏ stopwords và trả về list từ quan trọng sử dụng underthesea.
    
    Hàm này sử dụng underthesea (POS tags, NER tags) kết hợp với heuristic
    để extract các từ quan trọng từ query, loại bỏ stopwords và trả về
    tối đa max_words từ quan trọng nhất.
    
    Args:
        query: Chuỗi query từ người dùng (string)
        max_words: Số lượng từ tối đa cần trả về (mặc định: 10)
    
    Returns:
        List[str]: Danh sách các từ quan trọng (không có stopwords, length > 1),
                  tối đa max_words từ, được sắp xếp theo độ quan trọng
    
    Example:
        >>> remove_stopwords("Tìm các issue của Pham Ngoc Canh về bug fix")
        ['issue', 'pham', 'ngoc', 'canh', 'bug', 'fix']
    """
    return _extract_keywords_with_phrases(query, max_words)


def _is_meaningless_phrase(phrase: str, pos_tags: Dict[str, str] = None, ner_tags: Dict[str, str] = None) -> bool:
    """Kiểm tra xem cụm từ có phải là cụm từ không có nghĩa không.
    
    Logic cải thiện: Loại bỏ cụm từ không có từ quan trọng (POS/NER tags).
    Với underthesea, POS tags và NER tags đã xử lý phần lớn việc phát hiện cụm từ có nghĩa.
    
    Args:
        phrase: Cụm từ cần kiểm tra
        pos_tags: Dictionary mapping từ -> POS tag (optional)
        ner_tags: Dictionary mapping từ -> NER tag (optional)
    
    Returns:
        bool: True nếu cụm từ rõ ràng không có nghĩa, False nếu có thể có nghĩa
    """
    words = phrase.lower().split()
    
    # Nếu có POS/NER tags, kiểm tra xem cụm từ có từ quan trọng không
    if pos_tags or ner_tags:
        has_important_word = False
        for word in words:
            # Kiểm tra POS tag
            if pos_tags and pos_tags.get(word, '') in IMPORTANT_POS_TAGS:
                has_important_word = True
                break
            # Kiểm tra NER tag
            if ner_tags and ner_tags.get(word, '') in IMPORTANT_NER_TAGS:
                has_important_word = True
                break
        
        # Nếu cụm từ không có từ quan trọng nào, có thể không có nghĩa
        if not has_important_word:
            return True
    
    # Loại bỏ cụm từ chỉ gồm các từ quá ngắn (<= 2 ký tự mỗi từ)
    if len(words) >= 2:
        all_words_very_short = all(len(w) <= 2 for w in words)
        if all_words_very_short:
            return True
    
    # Mặc định: Không loại bỏ
    return False


def _extract_candidates_with_phrases(query: str) -> List[str]:
    """Extract candidates bao gồm cả từ đơn và cụm từ từ query.
    
    Logic cải thiện với underthesea:
    - Sử dụng word_tokenize để tách từ chính xác hơn
    - Sử dụng POS tags để ưu tiên danh từ, động từ, tính từ, tên riêng
    - Sử dụng NER để nhận diện tên riêng (PER, LOC, ORG)
    - Ưu tiên trigrams trước (cụm từ 3 từ)
    - Loại bỏ các cụm từ không có nghĩa ngay từ đầu
    - Chỉ giữ bigrams không nằm trong trigrams có nghĩa đã chọn
    
    Args:
        query: Chuỗi query gốc
    
    Returns:
        List[str]: Danh sách candidates (từ đơn và cụm từ 2-3 từ)
    """
    candidates = []
    query_lower = query.lower()
    
    # 1. Tokenize sử dụng underthesea và lọc stopwords
    original_words = _tokenize_with_underthesea(query)
    words = [w.lower() for w in original_words if w.lower() not in STOPWORDS and len(w) > 1]
    
    if not words:
        return []
    
    # 2. Lấy POS tags và NER tags để ưu tiên các từ quan trọng
    pos_tags = _get_pos_tags(query)
    ner_tags = _get_ner_entities(query)
    
    # 2.1. Extract cụm từ từ NER tags trước (tên riêng quan trọng)
    # NER tags có thể trả về cụm từ như "Pham Ngoc Canh", "Việt Nam"
    ner_phrases = []
    _, _, ner_func = _ensure_underthesea()
    if ner_func:
        try:
            ner_results = ner_func(query)
            # ner trả về list of tuples: [('từ', 'POS', 'Chunk', 'NER'), ...]
            for word, pos, chunk, ner_tag in ner_results:
                # Chỉ lấy cụm từ (có space) và có NER tag quan trọng
                if ' ' in word and ner_tag in IMPORTANT_NER_TAGS:
                    word_lower = word.lower()
                    if word_lower not in ner_phrases:
                        ner_phrases.append(word_lower)
        except Exception as e:
            logger.debug(f"Failed to extract NER phrases: {e}")
    
    # 3. Extract cụm từ (ưu tiên trigrams trước)
    original_lower = [w.lower() for w in original_words]
    
    trigrams = []
    bigrams = []
    
    # Trigrams (3 từ) - ưu tiên cao nhất, nhưng filter các cụm từ không có nghĩa
    for i in range(len(original_lower) - 2):
        word1, word2, word3 = original_lower[i], original_lower[i + 1], original_lower[i + 2]
        if (word1 not in STOPWORDS and len(word1) > 1 and
            word2 not in STOPWORDS and len(word2) > 1 and
            word3 not in STOPWORDS and len(word3) > 1):
            phrase = f"{word1} {word2} {word3}"
            
            # Ưu tiên các cụm từ có POS tags quan trọng hoặc NER tags
            has_important_pos = any(
                pos_tags.get(w, '') in IMPORTANT_POS_TAGS 
                for w in [word1, word2, word3]
            )
            has_ner = any(
                ner_tags.get(w, '') in IMPORTANT_NER_TAGS 
                for w in [word1, word2, word3]
            )
            
            # Chỉ thêm trigram nếu không phải cụm từ không có nghĩa
            # (kiểm tra với POS/NER tags để chính xác hơn)
            if not _is_meaningless_phrase(phrase, pos_tags, ner_tags) or has_important_pos or has_ner:
                if phrase not in trigrams:
                    trigrams.append(phrase)
    
    # Bigrams (2 từ) - chỉ lấy những cái không nằm hoàn toàn trong trigrams có nghĩa
    for i in range(len(original_lower) - 1):
        word1, word2 = original_lower[i], original_lower[i + 1]
        if (word1 not in STOPWORDS and len(word1) > 1 and 
            word2 not in STOPWORDS and len(word2) > 1):
            phrase = f"{word1} {word2}"
            
            # Kiểm tra POS tags và NER tags
            has_important_pos = any(
                pos_tags.get(w, '') in IMPORTANT_POS_TAGS 
                for w in [word1, word2]
            )
            has_ner = any(
                ner_tags.get(w, '') in IMPORTANT_NER_TAGS 
                for w in [word1, word2]
            )
            
            # Loại bỏ bigrams không có nghĩa (trừ khi có POS/NER tags quan trọng)
            # (kiểm tra với POS/NER tags để chính xác hơn)
            if _is_meaningless_phrase(phrase, pos_tags, ner_tags) and not has_important_pos and not has_ner:
                continue
            
            # Kiểm tra xem bigram này có nằm hoàn toàn trong trigram có nghĩa nào không
            is_in_meaningful_trigram = False
            for trigram in trigrams:
                if phrase in trigram:
                    is_in_meaningful_trigram = True
                    break
            
            # Thêm bigram nếu:
            # 1. Không nằm trong trigram có nghĩa, HOẶC
            # 2. Có POS/NER tags quan trọng (bigram cũng có nghĩa, nên giữ lại cả hai)
            if not is_in_meaningful_trigram or has_important_pos or has_ner:
                if phrase not in bigrams:
                    bigrams.append(phrase)
    
    # Thêm vào candidates: NER phrases trước (ưu tiên cao nhất), sau đó trigrams, bigrams
    candidates.extend(ner_phrases)
    candidates.extend(trigrams)
    candidates.extend(bigrams)
    
    # 4. Thêm từ đơn (nếu chưa có trong cụm từ)
    for word in words:
        # Chỉ thêm từ đơn nếu nó không nằm trong bất kỳ cụm từ nào đã extract
        is_in_phrase = any(word in phrase.split() for phrase in candidates)
        if not is_in_phrase:
            candidates.append(word)
    
    return candidates


def _extract_keywords_with_phrases(query: str, max_words: int = 10) -> List[str]:
    """Extract keywords với cụm từ sử dụng underthesea (POS/NER tags) và heuristic.
    
    Sử dụng underthesea để:
    - Tách từ chính xác (word_tokenize)
    - Phân tích POS tags (N, V, A, Np) để ưu tiên từ quan trọng
    - Nhận diện tên riêng (NER: PER, LOC, ORG) để tăng điểm
    
    Args:
        query: Chuỗi query từ người dùng
        max_words: Số lượng từ/cụm từ tối đa
    
    Returns:
        List[str]: Danh sách từ/cụm từ quan trọng, đã sắp xếp theo độ quan trọng
    """
    candidates = _extract_candidates_with_phrases(query)
    
    if not candidates:
        return []
    
    # Score các candidates sử dụng heuristic + POS/NER tags
    candidate_scores = {}
    for candidate in candidates:
        words_in_candidate = candidate.split()
        # Tính score trung bình của các từ trong candidate
        scores = [_score_words_importance(query, [w]).get(w, 0.0) for w in words_in_candidate]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        # Bonus cho cụm từ - cụm từ thường có ngữ nghĩa tốt hơn
        word_count = len(words_in_candidate)
        if word_count >= 3:
            phrase_bonus = 0.25  # Trigrams có bonus cao nhất
        elif word_count == 2:
            phrase_bonus = 0.2   # Bigrams có bonus vừa
        else:
            phrase_bonus = 0.0   # Từ đơn không có bonus
        
        candidate_scores[candidate] = avg_score + phrase_bonus
    
    # Sắp xếp và lấy top
    sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Ưu tiên cụm từ
    selected = []
    phrases = [c for c, s in sorted_candidates if ' ' in c]
    words = [c for c, s in sorted_candidates if ' ' not in c]
    
    # Lấy cụm từ trước (tối đa 50%), sau đó từ đơn
    max_phrases = min(len(phrases), max_words // 2)
    selected = phrases[:max_phrases] + words[:max_words - max_phrases]
    
    logger.debug(f"Extracted {len(selected)} keywords/phrases from query: {selected}")
    return selected[:max_words]


def _score_words_importance(query: str, words: List[str]) -> Dict[str, float]:
    """Đánh giá độ quan trọng của từng từ trong query.
    
    Sử dụng các heuristic kết hợp với underthesea:
    - Length: từ dài hơn thường là keyword tốt hơn
    - Frequency: từ xuất hiện nhiều lần quan trọng hơn
    - POS tags: danh từ (N), động từ (V), tính từ (A), tên riêng (Np) quan trọng hơn
    - NER tags: tên riêng (PER, LOC, ORG) rất quan trọng
    - Capitalization: từ viết hoa có thể là tên riêng (quan trọng)
    
    Args:
        query: Chuỗi query gốc
        words: Danh sách từ đã filter
    
    Returns:
        Dict[str, float]: Dictionary mapping từ -> score
    """
    scores = {}
    query_lower = query.lower()
    original_words = _tokenize_with_underthesea(query)
    
    # Lấy POS tags và NER tags từ underthesea
    pos_tags = _get_pos_tags(query)
    ner_tags = _get_ner_entities(query)
    
    for word in words:
        score = 0.0
        word_lower = word.lower()
        
        # 1. Length score: từ dài hơn thường là keyword tốt
        length_score = min(len(word) / 10.0, 1.0)  # Normalize
        score += length_score * 0.2
        
        # 2. Frequency score: từ xuất hiện nhiều lần
        freq = query_lower.count(word_lower)
        freq_score = min(freq / 3.0, 1.0)  # Normalize
        score += freq_score * 0.2
        
        # 3. POS tag score: danh từ, động từ, tính từ, tên riêng quan trọng hơn
        pos_tag = pos_tags.get(word_lower, '')
        if pos_tag in IMPORTANT_POS_TAGS:
            if pos_tag == 'Np':  # Tên riêng - rất quan trọng
                score += 0.3
            elif pos_tag in {'N', 'V', 'A'}:  # Danh từ, động từ, tính từ
                score += 0.2
        
        # 4. NER tag score: tên riêng (PER, LOC, ORG) rất quan trọng
        ner_tag = ner_tags.get(word_lower, '')
        if ner_tag in IMPORTANT_NER_TAGS:
            # Tên riêng có điểm cao nhất
            if 'PER' in ner_tag:
                score += 0.4  # Tên người rất quan trọng
            elif 'LOC' in ner_tag:
                score += 0.35  # Địa điểm quan trọng
            elif 'ORG' in ner_tag:
                score += 0.35  # Tổ chức quan trọng
        
        # 5. Capitalization: kiểm tra xem có phải tên riêng không
        # Tìm từ gốc trong query để check capitalization
        for orig_word in original_words:
            if orig_word.lower() == word_lower:
                if orig_word[0].isupper() and len(orig_word) > 2:
                    # Chỉ thêm bonus nếu chưa có NER tag (tránh double counting)
                    if ner_tag not in IMPORTANT_NER_TAGS:
                        score += 0.2  # Tên riêng thường quan trọng
                break
        
        scores[word] = score
    
    return scores




def build_fts_query(query: str) -> Optional[str]:
    """Build PostgreSQL tsquery với OR logic giữa các từ/cụm từ.
    
    Hàm này chuyển đổi query của người dùng thành PostgreSQL tsquery format.
    - Cụm từ (phrases) được convert thành AND query: "thông tin" -> "thông & tin"
    - Các từ đơn và cụm từ được nối bằng OR: "word1 | phrase1 | phrase2"
    - Điều này cho phép match documents có BẤT KỲ từ/cụm từ nào trong query.
    
    Args:
        query: Chuỗi query từ người dùng (string)
    
    Returns:
        Optional[str]: PostgreSQL tsquery string với OR logic giữa các từ/cụm từ,
                      hoặc None nếu không có từ quan trọng
    
    Example:
        >>> build_fts_query("Tìm các issue của Pham Ngoc Canh")
        'issue | pham | ngoc | canh'
        
        >>> build_fts_query("Tôi muốn thông tin về server")
        'thông & tin | server'
        
        >>> build_fts_query("của và là")
        None  # Chỉ có stopwords
    
    Note:
        - Cụm từ được convert thành AND query để tìm chính xác
        - Sử dụng OR (|) giữa các từ/cụm từ để tăng recall
        - Chunks match nhiều từ/cụm từ sẽ có ts_rank cao hơn
        - Trả về None nếu query chỉ có stopwords
    """
    important_words = remove_stopwords(query)
    
    if not important_words:
        logger.debug(f"Query '{query}' only contains stopwords, returning None")
        return None
    
    # Build FTS query: xử lý cụm từ và từ đơn
    fts_parts = []
    for item in important_words:
        if ' ' in item:
            # Cụm từ: convert thành AND query
            # "thông tin" -> "thông & tin"
            words_in_phrase = item.split()
            phrase_query = ' & '.join(words_in_phrase)
            fts_parts.append(f"({phrase_query})")
        else:
            # Từ đơn: giữ nguyên
            fts_parts.append(item)
    
    # Join bằng OR: "word1 | (word2 & word3) | word4"
    fts_query = ' | '.join(fts_parts)
    logger.debug(f"Built FTS query: '{fts_query}' from '{query}' (extracted: {important_words})")
    
    return fts_query


def keyword_search(
    query: str,
    db: Session,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Full-text search với PostgreSQL.
    
    Hàm này thực hiện full-text search sử dụng PostgreSQL FTS với GIN index.
    Query được xử lý để loại bỏ stopwords và sử dụng OR logic.
    
    Args:
        query: Chuỗi query từ người dùng (string)
        db: Database session
        limit: Số lượng kết quả tối đa (mặc định: 50)
    
    Returns:
        List[Dict[str, Any]]: Danh sách chunks đã match, mỗi chunk chứa:
            - chunk_id: UUID của chunk (str)
            - text: Nội dung chunk (str)
            - chunk_type: Loại chunk (str)
            - fts_rank: Điểm ranking từ ts_rank (float)
            - metadata: Dictionary metadata (source_reference, source_type, etc.)
    
    Note:
        - Sử dụng to_tsvector('simple', ...) để hỗ trợ tiếng Việt
        - Trả về empty list nếu query chỉ có stopwords
        - Kết quả được sắp xếp theo fts_rank giảm dần
    """
    # Build FTS query
    fts_query = build_fts_query(query)
    
    if not fts_query:
        logger.info(f"Keyword search skipped: query '{query}' only contains stopwords")
        return []
    
    try:
        sql = """
            SELECT 
                c.id,
                c.text_content,
                c.chunk_type,
                c.heading_title,
                c.author_name,
                c.page_number,
                s.external_id AS source_reference,
                s.source_type,
                s.external_url,
                s.project_key,
                s.language,
                ts_rank(
                    to_tsvector('simple', c.text_content),
                    to_tsquery('simple', :fts_query)
                ) AS fts_rank
            FROM chunk c
            JOIN source s ON c.source_id = s.id
            WHERE c.status = 'processed'
              AND to_tsvector('simple', c.text_content) @@ to_tsquery('simple', :fts_query)
            ORDER BY fts_rank DESC
            LIMIT :limit
        """
        
        result = db.execute(text(sql), {'fts_query': fts_query, 'limit': limit})
        rows = result.fetchall()
        
        logger.debug(f"Keyword search found {len(rows)} results for query '{query}'")
        
        # Format results
        results = []
        for row in rows:
            results.append(_format_keyword_result(row))
        
        return results
        
    except Exception as e:
        logger.error(f"Keyword search failed: {e}", exc_info=True)
        return []


def _format_keyword_result(row) -> Dict[str, Any]:
    """Format một database row từ keyword search thành dictionary.
    
    Args:
        row: Database row từ keyword search query
    
    Returns:
        Dict[str, Any]: Dictionary kết quả đã format
    """
    return {
        'chunk_id': str(row.id),
        'text': row.text_content,
        'chunk_type': row.chunk_type,
        'fts_rank': float(row.fts_rank),
        'metadata': {
            'source_reference': row.source_reference,
            'source_type': row.source_type,
            'external_url': row.external_url,
            'project_key': row.project_key,
            'language': row.language,
            'heading': row.heading_title,
            'author': row.author_name,
            'page': row.page_number,
        }
    }

