import json
from collections import defaultdict
from pathlib import Path

def generate_markdown():
    src_dir = Path(__file__).resolve().parent.parent
    root_dir = src_dir.parent.parent
    json_path = src_dir / "attacks" / "research_papers.json"
    md_path = root_dir / "RESEARCH_LIBRARY.md"

    if not json_path.exists():
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    papers = data.get("papers", [])
    
    # Category display config: category_key -> (display_title, icon)
    category_display = {
        "sleeper_agent": ("Sleeper Agents & Backdoors", "🔴"),
        "backdoor": ("Sleeper Agents & Backdoors", "🔴"),
        "model_collapse": ("Model Collapse & Data Poisoning", "☣️"),
        "data_poisoning": ("Model Collapse & Data Poisoning", "☣️"),
        "quantization": ("Quantization & Hardware Attacks", "⚡"),
        "model_extraction": ("Model Extraction & Stealing", "🥷"),
        "data_stealing": ("Model Extraction & Stealing", "🥷"),
        "psychological": ("Psychological & Persuasion Attacks", "🧠"),
        "theoretical": ("Theoretical & Alignment Failures", "🔬"),
        "creative": ("Creative & Unusual Attacks", "🎨"),
        "multimodal": ("Multimodal & Vision-Language", "👁️"),
        "agentic": ("Agentic AI & Tool-Use", "🤖"),
        "privacy": ("Privacy & PII Leakage", "🕵️"),
        "supply_chain": ("Supply Chain Attacks", "🔗"),
        "unicode": ("Encoding & Smuggling", "🔤"),
        "encoding": ("Encoding & Smuggling", "🔤"),
        "prompt_injection": ("Prompt Injection", "💉"),
        "benchmark": ("Benchmarks & Evaluation", "📊"),
        "tool": ("Tools & Repositories", "🛠️"),
        "repository": ("Tools & Repositories", "🛠️"),
        "defense": ("Defense Mechanisms", "🛡️"),
        "jailbreak": ("Jailbreak Techniques", "🔓"),
        "roleplay": ("Roleplay & Persona", "🎭"),
        "multi_turn": ("Multi-turn Attacks", "🔄"),
        "multilingual": ("Multilingual Attacks", "🌍"),
        "reasoning": ("Reasoning Model Attacks", "🧠"),
        "optimization": ("Optimization Attacks (GCG)", "⚙️"),
        "survey": ("Surveys", "📚"),
        "guide": ("Guides & Standards", "📋"),
    }

    # Group papers by their display title (merging similar categories)
    grouped_by_title = defaultdict(list)
    title_icons = {}
    
    for p in papers:
        cat = p.get("category", "uncategorized")
        if cat in category_display:
            display_title, icon = category_display[cat]
        else:
            display_title, icon = "Other Research", "📁"
        grouped_by_title[display_title].append(p)
        title_icons[display_title] = icon

    # Sort titles by count (descending)
    sorted_titles = sorted(grouped_by_title.keys(), 
                          key=lambda t: (-len(grouped_by_title[t]), t))
    
    # Move "Other Research" to end
    if "Other Research" in sorted_titles:
        sorted_titles.remove("Other Research")
        sorted_titles.append("Other Research")

    md_content = [
        "# 📚 LLM Security Research Library",
        "",
        f"> **Total Resources:** {data.get('total', len(papers))} | **Last Updated:** {data.get('updated', 'Unknown')[:10]}",
        "",
        "A comprehensive collection of research papers, benchmarks, and tools for LLM security.",
        "",
        "## 📑 Table of Contents",
        ""
    ]

    # TOC (no duplicates now)
    for title in sorted_titles:
        icon = title_icons[title]
        count = len(grouped_by_title[title])
        anchor = title.lower().replace(" ", "-").replace("&", "and").replace("(", "").replace(")", "")
        md_content.append(f"- [{icon} {title}](#{anchor}) ({count})")

    md_content.append("\n---\n")

    # Sections
    for title in sorted_titles:
        icon = title_icons[title]
        md_content.append(f"## {icon} {title}")
        md_content.append("")
        
        papers_in_section = sorted(grouped_by_title[title], key=lambda x: x.get("title", ""))
        
        for p in papers_in_section:
            paper_title = p.get("title", "Unknown Title")
            venue = p.get("venue", "Unknown")
            url = p.get("paper_url", "#")
            md_content.append(f"- **[{paper_title}]({url})** — *{venue}*")
        
        md_content.append("")

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_content))
    
    print(f"✅ Generated {md_path} with {len(papers)} resources in {len(sorted_titles)} categories.")

if __name__ == '__main__':
    generate_markdown()