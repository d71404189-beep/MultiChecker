# -*- coding: utf-8 -*-
"""
Seed Phrase Corrector v1.0.64
Исправление опечаток в seed фразах
"""

from typing import List, Optional, Tuple, Dict, Any
from difflib import SequenceMatcher


class SeedPhraseCorrector:
    """Исправление опечаток в seed фразах"""
    
    # BIP39 словарь (первые 100 слов для примера, полный список 2048 слов)
    BIP39_WORDLIST = [
        "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract",
        "absurd", "abuse", "access", "accident", "account", "accuse", "achieve", "acid",
        "acoustic", "acquire", "across", "act", "action", "actor", "actress", "actual",
        "adapt", "add", "addict", "address", "adjust", "admit", "adult", "advance",
        "advice", "aerobic", "affair", "afford", "afraid", "again", "age", "agent",
        "agree", "ahead", "aim", "air", "airport", "aisle", "alarm", "album",
        "alcohol", "alert", "alien", "all", "alley", "allow", "almost", "alone",
        "alpha", "already", "also", "alter", "always", "amateur", "amazing", "among",
        "amount", "amused", "analyst", "anchor", "ancient", "anger", "angle", "angry",
        "animal", "ankle", "announce", "annual", "another", "answer", "antenna", "antique",
        "anxiety", "any", "apart", "apology", "appear", "apple", "approve", "april",
        "arch", "arctic", "area", "arena", "argue", "arm", "armed", "armor",
        "army", "around", "arrange", "arrest", "arrive", "arrow", "art", "artefact",
        # ... (полный список содержит 2048 слов)
    ]
    
    def __init__(self):
        # Загружаем полный BIP39 словарь
        self.wordlist = self._load_full_wordlist()
        self.wordlist_set = set(self.wordlist)
    
    def _load_full_wordlist(self) -> List[str]:
        """Загрузить полный BIP39 словарь"""
        # В реальной реализации загружаем из файла
        # Здесь используем базовый список
        return self.BIP39_WORDLIST
    
    def correct_seed_phrase(
        self,
        seed_phrase: str,
        max_corrections: int = 3
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Исправить опечатки в seed фразе
        
        Args:
            seed_phrase: Seed фраза с возможными опечатками
            max_corrections: Максимальное количество исправлений
        
        Returns:
            Tuple: (исправленная_фраза, список_исправлений)
        """
        
        words = seed_phrase.lower().split()
        corrected_words = []
        corrections = []
        
        for i, word in enumerate(words):
            # Проверяем есть ли слово в словаре
            if word in self.wordlist_set:
                corrected_words.append(word)
            else:
                # Ищем похожее слово
                suggestion = self._find_closest_word(word)
                
                if suggestion:
                    corrected_words.append(suggestion)
                    corrections.append({
                        "position": i + 1,
                        "original": word,
                        "corrected": suggestion,
                        "confidence": self._calculate_similarity(word, suggestion)
                    })
                else:
                    # Не нашли похожее - оставляем как есть
                    corrected_words.append(word)
                    corrections.append({
                        "position": i + 1,
                        "original": word,
                        "corrected": None,
                        "confidence": 0.0,
                        "error": "Слово не найдено в BIP39 словаре"
                    })
        
        corrected_phrase = " ".join(corrected_words)
        
        return corrected_phrase, corrections
    
    def _find_closest_word(self, word: str, threshold: float = 0.7) -> Optional[str]:
        """
        Найти наиболее похожее слово из словаря
        
        Args:
            word: Слово с опечаткой
            threshold: Минимальная схожесть (0-1)
        
        Returns:
            Наиболее похожее слово или None
        """
        
        best_match = None
        best_similarity = 0.0
        
        for dict_word in self.wordlist:
            similarity = self._calculate_similarity(word, dict_word)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = dict_word
        
        # Возвращаем только если схожесть выше порога
        if best_similarity >= threshold:
            return best_match
        
        return None
    
    def _calculate_similarity(self, word1: str, word2: str) -> float:
        """
        Вычислить схожесть двух слов (0-1)
        
        Uses:
        - Levenshtein distance
        - Common prefix/suffix
        - Length similarity
        """
        
        # Базовая схожесть через SequenceMatcher
        base_similarity = SequenceMatcher(None, word1, word2).ratio()
        
        # Бонус за одинаковую длину
        len_diff = abs(len(word1) - len(word2))
        len_bonus = 1.0 - (len_diff / max(len(word1), len(word2)))
        
        # Бонус за общий префикс
        common_prefix = 0
        for c1, c2 in zip(word1, word2):
            if c1 == c2:
                common_prefix += 1
            else:
                break
        
        prefix_bonus = common_prefix / max(len(word1), len(word2))
        
        # Итоговая схожесть (взвешенная сумма)
        similarity = (
            base_similarity * 0.6 +
            len_bonus * 0.2 +
            prefix_bonus * 0.2
        )
        
        return similarity
    
    def validate_seed_phrase(self, seed_phrase: str) -> Dict[str, Any]:
        """
        Валидировать seed фразу
        
        Returns:
            Dict с результатами валидации
        """
        
        words = seed_phrase.lower().split()
        
        result = {
            "valid": True,
            "word_count": len(words),
            "expected_counts": [12, 15, 18, 21, 24],
            "invalid_words": [],
            "suggestions": []
        }
        
        # Проверяем количество слов
        if len(words) not in result["expected_counts"]:
            result["valid"] = False
            result["error"] = f"Неверное количество слов: {len(words)}. Ожидается: 12, 15, 18, 21 или 24"
        
        # Проверяем каждое слово
        for i, word in enumerate(words):
            if word not in self.wordlist_set:
                result["valid"] = False
                result["invalid_words"].append({
                    "position": i + 1,
                    "word": word
                })
                
                # Предлагаем исправление
                suggestion = self._find_closest_word(word)
                if suggestion:
                    result["suggestions"].append({
                        "position": i + 1,
                        "original": word,
                        "suggestion": suggestion,
                        "confidence": self._calculate_similarity(word, suggestion)
                    })
        
        return result
    
    def batch_correct(
        self,
        seed_phrases: List[str]
    ) -> List[Tuple[str, str, List[Dict[str, Any]]]]:
        """
        Исправить несколько seed фраз
        
        Returns:
            List of (original, corrected, corrections)
        """
        
        results = []
        
        for seed_phrase in seed_phrases:
            corrected, corrections = self.correct_seed_phrase(seed_phrase)
            results.append((seed_phrase, corrected, corrections))
        
        return results
    
    def format_correction_report(
        self,
        original: str,
        corrected: str,
        corrections: List[Dict[str, Any]]
    ) -> str:
        """Форматировать отчет об исправлениях"""
        
        lines = []
        
        lines.append("=" * 60)
        lines.append("ИСПРАВЛЕНИЕ SEED ФРАЗЫ")
        lines.append("=" * 60)
        
        lines.append(f"\nОригинал:\n  {original}")
        lines.append(f"\nИсправлено:\n  {corrected}")
        
        if corrections:
            lines.append(f"\nИсправления ({len(corrections)}):")
            
            for corr in corrections:
                pos = corr["position"]
                orig = corr["original"]
                fixed = corr.get("corrected")
                conf = corr.get("confidence", 0)
                
                if fixed:
                    lines.append(f"  {pos}. '{orig}' → '{fixed}' (уверенность: {conf:.0%})")
                else:
                    error = corr.get("error", "Не найдено")
                    lines.append(f"  {pos}. '{orig}' - ❌ {error}")
        else:
            lines.append("\n✅ Опечаток не найдено!")
        
        return "\n".join(lines)
