"""Category taxonomy + keyword classifier.

Sources can pin a category (trusted curation, e.g. studentoffers.co is always
student_offers). Everything else is routed by keyword rules — first match wins.
No AI involved: deterministic, instant, free.
"""

from __future__ import annotations

from .models import RawOpportunity

# slug -> (display name, emoji)
CATEGORIES: dict[str, tuple[str, str]] = {
    "ai_freebies":      ("AI & API credits", "🤖"),
    "student_offers":   ("Student offers", "🎓"),
    "govt_schemes":     ("Govt schemes & yojanas", "🏛️"),
    "deals_shopping":   ("Deals & shopping", "🛒"),
    "food_dining":      ("Food & dining", "🍔"),
    "free_courses":     ("Free courses", "📚"),
    "hackathons":       ("Hackathons & competitions", "🏆"),
    "dev_programs":     ("Dev programs & cloud", "☁️"),
    "beta_early_access": ("Beta & early access", "🧪"),
    "other":            ("Everything else", "📌"),
}

# Ordered rules: (category, keywords). First category whose ANY keyword appears
# in "title description" (lowercased) wins. Order encodes priority.
RULES: list[tuple[str, tuple[str, ...]]] = [
    ("food_dining", ("mcdonald", "mcd ", "kfc", "domino", "pizza", "burger",
                     "swiggy", "zomato", "starbucks", "cafe coffee", "food offer",
                     "dining", "restaurant", "zepto", "blinkit")),
    ("govt_schemes", ("yojana", "yojna", "pm-", "pmss", "scholarship portal",
                      "government scheme", "govt scheme", "ministry", "subsidy",
                      "stipend", "aicte", "ugc ", "nsp ", "sarkari", "ladki bahin",
                      "ladli", "arogya", "ayushman", "mahadbt", "digital india",
                      "skill india", "startup india", "meity", "niti aayog")),
    ("ai_freebies", ("api key", "free api", "api credit", "free credits",
                     "llm", "gpt", "claude", "gemini", "deepseek", "qwen",
                     "mistral", "llama", "open weights", "openrouter",
                     "hugging face", "huggingface", "parameter model",
                     "ai model", "inference", "token free", "model release")),
    ("hackathons", ("hackathon", "hack day", "ctf", "coding competition",
                    "code challenge", "buildathon", "ideathon", "devpost",
                    "prize pool", "competition")),
    ("free_courses", ("udemy", "free course", "coursera", "certification voucher",
                      "certificate free", "bootcamp free", "freecodecamp",
                      "learning path", "tutorial series", "course free")),
    ("student_offers", ("student discount", "student offer", "student pack",
                        "student plan", "edu email", "campus", ".edu",
                        "for students", "student developer")),
    ("dev_programs", ("cloud credit", "aws credit", "azure credit", "gcp credit",
                      "github", "open source program", "oss ", "developer program",
                      "devops", "sdk", "vercel", "netlify", "supabase",
                      "free tier", "startup credits", "accelerator")),
    ("beta_early_access", ("beta", "early access", "waitlist", "preview access",
                           "invite only", "launch week", "show hn")),
    ("deals_shopping", ("deal", "discount", "% off", "sale", "cashback", "coupon",
                        "promo code", "offer", "free shipping", "freebie", "free sample",
                        "lifetime", "bank offer", "credit card", "upi", "flipkart",
                        "amazon", "myntra", "croma")),
]

VALID = set(CATEGORIES)


def categorize(opp: RawOpportunity) -> str:
    """Final category for an opportunity. Source pins win; keywords route the rest."""
    if opp.category in VALID and getattr(opp, "category_pinned", False):
        return opp.category
    text = f"{opp.title} {opp.description}".lower()
    for category, keywords in RULES:
        if any(k in text for k in keywords):
            return category
    return opp.category if opp.category in VALID else "other"
