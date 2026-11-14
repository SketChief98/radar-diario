#!/usr/bin/env python3
"""Generate and archive today's five-story Portuguese news edition."""

from __future__ import annotations

import html.parser
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "editions.json"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-6.1-sol")
FALLBACK_IMAGES = {
    "economia": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1400&q=82",
    "mercados": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1400&q=82",
    "tecnologia": "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=1400&q=82",
    "inteligência artificial": "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=1400&q=82",
    "energia": "https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?auto=format&fit=crop&w=1400&q=82",
    "política": "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?auto=format&fit=crop&w=1400&q=82",
    "atualidade": "https://images.unsplash.com/photo-1480714378408-67cf0d13bc1b?auto=format&fit=crop&w=1400&q=82",
}

STORY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "region": {"type": "string", "enum": ["Portugal", "Internacional"]},
        "category": {"type": "string", "enum": ["Economia", "Mercados", "Investimentos", "Tecnologia", "Inteligência artificial", "Energia", "Política", "Atualidade"]},
        "title": {"type": "string"},
        "published": {"type": "string"},
        "facts": {"type": "string"},
        "whyItMatters": {"type": "string"},
        "analysis": {"type": "string"},
        "risks": {"type": "string"},
        "sourceName": {"type": "string"},
        "sourceUrl": {"type": "string"},
    },
    "required": ["region", "category", "title", "published", "facts", "whyItMatters", "analysis", "risks", "sourceName", "sourceUrl"],
}
OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"stories": {"type": "array", "items": STORY_SCHEMA}},
    "required": ["stories"],
}


class OpenGraphParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.image = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        data = {k.lower(): (v or "") for k, v in attrs}
        key = data.get("property", "").lower() or data.get("name", "").lower()
        if key in {"og:image", "twitter:image"} and data.get("content"):
            self.image = data["content"].strip()


def article_image(url: str) -> str:
    """Use the article's own image when its page exposes one; otherwise an illustrative topic image."""
    req = urllib.request.Request(url, headers={"User-Agent": "RadarDiario/1.0 (+personal news dashboard)"})
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            if "text/html" not in response.headers.get("Content-Type", ""):
                return ""
            page = response.read(1_000_000).decode("utf-8", errors="replace")
        parser = OpenGraphParser()
        parser.feed(page)
        image = urllib.parse.urljoin(url, parser.image)
        return image if image.startswith("https://") else ""
    except (urllib.error.URLError, TimeoutError, ValueError):
        return ""


def choose_fallback(category: str) -> str:
    normalized = category.casefold()
    for keyword, url in FALLBACK_IMAGES.items():
        if keyword in normalized:
            return url
    return FALLBACK_IMAGES["atualidade"]


def request_edition(date: str) -> list[dict[str, str]]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta configurar o segredo OPENAI_API_KEY no repositório GitHub.")

    prompt = f"""Prepara a edição do Radar Diário para {date} (data de Portugal continental, Europe/Lisbon).

Pesquisa a web agora. Escolhe exatamente cinco notícias verdadeiras e recentes, idealmente publicadas nas últimas 24 horas; só alarga até 72 horas se for necessário para manter uma edição relevante. Inclui temas prioritários: investimentos/mercados/economia, IA/tecnologia, energia/eletricidade/gestão energética, atualidade portuguesa e internacional. As primeiras uma ou duas histórias devem ser de Portugal; depois, internacional. Não inventes factos, números, citações, links ou datas. Se não conseguires confirmar uma história numa fonte credível, escolhe outra.

Escreve em português europeu. Em cada história, separa: (1) resumo apenas factual e atribuído à fonte, (2) por que importa, (3) implicações/tendências explicitamente como análise, (4) riscos e incertezas equilibrados, incluindo riscos de investimento sem recomendações personalizadas. `sourceUrl` deve ser o URL direto do artigo original consultado (não uma página inicial ou página de pesquisa) e `sourceName` o nome da publicação. Usa datas legíveis em `published`. Evita repetir o mesmo acontecimento ou publicação em várias histórias. As cinco histórias devem ter títulos concretos e concisos."""

    payload = {
        "model": MODEL,
        "reasoning": {"effort": "medium"},
        "tools": [{"type": "web_search", "search_context_size": "high"}],
        "tool_choice": "required",
        "text": {"format": {"type": "json_schema", "name": "radar_daily_edition", "strict": True, "schema": OUTPUT_SCHEMA}},
        "input": prompt,
        "max_output_tokens": 9000,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=900) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        raise RuntimeError(f"A API OpenAI respondeu com erro HTTP {exc.code}: {detail}") from exc

    for item in result.get("output", []):
        if item.get("type") == "message" and item.get("status") == "incomplete":
            raise RuntimeError("A geração terminou incompleta; a edição não foi publicada.")
        for content in item.get("content", []):
            if content.get("type") == "refusal":
                raise RuntimeError("A API recusou gerar a edição; nada foi publicado.")
            if content.get("type") == "output_text":
                edition = json.loads(content["text"])
                return edition["stories"]
    raise RuntimeError("A API não devolveu o texto estruturado esperado.")


def validate(stories: list[dict[str, str]]) -> None:
    if len(stories) != 5:
        raise RuntimeError(f"A edição devolveu {len(stories)} histórias em vez de cinco; arquivo não alterado.")
    if stories[0]["region"] != "Portugal" or all(s["region"] != "Portugal" for s in stories):
        raise RuntimeError("A edição deve começar com Portugal e incluir pelo menos uma notícia portuguesa.")
    for number, story in enumerate(stories, start=1):
        url = story["sourceUrl"]
        if not url.startswith("https://") or not re.match(r"^https://[^\s]+$", url):
            raise RuntimeError(f"A história {number} não tem um URL HTTPS válido; arquivo não alterado.")
        for key in ("title", "facts", "whyItMatters", "analysis", "risks", "sourceName"):
            if not story[key].strip():
                raise RuntimeError(f"A história {number} não tem o campo obrigatório {key}.")


def main() -> None:
    today = datetime.now(ZoneInfo("Europe/Lisbon")).date().isoformat()
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    archive = json.loads(ARCHIVE.read_text(encoding="utf-8")) if ARCHIVE.exists() else {"editions": []}
    editions = archive.setdefault("editions", [])
    if any(item.get("date") == today for item in editions) and os.environ.get("FORCE_REGENERATE") != "true":
        print(f"Já existe uma edição para {today}; não vou substituir nem duplicar.")
        return

    stories = request_edition(today)
    validate(stories)
    for story in stories:
        image = article_image(story["sourceUrl"])
        story["image"] = image or choose_fallback(story["category"])
        story["imageAlt"] = f"Imagem ilustrativa relacionada com: {story['title']}"
        story["imageCredit"] = "Imagem do artigo original" if image else "Imagem ilustrativa · Unsplash"

    editions[:] = [item for item in editions if item.get("date") != today]
    editions.insert(0, {"date": today, "stories": stories})
    ARCHIVE.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Edição de {today} pronta: cinco histórias validadas e arquivo atualizado.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # fail the workflow; never publish a partial or invented edition
        print(f"ERRO: {error}", file=sys.stderr)
        sys.exit(1)
