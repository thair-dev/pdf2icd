"""Mark pdf2icd as a Python package."""

import csv
import sys

# Disease/diagnosis-related TUIs (UMLS Semantic Types)
# - T033: Finding (clinical findings - may include non-disease states)
# - T047: Disease or Syndrome (core disease/diagnosis)
# - T191: Neoplastic Process (cancer/tumors)
DISEASE_TUIS: set[str] = {"T033", "T047", "T191"}

# Increase CSV field size limit to max supported (for UMLS/RRF files)
csv.field_size_limit(sys.maxsize)
