"""Load 100 test inferences with realistic feedback into ClickHouse."""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.tensorzero_client import TensorZeroClient
from src.validation import SupportRequestInput


# Realistic test queries organized by category
TEST_QUERIES = {
    "integration_help": [
        "Grammarly isn't working in Google Docs. The extension is installed but not showing up.",
        "How do I enable Grammarly in Microsoft Word?",
        "I can't see Grammarly suggestions in my Gmail compose window",
        "Grammarly stopped working in Slack suddenly",
        "The Grammarly sidebar isn't appearing in Google Docs",
        "Can I use Grammarly with Notion?",
        "Grammarly is not detecting errors in PowerPoint",
        "How to integrate Grammarly with Outlook desktop app?",
        "Grammarly browser extension conflicts with other extensions",
        "Does Grammarly work with LibreOffice?"
    ],
    "technical_support": [
        "Grammarly is making my browser slow",
        "The extension crashes when I open large documents",
        "I'm getting an error code GR-4521 when trying to log in",
        "Grammarly keyboard on iOS keeps crashing",
        "Chrome says the Grammarly extension is corrupted",
        "My documents won't sync across devices",
        "Grammarly desktop app won't open on Mac",
        "Getting 'connection timeout' errors constantly",
        "The plagiarism checker is stuck at 0%",
        "Grammarly won't load after the latest Chrome update"
    ],
    "billing_inquiry": [
        "I was charged twice for my subscription this month",
        "How do I upgrade from Free to Premium?",
        "Can I get a refund? I meant to cancel before renewal",
        "What's the difference between Premium and Business plans?",
        "My student discount isn't applying correctly",
        "How do I change my payment method?",
        "When does the free trial end?",
        "I canceled but was still charged",
        "Can I pause my subscription instead of canceling?",
        "Is there a family plan available?"
    ],
    "account_management": [
        "How do I reset my password?",
        "I can't access my account after changing email",
        "How to merge two Grammarly accounts?",
        "Delete my personal data from Grammarly",
        "I forgot which email I used to sign up",
        "How do I enable two-factor authentication?",
        "Can I change my username?",
        "My account was hacked, what should I do?",
        "How to export all my documents?",
        "I want to transfer my subscription to a new email"
    ],
    "feature_request": [
        "Can Grammarly check grammar in Spanish?",
        "Will you add support for academic citations?",
        "I need Grammarly to work with LaTeX",
        "Can you add a dark mode to the mobile app?",
        "Please add support for markdown files",
        "We need better integration with Jira",
        "Can Grammarly check code comments?",
        "Add voice typing with grammar checking",
        "Support for checking Instagram captions",
        "Can you add a readability score feature?"
    ]
}

# User context variations
USER_CONTEXTS = [
    {"product": "grammarly_free", "platform": "chrome", "os": "windows"},
    {"product": "grammarly_premium", "platform": "chrome", "os": "mac"},
    {"product": "grammarly_business", "platform": "edge", "os": "windows"},
    {"product": "grammarly_premium", "platform": "safari", "os": "mac"},
    {"product": "grammarly_free", "platform": "firefox", "os": "linux"},
    {"product": "grammarly_premium", "platform": "mobile", "os": "ios"},
    {"product": "grammarly_free", "platform": "mobile", "os": "android"},
    {"product": "grammarly_business", "platform": "desktop_app", "os": "windows"},
    {"product": "grammarly_premium", "platform": "desktop_app", "os": "mac"},
    {"product": "grammarly_edu", "platform": "chrome", "os": "windows"},
]

# Conversation history templates
CONVERSATION_HISTORIES = [
    [],  # No history
    [
        {"role": "user", "content": "I'm having issues with Grammarly"},
        {"role": "assistant", "content": "I'd be happy to help you with Grammarly. Could you tell me more about the specific issue you're experiencing?"}
    ],
    [
        {"role": "user", "content": "My subscription renewed but I wanted to cancel"},
        {"role": "assistant", "content": "I understand you wanted to cancel before the renewal. Let me help you with that."}
    ],
    [
        {"role": "user", "content": "Grammarly was working yesterday but not today"},
        {"role": "assistant", "content": "I see the issue started recently. Let's troubleshoot this together."}
    ],
]


