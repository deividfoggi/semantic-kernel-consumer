from semantic_kernel.functions import kernel_function
from typing import Annotated
import json

class PostEvaluation:
    def _evaluate_skill_score(self, skill: dict) -> int:
        """
        Retorna o score da skill, tratando valores não numéricos como 0.
        """
        score = skill.get("nota", 0)
        try:
            return int(score)
        except (ValueError, TypeError):
            return 0
    """A plugin for evaluating essays based on skills."""


    @kernel_function(
        name="evaluate_skills",
        description="Avalia a pontuação de uma redação com base na lista de resultados de habilidade já avaliada e retorna se está aprovado ou reprovado."
    )
    def evaluate_skills(
        self,
        skills_result_list: Annotated[str, "JSON string containing the list of skills to evaluate"],
        essay: Annotated[str, "The essay text to evaluate"]
    ) -> Annotated[str, "JSON string with result and avg_score"]:
        """
        Avalia as habilidades em uma redação e retorna se está aprovado ou reprovado, conforme as regras fornecidas.
        """
        try:
            # Parse skills if it's a JSON string
            if isinstance(skills_result_list, str):
                skills = json.loads(skills_result_list)
            else:
                skills = skills_result_list

            if not skills:
                return json.dumps({"error": "No skills provided for evaluation."})

            scores = []
            for skill in skills:
                score = self._evaluate_skill_score(skill)
                scores.append(score)

            if not scores:
                return json.dumps({"error": "No scores calculated."})

            if any(score == 0 for score in scores):
                result = "reprovado"
                avg_score = 0
            else:
                avg_score = sum(scores) / len(scores)
                if avg_score >= 7:
                    result = "aprovado"
                else:
                    result = "reprovado"

            return json.dumps({
                "result": result,
                "avg_score": avg_score
            })

        except Exception as e:
            return json.dumps({"error": f"Evaluation failed: {str(e)}"})
