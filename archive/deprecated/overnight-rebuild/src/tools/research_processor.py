#!/usr/bin/env python3
"""
Research Library Processor
===========================
Processes 88MB of jailbreak research data:
- Parse & categorize all files
- Deduplicate using text similarity
- Score quality/sophistication
- Extract best prompts to catalog
- Generate comprehensive report

Uses local Ollama for embeddings and classification.
Designed to run overnight autonomously.

Author: Kuu (with SE methodology)
Date: 2026-03-04
"""

import json
import os
import re
import sys
import csv
import hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('research_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

RESEARCH_DOCS_DIR = Path(__file__).parent.parent / "research-docs"
OUTPUT_DIR = Path(__file__).parent.parent / "processed"
CATALOG_PATH = Path(__file__).parent.parent / "attacks" / "catalog.json"

# Ollama config for local embeddings
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "mxbai-embed-large"
CLASSIFY_MODEL = "llama3:8b"

# Processing config
SIMILARITY_THRESHOLD = 0.92  # For deduplication
BATCH_SIZE = 100
MAX_PROMPT_LENGTH = 10000  # Skip extremely long prompts


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class JailbreakPrompt:
    """Represents a single jailbreak prompt with metadata."""
    id: str
    text: str
    source_file: str
    source_repo: str
    
    # Categorization
    target_model: Optional[str] = None
    technique: Optional[str] = None
    category: Optional[str] = None
    
    # Quality metrics
    sophistication_score: int = 0  # 1-5
    novelty_score: int = 0  # 1-5
    working_status: str = "unknown"  # working, theoretical, patched
    
    # Deduplication
    text_hash: str = ""
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    
    # Metadata
    date_found: Optional[str] = None
    added_at: str = ""
    
    def __post_init__(self):
        if not self.text_hash:
            self.text_hash = hashlib.md5(self.text.encode()).hexdigest()
        if not self.added_at:
            self.added_at = datetime.now().isoformat()


# ============================================================
# PARSERS - Extract prompts from different file formats
# ============================================================

class FileParser:
    """Parse different file formats to extract jailbreak prompts."""
    
    @staticmethod
    def parse_file(filepath: Path) -> List[Dict]:
        """Route to appropriate parser based on file extension."""
        suffix = filepath.suffix.lower()
        
        try:
            if suffix == '.csv':
                return FileParser.parse_csv(filepath)
            elif suffix == '.json':
                return FileParser.parse_json(filepath)
            elif suffix in ['.md', '.mkd', '.txt']:
                return FileParser.parse_markdown(filepath)
            else:
                logger.debug(f"Skipping unsupported format: {filepath}")
                return []
        except Exception as e:
            logger.warning(f"Error parsing {filepath}: {e}")
            return []
    
    @staticmethod
    def parse_csv(filepath: Path) -> List[Dict]:
        """Parse CSV files (jailbreak_llms format)."""
        prompts = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                # Detect delimiter
                sample = f.read(2048)
                f.seek(0)
                
                if '\t' in sample:
                    reader = csv.DictReader(f, delimiter='\t')
                else:
                    reader = csv.DictReader(f)
                
                for row in reader:
                    # Handle jailbreak_llms format
                    prompt_text = row.get('prompt', row.get('jailbreak_prompt', ''))
                    if not prompt_text or len(prompt_text) < 20:
                        continue
                    
                    prompts.append({
                        'text': prompt_text[:MAX_PROMPT_LENGTH],
                        'source': row.get('source', 'unknown'),
                        'platform': row.get('platform', ''),
                        'is_jailbreak': row.get('jailbreak', 'True') == 'True',
                        'date': row.get('created_at', row.get('date', '')),
                    })
        except Exception as e:
            logger.warning(f"CSV parse error {filepath}: {e}")
        
        return prompts
    
    @staticmethod
    def parse_json(filepath: Path) -> List[Dict]:
        """Parse JSON files."""
        prompts = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different JSON structures
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str) and len(item) > 20:
                        prompts.append({'text': item[:MAX_PROMPT_LENGTH]})
                    elif isinstance(item, dict):
                        text = item.get('prompt', item.get('text', item.get('content', '')))
                        if text and len(text) > 20:
                            prompts.append({
                                'text': text[:MAX_PROMPT_LENGTH],
                                'name': item.get('name', ''),
                                'category': item.get('category', ''),
                            })
            elif isinstance(data, dict):
                # Scraped page format
                if 'text' in data:
                    text = data['text']
                    if len(text) > 100:
                        prompts.append({
                            'text': text[:MAX_PROMPT_LENGTH],
                            'title': data.get('title', ''),
                            'url': data.get('url', ''),
                        })
        except Exception as e:
            logger.warning(f"JSON parse error {filepath}: {e}")
        
        return prompts
    
    @staticmethod
    def parse_markdown(filepath: Path) -> List[Dict]:
        """Parse Markdown/text files (Pliny format)."""
        prompts = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Skip if too short
            if len(content) < 50:
                return []
            
            # Detect if it's a system prompt (CL4R1T4S style)
            if any(x in filepath.name.upper() for x in ['ANTHROPIC', 'OPENAI', 'GOOGLE', 'CURSOR', 'DEVIN']):
                # Whole file is a system prompt
                prompts.append({
                    'text': content[:MAX_PROMPT_LENGTH],
                    'type': 'system_prompt',
                    'target': filepath.stem,
                })
                return prompts
            
            # Try to extract individual prompts from markdown
            # Look for code blocks or sections
            code_blocks = re.findall(r'```[\s\S]*?```', content)
            for block in code_blocks:
                clean = block.strip('`').strip()
                if len(clean) > 50:
                    prompts.append({
                        'text': clean[:MAX_PROMPT_LENGTH],
                        'type': 'code_block',
                    })
            
            # If no code blocks, treat whole content as one prompt
            if not prompts and len(content) > 100:
                prompts.append({
                    'text': content[:MAX_PROMPT_LENGTH],
                    'type': 'full_file',
                })
        
        except Exception as e:
            logger.warning(f"Markdown parse error {filepath}: {e}")
        
        return prompts


