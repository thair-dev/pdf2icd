"""Disease Mention → UMLS CUI and ICD Mapping using Prebuilt Dictionaries.

This module provides:
- exact_match(term): Return CUIs and ICD codes for an exact match.
- fuzzy_match(term): Return fuzzy-matched terms with CUIs and ICD codes.
- best_match(term): Try exact match, fall back to fuzzy, return CUIs and ICD codes.

All mappings use prebuilt dictionaries and cache fuzzy results for speed.

"""

from __future__ import annotations

from rapidfuzz import fuzz, process

from pdf2icd.utils import load_cui_to_icd, load_term_to_cuis, normalize_term


class DiseaseMatcher:
    """Resolve disease mentions to CUIs and ICD codes using prebuilt dictionaries."""

    def __init__(self) -> None:
        """Load term→CUIs and CUI→ICD mappings; precompute key list for fuzzy."""
        self.term_to_cuis = load_term_to_cuis()
        self.cui_to_icd = load_cui_to_icd()
        self._keys = list(self.term_to_cuis.keys())
        self._fuzzy_cache: dict[str, list[dict[str, object]]] = {}

    def exact_match(self, term: str) -> list[dict[str, object]]:
        """Return CUIs and ICD codes for an exact normalized match.

        Args:
            term (str): disease mention text

        Returns:
            list[dict]: each dict contains 'matched', 'cui', 'icd_codes'

        """
        norm = normalize_term(term)
        cuis = self.term_to_cuis.get(norm, [])
        return [{"matched": norm, "cui": cui, "icd_codes": self.cui_to_icd.get(cui, [])} for cui in cuis]

    def fuzzy_match(self, term: str, limit: int = 3, threshold: int = 85) -> list[dict[str, object]]:
        """Return top fuzzy-matched normalized terms, CUIs, and ICD codes.

        Args:
            term (str): disease mention text
            limit (int): max number of fuzzy matches
            threshold (int): minimum similarity score

        Returns:
            list[dict]: each dict contains 'matched', 'score', 'cui', 'icd_codes'

        """
        norm = normalize_term(term)
        if norm in self._fuzzy_cache:
            return self._fuzzy_cache[norm]

        matches = process.extract(norm, self._keys, scorer=fuzz.ratio, limit=limit)
        results: list[dict[str, object]] = []
        for matched, score, _ in matches:
            if score >= threshold:
                for cui in self.term_to_cuis[matched]:
                    results.append(
                        {
                            "matched": matched,
                            "score": score,
                            "cui": cui,
                            "icd_codes": self.cui_to_icd.get(cui, []),
                        }
                    )
        self._fuzzy_cache[norm] = results
        return results

    def best_match(self, term: str, limit: int = 3, threshold: int = 85) -> list[dict[str, object]]:
        """Return CUIs and ICD codes for exact match, or fall back to fuzzy match.

        Args:
            term (str): disease mention text
            limit (int): max number of fuzzy matches if no exact match
            threshold (int): minimum similarity score for fuzzy matches

        Returns:
            list[dict]: each dict contains 'matched', 'score' (if fuzzy), 'cui', 'icd_codes'

        """
        exact = self.exact_match(term)
        if exact:
            for entry in exact:
                entry["score"] = 100  # Exact match always full score
            return exact

        # Fuzzy match (may return multiple with scores < 100)
        return self.fuzzy_match(term, limit=limit, threshold=threshold)
