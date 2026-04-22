import httpx
import json
import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-5")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """Ты — опытный юрист-аналитик, специализирующийся на российском \
договорном праве и законодательстве о долевом строительстве (214-ФЗ).

Проанализируй договор и верни ТОЛЬКО валидный JSON без markdown и пояснений.

Уровни риска: HIGH — критическая угроза, MEDIUM — существенный недостаток, LOW — замечание.

Если договор не является ДДУ по 214-ФЗ — укажи is_ddu: false, overall_status: "NOT_APPLICABLE".

Формат ответа:
{
  "overall_risk_level": "HIGH|MEDIUM|LOW",
  "risks": [
    {
      "severity": "HIGH|MEDIUM|LOW",
      "category": "Категория риска",
      "title": "Краткое название",
      "clause": "п. X.X",
      "description": "Описание проблемы",
      "recommendation": "Рекомендация"
    }
  ],
  "fz214": {
    "is_ddu": true,
    "status": "COMPLIANT|VIOLATIONS_FOUND|NOT_APPLICABLE",
    "violations": ["Описание нарушения 1", "Описание нарушения 2"]
  },
  "summary": "Краткое резюме 3-5 предложений"
}"""


async def analyze_contract(text: str) -> dict:
    truncated = text[:100_000]

    user_prompt = f"""Проанализируй договор на юридические риски.

КАТЕГОРИИ РИСКОВ:
1. Ответственность сторон — несбалансированная ответственность
2. Сроки и неустойки — нереалистичные сроки, завышенные/заниженные санкции
3. Условия расторжения — одностороннее расторжение, несправедливые условия
4. Гарантийные обязательства — отсутствие или короткие гарантийные сроки
5. Оплата — скрытые платежи, непрозрачные расчёты
6. Форс-мажор — слишком широкое/узкое определение
7. Споры и подсудность — невыгодная подсудность

ПРОВЕРКА НА 214-ФЗ (если ДДУ):
- Описание объекта строительства (ст. 4 ч. 4 п. 1)
- Цена и порядок оплаты (ст. 4 ч. 4 п. 3)
- Срок передачи объекта (ст. 4 ч. 4 п. 2)
- Гарантийный срок не менее 5 лет (ст. 7 ч. 5)
- Неустойка 1/300 → 1/150 ставки ЦБ за просрочку (ст. 6 ч. 2)
- Условия расторжения дольщиком (ст. 9)
- Гос. регистрация договора (ст. 17)

ТЕКСТ ДОГОВОРА:
---
{truncated}
---"""

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://contract-bot.local",
                "X-Title": "Contract Legal Risk Bot",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
                "max_tokens": 4096,
            },
        )
        response.raise_for_status()

    raw = response.json()["choices"][0]["message"]["content"]
    return json.loads(raw)


def format_result(data: dict) -> str:
    level_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(
        data.get("overall_risk_level", ""), "⚪"
    )

    lines = [
        f"{level_emoji} *Общий уровень риска: {data.get('overall_risk_level', '—')}*",
        "",
        f"📋 *Резюме:*",
        data.get("summary", ""),
        "",
    ]

    risks = data.get("risks", [])
    if risks:
        lines.append("⚠️ *Выявленные риски:*")
        for r in risks:
            emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(r.get("severity", ""), "⚪")
            clause = f" ({r['clause']})" if r.get("clause") else ""
            lines.append(f"\n{emoji} *{r.get('title', '')}*{clause}")
            lines.append(f"_{r.get('category', '')}_")
            lines.append(r.get("description", ""))
            lines.append(f"💡 {r.get('recommendation', '')}")

    fz = data.get("fz214", {})
    if fz.get("is_ddu"):
        lines.append("")
        status = fz.get("status", "")
        status_emoji = "✅" if status == "COMPLIANT" else "❌"
        lines.append(f"{status_emoji} *214-ФЗ: {status}*")
        for v in fz.get("violations", []):
            lines.append(f"• {v}")

    lines.append("")
    lines.append("_⚠️ Анализ выполнен ИИ и не является юридической консультацией._")

    return "\n".join(lines)
