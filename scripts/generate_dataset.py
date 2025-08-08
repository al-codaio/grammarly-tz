"""Generate synthetic customer support dataset for training and evaluation."""

import json
import random
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import asyncio
from openai import AsyncOpenAI


class DatasetGenerator:
    """Generate synthetic customer support queries and responses."""
    
    def __init__(self, articles_dir: str = "../data/scraped"):
        self.articles_dir = Path(articles_dir)
        self.articles = self.load_articles()
        self.client = AsyncOpenAI()
        
        # Query templates by intent
        self.query_templates = {
            "technical_support": [
                "Grammarly isn't working in {platform}, it was working {timeframe} but now {problem}",
                "I'm getting {error} when trying to {action} in {product}",
                "The {feature} feature stopped working after {event}",
                "{product} keeps {problem} on my {platform}",
                "Why is Grammarly {problem} when I {action}?"
            ],
            "billing_inquiry": [
                "I was charged {amount} but I {expectation}",
                "How do I {action} my {product} subscription?",
                "Can I get a refund for {reason}?",
                "Why was my payment {problem}?",
                "I want to {action} from {current_plan} to {new_plan}"
            ],
            "feature_request": [
                "Can Grammarly {feature_action} for {use_case}?",
                "It would be great if {product} could {feature_action}",
                "Why doesn't Grammarly support {feature}?",
                "Please add {feature} to {product}",
                "Is there a way to {feature_action} in Grammarly?"
            ],
            "account_management": [
                "How do I {action} my Grammarly account?",
                "I can't {action} because {problem}",
                "My account shows {status} but I {expectation}",
                "I forgot my {credential} and need to {action}",
                "How can I {action} for my team/organization?"
            ],
            "bug_report": [
                "Grammarly is {bug_behavior} when I {action}",
                "There's a bug where {bug_description}",
                "{feature} is broken - it {bug_behavior}",
                "I found an issue with {feature} in {product}",
                "Grammarly crashes when {action} on {platform}"
            ]
        }
        
        # Variable options
        self.variables = {
            "platform": ["Chrome", "Firefox", "Safari", "Edge", "Windows", "Mac", "iOS", "Android", "Google Docs", "Microsoft Word"],
            "timeframe": ["yesterday", "last week", "this morning", "a few days ago", "last month"],
            "problem": ["not showing up", "crashing", "freezing", "not detecting errors", "showing incorrect suggestions", "not loading", "very slow"],
            "error": ["error 403", "connection timeout", "sync error", "authentication failed", "network error"],
            "action": ["check my document", "save my work", "log in", "install the extension", "update", "share with my team"],
            "product": ["Grammarly Free", "Grammarly Premium", "Grammarly Business", "browser extension", "desktop app", "mobile app"],
            "feature": ["tone detector", "plagiarism checker", "vocabulary suggestions", "clarity improvements", "citation generator"],
            "event": ["the last update", "I restarted my computer", "changing my password", "installing a new extension"],
            "amount": ["$29.95", "$11.66", "$139.95", "$12.50", "twice"],
            "expectation": ["cancelled last month", "only signed up for free", "thought it was monthly", "already paid"],
            "current_plan": ["Free", "Premium monthly", "Premium annual"],
            "new_plan": ["Premium", "Business", "Free", "annual billing"],
            "feature_action": ["check for passive voice", "support multiple languages", "integrate with Slack", "work offline", "export reports"],
            "use_case": ["academic writing", "business emails", "creative writing", "ESL students", "technical documentation"],
            "status": ["Premium", "Free", "expired", "suspended"],
            "credential": ["password", "email", "security question"],
            "bug_behavior": ["highlighting everything", "not saving changes", "duplicating suggestions", "showing blank screen"],
            "bug_description": ["suggestions appear behind the text", "the sidebar overlaps with content", "undo doesn't work properly"]
        }
    
    def load_articles(self) -> List[Dict[str, Any]]:
        """Load scraped articles."""
        articles = []
        for file_path in self.articles_dir.glob("article_*.json"):
            with open(file_path, 'r', encoding='utf-8') as f:
                articles.append(json.load(f))
        return articles
    
    def generate_query(self, intent: str) -> str:
        """Generate a query for a given intent."""
        template = random.choice(self.query_templates.get(intent, []))
        
        # Replace variables in template
        query = template
        for var_name, var_options in self.variables.items():
            placeholder = f"{{{var_name}}}"
            if placeholder in query:
                query = query.replace(placeholder, random.choice(var_options))
        
        return query
    
    def extract_entities(self, query: str, intent: str) -> Dict[str, List[str]]:
        """Extract entities from a query."""
        entities = {
            "product": [],
            "feature": [],
            "error_code": [],
            "platform": []
        }
        
        query_lower = query.lower()
        
        # Extract products
        products = ["grammarly free", "grammarly premium", "grammarly business", 
                   "browser extension", "desktop app", "mobile app"]
        for product in products:
            if product in query_lower:
                entities["product"].append(product.replace(" ", "_"))
        
        # Extract platforms
        platforms = ["chrome", "firefox", "safari", "edge", "windows", "mac", 
                    "ios", "android", "google docs", "microsoft word"]
        for platform in platforms:
            if platform in query_lower:
                entities["platform"].append(platform.replace(" ", "_"))
        
        # Extract features
        features = ["tone detector", "plagiarism", "vocabulary", "clarity", "citation"]
        for feature in features:
            if feature in query_lower:
                entities["feature"].append(feature)
        
        # Extract error codes
        import re
        error_patterns = [r'error \d+', r'code \d+', r'err_\w+']
        for pattern in error_patterns:
            matches = re.findall(pattern, query_lower)
            entities["error_code"].extend(matches)
        
        return entities
    
    def determine_urgency(self, intent: str, query: str) -> str:
        """Determine urgency level based on intent and keywords."""
        critical_keywords = ["crashed", "lost data", "charged twice", "urgent", "immediately", "can't access"]
        high_keywords = ["not working", "broken", "failed", "error", "can't", "blocked"]
        
        query_lower = query.lower()
        
        if any(keyword in query_lower for keyword in critical_keywords):
            return "critical"
        elif intent in ["bug_report", "technical_support"] and any(keyword in query_lower for keyword in high_keywords):
            return "high"
        elif intent == "billing_inquiry":
            return "high"
        elif intent == "feature_request":
            return "low"
        else:
            return "medium"
    
    async def generate_ideal_response(self, query: str, intent: str, entities: Dict[str, Any]) -> str:
        """Generate an ideal support response using GPT-4."""
        prompt = f"""You are a Grammarly customer support specialist. Generate an ideal response to this customer query.

Query: {query}
Intent: {intent}
Identified Products: {', '.join(entities.get('product', []))}
Identified Platforms: {', '.join(entities.get('platform', []))}

Requirements:
1. Be empathetic and acknowledge their issue
2. Provide clear, actionable steps to resolve the problem
3. Offer alternatives if the primary solution might not work
4. Be concise but thorough
5. End with next steps or additional resources
6. If the issue requires human support, include [ESCALATE] in your response
7. If you're suggesting specific actions, include them as [ACTIONS] followed by a numbered list

Generate the ideal support response:"""
        
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    async def generate_dataset_entry(self, conversation_id: str, split: str) -> Dict[str, Any]:
        """Generate a single dataset entry."""
        intent = random.choice(list(self.query_templates.keys()))
        query = self.generate_query(intent)
        entities = self.extract_entities(query, intent)
        urgency = self.determine_urgency(intent, query)
        
        # Generate ideal response
        ideal_response = await self.generate_ideal_response(query, intent, entities)
        
        # Determine if it could be resolved without human
        resolution_potential = "[ESCALATE]" not in ideal_response
        
        return {
            "conversation_id": conversation_id,
            "split": split,
            "customer_query": query,
            "intent": intent,
            "confidence": round(random.uniform(0.8, 1.0), 2),
            "entities": json.dumps(entities),
            "urgency": urgency,
            "ideal_response": ideal_response,
            "resolution_potential": resolution_potential,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def generate_dataset(self, num_samples: int = 500, output_file: str = "../data/processed/grammarly_support_dataset.csv"):
        """Generate the full dataset."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Split distribution
        train_ratio = 0.7
        val_ratio = 0.15
        test_ratio = 0.15
        
        train_size = int(num_samples * train_ratio)
        val_size = int(num_samples * val_ratio)
        test_size = num_samples - train_size - val_size
        
        dataset = []
        
        # Generate samples
        print(f"Generating {num_samples} dataset entries...")
        
        # Create samples for each split
        sample_configs = [
            ("train", train_size),
            ("validation", val_size),
            ("test", test_size)
        ]
        
        for split, size in sample_configs:
            print(f"Generating {size} {split} samples...")
            tasks = []
            
            for i in range(size):
                conversation_id = f"{split}_{i:05d}"
                tasks.append(self.generate_dataset_entry(conversation_id, split))
                
                # Process in batches
                if len(tasks) >= 10:
                    results = await asyncio.gather(*tasks)
                    dataset.extend(results)
                    tasks = []
                    await asyncio.sleep(1)  # Rate limiting
            
            # Process remaining tasks
            if tasks:
                results = await asyncio.gather(*tasks)
                dataset.extend(results)
        
        # Save to CSV
        fieldnames = [
            "conversation_id", "split", "customer_query", "intent", 
            "confidence", "entities", "urgency", "ideal_response", 
            "resolution_potential", "timestamp"
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(dataset)
        
        print(f"Dataset saved to {output_path}")
        
        # Save statistics
        stats = {
            "total_samples": len(dataset),
            "splits": {
                "train": train_size,
                "validation": val_size,
                "test": test_size
            },
            "intents": {},
            "urgency_distribution": {},
            "resolution_rate": sum(1 for d in dataset if d["resolution_potential"]) / len(dataset)
        }
        
        for entry in dataset:
            intent = entry["intent"]
            urgency = entry["urgency"]
            stats["intents"][intent] = stats["intents"].get(intent, 0) + 1
            stats["urgency_distribution"][urgency] = stats["urgency_distribution"].get(urgency, 0) + 1
        
        stats_path = output_path.parent / "dataset_stats.json"
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        
        print(f"Statistics saved to {stats_path}")
        return dataset


async def main():
    """Main function to generate the dataset."""
    generator = DatasetGenerator()
    await generator.generate_dataset(num_samples=50)  # Start with 50 for testing


if __name__ == "__main__":
    asyncio.run(main())