async def generate_test_inference(
    client: TensorZeroClient,
    query: str,
    intent_category: str,
    user_context: Dict[str, str],
    conversation_history: List[Dict[str, str]],
    inference_num: int
) -> Dict[str, Any]:
    """Generate a single test inference with feedback."""
    
    print(f"\n[{inference_num}/100] Processing: {query[:50]}...")
    
    # Step 1: Classify intent
    conversation_id = f"test-conv-{inference_num:03d}"
    
    try:
        classification = await client.classify_intent(
            query=query,
            episode_id=None,
            conversation_id=conversation_id
        )
        
        episode_id = classification['raw_response'].get('episode_id')
        print(f"  ✓ Intent: {classification['intent']} (confidence: {classification['confidence']:.2f})")
        
        # Step 2: Generate response
        response = await client.generate_response(
            query=query,
            episode_id=episode_id,
            intent_data=classification,
            conversation_history=conversation_history
        )
        
        response_preview = response['content'][:100] + "..." if len(response['content']) > 100 else response['content']
        print(f"  ✓ Response generated: {response_preview}")
        
        # Step 3: Simulate quality metrics and feedback
        # Intent accuracy - higher confidence means more likely to be accurate
        intent_accurate = classification['confidence'] > 0.7 or random.random() > 0.2
        
        # Response quality - varies based on several factors
        base_quality = 0.6
        if classification['confidence'] > 0.8:
            base_quality += 0.15
        if conversation_history:
            base_quality += 0.1
        if classification['urgency'] in ['high', 'critical']:
            base_quality += 0.05
        
        response_quality = min(0.95, base_quality + random.uniform(-0.1, 0.2))
        
        # Resolution potential - higher for certain intents
        resolution_potential = False
        if intent_category in ['integration_help', 'technical_support']:
            resolution_potential = response_quality > 0.75 and random.random() > 0.3
        elif intent_category == 'account_management':
            resolution_potential = response_quality > 0.7 and random.random() > 0.4
        else:
            resolution_potential = response_quality > 0.8 and random.random() > 0.5
        
        # Customer satisfaction - correlated with quality and resolution
        satisfaction_base = response_quality * 0.8
        if resolution_potential:
            satisfaction_base += 0.15
        customer_satisfaction = min(1.0, satisfaction_base + random.uniform(-0.05, 0.1))
        
        # Step 4: Send feedback
        feedback_tasks = []
        
        # Intent accuracy feedback
        if 'classify_intent_inference_id' in classification['raw_response']:
            feedback_tasks.append(
                client.send_feedback(
                    inference_id=classification['raw_response']['inference_id'],
                    metric_name="intent_accuracy",
                    value=intent_accurate,
                    episode_id=episode_id
                )
            )
        
        # Response relevance feedback
        if 'inference_id' in response['raw_response']:
            feedback_tasks.append(
                client.send_feedback(
                    inference_id=response['raw_response']['inference_id'],
                    metric_name="response_relevance",
                    value=response_quality,
                    episode_id=episode_id
                )
            )
        
        # Episode-level feedback
        if resolution_potential:
            feedback_tasks.append(
                client.send_feedback(
                    inference_id=episode_id,
                    metric_name="resolution_potential",
                    value=resolution_potential,
                    episode_id=episode_id
                )
            )
        
        feedback_tasks.append(
            client.send_feedback(
                inference_id=episode_id,
                metric_name="customer_satisfaction",
                value=customer_satisfaction,
                episode_id=episode_id
            )
        )
        
        # Execute feedback (ignore errors)
        try:
            await asyncio.gather(*feedback_tasks, return_exceptions=True)
            print(f"  ✓ Feedback sent - Quality: {response_quality:.2f}, Satisfaction: {customer_satisfaction:.2f}")
        except Exception as e:
            print(f"  ⚠ Feedback error (continuing): {str(e)[:50]}")
        
        return {
            "success": True,
            "inference_num": inference_num,
            "query": query,
            "intent": classification['intent'],
            "response_length": len(response['content']),
            "quality_score": response_quality,
            "satisfaction": customer_satisfaction
        }
        
    except Exception as e:
        print(f"  ✗ Error: {str(e)[:100]}")
        return {
            "success": False,
            "inference_num": inference_num,
            "query": query,
            "error": str(e)
        }


async def load_test_inferences():
    """Load 100 test inferences into ClickHouse."""
    
    print("Loading 100 test inferences with realistic data...")
    print("=" * 60)
    
    # Prepare test cases
    test_cases = []
    queries_per_category = 20  # 5 categories × 20 = 100 inferences
    
    for category, queries in TEST_QUERIES.items():
        for i in range(queries_per_category):
            query = random.choice(queries)
            user_context = random.choice(USER_CONTEXTS)
            conversation_history = random.choice(CONVERSATION_HISTORIES)
            
            # Add some variation to queries
            if random.random() > 0.7:
                query = query.lower()  # Some users don't capitalize
            if random.random() > 0.8:
                query = query.rstrip('.,?!')  # Some users don't use punctuation
            
            test_cases.append({
                "query": query,
                "category": category,
                "user_context": user_context,
                "conversation_history": conversation_history
            })
    
    # Shuffle for more realistic distribution
    random.shuffle(test_cases)
    
    # Process inferences
    async with TensorZeroClient() as client:
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            result = await generate_test_inference(
                client=client,
                query=test_case["query"],
                intent_category=test_case["category"],
                user_context=test_case["user_context"],
                conversation_history=test_case["conversation_history"],
                inference_num=i
            )
            results.append(result)
            
            # Small delay to avoid overwhelming the system
            await asyncio.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    successful = [r for r in results if r.get("success", False)]
    failed = [r for r in results if not r.get("success", False)]
    
    print(f"Total inferences: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if successful:
        avg_quality = sum(r.get("quality_score", 0) for r in successful) / len(successful)
        avg_satisfaction = sum(r.get("satisfaction", 0) for r in successful) / len(successful)
        
        print(f"\nAverage quality score: {avg_quality:.3f}")
        print(f"Average satisfaction: {avg_satisfaction:.3f}")
        
        # Intent distribution
        intent_counts = {}
        for r in successful:
            intent = r.get("intent", "unknown")
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        print("\nIntent distribution:")
        for intent, count in sorted(intent_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {intent}: {count}")
    
    if failed:
        print(f"\nFailed inferences: {len(failed)}")
        for f in failed[:5]:  # Show first 5 failures
            print(f"  - {f['query'][:50]}... Error: {f.get('error', 'Unknown')[:50]}")
    
    print("\n✅ Test data loading complete!")


if __name__ == "__main__":
    asyncio.run(load_test_inferences())