#!/usr/bin/env python3
"""
Prepare the scraped Grammarly help articles as training data and knowledge base.
Uses REAL articles instead of synthetic data generation.
"""

import json
import csv
import random
import os
from pathlib import Path
from typing import List, Dict, Any
import hashlib
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class KnowledgeBaseProcessor:
    """Process scraped Grammarly articles into training data and searchable knowledge base."""
    
    def __init__(self, articles_dir: str = "data/scraped"):
        self.articles_dir = Path(articles_dir)
        self.articles = []
        self.categories = set()
        
    def load_articles(self) -> int:
        """Load all scraped articles."""
        json_files = sorted(self.articles_dir.glob("article_*.json"))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    article = json.load(f)
                    # Add article ID based on filename
                    article['article_id'] = json_file.stem
                    self.articles.append(article)
                    if article.get('category'):
                        self.categories.add(article['category'])
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
                continue
        
        print(f"Loaded {len(self.articles)} articles from {len(self.categories)} categories")
        return len(self.articles)
    
    def classify_intent(self, title: str, category: str) -> str:
        """Classify the intent based on article title and category."""
        title_lower = title.lower()
        category_lower = category.lower() if category else ""
        
        # Intent classification based on real patterns in Grammarly help
        if any(word in title_lower for word in ['how to', 'set up', 'install', 'configure', 'enable']):
            return "setup_guide"
        elif any(word in title_lower for word in ['not working', 'issue', 'problem', 'error', 'fix', 'resolve']):
            return "technical_support"
        elif any(word in title_lower for word in ['subscription', 'billing', 'payment', 'refund', 'cancel', 'upgrade']):
            return "billing_inquiry"
        elif any(word in title_lower for word in ['uninstall', 'remove', 'delete']):
            return "account_management"
        elif any(word in category_lower for word in ['security', 'privacy', 'sso', 'saml', 'scim']):
            return "security_config"
        elif 'bug' in category_lower or 'update' in category_lower:
            return "bug_report"
        elif any(word in title_lower for word in ['what is', 'about', 'overview']):
            return "feature_info"
        else:
            return "general_inquiry"
    
    def extract_key_points(self, content: str) -> List[str]:
        """Extract key action points from article content."""
        key_points = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for action items (numbered lists, bullet points, steps)
            if line and (
                line[0].isdigit() or 
                line.startswith('•') or 
                line.startswith('-') or
                line.lower().startswith('step') or
                line.lower().startswith('click') or
                line.lower().startswith('go to') or
                line.lower().startswith('tap')
            ):
                key_points.append(line)
        
        return key_points[:10]  # Limit to top 10 action items
    
    def prepare_training_entry(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Convert an article into a training data entry."""
        # Use article title as the customer query (these are real questions!)
        query = article['title']
        
        # The content is the ideal response
        response = article['content']
        
        # Extract metadata
        intent = self.classify_intent(article['title'], article.get('category', ''))
        key_points = self.extract_key_points(response)
        
        # Create a unique conversation ID
        conversation_id = hashlib.md5(f"{article['article_id']}_{article['url']}".encode()).hexdigest()[:12]
        
        return {
            'conversation_id': conversation_id,
            'article_id': article['article_id'],
            'customer_query': query,
            'intent': intent,
            'category': article.get('category', 'General'),
            'ideal_response': response,
            'key_action_points': json.dumps(key_points),
            'article_url': article['url'],
            'scraped_at': article.get('scraped_at', ''),
            'response_length': len(response),
            'has_steps': len(key_points) > 0
        }
    
    def create_training_dataset(self, output_file: str = "data/processed/grammarly_kb_dataset.csv"):
        """Create training dataset from real articles."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare all training entries
        training_data = []
        for article in self.articles:
            entry = self.prepare_training_entry(article)
            training_data.append(entry)
        
        # Shuffle for better training distribution
        random.shuffle(training_data)
        
        # Split into train/val/test
        total = len(training_data)
        train_size = int(total * 0.7)
        val_size = int(total * 0.15)
        
        for i, entry in enumerate(training_data):
            if i < train_size:
                entry['split'] = 'train'
            elif i < train_size + val_size:
                entry['split'] = 'validation'
            else:
                entry['split'] = 'test'
        
        # Save to CSV
        fieldnames = [
            'conversation_id', 'split', 'article_id', 'customer_query', 
            'intent', 'category', 'ideal_response', 'key_action_points',
            'article_url', 'scraped_at', 'response_length', 'has_steps'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(training_data)
        
        print(f"\nDataset saved to {output_path}")
        print(f"Total entries: {len(training_data)}")
        print(f"Train: {train_size}, Validation: {val_size}, Test: {total - train_size - val_size}")
        
        # Generate statistics
        self.generate_statistics(training_data, output_path.parent)
        
        return training_data
    
    def generate_statistics(self, dataset: List[Dict[str, Any]], output_dir: Path):
        """Generate statistics about the dataset."""
        stats = {
            'total_articles': len(dataset),
            'categories': {},
            'intents': {},
            'avg_response_length': sum(d['response_length'] for d in dataset) / len(dataset),
            'articles_with_steps': sum(1 for d in dataset if d['has_steps']),
            'splits': {
                'train': sum(1 for d in dataset if d['split'] == 'train'),
                'validation': sum(1 for d in dataset if d['split'] == 'validation'),
                'test': sum(1 for d in dataset if d['split'] == 'test')
            }
        }
        
        # Count by category and intent
        for entry in dataset:
            category = entry['category']
            intent = entry['intent']
            stats['categories'][category] = stats['categories'].get(category, 0) + 1
            stats['intents'][intent] = stats['intents'].get(intent, 0) + 1
        
        # Save statistics
        stats_file = output_dir / 'kb_dataset_stats.json'
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        
        print(f"\nStatistics saved to {stats_file}")
        print(f"\nDataset Statistics:")
        print(f"- Total articles: {stats['total_articles']}")
        print(f"- Categories: {len(stats['categories'])}")
        print(f"- Average response length: {stats['avg_response_length']:.0f} characters")
        print(f"- Articles with action steps: {stats['articles_with_steps']}")
        print(f"\nTop 5 categories:")
        for cat, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {cat}: {count} articles")
        print(f"\nIntent distribution:")
        for intent, count in sorted(stats['intents'].items(), key=lambda x: x[1], reverse=True):
            print(f"  - {intent}: {count} articles")
    
    def create_knowledge_index(self, output_file: str = "data/processed/knowledge_index.json"):
        """Create a searchable index of all articles."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create index with essential fields for quick searching
        index = []
        for article in self.articles:
            index_entry = {
                'article_id': article['article_id'],
                'title': article['title'],
                'category': article.get('category', ''),
                'url': article['url'],
                'intent': self.classify_intent(article['title'], article.get('category', '')),
                # Store first 500 chars for preview
                'preview': article['content'][:500] if article.get('content') else ''
            }
            index.append(index_entry)
        
        # Save index
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)
        
        print(f"\nKnowledge index saved to {output_path}")
        return index


def main():
    """Process scraped articles into training data and knowledge base."""
    processor = KnowledgeBaseProcessor()
    
    # Load articles
    num_articles = processor.load_articles()
    if num_articles == 0:
        print("No articles found to process!")
        return
    
    # Create training dataset from real articles
    print("\nCreating training dataset from real Grammarly help articles...")
    processor.create_training_dataset()
    
    # Create searchable index
    print("\nCreating searchable knowledge index...")
    processor.create_knowledge_index()
    
    print("\n✅ Knowledge base preparation complete!")
    print("The system can now learn from REAL Grammarly help content.")


if __name__ == "__main__":
    main()