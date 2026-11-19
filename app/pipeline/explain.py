import os
import json
import logging
from pathlib import Path
from typing import List, Tuple, Optional
from dotenv import load_dotenv

from app.schemas import MatchedFlag

load_dotenv()
logger = logging.getLogger(__name__)


class ExplanationManager:
    """
    Generates plain-language scam explanations.
    Uses Google Gemini API (via google-genai SDK) when available,
    and reliably falls back to predefined templates (data/templates.json) on any failure.
    """

    def __init__(self, templates_path: Optional[Path] = None):
        if templates_path is None:
            templates_path = Path(__file__).resolve().parent.parent.parent / "data" / "templates.json"
        
        self.templates_path = Path(templates_path)
        self.templates = self._load_templates()
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()

    def _load_templates(self) -> dict:
        if not self.templates_path.exists():
            return {"categories": {}, "zero_flags": {}}
        with open(self.templates_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_template_explanation(self, category_id: str, language: str = "en", is_zero_flags: bool = False) -> str:
        """Retrieves verified static fallback explanation from templates.json."""
        lang = "hi" if language == "hi" else "en"
        if is_zero_flags:
            return self.templates.get("zero_flags", {}).get(lang, "No known red flags detected. Stay cautious.")
        
        cat_tpl = self.templates.get("categories", {}).get(category_id, {})
        if not cat_tpl:
            cat_tpl = self.templates.get("categories", {}).get("general_suspicious", {})
        
        return cat_tpl.get(lang, "This message shows suspicious manipulation tactics. Stay cautious.")

    def explain(
        self,
        masked_text: str,
        category_id: str,
        category_name: str,
        matched_flags: List[MatchedFlag],
        language: str = "en",
        is_zero_flags: bool = False
    ) -> Tuple[str, str]:
        """
        Generates explanation.
        Returns: (explanation_text, explanation_source) where source is 'llm' or 'template'.
        """
        lang = "hi" if language == "hi" else "en"

        # Rule: Only call LLM if >= 1 red flag. Zero-flag never invokes LLM.
        if is_zero_flags or not matched_flags:
            return self.get_template_explanation(category_id, language=lang, is_zero_flags=True), "template"

        # Check for API key
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return self.get_template_explanation(category_id, language=lang), "template"

        # Attempt Gemini API call
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)

            # Build list of matched flag names for the prompt
            flag_summaries = []
            for f in matched_flags:
                name = f.name_hi if lang == "hi" else f.name_en
                snippets_str = ", ".join(f'"{s}"' for s in f.snippets[:3])
                flag_summaries.append(f"- {name} (Evidence: {snippets_str})")
            flags_text = "\n".join(flag_summaries)

            if lang == "hi":
                prompt = (
                    f"आप भारत में वरिष्ठ नागरिकों को धोखाधड़ी (Scam) के हथकंडे समझाने वाले एक सहायक हैं।\n"
                    f"संदेश की श्रेणी: {category_name}\n"
                    f"संदेश में पाए गए संदिग्ध लाल झंडे (Red Flags):\n{flags_text}\n\n"
                    f"जांचा गया संदेश (गोपनीय जानकारी पहले से सुरक्षित/मास्क की गई है):\n"
                    f"\"{masked_text}\"\n\n"
                    f"निर्देश:\n"
                    f"1. केवल ऊपर दिए गए लाल झंडों को सरल, सम्मानजनक हिंदी में समझाइए।\n"
                    f"2. 3 से 5 छोटे और सीधे वाक्य लिखें।\n"
                    f"3. कोई तकनीकी जटिल शब्द न इस्तेमाल करें।\n"
                    f"4. कोई भी काल्पनिक या बाहरी तथ्य न जोड़ें; केवल यह बताएं कि ये बातें क्यों खतरनाक हैं।"
                )
            else:
                prompt = (
                    f"You are a helpful assistant explaining scam tactics to senior citizens in India in plain words.\n"
                    f"Scam Category: {category_name}\n"
                    f"Detected Red Flags in message:\n{flags_text}\n\n"
                    f"Analyzed message (sensitive numbers already masked for privacy):\n"
                    f"\"{masked_text}\"\n\n"
                    f"Instructions:\n"
                    f"1. Explain ONLY the detected red flags listed above in simple, respectful English for an elderly person.\n"
                    f"2. Write exactly 3 to 5 short, reassuring sentences.\n"
                    f"3. Do NOT use technical fraud jargon.\n"
                    f"4. Do NOT invent any facts not present in the message; focus strictly on why these red flags are dangerous."
                )

            # Call Gemini model
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )

            if response and response.text:
                return response.text.strip(), "llm"

        except Exception as e:
            logger.warning(f"Gemini API call failed or timed out: {e}. Falling back to template explanation.")

        # Fallback to predefined template on any API error or timeout
        return self.get_template_explanation(category_id, language=lang), "template"