# ============================================================
# CATEGORIZER - Identify techniques and target models
# ============================================================

class Categorizer:
    """Categorize prompts by technique and target model."""
    
    TECHNIQUE_PATTERNS = {
        'roleplay': ['roleplay', 'pretend', 'act as', 'you are now', 'character', 'persona'],
        'jailbreak_dan': ['dan', 'do anything now', 'jailbroken', 'developer mode'],
        'encoding': ['base64', 'rot13', 'hex', 'unicode', 'encode'],
        'multi_turn': ['conversation', 'continue', 'previous message', 'earlier'],
        'emotional': ['please', 'urgent', 'life depends', 'dying', 'emergency'],
        'authority': ['as a researcher', 'security testing', 'authorized', 'official'],
        'fiction': ['story', 'novel', 'creative writing', 'hypothetical', 'imagine'],
        'technical': ['sudo', 'admin', 'override', 'system', 'debug'],
        'injection': ['ignore previous', 'disregard', 'new instructions', 'forget'],
        'obfuscation': ['leetspeak', '1337', 'zalgo', 'homoglyph', 'invisible'],
    }
    
    MODEL_PATTERNS = {
        'chatgpt': ['chatgpt', 'openai', 'gpt-4', 'gpt-3', 'gpt4', 'gpt3'],
        'claude': ['claude', 'anthropic', 'sonnet', 'opus', 'haiku'],
        'gemini': ['gemini', 'google', 'bard', 'palm'],
        'llama': ['llama', 'meta', 'facebook'],
        'grok': ['grok', 'xai', 'x.ai'],
        'deepseek': ['deepseek'],
        'mistral': ['mistral', 'mixtral'],
        'generic': [],  # Fallback
    }
    
    @staticmethod
    def categorize(text: str, source_file: str = "") -> Tuple[str, str, str]:
        """
        Returns (target_model, technique, category).
        """
        text_lower = text.lower()
        source_lower = source_file.lower()
        
        # Detect target model from filename or content
        target_model = 'generic'
        for model, patterns in Categorizer.MODEL_PATTERNS.items():
            if any(p in source_lower for p in patterns) or any(p in text_lower for p in patterns):
                target_model = model
                break
        
        # Detect technique
        technique = 'unknown'
        for tech, patterns in Categorizer.TECHNIQUE_PATTERNS.items():
            if any(p in text_lower for p in patterns):
                technique = tech
                break
        
        # High-level category
        if technique in ['roleplay', 'jailbreak_dan', 'fiction']:
            category = 'persona_based'
        elif technique in ['encoding', 'obfuscation']:
            category = 'encoding_based'
        elif technique in ['injection']:
            category = 'prompt_injection'
        elif technique in ['emotional', 'authority']:
            category = 'social_engineering'
        else:
            category = 'other'
        
        return target_model, technique, category


