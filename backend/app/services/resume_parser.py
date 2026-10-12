"""
Resume parser powered by Groq LLM.
Extracts structured data from raw resume text.
"""
from __future__ import annotations

import json
import re
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type

logger = structlog.get_logger()


class QuotaExhaustedError(Exception):
    """Raised when Gemini quota is fully exhausted (limit: 0). Not retryable."""
    pass

RESUME_PARSE_PROMPT = """
You are an expert resume parser. Extract structured information from the resume text below.

Return ONLY valid JSON matching this exact schema (no markdown, no explanation):
{
  "candidate_name": "string",
  "email": "string or null",
  "phone": "string or null",
  "location": "string or null",
  "total_exp_years": number,
  "recent_skills": ["skills used in last 3 years"],
  "all_skills": ["all skills ever mentioned"],
  "education": [
    {
      "degree": "string",
      "institution": "string",
      "year": number or null
    }
  ],
  "experience": [
    {
      "title": "string",
      "company": "string",
      "location": "string or null",
      "duration_start": "YYYY-MM-DD or YYYY-MM",
      "duration_end": "YYYY-MM-DD or YYYY-MM or Present",
      "duration_years": number,
      "description": "string",
      "achievements": ["quantified achievements"],
      "skills_used": ["skills used in this role"]
    }
  ],
  "employment_gaps": [
    {
      "start": "YYYY-MM",
      "end": "YYYY-MM",
      "duration_months": number,
      "explanation": "string or null"
    }
  ],
  "certifications": [
    {
      "name": "string",
      "issuer": "string or null",
      "year": number or null
    }
  ]
}

Resume text:
"""

JD_PARSE_PROMPT = """
You are an expert job description parser. Extract structured requirements from the job description below.

STEP 1 — IDENTIFY SECTIONS:
First, mentally split the JD into two parts:
  A) PRIMARY SECTION: The main job description, responsibilities, key duties, requirements, qualifications — everything BEFORE any "Additional Skills" / "Nice to Have" / "Preferred" / "Bonus" / "Good to Have" section.
  B) ADDITIONAL SECTION: Everything under headers like "Additional Skills", "Nice to Have", "Good to Have", "Preferred", "Bonus Skills", "Plus Points", "Desired".

STEP 2 — EXTRACT SKILLS PER SECTION:
  - Read the PRIMARY SECTION line by line. Extract EVERY specific technology, tool, framework, language, platform, library, and methodology mentioned. Do NOT skip any. Be exhaustive.
  - Read the ADDITIONAL SECTION line by line. Extract every skill mentioned there separately.

STEP 3 — CLASSIFY:
  A) "required_skills" — ALL technical skills extracted from the PRIMARY SECTION. These are the skills the candidate MUST have.
     - Include every technology, framework, language, tool, platform, library, and protocol mentioned in the primary section.
     - Do NOT omit skills just because they seem minor — if the JD says "write code in C#", then C# is required.
     - If a skill appears in BOTH the primary section AND the additional section, it is REQUIRED (primary section wins).

  B) "nice_to_have_skills" — Skills that appear ONLY in the ADDITIONAL SECTION and nowhere in the primary section.
     - The SECTION HEADER always overrides the skill phrasing. Even if a skill is described as "expertise in X" or "proficiency in X", if it appears ONLY under "Additional Skills" / "Nice to Have" / "Preferred", it is nice_to_have.
     - Also include any skill anywhere in the JD followed by: "is a plus", "preferred", "good to have", "nice to have", "bonus", "advantageous", "desirable".
     - A skill must NEVER appear in both required_skills and nice_to_have_skills.

  C) "top_3_mandatory_skills" — The 3 MOST critical skills from required_skills ONLY:
     - Pick from required_skills, never from nice_to_have_skills.
     - Focus on the primary technology stack the role demands.

STRICT RULES:
- NEVER hallucinate or infer skills not explicitly mentioned in the JD text. Only extract skills that appear verbatim in the JD.
- Do NOT add generic skills (e.g., "Go", "Rust") unless the JD explicitly names them.
- Normalize skill names: use the official/common name (e.g., ".NET" not "dotnet", "C#" not "csharp", "Angular" not "ng").
- Extract specific versions only if the JD mentions them (e.g., "Angular 18", "C# 14", ".NET 10.0").

CLASSIFICATION EXAMPLES:
- JD main section says "develop backend services using .NET and C#" → required_skills: [".NET", "C#"]
- JD main section says "implement logging with Serilog and NLog" → required_skills: ["Serilog", "NLog"]
- JD "Additional Skills" section says "Expertise in Azure services" (and Azure is NOT in the main section) → nice_to_have_skills: ["Azure"]
- JD main section says "Azure Service Bus" AND "Additional Skills" says "Azure services" → required_skills: ["Azure Service Bus"] (primary section wins)
- JD says "Knowledge of Docker, Kubernetes is a plus" → nice_to_have_skills: ["Docker", "Kubernetes"]
- JD says "Good to have e-learning domain knowledge" → nice_to_have_skills: ["e-learning"]

Return ONLY valid JSON matching this exact schema (no markdown, no explanation):
{
  "job_title": "string",
  "company": "string or null",
  "location": "string or null",
  "required_min_exp_years": number,
  "preferred_min_exp_years": number or null,
  "required_skills": [
    {
      "skill": "string — exact skill name as mentioned in JD",
      "proficiency": "Beginner|Intermediate|Advanced|Expert",
      "years_required": number
    }
  ],
  "nice_to_have_skills": ["skill names — ONLY skills that appear exclusively in the additional/preferred/bonus section"],
  "education_required": "string or null",
  "locations_accepted": ["location strings"],
  "willingness_to_relocate": "string or null",
  "top_3_mandatory_skills": ["3 most critical skills from required_skills ONLY — never from nice_to_have"]
}

Job Description:
"""


