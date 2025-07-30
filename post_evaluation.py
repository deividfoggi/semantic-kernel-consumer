from semantic_kernel.functions import kernel_function

class PostEvaluation:

    @kernel_function(
            name="RunEvaluationTask",
            description="This function runs a post evaluation task."
    )
    async def run_evaluation_task(self, skill_list):
        # a code that will evaluate each skill score using the following rule:
        # if any skill score is 0, then the essay is cancelled
        # if the average of all skill scores is more than 4, then the essay is approved
        if not skill_list:
            return "No skills provided for evaluation."
        if any(skill['score'] == 0 for skill in skill_list):
            return "Essay cancelled due to a skill score of 0."
        average_score = sum(skill['score'] for skill in skill_list) / len(skill_list)
        if average_score > 4:
            return "Essay approved."
        else:
            return "Essay not approved."
