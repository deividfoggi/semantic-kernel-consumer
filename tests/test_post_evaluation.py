import pytest
import json
import os
import sys
from unittest.mock import Mock

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from post_evaluation import PostEvaluation


class TestPostEvaluation:
    """Test suite for PostEvaluation class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.post_eval = PostEvaluation()

    def test_evaluate_skill_score_valid_integer(self):
        """Test _evaluate_skill_score with valid integer score."""
        # Setup
        skill = {"nota": 8}
        
        # Execute
        score = self.post_eval._evaluate_skill_score(skill)
        
        # Verify
        assert score == 8

    def test_evaluate_skill_score_valid_string_integer(self):
        """Test _evaluate_skill_score with valid string integer score."""
        # Setup
        skill = {"nota": "7"}
        
        # Execute
        score = self.post_eval._evaluate_skill_score(skill)
        
        # Verify
        assert score == 7

    def test_evaluate_skill_score_invalid_string(self):
        """Test _evaluate_skill_score with invalid string score."""
        # Setup
        skill = {"nota": "invalid"}
        
        # Execute
        score = self.post_eval._evaluate_skill_score(skill)
        
        # Verify
        assert score == 0

    def test_evaluate_skill_score_missing_nota(self):
        """Test _evaluate_skill_score with missing nota field."""
        # Setup
        skill = {"habilidade": "writing"}
        
        # Execute
        score = self.post_eval._evaluate_skill_score(skill)
        
        # Verify
        assert score == 0

    def test_evaluate_skill_score_none_value(self):
        """Test _evaluate_skill_score with None nota value."""
        # Setup
        skill = {"nota": None}
        
        # Execute
        score = self.post_eval._evaluate_skill_score(skill)
        
        # Verify
        assert score == 0

    def test_evaluate_skill_score_float_value(self):
        """Test _evaluate_skill_score with float value (should convert to int)."""
        # Setup
        skill = {"nota": 8.7}
        
        # Execute
        score = self.post_eval._evaluate_skill_score(skill)
        
        # Verify
        assert score == 8

    def test_evaluate_skills_success_approved(self):
        """Test evaluate_skills with approved result (average >= 7)."""
        # Setup
        skills_list = [
            {"habilidade": "writing", "nota": 8},
            {"habilidade": "grammar", "nota": 7},
            {"habilidade": "coherence", "nota": 9}
        ]
        skills_json = json.dumps(skills_list)
        essay = "This is a test essay."
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "aprovado"
        assert result_dict["avg_score"] == 8.0

    def test_evaluate_skills_success_reproved_low_average(self):
        """Test evaluate_skills with reproved result (average < 7)."""
        # Setup
        skills_list = [
            {"habilidade": "writing", "nota": 5},
            {"habilidade": "grammar", "nota": 6},
            {"habilidade": "coherence", "nota": 4}
        ]
        skills_json = json.dumps(skills_list)
        essay = "This is a test essay."
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "reprovado"
        assert result_dict["avg_score"] == 5.0

    def test_evaluate_skills_reproved_zero_score(self):
        """Test evaluate_skills with reproved result due to zero score."""
        # Setup
        skills_list = [
            {"habilidade": "writing", "nota": 8},
            {"habilidade": "grammar", "nota": 0},  # Zero score = automatic failure
            {"habilidade": "coherence", "nota": 9}
        ]
        skills_json = json.dumps(skills_list)
        essay = "This is a test essay."
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "reprovado"
        assert result_dict["avg_score"] == 0

    def test_evaluate_skills_json_string_input(self):
        """Test evaluate_skills with JSON string input."""
        # Setup
        skills_json = '[{"habilidade": "writing", "nota": 8}, {"habilidade": "grammar", "nota": 7}]'
        essay = "Test essay"
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "aprovado"
        assert result_dict["avg_score"] == 7.5

    def test_evaluate_skills_list_input(self):
        """Test evaluate_skills with direct list input."""
        # Setup
        skills_list = [
            {"habilidade": "writing", "nota": 6},
            {"habilidade": "grammar", "nota": 5}
        ]
        essay = "Test essay"
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_list, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "reprovado"
        assert result_dict["avg_score"] == 5.5

    def test_evaluate_skills_empty_skills_list(self):
        """Test evaluate_skills with empty skills list."""
        # Setup
        skills_json = json.dumps([])
        essay = "Test essay"
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert "error" in result_dict
        assert "No skills provided" in result_dict["error"]

    def test_evaluate_skills_invalid_json(self):
        """Test evaluate_skills with invalid JSON string."""
        # Setup
        skills_json = "invalid json string"
        essay = "Test essay"
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert "error" in result_dict
        assert "Evaluation failed" in result_dict["error"]

    def test_evaluate_skills_skills_with_invalid_scores(self):
        """Test evaluate_skills with skills containing invalid scores."""
        # Setup
        skills_list = [
            {"habilidade": "writing", "nota": "invalid"},
            {"habilidade": "grammar", "nota": 8},
            {"habilidade": "coherence", "nota": None}
        ]
        skills_json = json.dumps(skills_list)
        essay = "Test essay"
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "reprovado"
        assert result_dict["avg_score"] == 0  # Due to zero scores

    def test_evaluate_skills_boundary_case_exactly_seven(self):
        """Test evaluate_skills with average exactly 7.0."""
        # Setup
        skills_list = [
            {"habilidade": "writing", "nota": 7},
            {"habilidade": "grammar", "nota": 7},
            {"habilidade": "coherence", "nota": 7}
        ]
        skills_json = json.dumps(skills_list)
        essay = "Test essay"
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "aprovado"
        assert result_dict["avg_score"] == 7.0

    def test_evaluate_skills_boundary_case_just_below_seven(self):
        """Test evaluate_skills with average just below 7.0."""
        # Setup
        skills_list = [
            {"habilidade": "writing", "nota": 6},
            {"habilidade": "grammar", "nota": 7},
            {"habilidade": "coherence", "nota": 7}
        ]
        skills_json = json.dumps(skills_list)
        essay = "Test essay"
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "reprovado"
        assert abs(result_dict["avg_score"] - 6.666666666666667) < 0.0001

    def test_evaluate_skills_single_skill(self):
        """Test evaluate_skills with single skill."""
        # Setup
        skills_list = [{"habilidade": "writing", "nota": 9}]
        skills_json = json.dumps(skills_list)
        essay = "Test essay"
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "aprovado"
        assert result_dict["avg_score"] == 9.0

    def test_evaluate_skills_maximum_scores(self):
        """Test evaluate_skills with maximum scores."""
        # Setup
        skills_list = [
            {"habilidade": "writing", "nota": 10},
            {"habilidade": "grammar", "nota": 10},
            {"habilidade": "coherence", "nota": 10}
        ]
        skills_json = json.dumps(skills_list)
        essay = "Test essay"
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "aprovado"
        assert result_dict["avg_score"] == 10.0

    def test_evaluate_skills_minimum_scores(self):
        """Test evaluate_skills with minimum scores."""
        # Setup
        skills_list = [
            {"habilidade": "writing", "nota": 1},
            {"habilidade": "grammar", "nota": 1},
            {"habilidade": "coherence", "nota": 1}
        ]
        skills_json = json.dumps(skills_list)
        essay = "Test essay"
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "reprovado"
        assert result_dict["avg_score"] == 1.0

    def test_evaluate_skills_mixed_score_types(self):
        """Test evaluate_skills with mixed score types (int, string, float)."""
        # Setup
        skills_list = [
            {"habilidade": "writing", "nota": 8},      # int
            {"habilidade": "grammar", "nota": "7"},    # string
            {"habilidade": "coherence", "nota": 9.5}  # float
        ]
        skills_json = json.dumps(skills_list)
        essay = "Test essay"
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "aprovado"
        # Should be (8 + 7 + 9) / 3 = 8.0 (float converted to int)
        assert result_dict["avg_score"] == 8.0

    def test_evaluate_skills_exception_handling(self):
        """Test evaluate_skills handles unexpected exceptions gracefully."""
        # Setup - create a scenario that causes a JSON parsing exception
        skills_json = "{"  # Malformed JSON that will cause an exception in json.loads
        essay = "Test essay"
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert "error" in result_dict
        assert "Evaluation failed" in result_dict["error"]

    def test_evaluate_skills_none_input(self):
        """Test evaluate_skills with None input."""
        # Setup
        skills_json = None
        essay = "Test essay"
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert "error" in result_dict
        assert "No skills provided" in result_dict["error"]

    def test_evaluate_skills_large_number_of_skills(self):
        """Test evaluate_skills with a large number of skills."""
        # Setup
        skills_list = [
            {"habilidade": f"skill_{i}", "nota": (i % 10) + 1} 
            for i in range(20)
        ]
        skills_json = json.dumps(skills_list)
        essay = "Test essay"
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert "result" in result_dict
        assert "avg_score" in result_dict
        assert isinstance(result_dict["avg_score"], (int, float))

    def test_evaluate_skills_with_additional_fields(self):
        """Test evaluate_skills with skills containing additional fields."""
        # Setup
        skills_list = [
            {
                "habilidade": "writing", 
                "nota": 8,
                "comentarios": "Good writing style",
                "categoria": "language"
            },
            {
                "habilidade": "grammar", 
                "nota": 7,
                "comentarios": "Minor errors",
                "peso": 0.5
            }
        ]
        skills_json = json.dumps(skills_list)
        essay = "Test essay"
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "aprovado"
        assert result_dict["avg_score"] == 7.5

    def test_evaluate_skills_empty_essay(self):
        """Test evaluate_skills with empty essay (should still work)."""
        # Setup
        skills_list = [
            {"habilidade": "writing", "nota": 8},
            {"habilidade": "grammar", "nota": 7}
        ]
        skills_json = json.dumps(skills_list)
        essay = ""  # Empty essay
        
        # Execute
        result = self.post_eval.evaluate_skills(skills_json, essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "aprovado"
        assert result_dict["avg_score"] == 7.5


class TestPostEvaluationIntegration:
    """Integration tests for PostEvaluation class."""

    def test_complete_evaluation_workflow_approved(self):
        """Test complete evaluation workflow with approved result."""
        # Setup
        post_eval = PostEvaluation()
        
        # Realistic skills evaluation
        skills_evaluation = [
            {
                "habilidade": "Domínio da modalidade escrita formal da língua portuguesa",
                "comentarios": "Excelente domínio da norma culta com raros desvios.",
                "nota": 9
            },
            {
                "habilidade": "Compreender a proposta de redação e aplicar conceitos de várias áreas",
                "comentarios": "Demonstra boa compreensão do tema e conhecimento interdisciplinar.",
                "nota": 8
            },
            {
                "habilidade": "Selecionar, relacionar, organizar e interpretar informações",
                "comentarios": "Organização clara e coerente das ideias.",
                "nota": 8
            },
            {
                "habilidade": "Demonstrar conhecimento dos mecanismos linguísticos",
                "comentarios": "Uso adequado de conectivos e progressão textual.",
                "nota": 7
            },
            {
                "habilidade": "Elaborar proposta de intervenção",
                "comentarios": "Proposta bem estruturada e viável.",
                "nota": 8
            }
        ]
        
        essay = """
        A sociedade contemporânea enfrenta desafios significativos relacionados à sustentabilidade ambiental.
        É fundamental que desenvolvamos estratégias integradas que envolvam tanto políticas públicas quanto
        a participação ativa da sociedade civil para garantir um futuro sustentável para as próximas gerações.
        """
        
        # Execute
        result = post_eval.evaluate_skills(json.dumps(skills_evaluation), essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "aprovado"
        assert result_dict["avg_score"] == 8.0

    def test_complete_evaluation_workflow_reproved(self):
        """Test complete evaluation workflow with reproved result."""
        # Setup
        post_eval = PostEvaluation()
        
        skills_evaluation = [
            {
                "habilidade": "Domínio da modalidade escrita formal da língua portuguesa",
                "comentarios": "Vários desvios da norma culta.",
                "nota": 4
            },
            {
                "habilidade": "Compreender a proposta de redação e aplicar conceitos",
                "comentarios": "Compreensão parcial do tema.",
                "nota": 5
            },
            {
                "habilidade": "Selecionar, relacionar, organizar e interpretar informações",
                "comentarios": "Organização confusa das ideias.",
                "nota": 3
            }
        ]
        
        essay = "Texto com varios erro de português e falta de clareza nas ideia."
        
        # Execute
        result = post_eval.evaluate_skills(json.dumps(skills_evaluation), essay)
        
        # Verify
        result_dict = json.loads(result)
        assert result_dict["result"] == "reprovado"
        assert result_dict["avg_score"] == 4.0


# Fixtures for reuse across tests
@pytest.fixture
def sample_skills_approved():
    """Fixture providing skills data that should result in approval."""
    return [
        {"habilidade": "writing", "nota": 8},
        {"habilidade": "grammar", "nota": 7},
        {"habilidade": "coherence", "nota": 9},
        {"habilidade": "creativity", "nota": 8}
    ]


@pytest.fixture
def sample_skills_reproved():
    """Fixture providing skills data that should result in reproval."""
    return [
        {"habilidade": "writing", "nota": 5},
        {"habilidade": "grammar", "nota": 4},
        {"habilidade": "coherence", "nota": 6},
        {"habilidade": "creativity", "nota": 3}
    ]


@pytest.fixture
def sample_essay():
    """Fixture providing a sample essay for testing."""
    return """
    A educação é um dos pilares fundamentais para o desenvolvimento de qualquer sociedade.
    Através dela, formamos cidadãos conscientes, críticos e capazes de contribuir para
    o progresso coletivo. É essencial que investimentos em educação sejam priorizados
    pelos governos, garantindo acesso universal e qualidade de ensino para todos.
    
    Além disso, a educação deve acompanhar as transformações tecnológicas e sociais,
    preparando os estudantes para os desafios do futuro. Isso inclui o desenvolvimento
    de habilidades digitais, pensamento crítico e competências socioemocionais.
    
    Portanto, é fundamental que sociedade, governo e instituições educacionais trabalhem
    em conjunto para construir um sistema educacional mais inclusivo, inovador e eficaz.
    """


# Parameterized tests for different score scenarios
@pytest.mark.parametrize("scores,expected_result,expected_avg", [
    ([10, 9, 8, 9], "aprovado", 9.0),
    ([7, 7, 7, 7], "aprovado", 7.0),
    ([6, 8, 5, 7], "reprovado", 6.5),
    ([0, 8, 9, 10], "reprovado", 0),  # Zero score causes automatic failure
    ([1, 2, 3, 4], "reprovado", 2.5),
    ([8, 9, 10], "aprovado", 9.0),
    ([5], "reprovado", 5.0),
])
def test_evaluate_skills_score_scenarios(scores, expected_result, expected_avg):
    """Test evaluate_skills with various score scenarios."""
    # Setup
    post_eval = PostEvaluation()
    skills_list = [
        {"habilidade": f"skill_{i}", "nota": score} 
        for i, score in enumerate(scores)
    ]
    skills_json = json.dumps(skills_list)
    essay = "Test essay"
    
    # Execute
    result = post_eval.evaluate_skills(skills_json, essay)
    
    # Verify
    result_dict = json.loads(result)
    assert result_dict["result"] == expected_result
    assert result_dict["avg_score"] == expected_avg


# Performance test
def test_evaluate_skills_performance_large_dataset():
    """Test evaluate_skills performance with large dataset."""
    # Setup
    post_eval = PostEvaluation()
    
    # Create a large skills dataset
    skills_list = [
        {"habilidade": f"skill_{i}", "nota": (i % 10) + 1} 
        for i in range(1000)
    ]
    skills_json = json.dumps(skills_list)
    essay = "Test essay for performance testing"
    
    # Execute
    import time
    start_time = time.time()
    result = post_eval.evaluate_skills(skills_json, essay)
    end_time = time.time()
    
    # Verify
    result_dict = json.loads(result)
    assert "result" in result_dict
    assert "avg_score" in result_dict
    
    # Performance check - should complete in reasonable time
    execution_time = end_time - start_time
    assert execution_time < 1.0  # Should complete in less than 1 second
