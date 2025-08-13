"""Prepare data for Dynamic In-Context Learning (DICL) in TensorZero."""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any
import asyncio
from openai import AsyncOpenAI


class DICLDataPreparer:
    """Prepare scraped articles and examples for DICL."""
    
    def __init__(self, articles_dir: str = "../data/scraped"):
        self.articles_dir = Path(articles_dir)
        self.client = AsyncOpenAI()
        
    def load_articles(self) -> List[Dict[str, Any]]:
        """Load all scraped articles."""
        articles = []
        for file_path in sorted(self.articles_dir.glob("article_*.json")):
            with open(file_path, 'r', encoding='utf-8') as f:
                article = json.load(f)
                articles.append(article)
        return articles
    
    def create_article_chunks(self, articles: List[Dict[str, Any]], chunk_size: int = 500) -> List[Dict[str, Any]]:
        """Split articles into chunks for embedding."""
        chunks = []
        
        for article in articles:
            content = article['content']
            title = article['title']
            category = article.get('category', 'General')
            
            # Split content into paragraphs
            paragraphs = content.split('\n\n')
            
            # Group paragraphs into chunks
            current_chunk = []
            current_size = 0
            
            for para in paragraphs:
                para_size = len(para.split())
                
                if current_size + para_size > chunk_size and current_chunk:
                    # Save current chunk
                    chunk_text = '\n\n'.join(current_chunk)
                    chunks.append({
                        'text': f"Title: {title}\nCategory: {category}\n\n{chunk_text}",
                        'metadata': {
                            'article_title': title,
                            'category': category,
                            'url': article['url'],
                            'chunk_id': f"{article['url']}#{len(chunks)}"
                        }
                    })
                    current_chunk = [para]
                    current_size = para_size
                else:
                    current_chunk.append(para)
                    current_size += para_size
            
            # Don't forget the last chunk
            if current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append({
                    'text': f"Title: {title}\nCategory: {category}\n\n{chunk_text}",
                    'metadata': {
                        'article_title': title,
                        'category': category,
                        'url': article['url'],
                        'chunk_id': f"{article['url']}#{len(chunks)}"
                    }
                })
        
        return chunks
    
    async def create_embeddings(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Create embeddings for texts using OpenAI's text-embedding-3-small."""
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=batch
            )
            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)
            
            if i + batch_size < len(texts):
                await asyncio.sleep(0.5)  # Rate limiting
        
        return embeddings
    
    async def prepare_knowledge_base(self, output_dir: str = "../data/processed"):
        """Prepare knowledge base for DICL."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print("Loading articles...")
        articles = self.load_articles()
        print(f"Loaded {len(articles)} articles")
        
        print("Creating article chunks...")
        chunks = self.create_article_chunks(articles)
        print(f"Created {len(chunks)} chunks")
        
        print("Generating embeddings...")
        texts = [chunk['text'] for chunk in chunks]
        embeddings = await self.create_embeddings(texts)
        
        # Save chunks with embeddings
        knowledge_base = []
        for chunk, embedding in zip(chunks, embeddings):
            knowledge_base.append({
                'text': chunk['text'],
                'embedding': embedding,
                'metadata': chunk['metadata']
            })
        
        # Save to file
        kb_path = output_path / "knowledge_base_embeddings.json"
        with open(kb_path, 'w', encoding='utf-8') as f:
            json.dump(knowledge_base, f, indent=2)
        
        print(f"Knowledge base saved to {kb_path}")
        
        # Also save a CSV for easier inspection
        csv_path = output_path / "knowledge_base.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['chunk_id', 'title', 'category', 'text_preview'])
            writer.writeheader()
            for chunk in chunks:
                writer.writerow({
                    'chunk_id': chunk['metadata']['chunk_id'],
                    'title': chunk['metadata']['article_title'],
                    'category': chunk['metadata']['category'],
                    'text_preview': chunk['text'][:200] + '...'
                })
        
        print(f"Knowledge base CSV saved to {csv_path}")
        
        return knowledge_base
    
    async def create_example_interactions(self, num_examples: int = 100):
        """Create example query-response pairs from articles for DICL."""
        articles = self.load_articles()
        examples = []
        
        
        print(f"Creating {num_examples} example interactions...")
        
        for i in range(num_examples):
            article = articles[i % len(articles)]
            category = article.get('category', 'General')
            
            # Generate a query based on the article
            prompt = f"""Based on this help article, generate a realistic customer support query that this article would answer.

Article Title: {article['title']}
Category: {category}
Content Preview: {article['content'][:500]}...

Generate a natural customer query (1-2 sentences) that someone might ask if they needed this information:"""
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=100
            )
            
            query = response.choices[0].message.content.strip()
            
            # Create example
            examples.append({
                'query': query,
                'response': f"Based on the article '{article['title']}': {article['content'][:300]}...",
                'article_url': article['url'],
                'category': category
            })
            
            if (i + 1) % 10 == 0:
                print(f"Created {i + 1} examples...")
                await asyncio.sleep(1)  # Rate limiting
        
        # Save examples
        output_path = Path("../data/processed")
        examples_path = output_path / "dicl_examples.json"
        with open(examples_path, 'w', encoding='utf-8') as f:
            json.dump(examples, f, indent=2)
        
        print(f"Examples saved to {examples_path}")
        return examples


async def main():
    """Main function to prepare DICL data."""
    preparer = DICLDataPreparer()
    
    # Prepare knowledge base with embeddings
    await preparer.prepare_knowledge_base()
    
    # Create example interactions
    await preparer.create_example_interactions(num_examples=50)


if __name__ == "__main__":
    asyncio.run(main())