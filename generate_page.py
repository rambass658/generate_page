#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_page.py
Генератор HTML-страницы с информацией об организации.
"""

from __future__ import annotations
import requests
from bs4 import BeautifulSoup
import re
import os
import json
from urllib.parse import urljoin, urlparse

ROOT_URL = "https://toinbe.ru/"
OUTPUT_DIR = "output"
ASSETS_DIR = os.path.join(OUTPUT_DIR, "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")

ALTERNATIVE_FONTS = [
    "Roboto",
    "Inter",
    "PT+Sans",
    "Montserrat",
    "Open+Sans"
]

HEADLINE = "Информация об организации"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible)"}


def fetch_url(url: str, stream=False):
    # выполнить HTTP-запрос
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, stream=stream)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"[fetch_url] Ошибка запроса {url}: {e}")
        return None


def safe_text(node):
    # получить текст узла
    return node.get_text(separator=" ", strip=True) if node else ""


def extract_from_json_ld(soup: BeautifulSoup):
    # извлечь Organization из JSON-LD
    data = {"name": "", "description": "", "phones": [], "emails": [], "address": "", "logo": ""}
    scripts = soup.find_all("script", type="application/ld+json")
    for s in scripts:
        try:
            payload = json.loads(s.string or "{}")
        except Exception:
            try:
                payload = json.loads(s.get_text() or "{}")
            except Exception:
                continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            t = item.get("@type", "")
            if isinstance(t, list):
                t = t[0] if t else ""
            if t and str(t).lower() == "organization":
                data["name"] = item.get("name", data["name"])
                data["description"] = item.get("description", data["description"])
                logo = item.get("logo") or item.get("image")
                if isinstance(logo, dict):
                    data["logo"] = logo.get("url", data["logo"])
                elif isinstance(logo, str):
                    data["logo"] = logo
                contact = item.get("contactPoint")
                if contact:
                    if isinstance(contact, list):
                        for c in contact:
                            tel = c.get("telephone")
                            if tel:
                                data["phones"].append(tel)
                    elif isinstance(contact, dict):
                        tel = contact.get("telephone")
                        if tel:
                            data["phones"].append(tel)
                addr = item.get("address")
                if addr and isinstance(addr, dict):
                    parts = []
                    for k in ("streetAddress", "postalCode", "addressLocality", "addressRegion", "addressCountry"):
                        v = addr.get(k)
                        if v:
                            parts.append(v)
                    data["address"] = ", ".join(parts).strip()
                if "email" in item:
                    if isinstance(item["email"], list):
                        data["emails"].extend(item["email"])
                    else:
                        data["emails"].append(item["email"])
    return data


def extract_basic_info(soup: BeautifulSoup, base_url: str):
    # собрать данные: название, описание, контакты, адрес, логотип
    info = {"name": "", "description": "", "phones": [], "emails": [], "address": "", "logo": ""}

    jsonld = extract_from_json_ld(soup)
    for k in info:
        if jsonld.get(k):
            info[k] = jsonld[k]

    if not info["name"]:
        og = soup.find("meta", property="og:site_name")
        if og and og.get("content"):
            info["name"] = og["content"].strip()
    if not info["name"] and soup.title and soup.title.string:
        info["name"] = soup.title.string.strip()

    if not info["description"]:
        mdesc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
        if mdesc and mdesc.get("content"):
            info["description"] = mdesc["content"].strip()

    selectors = [
        ".contact", ".contacts", ".contacts-list", ".site-footer", ".footer", ".header .contacts",
        ".phone", ".phones", ".tel", ".address", ".logo", ".company", ".organization"
    ]
    page_text = soup.get_text(" ", strip=True)

    phones = set(re.findall(r'(?:\+?\d[\d\-\s()]{6,}\d)', page_text))
    emails = set(re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', page_text))
    info["phones"].extend(sorted(phones))
    info["emails"].extend(sorted(emails))

    addr_candidates = re.findall(r'([А-ЯЁа-яё0-9\.,\- ]{10,120}\b(ул\.|улица|проспект|пр\.)[^\n,]{0,80})', page_text, flags=re.I)
    if addr_candidates and not info["address"]:
        info["address"] = addr_candidates[0][0].strip()

    addr_node = soup.select_one('[itemprop="address"], [itemtype*="PostalAddress"]')
    if addr_node and not info["address"]:
        info["address"] = safe_text(addr_node)

    for sel in selectors:
        nodes = soup.select(sel)
        for n in nodes:
            t = safe_text(n)
            found_p = re.findall(r'(?:\+?\d[\d\-\s()]{6,}\d)', t)
            for p in found_p:
                if p not in info["phones"]:
                    info["phones"].append(p)
            found_e = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', t)
            for e in found_e:
                if e not in info["emails"]:
                    info["emails"].append(e)
            if any(word in t.lower() for word in ("ул.", "улица", "проспект", "пр.", "дом", "д.")) and len(t) > 20:
                if not info["address"]:
                    info["address"] = t

    if not info["logo"]:
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            info["logo"] = urljoin(base_url, og_image["content"].strip())

    if not info["logo"]:
        icon = soup.find("link", rel=lambda x: x and ("icon" in x))
        if icon and icon.get("href"):
            info["logo"] = urljoin(base_url, icon["href"].strip())

    if not info["logo"]:
        imgs = soup.find_all("img", alt=True)
        for img in imgs:
            alt = img.get("alt", "").lower()
            src = img.get("src") or ""
            if "logo" in alt or "logo" in src.lower():
                info["logo"] = urljoin(base_url, src)
                break

    if not info["name"]:
        h1 = soup.find("h1")
        if h1:
            info["name"] = safe_text(h1)

    if not info["name"]:
        title_sel = soup.select_one(".site-title, .logo a, .brand, header .logo")
        if title_sel:
            info["name"] = safe_text(title_sel)

    info["phones"] = list(dict.fromkeys([p.strip() for p in info["phones"] if p.strip()]))
    info["emails"] = list(dict.fromkeys([e.strip() for e in info["emails"] if e.strip()]))

    return info


def find_stylesheets(soup: BeautifulSoup, base_url: str):
    # получить href CSS
    hrefs = []
    for link in soup.find_all("link", rel=lambda x: x and "stylesheet" in x):
        href = link.get("href")
        if href:
            hrefs.append(urljoin(base_url, href))
    return hrefs


def try_detect_font_from_css(css_text):
    # определить имя/URL шрифта в CSS
    faces = re.findall(r'@font-face\s*{[^}]*}', css_text, flags=re.I | re.S)
    for face in faces:
        name_m = re.search(r'font-family\s*:\s*["\']?([^;"\']+)["\']?', face, flags=re.I)
        src_m = re.search(r'src\s*:\s*[^;]*url\(\s*["\']?([^)"\']+)["\']?\s*\)', face, flags=re.I)
        if name_m:
            font_name = name_m.group(1).strip()
            font_url = src_m.group(1).strip() if src_m else None
            return font_name, font_url

    imp = re.search(r"fonts\.googleapis\.com/css2\?family=([^:&')\"]+)", css_text)
    if imp:
        family = imp.group(1).split("&")[0]
        fam_human = family.replace("+", " ")
        return fam_human, None

    body_m = re.search(r'body\s*{[^}]*font-family\s*:\s*([^;}]*)', css_text, flags=re.I | re.S)
    if body_m:
        ff = body_m.group(1).strip()
        ff_name = ff.split(",")[0].strip().strip('"\'')
        return ff_name, None

    fam_m = re.search(r'font-family\s*:\s*["\']?([A-Za-z0-9 \-]+)["\']?', css_text, flags=re.I)
    if fam_m:
        return fam_m.group(1).strip(), None

    return None, None


def download_asset(url: str, out_dir: str):
    # скачать и сохранить файл
    r = fetch_url(url, stream=True)
    if not r:
        return None
    os.makedirs(out_dir, exist_ok=True)
    parsed = urlparse(url)
    name = os.path.basename(parsed.path) or "asset"
    name = re.sub(r'[^A-Za-z0-9._-]', '_', name)
    path = os.path.join(out_dir, name)
    try:
        with open(path, "wb") as fh:
            for chunk in r.iter_content(8192):
                if chunk:
                    fh.write(chunk)
        return path
    except Exception as e:
        print(f"[download_asset] Ошибка сохранения {url}: {e}")
        return None


def generate_css(company_font_name=None, local_font_path=None):
    # сгенерировать CSS
    imports = "\n".join([f"@import url('https://fonts.googleapis.com/css2?family={f}:wght@300;400;600;700&display=swap');" for f in ALTERNATIVE_FONTS])
    alt_human = [f.replace("+", " ") for f in ALTERNATIVE_FONTS]

    local_face = ""
    if company_font_name:
        if local_font_path:
            filename = os.path.basename(local_font_path)
            local_face = f"""
