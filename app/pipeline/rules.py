import json
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from app.schemas import (
    RedFlagsConfig,
    RedFlagDefinition,
    CategoryDefinition,
    MatchedFlag,
)


class RuleEngine:
    """Pure Python red-flag detection and risk classification engine."""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).resolve().parent.parent.parent / "data" / "red_flags.json"
        
        self.config_path = Path(config_path)
        self.config: RedFlagsConfig = self._load_and_validate_config()
        self._compiled_patterns: Dict[str, List[re.Pattern]] = self._compile_patterns()
        self._compiled_pretext_keywords: Dict[str, List[re.Pattern]] = self._compile_pretext_keywords()
        self._categories_by_id: Dict[str, CategoryDefinition] = {
            c.id: c for c in self.config.categories
        }

    def _load_and_validate_config(self) -> RedFlagsConfig:
        """Loads and validates red-flag configuration using Pydantic."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Red flags configuration file not found at: {self.config_path}")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return RedFlagsConfig(**data)

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Pre-compiles regex patterns for high-speed matching."""
        compiled = {}
        for flag in self.config.flags:
            patterns = []
            for pat in flag.patterns:
                try:
                    patterns.append(re.compile(pat, re.IGNORECASE | re.UNICODE))
                except re.error:
                    escaped = re.escape(pat)
                    patterns.append(re.compile(escaped, re.IGNORECASE | re.UNICODE))
            compiled[flag.id] = patterns
        return compiled

    def _compile_pretext_keywords(self) -> Dict[str, List[re.Pattern]]:
        """Pre-compiles pretext keywords for category disambiguation."""
        compiled = {}
        for cat in self.config.categories:
            patterns = []
            for kw in cat.pretext_keywords:
                # Word boundary match for ASCII, direct regex search for Devanagari
                if re.match(r'^[a-zA-Z0-9\s-]+$', kw):
                    pat = rf"\b{re.escape(kw)}\b"
                else:
                    pat = re.escape(kw)
                try:
                    patterns.append(re.compile(pat, re.IGNORECASE | re.UNICODE))
                except re.error:
                    pass
            compiled[cat.id] = patterns
        return compiled

    def evaluate(self, text: str) -> Dict[str, Any]:
        """
        Evaluates input text against red flag rules.
        
        Returns a dictionary with:
          - score: total weighted score
          - risk_level: "Low", "Medium", or "High"
          - category_id: e.g. "digital_arrest"
          - category_name_en: English name
          - category_name_hi: Hindi name
          - matched_flags: List[MatchedFlag]
          - is_zero_flags: bool
        """
        matched_flags: List[MatchedFlag] = []
        total_score = 0
        matched_flag_ids = set()

        # Step 1: Match red flags
        for flag in self.config.flags:
            patterns = self._compiled_patterns.get(flag.id, [])
            snippets = set()

            for pattern in patterns:
                for match in pattern.finditer(text):
                    snippet = match.group(0).strip()
                    if snippet:
                        snippets.add(snippet)

            if snippets:
                mf = MatchedFlag(
                    id=flag.id,
                    name_en=flag.name_en,
                    name_hi=flag.name_hi,
                    weight=flag.weight,
                    snippets=sorted(list(snippets)),
                )
                matched_flags.append(mf)
                total_score += flag.weight
                matched_flag_ids.add(flag.id)

        # Step 2: Determine risk level based on thresholds
        # score <= low_max: Low, 3-5: Medium, >= 6: High
        thresholds = self.config.thresholds
        if total_score <= thresholds.low_max:
            risk_level = "Low"
        elif total_score <= thresholds.medium_max:
            risk_level = "Medium"
        else:
            risk_level = "High"

        # Step 3: Determine category (most matching flags among 6 categories + pretext disambiguation)
        best_category_id = "general_suspicious"
        best_tuple = (-1, -1, -1)  # (flag_match_count, pretext_match_count, assoc_weight)

        if matched_flags:
            for cat in self.config.categories:
                if cat.id == "general_suspicious":
                    continue
                
                # Count matching associated flags
                matching_assoc = [fid for fid in cat.associated_flags if fid in matched_flag_ids]
                flag_match_count = len(matching_assoc)

                if flag_match_count == 0:
                    continue

                # Count matching pretext keywords in text
                pretext_pats = self._compiled_pretext_keywords.get(cat.id, [])
                pretext_count = 0
                for pat in pretext_pats:
                    if pat.search(text):
                        pretext_count += 1

                # Sum weight of associated matched flags
                assoc_weight = sum(
                    mf.weight for mf in matched_flags if mf.id in cat.associated_flags
                )

                candidate_tuple = (flag_match_count, pretext_count, assoc_weight)
                if candidate_tuple > best_tuple:
                    best_tuple = candidate_tuple
                    best_category_id = cat.id

        is_zero_flags = (len(matched_flags) == 0)

        # Retrieve category object
        cat_obj = self._categories_by_id.get(best_category_id)
        if not cat_obj:
            cat_obj = CategoryDefinition(
                id="general_suspicious",
                name_en="General Suspicious Communication",
                name_hi="सामान्य संदिग्ध संदेश",
                associated_flags=[],
                pretext_keywords=[],
            )

        return {
            "score": total_score,
            "risk_level": risk_level,
            "category_id": cat_obj.id,
            "category_name_en": cat_obj.name_en,
            "category_name_hi": cat_obj.name_hi,
            "matched_flags": matched_flags,
            "is_zero_flags": is_zero_flags,
        }
