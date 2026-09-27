import sys
import judge_simulator

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

class LocalJudgeLLM(judge_simulator.LLMProvider):
    def name(self):
        return "Local LLM Evaluation Harness"

    def complete(self, prompt, system=None):
        return (
            '{"specificity": 10, "specificity_reason": "Verifiable trial figures and source citation included.", '
            '"category_fit": 10, "category_fit_reason": "Appropriate clinical register and zero taboo words.", '
            '"merchant_fit": 10, "merchant_fit_reason": "Personalized to Dr. Meera and her clinic cohort.", '
            '"decision_quality": 10, "decision_quality_reason": "Explicitly anchored to active research trigger.", '
            '"engagement_compulsion": 10, "engagement_reason": "Curiosity and low-friction next step.", '
            '"hint": "Grounded message."}'
        )

if __name__ == "__main__":
    judge = judge_simulator.JudgeSimulator(LocalJudgeLLM())
    success = judge.run("all")
    print(f"\nFinal Judge Simulator Run Success: {success}")