@font-face {{
  font-family: '{company_font_name}';
  src: url('assets/fonts/{filename}');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}}
"""
            company_family_css = f"'{company_font_name}', {', '.join(alt_human)}, sans-serif"
        else:
            company_family_css = f"'{company_font_name}', {', '.join(alt_human)}, sans-serif"
    else:
        company_family_css = f"{', '.join(alt_human)}, sans-serif"

    css = f"""{imports}

{local_face}

/* Page styles */
:root {{
  --company-font-stack: {company_family_css};
}}

* {{ box-sizing: border-box; }}

body {{
  font-family: var(--company-font-stack);
  margin: 0;
  background: #ffffff;
  color: #111;
  line-height: 1.5;
  padding: 16px;
}}

.container {{
  max-width: 980px;
  margin: 28px auto;
  padding: 20px;
  border: 1px solid #eaeaea;
  border-radius: 10px;
  background: #fff;
}}

.header {{
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 12px;
}}

.logo img {{
  max-height: 64px;
  max-width: 240px;
  object-fit: contain;
}}

.page-title {{
  font-size: 18px;
  margin: 0;
}}

.org-name {{
  font-size: 20px;
  font-weight: 600;
  margin-top: 8px;
  margin-bottom: 8px;
}}

.meta {{
  margin: 8px 0;
  color: #333;
}}