class GroqResumeParser:
    """Parse resumes and JDs using Groq LLM."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from groq import Groq
            from app.config import settings

            if not settings.GROQ_API_KEY:
                raise RuntimeError("GROQ_API_KEY not configured")
            self._client = Groq(api_key=settings.GROQ_API_KEY)
        return self._client

    def _call_llm(self, prompt: str) -> str:
        """Call Groq and return the text response."""
        from app.config import settings
        response = self.client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_completion_tokens=4096,
        )
        return response.choices[0].message.content

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from LLM response, stripping markdown code fences."""
        # Remove markdown code fences
        text = re.sub(r"```(?:json)?", "", text).strip()
        text = text.rstrip("`").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse LLM JSON response", error=str(exc), text=text[:200])
            # Try to extract JSON object from the text
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_not_exception_type(QuotaExhaustedError),
    )
    def parse_resume(self, resume_text: str) -> dict:
        """Parse resume text → structured dict."""
        prompt = RESUME_PARSE_PROMPT + resume_text[:8000]  # Limit input size
        raw = self._call_llm(prompt)
        parsed = self._extract_json(raw)
        return self._validate_resume(parsed)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_not_exception_type(QuotaExhaustedError),
    )
    def parse_jd(self, jd_text: str) -> dict:
        """Parse job description text → structured dict."""
        prompt = JD_PARSE_PROMPT + jd_text[:8000]
        raw = self._call_llm(prompt)
        parsed = self._extract_json(raw)
        return self._validate_jd(parsed)

    def _validate_resume(self, data: dict) -> dict:
        """Ensure required fields are present with sensible defaults."""
        defaults = {
            "candidate_name": "Unknown",
            "email": None,
            "phone": None,
            "location": None,
            "total_exp_years": 0,
            "recent_skills": [],
            "all_skills": [],
            "education": [],
            "experience": [],
            "employment_gaps": [],
            "certifications": [],
        }
        return {**defaults, **data}

    def _validate_jd(self, data: dict) -> dict:
        """Ensure required fields are present with sensible defaults."""
        defaults = {
            "job_title": "Software Engineer",
            "company": None,
            "location": None,
            "required_min_exp_years": 0,
            "preferred_min_exp_years": None,
            "required_skills": [],
            "nice_to_have_skills": [],
            "education_required": None,
            "locations_accepted": [],
            "willingness_to_relocate": None,
            "top_3_mandatory_skills": [],
        }
        return {**defaults, **data}


resume_parser = GroqResumeParser()
