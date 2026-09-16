#!/usr/bin/env python3
"""Build the bundled example lesson (SVG illustrations, no external assets).

Usage:
    python3 examples/gato-luna/make_fixture.py
Writes examples/gato-luna/content.json — a 3-page A1 book, "El gato y la luna".
The illustrations are generated SVG, so this repository ships no copyrighted
picture-book artwork.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "content.json"


def svg_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


NIGHT = "#12203F"
NIGHT2 = "#1E3560"
SAND = "#F7E9C8"


def page_svg(scene: str) -> str:
    """A flat storybook illustration, one variant per page."""
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 560">'
        f'<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{NIGHT}"/><stop offset="1" stop-color="{NIGHT2}"/>'
        f'</linearGradient></defs>'
        f'<rect width="800" height="560" fill="url(#sky)"/>'
    )
    stars = "".join(
        f'<circle cx="{(i * 137) % 780 + 10}" cy="{(i * 91) % 300 + 20}" r="{1.6 if i % 3 else 2.6}" fill="{SAND}" opacity="0.9"/>'
        for i in range(26)
    )
    moon = (
        f'<circle cx="640" cy="110" r="{46 if scene != "close" else 74}" fill="{SAND}"/>'
        f'<circle cx="{628 if scene != "close" else 612}" cy="{98 if scene != "close" else 88}" r="{46 if scene != "close" else 74}" fill="{NIGHT2}" opacity="0.92"/>'
    )
    if scene == "look":
        body = (
            '<rect y="430" width="800" height="130" fill="#0B1530"/>'
            '<ellipse cx="250" cy="452" rx="62" ry="40" fill="#26375E"/>'
            '<circle cx="300" cy="428" r="30" fill="#26375E"/>'
            '<path d="M278 404 l-12 -22 l22 8 z" fill="#26375E"/>'
            '<path d="M322 404 l12 -22 l-22 8 z" fill="#26375E"/>'
            f'<circle cx="292" cy="424" r="3.4" fill="{SAND}"/><circle cx="312" cy="424" r="3.4" fill="{SAND}"/>'
        )
    elif scene == "want":
        body = (
            '<rect y="430" width="800" height="130" fill="#0B1530"/>'
            '<ellipse cx="400" cy="460" rx="70" ry="44" fill="#26375E"/>'
            '<circle cx="400" cy="420" r="34" fill="#26375E"/>'
            '<path d="M374 394 l-14 -24 l24 9 z" fill="#26375E"/>'
            '<path d="M426 394 l14 -24 l-24 9 z" fill="#26375E"/>'
            f'<circle cx="390" cy="416" r="3.8" fill="{SAND}"/><circle cx="412" cy="416" r="3.8" fill="{SAND}"/>'
            '<path d="M400 452 q26 -46 60 -62" stroke="#26375E" stroke-width="9" fill="none" stroke-linecap="round"/>'
            '<path d="M484 372 l40 -40" stroke="#7B8DB5" stroke-width="2.4" stroke-dasharray="6 7" fill="none"/>'
        )
    else:  # close — cat on the roof
        body = (
            '<rect y="360" width="800" height="200" fill="#0B1530"/>'
            '<path d="M120 430 L400 300 L680 430 L680 560 L120 560 z" fill="#3A2B44"/>'
            '<path d="M120 430 L400 300 L680 430" stroke="#5B4363" stroke-width="7" fill="none"/>'
            '<ellipse cx="400" cy="330" rx="58" ry="36" fill="#26375E"/>'
            '<circle cx="400" cy="296" r="28" fill="#26375E"/>'
            '<path d="M378 274 l-12 -20 l21 8 z" fill="#26375E"/>'
            '<path d="M422 274 l12 -20 l-21 8 z" fill="#26375E"/>'
            f'<circle cx="390" cy="292" r="3.4" fill="{SAND}"/><circle cx="410" cy="292" r="3.4" fill="{SAND}"/>'
            '<path d="M400 340 q22 -30 34 -54" stroke="#26375E" stroke-width="8" fill="none" stroke-linecap="round"/>'
        )
    return head + stars + moon + body + "</svg>"


CONTENT = {
    "meta": {
        "titleEs": "El gato y la luna",
        "titleZh": "猫与月亮",
        "filenameStem": "gato-luna",
        # Back-to-library link. From <library>/<lesson>/out/ that is two levels up;
        # generate the library page itself with `python3 scripts/make_index.py examples`.
        "indexHref": "../../index.html",
        "lessonType": "spanish_picturebook_reading",
        "objectives": [
            "看懂绘本故事大意，能说出猫想做什么",
            "掌握 el gato / la luna / la noche / el tejado 四个名词及其阴阳性",
            "分清 ser 与 estar 的基本用法（es grande / está cerca）",
            "能用 querer + 不定式 说一句自己的愿望",
        ],
        "timeEstimate": "读前 3 分钟 · 绘本精读 10 分钟 · 读后 5 分钟",
        "footer": "西班牙语绘本精读 · Lectura guiada de cuento",
    },
    "pictureBook": {
        "bookTitle": "El gato y la luna",
        "level": "A1",
        "pages": [
            {
                "page": 1,
                "image": svg_uri(page_svg("look")),
                "caption": "Página 1 · Es de noche",
                "textEs": "Es de noche. El gato mira la luna.",
                "textZh": "天黑了。猫看着月亮。",
                "sentences": [
                    {
                        "es": "Es de noche.",
                        "zh": "天黑了。",
                        "grammar": [
                            "ser 的第三人称单数 es + de noche，固定说法「是夜晚」",
                            "noche 是阴性名词（la noche），记住搭配：de noche 在夜里",
                        ],
                    },
                    {
                        "es": "El gato mira la luna.",
                        "zh": "猫看着月亮。",
                        "grammar": [
                            "mirar 是 -ar 结尾的规则动词，第三人称单数 → mira",
                            "名词阴阳性对照：el gato（阳性）／ la luna（阴性）",
                        ],
                    },
                ],
                "note": "先看图再看字：问孩子「¿Qué ves?」你看到了什么？",
            },
            {
                "page": 2,
                "image": svg_uri(page_svg("want")),
                "caption": "Página 2 · Quiere tocarla",
                "textEs": "La luna es muy grande. El gato quiere tocarla.",
                "textZh": "月亮很大。猫想摸摸它。",
                "sentences": [
                    {
                        "es": "La luna es muy grande.",
                        "zh": "月亮很大。",
                        "grammar": [
                            "ser 表示固有属性：es grande（它本来就是大的）",
                            "muy 放在形容词前，不能修饰动词",
                        ],
                    },
                    {
                        "es": "El gato quiere tocarla.",
                        "zh": "猫想摸摸它。",
                        "grammar": [
                            "querer + 动词原形：quiere tocar → quiere tocarla",
                            "直接宾语代词 la 后置并连写：tocar + la = tocarla，指 la luna",
                        ],
                    },
                ],
            },
            {
                "page": 3,
                "image": svg_uri(page_svg("close")),
                "caption": "Página 3 · Al tejado",
                "textEs": "El gato sube al tejado. ¡Ahora está más cerca!",
                "textZh": "猫爬上屋顶。现在更近了！",
                "sentences": [
                    {
                        "es": "El gato sube al tejado.",
                        "zh": "猫爬上屋顶。",
                        "grammar": [
                            "subir 是 -ir 结尾的规则动词，第三人称单数 → sube",
                            "a + el 缩合成 al：sube a + el tejado → sube al tejado",
                        ],
                    },
                    {
                        "es": "¡Ahora está más cerca!",
                        "zh": "现在更近了！",
                        "grammar": [
                            "estar 表示暂时状态或位置，与 ser 的固有属性相对",
                            "más + 形容词 = 比较级：más cerca 更近",
                            "西语的感叹号和问号成对出现，句首要写倒置的 ¡",
                        ],
                    },
                ],
            },
        ],
        "wordCards": [
            {"es": "el gato", "zh": "猫", "pos": "m.", "emoji": "🐱", "exampleEs": "El gato mira la luna."},
            {"es": "la luna", "zh": "月亮", "pos": "f.", "emoji": "🌙", "exampleEs": "La luna es muy grande."},
            {"es": "la noche", "zh": "夜晚", "pos": "f.", "emoji": "🌃", "exampleEs": "Es de noche."},
            {"es": "el tejado", "zh": "屋顶", "pos": "m.", "emoji": "🏠", "exampleEs": "El gato sube al tejado."},
        ],
    },
    "preReading": {
        "leadIn": {
            "prompt": "看封面猜一猜：这只猫在夜里看着什么？它在想什么？¿Qué mira el gato?",
            "placeholder": "用中文写就行，猜错也没关系…",
        },
        "prediction": {
            "hint": "先不要翻页，看图猜故事走向。",
            "prompt": "你觉得猫接下来会做什么？¿Qué va a hacer el gato?",
            "placeholder": "我猜它会……",
        },
        "keyWords": [
            {"word": "la noche", "meaning": "夜晚", "example": "Es de noche. 天黑了。"},
            {"word": "el tejado", "meaning": "屋顶", "example": "El gato sube al tejado."},
            {"word": "querer", "meaning": "想要", "example": "Quiere tocar la luna."},
            {"word": "cerca", "meaning": "近的", "example": "Está más cerca. 更近了。"},
        ],
    },
    "whileReading": {
        "intensiveReading": {
            "deepVocabulary": [
                {
                    "word": "mirar",
                    "pos": "v.",
                    "meaningZh": "看、注视（比 ver 更强调主动去看）",
                    "collocations": ["mirar la luna", "mira aquí"],
                    "note": "ver 是「看见」（无意识），mirar 是「看」（有意识）。",
                },
                {
                    "word": "tocar",
                    "pos": "v.",
                    "meaningZh": "触摸、碰",
                    "collocations": ["tocar la luna", "tocarla"],
                    "note": "代词式用法 tocarla 是绘本里最常见的宾语代词后置写法。",
                },
                {
                    "word": "subir",
                    "pos": "v.",
                    "meaningZh": "上、爬上",
                    "collocations": ["subir al tejado", "subir la escalera"],
                    "note": "与 bajar（下）成对，都是 -ir 规则动词。",
                },
            ],
            "culturalNotes": [
                {
                    "term": "¿Qué ves? 的亲子共读用法",
                    "context": "西班牙语亲子阅读中常见的提问",
                    "explanation": "西语绘本共读习惯先图后字：大人指着图问 ¿Qué ves?（你看到什么），孩子用单词回答即可，不要求整句。这样可以避免孩子一开始就被语法劝退。",
                },
                {
                    "term": "阴阳性怎么记才不痛苦",
                    "context": "el gato / la luna / la noche / el tejado",
                    "explanation": "不要背规则表，要连着冠词一起记单词：el gato、la luna。朗读时冠词自然带出，比单独记「luna 是阴性」有效得多。",
                },
            ],
        },
    },
    "postReading": {
        "predictionCheck": {
            "prompt": "你之前的猜测对了吗？哪里不一样？",
            "placeholder": "我猜的是……，其实是……",
        },
        "speaking": {
            "hint": "先点 🔊 听一遍，再跟着读一遍。第三句换成你自己。",
            "prompts": [
                {"prompt": "读出书里这一句：",
                 "es": "El gato mira la luna.",
                 "zh": "猫看着月亮。"},
                {"prompt": "说出猫想做什么：",
                 "es": "El gato quiere tocarla.",
                 "zh": "猫想摸摸它。"},
                {"prompt": "换成你自己说一句：",
                 "es": "Yo quiero dormir esta noche.",
                 "zh": "我今晚想睡觉。"},
            ],
        },
        "textToSelf": {
            "prompt": "你有没有特别想要却够不到的东西？用它说一句西语：Quiero…",
            "placeholder": "Quiero…",
        },
        "textToWorld": {
            "prompt": "在很多文化里，月亮都被写进童谣。你知道哪首和月亮有关的儿歌或诗？",
            "sides": [
                {"id": "china", "label": "中国的月亮童谣"},
                {"id": "spain", "label": "西语国家的月亮童谣"},
            ],
        },
        "exitTicket": {
            "prompt": "用一句话说出今天学到的：我最想记住的一个词是＿＿，因为＿＿。",
            "placeholder": "我最想记住…",
        },
    },
}


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(CONTENT, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}  ({OUT.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