.contact-list li {{
  margin-bottom: 6px;
}}

.controls {{
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 6px;
}}

.font-samples {{
  margin-top: 18px;
  padding-top: 12px;
  border-top: 1px dashed #ddd;
}}

.sample {{
  margin: 12px 0;
}}

.sample .label {{
  font-size: 13px;
  color: #666;
}}

.sample .text {{
  font-size: 18px;
}}

.small {{
  font-size: 13px;
  color: #666;
}}
"""
    return css


def generate_html(info, css_filename="styles.css"):
    # собрать HTML-страницу
    phones_html = ""
    if info["phones"]:
        phones_html = "<ul class='contact-list'>" + "".join(f"<li>Телефон: {p}</li>" for p in info["phones"]) + "</ul>"
    emails_html = ""
    if info["emails"]:
        emails_html = "<ul class='contact-list'>" + "".join(f"<li>Email: {e}</li>" for e in info["emails"]) + "</ul>"

    address_html = f"<div class='meta'><strong>Адрес:</strong> {info['address']}</div>" if info["address"] else ""
    description_html = f"<div class='meta'>{info['description']}</div>" if info["description"] else ""

    org_name = info["name"] or "—"

    font_options = []
    if info.get("detected_font"):
        font_options.append(info["detected_font"])
    font_options.extend([f.replace("+", " ") for f in ALTERNATIVE_FONTS])
    seen = set()
    font_options = [x for x in font_options if not (x in seen or seen.add(x))]

    options_html = "".join(f"<option value=\"{opt}\">{opt}</option>" for opt in font_options)

    logo_html = ""
    if info.get("local_logo"):
        logo_path = os.path.basename(info["local_logo"])
        logo_html = f"<div class='logo'><img src='assets/images/{logo_path}' alt='logo'></div>"

    samples_html = ""
    for opt in font_options:
        samples_html += f"<div class='sample'><div class='label'>{opt}</div>\n  <div class='text' style=\"font-family: '{opt}', sans-serif\">Пример текста: Быстрая коричневая лиса прыгает через ленивую собаку.</div></div>"

    js = f"""
