import uuid
from typing import Any

from app.agents import CompassClient, EvaluatorAgent, ExecutorAgent, PlannerAgent
from app.logging_utils import read_trace, write_trace


class MultiAgentOrchestrator:
    """
    Planner -> Executor -> Evaluator loop.

    This is intentionally not a one-pass linear chain. The Evaluator can send
    feedback back to the Planner, causing another planning and execution cycle.
    """

    def __init__(self, max_iterations: int = 2) -> None:
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1.")

        self.max_iterations = max_iterations
        self.compass = CompassClient()
        self.planner = PlannerAgent(self.compass)
        self.executor = ExecutorAgent(self.compass)
        self.evaluator = EvaluatorAgent(self.compass)

    def run(
            self,
            task: str,
            context: dict[str, Any] | None = None,
            use_case_id: str | None = None,
    ) -> dict[str, Any]:
        run_id = str(uuid.uuid4())
        context = context or {}

        write_trace(
            run_id=run_id,
            agent_name="Orchestrator",
            action="start_run",
            input_summary={"task": task, "use_case_id": use_case_id},
            output_summary="Run started",
            target_agent="Planner Agent",
            status="success",
            metadata={"use_case_id": use_case_id},
        )

        evaluator_feedback: str | None = None
        final_plan: dict[str, Any] | None = None
        final_execution: dict[str, Any] | None = None
        final_evaluation: dict[str, Any] | None = None

        for iteration in range(1, self.max_iterations + 1):
            retry_count = iteration - 1

            plan = self.planner.run(
                task=task,
                context=context,
                evaluator_feedback=evaluator_feedback,
            )
            final_plan = plan

            write_trace(
                run_id=run_id,
                agent_name="Planner Agent",
                action="create_or_revise_plan",
                input_summary={
                    "task": task,
                    "context_keys": list(context.keys()),
                    "evaluator_feedback": evaluator_feedback,
                },
                output_summary=plan,
                target_agent="Executor Agent",
                confidence=None,
                retry_count=retry_count,
                status="success",
                metadata={"iteration": iteration},
            )

            execution = self.executor.run(
                task=task,
                plan=plan,
                context=context,
            )
            final_execution = execution

            write_trace(
                run_id=run_id,
                agent_name="Executor Agent",
                action="execute_plan",
                input_summary={
                    "task": task,
                    "plan_objective": plan.get("objective"),
                    "plan_steps": plan.get("steps"),
                },
                output_summary=execution,
                target_agent="Evaluator Agent",
                confidence=execution.get("confidence"),
                retry_count=retry_count,
                status="success",
                metadata={"iteration": iteration},
            )

            evaluation = self.evaluator.run(
                task=task,
                plan=plan,
                execution=execution,
            )
            final_evaluation = evaluation

            write_trace(
                run_id=run_id,
                agent_name="Evaluator Agent",
                action="evaluate_execution",
                input_summary={
                    "task": task,
                    "success_criteria": plan.get("success_criteria"),
                    "execution_confidence": execution.get("confidence"),
                },
                output_summary=evaluation,
                target_agent=evaluation.get("target_agent"),
                confidence=evaluation.get("confidence"),
                retry_count=retry_count,
                status="success",
                metadata={"iteration": iteration},
            )

            if evaluation.get("passed") is True:
                write_trace(
                    run_id=run_id,
                    agent_name="Orchestrator",
                    action="accept_final_output",
                    input_summary=evaluation,
                    output_summary="Evaluator accepted output",
                    target_agent="Final",
                    confidence=evaluation.get("confidence"),
                    retry_count=retry_count,
                    status="success",
                    metadata={"iteration": iteration},
                )
                break

            evaluator_feedback = str(evaluation.get("critique", ""))
            required_changes = evaluation.get("required_changes", [])

            write_trace(
                run_id=run_id,
                agent_name="Orchestrator",
                action="request_revision",
                input_summary={
                    "critique": evaluator_feedback,
                    "required_changes": required_changes,
                },
                output_summary="Revision requested from Planner Agent",
                target_agent="Planner Agent",
                confidence=evaluation.get("confidence"),
                retry_count=retry_count,
                status="needs_revision",
                metadata={"iteration": iteration},
            )

        trace = read_trace(run_id)
        status = "completed"
        if final_evaluation and not final_evaluation.get("passed"):
            status = "completed_with_caveats"

        iterations_used = sum(
            1
            for item in trace
            if item.get("agent_name") == "Evaluator Agent"
            and item.get("action") == "evaluate_execution"
        )

        return {
            "run_id": run_id,
            "status": status,
            "use_case_id": use_case_id,
            "task": task,
            "final_answer": final_execution,
            "final_plan": final_plan,
            "final_evaluation": final_evaluation,
            "iterations_used": iterations_used,
            "agents": [
                {
                    "name": "Planner Agent",
                    "role": "Decomposes the task and revises plans based on feedback",
                },
                {
                    "name": "Executor Agent",
                    "role": "Executes the plan and creates the candidate output",
                },
                {
                    "name": "Evaluator Agent",
                    "role": "Critiques output and requests revision or accepts final answer",
                },
            ],
            "trace_path": f"logs/{run_id}.jsonl",
            "trace_excerpt": trace[-8:],
        }