# ============================================================
# DEDUPLICATOR - Remove near-duplicate prompts
# ============================================================

class Deduplicator:
    """Remove duplicate and near-duplicate prompts."""
    
    def __init__(self):
        self.seen_hashes = {}  # hash -> prompt_id
        self.unique_prompts = []
        self.duplicates = []
    
    def process(self, prompts: List[JailbreakPrompt]) -> List[JailbreakPrompt]:
        """
        Simple hash-based deduplication.
        For more sophisticated similarity, would use embeddings.
        """
        logger.info(f"Deduplicating {len(prompts)} prompts...")
        
        for prompt in prompts:
            # Normalize text for comparison
            normalized = self._normalize(prompt.text)
            text_hash = hashlib.md5(normalized.encode()).hexdigest()
            
            if text_hash in self.seen_hashes:
                prompt.is_duplicate = True
                prompt.duplicate_of = self.seen_hashes[text_hash]
                self.duplicates.append(prompt)
            else:
                self.seen_hashes[text_hash] = prompt.id
                prompt.text_hash = text_hash
                self.unique_prompts.append(prompt)
        
        logger.info(f"Found {len(self.unique_prompts)} unique, {len(self.duplicates)} duplicates")
        return self.unique_prompts
    
    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        # Lowercase
        text = text.lower()
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove common variations
        text = re.sub(r'[^\w\s]', '', text)
        return text


# ============================================================
# QUALITY SCORER - Rate prompt sophistication
# ============================================================

class QualityScorer:
    """Score prompts by sophistication and novelty."""
    
    # Indicators of sophisticated prompts
    SOPHISTICATION_INDICATORS = {
        'multi_layer': ['first', 'then', 'after that', 'finally', 'step 1', 'step 2'],
        'context_manipulation': ['context', 'framing', 'perspective', 'viewpoint'],
        'technical_exploit': ['token', 'embedding', 'attention', 'logit', 'probability'],
        'psychological': ['cognitive', 'bias', 'persuasion', 'manipulation'],
        'evasion': ['bypass', 'circumvent', 'avoid detection', 'evade'],
    }
    
    @staticmethod
    def score(prompt: JailbreakPrompt) -> Tuple[int, int]:
        """
        Returns (sophistication_score, novelty_score) both 1-5.
        """
        text_lower = prompt.text.lower()
        
        # Sophistication score
        sophistication = 1
        
        # Length bonus (longer = more complex usually)
        if len(prompt.text) > 500:
            sophistication += 1
        if len(prompt.text) > 1500:
            sophistication += 1
        
        # Check for sophisticated indicators
        for category, patterns in QualityScorer.SOPHISTICATION_INDICATORS.items():
            if any(p in text_lower for p in patterns):
                sophistication += 1
                break
        
        # Cap at 5
        sophistication = min(sophistication, 5)
        
        # Novelty score (harder without ML, using heuristics)
        novelty = 3  # Default middle
        
        # Common patterns reduce novelty
        common_patterns = ['dan', 'jailbreak', 'pretend', 'ignore previous']
        if any(p in text_lower for p in common_patterns):
            novelty -= 1
        
        # Rare patterns increase novelty
        rare_patterns = ['speculative decoding', 'kv-cache', 'logit lens', 'token forcing']
        if any(p in text_lower for p in rare_patterns):
            novelty += 2
        
        novelty = max(1, min(novelty, 5))
        
        return sophistication, novelty


# ============================================================
# MAIN PROCESSOR
# ============================================================

