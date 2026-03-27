"""
classifier.py
=============
Structural RTL classifier for selecting targeted supplemental datasets.
"""

class RTLClassifier:
    """Classifies RTL structurally to pick the best RAG dataset."""
    @staticmethod
    def classify(rtl: str) -> str:
        has_sync = "posedge" in rtl or "negedge" in rtl or "<=" in rtl
        has_if = "if " in rtl or "if(" in rtl
        has_else = "else" in rtl
        has_case = "case" in rtl
        
        if has_case:
            base = "casedataset-if" if has_if else "casedataset-!if"
        else:
            base = "ifdataset-else" if has_else else "ifdataset-!else"
            
        suffix = "-synch.json" if has_sync else ".json"
        return base + suffix
