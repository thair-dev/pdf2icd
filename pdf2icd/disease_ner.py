"""Disease Mention Extraction using spaCy NER.

Extracts disease mentions from biomedical text using a spaCy NER model.
Runs NER on both the raw text and a normalized version to capture additional mentions.

"""

from __future__ import annotations

import spacy

# package imports
from pdf2icd.logs import get_logger
from pdf2icd.utils import is_valid_mention, normalize_term

log = get_logger()


class DiseaseNER:
    """Extract disease mentions from biomedical text using spaCy NER."""

    def __init__(self, ner_model: str = "en_ner_bc5cdr_md") -> None:
        """Initialize the DiseaseNER with the specified spaCy NER model.

        Args:
            ner_model (str): spaCy NER model name for disease mention extraction. Defaults to
                "en_ner_bc5cdr_md"

        """
        log.info(f"Loading spaCy NER model: {ner_model}")
        self.ner_nlp = spacy.load(ner_model)
        log.info("DiseaseNER pipeline initialized.")

    def extract_mentions(self, text: str) -> list[str]:
        """Extract unique disease mentions from text using dual-pass NER.

        NER is run twice: once on the raw text, and once on a normalized version of the text to improve recall for
        abbreviations and minor variants.

        Returns only unique mention strings (deduplicated by normalized form) without character positions because
        downstream steps (e.g. CUI/ICD mapping) do not require offsets in the original text.

        Args:
            text (str): biomedical input text

        Returns:
            list[str]: unique disease mention strings

        """
        mentions: list[str] = []

        log.info("Running NER on raw text")
        doc_raw = self.ner_nlp(text)
        mentions.extend(ent.text for ent in doc_raw.ents if ent.label_ == "DISEASE")

        log.info("Running NER on normalized text")
        norm_text = normalize_term(text)
        doc_norm = self.ner_nlp(norm_text)
        mentions.extend(ent.text for ent in doc_norm.ents if ent.label_ == "DISEASE")

        # Deduplicate based on normalized form
        seen: set[str] = set()
        unique_mentions: list[str] = []
        for m in mentions:
            norm_m = normalize_term(m)
            if norm_m not in seen and is_valid_mention(m):
                seen.add(norm_m)
                unique_mentions.append(m)

        return sorted(unique_mentions)