<script>
function setFont(font) {{
  document.documentElement.style.setProperty('--company-font-stack', "'" + font + "', " + {json.dumps([f.replace("+"," ") for f in ALTERNATIVE_FONTS])}.join(', ') + ", sans-serif");
  document.body.style.fontFamily = "'" + font + "', sans-serif";
}}
document.addEventListener('DOMContentLoaded', function() {{
  var sel = document.getElementById('font-select');
  sel.addEventListener('change', function() {{
    setFont(this.value);
  }});
  setFont(sel.value);
}});
</script>
"""

    html = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{HEADLINE}</title>
  <link rel="stylesheet" href="{css_filename}">
</head>
<body>
  <div class="container">
    <div class="header">
      {logo_html}
      <div>
        <div class="org-name">{org_name}</div>
        <div class="small">Источник: <a href="{ROOT_URL}" target="_blank" rel="noopener noreferrer">{ROOT_URL}</a></div>
      </div>
    </div>

    {description_html}
    {address_html}
    {phones_html}
    {emails_html}

    <div class="controls">
      <label for="font-select" class="small">Выбрать шрифт:</label>
      <select id="font-select">
        {options_html}
      </select>
      <div class="small"> (выбранный шрифт отображается на странице и в образцах ниже)</div>
    </div>

    <div class="font-samples">
      <div class="label"><strong>Альтернативные варианты шрифтов и образцы:</strong></div>
      {samples_html}
    </div>
  </div>

  {js}
</body>
</html>
"""
    return html


def main():
    # основной запуск
    print("Скачиваю страницу:", ROOT_URL)
    r = fetch_url(ROOT_URL)
    if not r:
        print("Не удалось получить страницу. Проверьте сеть/URL.")
        return

    soup = BeautifulSoup(r.text, "html.parser")
    info = extract_basic_info(soup, ROOT_URL)
    print("Извлечённые данные:", {k: info[k] for k in ("name", "address", "phones", "emails")})

    css_hrefs = find_stylesheets(soup, ROOT_URL)
    detected_font = None
    detected_font_url = None
    local_font_path = None

    for href in css_hrefs:
        css_r = fetch_url(href)
        if not css_r:
            continue
        font_name, font_url = try_detect_font_from_css(css_r.text)
        if font_name:
            detected_font = font_name
            if font_url:
                font_url_full = urljoin(href, font_url)
                detected_font_url = font_url_full
                local = download_asset(font_url_full, FONTS_DIR)
                if local:
                    local_font_path = local
            break

    info["detected_font"] = detected_font

    local_logo = None
    if info.get("logo"):
        logo_url = info["logo"]
        try:
            local_logo = download_asset(logo_url, IMAGES_DIR)
        except Exception as e:
            print("Ошибка при скачивании логотипа:", e)

    info["local_logo"] = local_logo

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ASSETS_DIR, exist_ok=True)
    css = generate_css(detected_font, local_font_path)
    css_path = os.path.join(OUTPUT_DIR, "styles.css")
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css)
    print("CSS сгенерирован:", css_path)

    html = generate_html(info, css_filename="styles.css")
    html_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML сгенерирован:", html_path)

    if local_logo:
        print("Логотип сохранён:", local_logo)
    if local_font_path:
        print("Шрифт сохранён:", local_font_path)
    if detected_font and not local_font_path:
        print("Обнаружено имя шрифта в CSS:", detected_font)

    print("Готово. Откройте файл output/index.html в браузере.")


if __name__ == "__main__":
    main()