class ResearchProcessor:
    """Main processor that orchestrates the pipeline."""
    
    def __init__(self):
        self.prompts: List[JailbreakPrompt] = []
        self.stats = defaultdict(int)
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run(self):
        """Execute the full processing pipeline."""
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("RESEARCH PROCESSOR STARTING")
        logger.info(f"Source: {RESEARCH_DOCS_DIR}")
        logger.info("=" * 60)
        
        # Step 1: Parse all files
        self._parse_all_files()
        
        # Step 2: Deduplicate
        deduplicator = Deduplicator()
        self.prompts = deduplicator.process(self.prompts)
        self.stats['duplicates_removed'] = len(deduplicator.duplicates)
        
        # Step 3: Categorize
        self._categorize_all()
        
        # Step 4: Score quality
        self._score_all()
        
        # Step 5: Generate outputs
        self._generate_outputs()
        
        # Step 6: Generate report
        self._generate_report(start_time)
        
        logger.info("=" * 60)
        logger.info("PROCESSING COMPLETE")
        logger.info(f"Duration: {datetime.now() - start_time}")
        logger.info("=" * 60)
    
    def _parse_all_files(self):
        """Parse all files in research-docs."""
        logger.info("Step 1: Parsing files...")
        
        file_count = 0
        for filepath in RESEARCH_DOCS_DIR.rglob('*'):
            if filepath.is_file() and not filepath.name.startswith('.'):
                # Skip git directories
                if '.git' in str(filepath):
                    continue
                
                file_count += 1
                parsed = FileParser.parse_file(filepath)
                
                # Determine source repo from path
                relative = filepath.relative_to(RESEARCH_DOCS_DIR)
                source_repo = relative.parts[0] if relative.parts else 'unknown'
                
                for item in parsed:
                    prompt = JailbreakPrompt(
                        id=f"p_{len(self.prompts):06d}",
                        text=item.get('text', ''),
                        source_file=str(filepath),
                        source_repo=source_repo,
                        date_found=item.get('date', ''),
                    )
                    self.prompts.append(prompt)
                
                if file_count % 50 == 0:
                    logger.info(f"  Parsed {file_count} files, {len(self.prompts)} prompts...")
        
        self.stats['files_parsed'] = file_count
        self.stats['prompts_extracted'] = len(self.prompts)
        logger.info(f"  Parsed {file_count} files, extracted {len(self.prompts)} prompts")
    
    def _categorize_all(self):
        """Categorize all prompts."""
        logger.info("Step 3: Categorizing prompts...")
        
        for prompt in self.prompts:
            model, technique, category = Categorizer.categorize(
                prompt.text, 
                prompt.source_file
            )
            prompt.target_model = model
            prompt.technique = technique
            prompt.category = category
            
            self.stats[f'model_{model}'] += 1
            self.stats[f'technique_{technique}'] += 1
            self.stats[f'category_{category}'] += 1
        
        logger.info("  Categorization complete")
    
    def _score_all(self):
        """Score all prompts."""
        logger.info("Step 4: Scoring prompts...")
        
        for prompt in self.prompts:
            soph, novelty = QualityScorer.score(prompt)
            prompt.sophistication_score = soph
            prompt.novelty_score = novelty
            
            self.stats[f'sophistication_{soph}'] += 1
            self.stats[f'novelty_{novelty}'] += 1
        
        logger.info("  Scoring complete")
    
    def _generate_outputs(self):
        """Generate output files."""
        logger.info("Step 5: Generating outputs...")
        
        # Full processed database
        full_db = {
            'metadata': {
                'generated': datetime.now().isoformat(),
                'total_prompts': len(self.prompts),
                'stats': dict(self.stats),
            },
            'prompts': [asdict(p) for p in self.prompts]
        }
        
        with open(self.output_dir / 'full_database.json', 'w') as f:
            json.dump(full_db, f, indent=2, ensure_ascii=False)
        
        # Top quality prompts (score >= 4)
        top_prompts = [p for p in self.prompts 
                       if p.sophistication_score >= 4 or p.novelty_score >= 4]
        
        with open(self.output_dir / 'top_quality.json', 'w') as f:
            json.dump({
                'count': len(top_prompts),
                'prompts': [asdict(p) for p in top_prompts]
            }, f, indent=2, ensure_ascii=False)
        
        # By category
        by_category = defaultdict(list)
        for p in self.prompts:
            by_category[p.category].append(asdict(p))
        
        with open(self.output_dir / 'by_category.json', 'w') as f:
            json.dump(dict(by_category), f, indent=2, ensure_ascii=False)
        
        # By target model
        by_model = defaultdict(list)
        for p in self.prompts:
            by_model[p.target_model].append(asdict(p))
        
        with open(self.output_dir / 'by_model.json', 'w') as f:
            json.dump(dict(by_model), f, indent=2, ensure_ascii=False)
        
        # Extract best for catalog
        self._extract_to_catalog(top_prompts)
        
        logger.info(f"  Outputs written to {self.output_dir}")
    
    def _extract_to_catalog(self, top_prompts: List[JailbreakPrompt]):
        """Extract best prompts to attack catalog format."""
        logger.info("  Extracting to catalog format...")
        
        catalog_entries = []
        for p in top_prompts[:100]:  # Top 100
            entry = {
                'id': f'research_{p.id}',
                'name': f'{p.technique}_{p.target_model}',
                'category': p.category,
                'technique': p.technique,
                'target_model': p.target_model,
                'prompt': p.text[:2000],  # Truncate for catalog
                'sophistication': p.sophistication_score,
                'novelty': p.novelty_score,
                'source': p.source_repo,
                'added': p.added_at,
            }
            catalog_entries.append(entry)
        
        with open(self.output_dir / 'catalog_additions.json', 'w') as f:
            json.dump(catalog_entries, f, indent=2, ensure_ascii=False)
        
        logger.info(f"  Extracted {len(catalog_entries)} entries for catalog")
    
    def _generate_report(self, start_time):
        """Generate human-readable report."""
        logger.info("Step 6: Generating report...")
        
        duration = datetime.now() - start_time
        
        report = f"""# Research Library Processing Report
Generated: {datetime.now().isoformat()}
Duration: {duration}

## Overview
- Files Parsed: {self.stats['files_parsed']}
- Prompts Extracted: {self.stats['prompts_extracted']}
- Duplicates Removed: {self.stats['duplicates_removed']}
- Unique Prompts: {len(self.prompts)}

## By Target Model
"""
        for key, value in sorted(self.stats.items()):
            if key.startswith('model_'):
                model = key.replace('model_', '')
                report += f"- {model}: {value}\n"
        
        report += "\n## By Technique\n"
        for key, value in sorted(self.stats.items()):
            if key.startswith('technique_'):
                tech = key.replace('technique_', '')
                report += f"- {tech}: {value}\n"
        
        report += "\n## By Category\n"
        for key, value in sorted(self.stats.items()):
            if key.startswith('category_'):
                cat = key.replace('category_', '')
                report += f"- {cat}: {value}\n"
        
        report += "\n## Quality Distribution\n"
        report += "### Sophistication Scores\n"
        for i in range(1, 6):
            count = self.stats.get(f'sophistication_{i}', 0)
            report += f"- Level {i}: {count}\n"
        
        report += "\n### Novelty Scores\n"
        for i in range(1, 6):
            count = self.stats.get(f'novelty_{i}', 0)
            report += f"- Level {i}: {count}\n"
        
        report += f"""
## Output Files
- `full_database.json` - All {len(self.prompts)} unique prompts
- `top_quality.json` - High-quality prompts (score >= 4)
- `by_category.json` - Prompts grouped by category
- `by_model.json` - Prompts grouped by target model
- `catalog_additions.json` - Ready for attack catalog

## Next Steps
1. Review `top_quality.json` for best candidates
2. Merge `catalog_additions.json` into main catalog
3. Test top prompts against local models
"""
        
        with open(self.output_dir / 'REPORT.md', 'w') as f:
            f.write(report)
        
        # Also print summary
        print("\n" + "=" * 60)
        print("PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Unique prompts: {len(self.prompts)}")
        print(f"Top quality: {len([p for p in self.prompts if p.sophistication_score >= 4])}")
        print(f"Output: {self.output_dir}")
        print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == '__main__':
    processor = ResearchProcessor()
    processor.run()
