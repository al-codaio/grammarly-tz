"""Evaluate different TensorZero variants and generate performance reports."""

import asyncio
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm.asyncio import tqdm

from ..utils.tensorzero_client import TensorZeroClient
from ..langgraph.app import GrammarlySupportChatBot


class VariantEvaluator:
    """Evaluate different variants of the chatbot."""
    
    def __init__(self, dataset_path: str = "../data/processed/grammarly_support_dataset.csv"):
        self.dataset_path = Path(dataset_path)
        self.results = []
        self.client = TensorZeroClient()
        self.bot = GrammarlySupportChatBot()
    
    async def load_test_data(self) -> pd.DataFrame:
        """Load test dataset."""
        df = pd.read_csv(self.dataset_path)
        # Use only test split for evaluation
        test_df = df[df['split'] == 'test']
        return test_df
    
    async def evaluate_single_query(
        self,
        query: str,
        expected_intent: str,
        expected_response: str,
        variant: Optional[str] = None,
        episode_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluate a single query."""
        start_time = datetime.utcnow()
        
        try:
            # Process query through the chatbot
            result = await self.bot.process_query(
                query=query,
                episode_id=episode_id
            )
            
            end_time = datetime.utcnow()
            latency = (end_time - start_time).total_seconds()
            
            # Evaluate intent accuracy
            intent_correct = result.get("intent") == expected_intent
            
            # Evaluate response quality (simplified - in production use LLM judge)
            response_length = len(result.get("response", ""))
            has_response = response_length > 50
            
            # Check if escalation matches expectation
            expected_escalation = "[ESCALATE]" in expected_response
            actual_escalation = result.get("requires_human", False)
            escalation_correct = expected_escalation == actual_escalation
            
            return {
                "success": True,
                "variant": variant,
                "latency": latency,
                "intent_correct": intent_correct,
                "predicted_intent": result.get("intent"),
                "expected_intent": expected_intent,
                "has_valid_response": has_response,
                "response_length": response_length,
                "escalation_correct": escalation_correct,
                "requires_human": actual_escalation,
                "quality_score": result.get("quality_score", 0.0),
                "error": None
            }
            
        except Exception as e:
            end_time = datetime.utcnow()
            latency = (end_time - start_time).total_seconds()
            
            return {
                "success": False,
                "variant": variant,
                "latency": latency,
                "intent_correct": False,
                "predicted_intent": None,
                "expected_intent": expected_intent,
                "has_valid_response": False,
                "response_length": 0,
                "escalation_correct": False,
                "requires_human": True,
                "quality_score": 0.0,
                "error": str(e)
            }
    
    async def evaluate_variant(self, variant_name: str, test_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Evaluate a specific variant."""
        print(f"\nEvaluating variant: {variant_name}")
        
        results = []
        tasks = []
        
        for _, row in test_df.iterrows():
            episode_id = f"eval_{variant_name}_{row['conversation_id']}"
            
            task = self.evaluate_single_query(
                query=row['customer_query'],
                expected_intent=row['intent'],
                expected_response=row['ideal_response'],
                variant=variant_name,
                episode_id=episode_id
            )
            tasks.append(task)
        
        # Process in batches
        batch_size = 5
        for i in tqdm(range(0, len(tasks), batch_size), desc=f"Evaluating {variant_name}"):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)
            await asyncio.sleep(0.5)  # Rate limiting
        
        return results
    
    async def evaluate_all_variants(self):
        """Evaluate all configured variants."""
        test_df = await self.load_test_data()
        print(f"Loaded {len(test_df)} test samples")
        
        # Define variants to test
        variants = [
            "gpt_4o",
            "gpt_4o_mini",
            "gpt_4o_mini_dicl",
            # "gpt_4o_mini_fine_tuned"  # Uncomment when fine-tuned model is ready
        ]
        
        all_results = []
        
        for variant in variants:
            variant_results = await self.evaluate_variant(variant, test_df)
            for result in variant_results:
                result['variant'] = variant
            all_results.extend(variant_results)
        
        self.results = all_results
        return all_results
    
    def calculate_metrics(self) -> pd.DataFrame:
        """Calculate evaluation metrics for each variant."""
        df = pd.DataFrame(self.results)
        
        metrics = []
        for variant in df['variant'].unique():
            variant_df = df[df['variant'] == variant]
            
            metrics.append({
                'variant': variant,
                'success_rate': variant_df['success'].mean(),
                'intent_accuracy': variant_df['intent_correct'].mean(),
                'response_validity': variant_df['has_valid_response'].mean(),
                'escalation_accuracy': variant_df['escalation_correct'].mean(),
                'avg_quality_score': variant_df['quality_score'].mean(),
                'avg_latency': variant_df['latency'].mean(),
                'p95_latency': variant_df['latency'].quantile(0.95),
                'error_rate': (variant_df['error'].notna()).mean(),
                'human_escalation_rate': variant_df['requires_human'].mean(),
                'avg_response_length': variant_df['response_length'].mean()
            })
        
        return pd.DataFrame(metrics)
    
    def generate_visualization(self, output_dir: str = "../data/results"):
        """Generate performance visualization charts."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        metrics_df = self.calculate_metrics()
        
        # Set up the plot style
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('TensorZero Variant Performance Comparison', fontsize=16)
        
        # 1. Intent Accuracy Comparison
        ax1 = axes[0, 0]
        metrics_df.plot(x='variant', y='intent_accuracy', kind='bar', ax=ax1, color='steelblue')
        ax1.set_title('Intent Classification Accuracy')
        ax1.set_ylabel('Accuracy')
        ax1.set_ylim(0, 1.1)
        ax1.set_xticklabels(metrics_df['variant'], rotation=45, ha='right')
        
        # Add value labels on bars
        for i, v in enumerate(metrics_df['intent_accuracy']):
            ax1.text(i, v + 0.01, f'{v:.2%}', ha='center')
        
        # 2. Response Quality Score
        ax2 = axes[0, 1]
        metrics_df.plot(x='variant', y='avg_quality_score', kind='bar', ax=ax2, color='darkorange')
        ax2.set_title('Average Response Quality Score')
        ax2.set_ylabel('Quality Score')
        ax2.set_ylim(0, 1.1)
        ax2.set_xticklabels(metrics_df['variant'], rotation=45, ha='right')
        
        for i, v in enumerate(metrics_df['avg_quality_score']):
            ax2.text(i, v + 0.01, f'{v:.2f}', ha='center')
        
        # 3. Latency Comparison
        ax3 = axes[1, 0]
        x = range(len(metrics_df))
        width = 0.35
        ax3.bar([i - width/2 for i in x], metrics_df['avg_latency'], width, label='Avg Latency', color='lightgreen')
        ax3.bar([i + width/2 for i in x], metrics_df['p95_latency'], width, label='P95 Latency', color='salmon')
        ax3.set_title('Response Latency')
        ax3.set_ylabel('Latency (seconds)')
        ax3.set_xticks(x)
        ax3.set_xticklabels(metrics_df['variant'], rotation=45, ha='right')
        ax3.legend()
        
        # 4. Success Metrics
        ax4 = axes[1, 1]
        success_metrics = ['success_rate', 'response_validity', 'escalation_accuracy']
        metrics_subset = metrics_df[['variant'] + success_metrics]
        metrics_subset.set_index('variant').plot(kind='bar', ax=ax4)
        ax4.set_title('Success Metrics Comparison')
        ax4.set_ylabel('Rate')
        ax4.set_ylim(0, 1.1)
        ax4.set_xticklabels(metrics_df['variant'], rotation=45, ha='right')
        ax4.legend(['Success Rate', 'Valid Response', 'Escalation Accuracy'])
        
        plt.tight_layout()
        plt.savefig(output_path / 'variant_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Save metrics to CSV
        metrics_df.to_csv(output_path / 'evaluation_metrics.csv', index=False)
        
        # Generate detailed report
        self.generate_report(metrics_df, output_path)
        
        print(f"Visualizations and reports saved to {output_path}")
    
    def generate_report(self, metrics_df: pd.DataFrame, output_path: Path):
        """Generate detailed evaluation report."""
        report = {
            "evaluation_date": datetime.utcnow().isoformat(),
            "total_samples_evaluated": len(self.results),
            "variants_tested": metrics_df['variant'].tolist(),
            "summary": {},
            "recommendations": []
        }
        
        # Find best variant for each metric
        best_intent = metrics_df.loc[metrics_df['intent_accuracy'].idxmax(), 'variant']
        best_quality = metrics_df.loc[metrics_df['avg_quality_score'].idxmax(), 'variant']
        best_latency = metrics_df.loc[metrics_df['avg_latency'].idxmin(), 'variant']
        
        report["summary"] = {
            "best_intent_accuracy": {
                "variant": best_intent,
                "accuracy": float(metrics_df[metrics_df['variant'] == best_intent]['intent_accuracy'].values[0])
            },
            "best_quality_score": {
                "variant": best_quality,
                "score": float(metrics_df[metrics_df['variant'] == best_quality]['avg_quality_score'].values[0])
            },
            "best_latency": {
                "variant": best_latency,
                "latency": float(metrics_df[metrics_df['variant'] == best_latency]['avg_latency'].values[0])
            }
        }
        
        # Add recommendations
        if "gpt_4o_mini_dicl" in metrics_df['variant'].values:
            dicl_metrics = metrics_df[metrics_df['variant'] == 'gpt_4o_mini_dicl'].iloc[0]
            base_metrics = metrics_df[metrics_df['variant'] == 'gpt_4o_mini'].iloc[0]
            
            if dicl_metrics['intent_accuracy'] > base_metrics['intent_accuracy']:
                improvement = (dicl_metrics['intent_accuracy'] - base_metrics['intent_accuracy']) / base_metrics['intent_accuracy'] * 100
                report["recommendations"].append(
                    f"DICL improves intent accuracy by {improvement:.1f}% over base GPT-4o-mini"
                )
        
        # Save report
        with open(output_path / 'evaluation_report.json', 'w') as f:
            json.dump(report, f, indent=2)


async def main():
    """Main evaluation function."""
    evaluator = VariantEvaluator()
    
    # Run evaluation
    await evaluator.evaluate_all_variants()
    
    # Generate visualizations and reports
    evaluator.generate_visualization()


if __name__ == "__main__":
    asyncio.run(main())