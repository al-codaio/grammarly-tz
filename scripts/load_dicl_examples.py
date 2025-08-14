#!/usr/bin/env python3
"""Load DICL examples from scraped Grammarly articles into ClickHouse for TensorZero."""

import json
import uuid
from typing import List, Dict, Any, Optional
import clickhouse_connect
from openai import OpenAI
from tqdm import tqdm
import os
from dotenv import load_dotenv

load_dotenv()

class DICLExampleLoader:
    def __init__(self):
        self.client = clickhouse_connect.get_client(
            host='localhost',
            port=8123,
            username='chuser',
            password='chpassword',
            database='tensorzero'
        )
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def load_knowledge_base_embeddings(self) -> List[Dict[str, Any]]:
        """Load the complete knowledge base with embeddings."""
        print("Loading knowledge base embeddings...")
        with open("data/processed/knowledge_base_embeddings.json", "r") as f:
            return json.load(f)
    
    def classify_intent_from_article(self, article_text: str, metadata: Dict) -> Dict[str, Any]:
        """Generate an intent classification output based on article content."""
        # Map article categories to intents
        category = metadata.get('category', '').lower()
        
        intent_mapping = {
            'account': 'account_management',
            'billing': 'billing_inquiry',
            'technical': 'technical_support',
            'feature': 'feature_request',
            'integration': 'technical_support',
            'grammar': 'general_inquiry',
            'writing': 'general_inquiry',
            'business': 'account_management',
            'education': 'general_inquiry',
            'security': 'account_management'
        }
        
        # Find the best matching intent
        intent = 'general_inquiry'
        for key, value in intent_mapping.items():
            if key in category:
                intent = value
                break
        
        # Determine urgency based on keywords
        urgent_keywords = ['not working', 'error', 'failed', 'broken', 'urgent', 'immediately']
        urgency = 'high' if any(kw in article_text.lower() for kw in urgent_keywords) else 'medium'
        
        return {
            "intent": intent,
            "confidence": 0.85,
            "urgency": urgency,
            "entities": {
                "product": [],
                "platform": [],
                "feature": [],
                "error_code": []
            }
        }
    
    def prepare_dicl_examples(self) -> List[Dict[str, Any]]:
        """Prepare DICL examples from knowledge base for ClickHouse."""
        # Load knowledge base with embeddings
        kb_data = self.load_knowledge_base_embeddings()
        
        prepared_examples = []
        print(f"Processing {len(kb_data)} knowledge base articles...")
        
        for item in tqdm(kb_data):  # Process all articles
            text = item['text']
            embedding = item['embedding']
            metadata = item.get('metadata', {})
            
            # Skip if text is too short
            if len(text) < 50:
                continue
            
            # Generate a question-like input from the article
            # Take the first sentence or title as the "question"
            lines = text.split('\n')
            title = metadata.get('title', lines[0] if lines else text[:100])
            
            # Create example for classify_intent
            intent_output = self.classify_intent_from_article(text, metadata)
            
            intent_example = {
                'id': str(uuid.uuid4()),  # TensorZero will handle UUID conversion
                'function_name': 'classify_intent',
                'variant_name': 'gpt_4o_mini_dicl',
                'namespace': metadata.get('category', 'general'),
                'input': json.dumps({
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "value": title}]
                        }
                    ]
                }),
                'output': json.dumps(intent_output),
                'embedding': embedding
            }
            prepared_examples.append(intent_example)
            
            # Create example for generate_response
            # The output is the actual article content (the answer)
            response_example = {
                'id': str(uuid.uuid4()),
                'function_name': 'generate_response',
                'variant_name': 'gpt_4o_mini_dicl',
                'namespace': metadata.get('category', 'general'),
                'input': json.dumps({
                    "query": title,
                    "intent": intent_output['intent'],
                    "urgency": intent_output['urgency'],
                    "entities": intent_output['entities'],
                    "conversation_history": []
                }),
                'output': text[:1000],  # Limit response length
                'embedding': embedding
            }
            prepared_examples.append(response_example)
        
        return prepared_examples
    
    def insert_examples(self, examples: List[Dict[str, Any]]):
        """Insert examples into ClickHouse."""
        if not examples:
            print("No examples to insert")
            return
        
        print(f"Inserting {len(examples)} examples into ClickHouse...")
        
        # Prepare data for insertion
        data = []
        for ex in examples:
            data.append([
                ex['id'],
                ex['function_name'],
                ex['variant_name'],
                ex['namespace'],
                ex['input'],
                ex['output'],
                ex['embedding']
            ])
        
        # Insert into ClickHouse in batches
        batch_size = 100
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            self.client.insert(
                'DynamicInContextLearningExample',
                batch,
                column_names=['id', 'function_name', 'variant_name', 'namespace', 'input', 'output', 'embedding']
            )
            print(f"  Inserted batch {i//batch_size + 1}/{(len(data)-1)//batch_size + 1}")
        
        print(f"✅ Successfully inserted {len(examples)} examples!")
    
    def verify_insertion(self):
        """Verify examples were inserted and show statistics."""
        # Total count
        result = self.client.query("SELECT COUNT(*) FROM DynamicInContextLearningExample")
        total_count = result.result_rows[0][0]
        print(f"\n📊 Total examples in ClickHouse: {total_count}")
        
        # Count by function
        function_counts = self.client.query("""
            SELECT function_name, COUNT(*) as count
            FROM DynamicInContextLearningExample
            GROUP BY function_name
        """)
        
        print("\n📈 Examples by function:")
        for row in function_counts.result_rows:
            print(f"  - {row[0]}: {row[1]} examples")
        
        # Count by namespace
        namespace_counts = self.client.query("""
            SELECT namespace, COUNT(*) as count
            FROM DynamicInContextLearningExample
            GROUP BY namespace
            ORDER BY count DESC
            LIMIT 5
        """)
        
        print("\n📁 Top 5 namespaces:")
        for row in namespace_counts.result_rows:
            print(f"  - {row[0]}: {row[1]} examples")
        
        # Show sample examples
        samples = self.client.query("""
            SELECT function_name, namespace, 
                   substring(input, 1, 100) as input_sample,
                   substring(output, 1, 100) as output_sample
            FROM DynamicInContextLearningExample 
            LIMIT 3
        """)
        
        print("\n📝 Sample examples:")
        for i, row in enumerate(samples.result_rows, 1):
            print(f"\nExample {i}:")
            print(f"  Function: {row[0]}")
            print(f"  Namespace: {row[1]}")
            print(f"  Input: {row[2][:80]}...")
            print(f"  Output: {row[3][:80]}...")
    
    def test_similarity_search(self, query: str = "How do I reset my password?"):
        """Test that similarity search works with the loaded examples."""
        print(f"\n🔍 Testing similarity search for: '{query}'")
        
        # Generate embedding for the query
        embedding = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        ).data[0].embedding
        
        # Search for similar examples
        result = self.client.query(f"""
            SELECT 
                namespace,
                substring(output, 1, 200) as output_sample,
                cosineDistance(embedding, {embedding}) as distance
            FROM DynamicInContextLearningExample
            WHERE function_name = 'generate_response'
            ORDER BY distance ASC
            LIMIT 3
        """)
        
        print("\nTop 3 most similar examples:")
        for i, row in enumerate(result.result_rows, 1):
            print(f"\n{i}. Namespace: {row[0]}, Distance: {row[2]:.4f}")
            print(f"   Response: {row[1][:150]}...")
    
    def run(self):
        """Main execution function."""
        try:
            # Check if examples already exist
            result = self.client.query("SELECT COUNT(*) FROM DynamicInContextLearningExample")
            existing_count = result.result_rows[0][0]
            
            if existing_count > 0:
                print(f"⚠️  Found {existing_count} existing examples in ClickHouse.")
                response = input("Do you want to clear existing examples and reload? (y/n): ")
                if response.lower() == 'y':
                    self.client.query("TRUNCATE TABLE DynamicInContextLearningExample")
                    print("🗑️  Cleared existing examples.")
                else:
                    print("Keeping existing examples.")
                    self.verify_insertion()
                    self.test_similarity_search()
                    return
            
            # Prepare and insert examples
            examples = self.prepare_dicl_examples()
            self.insert_examples(examples)
            
            # Verify insertion
            self.verify_insertion()
            
            # Test similarity search
            self.test_similarity_search()
            
            print("\n✅ DICL examples loaded successfully!")
            print("🚀 TensorZero will now use these examples for the DICL variants.")
            print("\nWhen a user query comes in:")
            print("1. TensorZero generates an embedding of the query")
            print("2. Searches for the k most similar examples from your Grammarly articles")
            print("3. Includes those examples in the prompt for better context-aware responses")
            
        except Exception as e:
            print(f"❌ Error loading examples: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    loader = DICLExampleLoader()
    loader.run()