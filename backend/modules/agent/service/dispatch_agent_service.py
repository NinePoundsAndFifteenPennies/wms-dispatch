import asyncio
import logging
import math
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import text

from modules.agent.bailian_provider import BailianProvider
from modules.agent.skill_loader import AgentSkillLoader
from modules.dispatcher.schemas import (
    DispatcherAgentConfirmStageResultResponse,
    DispatcherAgentConfirmWorkOrderRequest,
    DispatcherAgentConfirmWorkOrderResponse,
    DispatcherAgentStageSuggestionResponse,
    DispatcherAgentSuggestWorkOrderRequest,
    DispatcherAgentSuggestWorkOrderResponse,
    DispatcherAgentWorkerScoreResponse,
    DispatcherAgentWorkerSummaryResponse,
    DispatcherCreateWorkOrderRequest,
    DispatcherOrderWorkOrderResponse,
    DispatcherWorkOrderRiskResponse,
)
from modules.shared.config import settings


logger = logging.getLogger(__name__)


class DispatcherAgentServiceMixin:
    _SKILL_FILES = ("order-dispatchSkill.md", "worker-scoreSkill.md")
    _STAGE_ORDER = {"picking": 1, "staging": 2, "shipping": 3}
    _STAGE_LABELS = {"picking": "分拣", "staging": "备货装箱", "shipping": "发货装车"}
    _MAX_SKILL = 10
    _MAX_SPEEDUP = 3.0
    _LOAD_FACTOR = 0.4
    _skill_context_cache: str | None = None
    _MODEL_POOL_BY_STAGE = {
        "picking": ("qwen3.5-flash", "qwen3.5-122b-a10b"),
        "staging": ("glm-5", "MiniMax-M2.5"),
        "shipping": ("qwen3.5-plus", "qwen3.5-plus-2026-02-15", "kimi-k2.5"),
    }

    @staticmethod
    def _sanitize_guidance_text(text: str | None) -> str | None:
        if text is None:
            return None
        # Remove any internal agent metadata lines before exposing to workers.
        lines = [line for line in text.splitlines() if not line.strip().startswith("[agent-guidance]")]
        cleaned = "\n".join(lines).strip()
        return cleaned or None

    @staticmethod
    def _format_llm_refine_error_detail(error: Exception) -> str:
        if isinstance(error, HTTPException):
            return str(getattr(error, "detail", str(error)))
        return f"AI 工单描述生成失败：{str(error)}"

    @staticmethod
    def _append_workflow_trace(trace: list[dict], *, stage_type: str | None, model: str | None, status: str, detail: str | None = None) -> None:
        trace.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "stage_type": stage_type,
                "model": model,
                "status": status,
                "detail": detail,
            }
        )

    @classmethod
    def _build_guidance_text(
        cls,
        *,
        order_no: str,
        stage_type: str,
        required_skill_min: int,
        required_skill_max: int,
        worker_skill: int,
        skill_products: list[dict],
        priority: str,
        intent: str | None,
    ) -> str:
        stage_label = cls._STAGE_LABELS.get(stage_type)
        if stage_label is None:
            logger.warning("Unknown stage type for guidance generation: %s", stage_type)
            stage_label = "未知阶段"
        skill_match_scenario = "技能覆盖全部商品要求"
        if required_skill_min < worker_skill < required_skill_max:
            skill_match_scenario = "技能介于最低与最高要求之间，存在受限商品"
        elif worker_skill == required_skill_min:
            skill_match_scenario = "技能恰好达到最低要求，需谨慎执行"

        eligible_products: list[str] = []
        blocked_products: list[str] = []
        product_lines: list[str] = []
        for item in skill_products:
            try:
                required_skill = int(item.get("required_skill", 0))
            except (TypeError, ValueError):
                logger.warning(
                    "Invalid required_skill in skill_products for order %s stage %s: %s",
                    order_no,
                    stage_type,
                    item.get("required_skill"),
                )
                required_skill = 0
            product_name = str(item.get("product_name") or "未知商品")
            product_sku = str(item.get("product_sku") or "-")
            if required_skill <= worker_skill:
                eligible_products.append(product_name)
            else:
                blocked_products.append(product_name)
            product_lines.append(
                f"- {product_name}（SKU: {product_sku}），要求技能 {required_skill}"
            )
        lines = [
            f"订单号：{order_no}",
            f"阶段：{stage_label}",
            f"工单优先级：{priority}",
            f"技能区间：{required_skill_min}-{required_skill_max}，当前工人技能：{worker_skill}",
            f"判定场景：{skill_match_scenario}",
            "待处理商品：",
            *product_lines,
            f"可处理商品：{', '.join(eligible_products) if eligible_products else '无'}",
            f"超技能商品：{', '.join(blocked_products) if blocked_products else '无'}",
            "请按技能边界生成纯文本建议，不要输出 Markdown。",
        ]
        if intent:
            lines.append(f"调度意图：{intent.strip()[:200]}")
        return "\n".join(lines)

    @classmethod
    def _next_priority(cls, priority: str) -> str:
        if priority == "low":
            return "medium"
        if priority == "medium":
            return "high"
        return "high"

    @classmethod
    def _prev_priority(cls, priority: str) -> str:
        if priority == "high":
            return "medium"
        if priority == "medium":
            return "low"
        return "low"

    @classmethod
    def _decide_agent_priority(cls, *, order_priority: str, timeout_revert_count: int, stage_row: dict, stages_by_type: dict) -> str:
        priority = order_priority if order_priority in {"low", "medium", "high"} else "medium"

        if timeout_revert_count >= 2 and priority in {"low", "medium"}:
            priority = "high"
        elif timeout_revert_count >= 1 and priority == "medium":
            priority = "high"

        if stage_row["stage_type"] == "shipping":
            picking_completed = stages_by_type.get("picking", {}).get("status") == "completed"
            staging_completed = stages_by_type.get("staging", {}).get("status") == "completed"
            if picking_completed and staging_completed:
                priority = cls._next_priority(priority)

        previous_stage_type = {
            "staging": "picking",
            "shipping": "staging",
        }.get(stage_row["stage_type"])
        if stage_row["status"] == "not_started" and previous_stage_type:
            previous_completed = stages_by_type.get(previous_stage_type, {}).get("status") == "completed"
            if not previous_completed:
                priority = cls._prev_priority(priority)

        return priority

    @classmethod
    def _calculate_worker_score(cls, *, skill_level: int, pending_count: int, in_progress_count: int) -> dict:
        normalized_skill = max(0, min(int(skill_level), cls._MAX_SKILL))
        speedup = 1 + (cls._MAX_SPEEDUP - 1) * math.log(
            1 + (normalized_skill / cls._MAX_SKILL) * (math.e - 1)
        )
        eff_norm = (speedup - 1) / (cls._MAX_SPEEDUP - 1)
        load = float(in_progress_count) * 1.0 + float(pending_count) * 0.5
        load_penalty = 1 / (1 + load * cls._LOAD_FACTOR)
        final_score = eff_norm * 100 * load_penalty
        return {
            "speedup": round(speedup, 4),
            "load": round(load, 4),
            "load_penalty": round(load_penalty, 4),
            "final_score": round(final_score, 4),
        }

    async def _list_order_stages(self, order_id: int) -> list[dict]:
        stages_result = await self.session.execute(
            text(
                """
                SELECT id, stage_type, status
                FROM order_stages
                WHERE order_id = :order_id
                ORDER BY
                    CASE stage_type
                        WHEN 'picking' THEN 1
                        WHEN 'staging' THEN 2
                        WHEN 'shipping' THEN 3
                        ELSE 99
                    END,
                    id ASC
                """
            ),
            {"order_id": order_id},
        )
        stages = [dict(row) for row in stages_result.mappings().all()]
        if not stages:
            raise HTTPException(status_code=404, detail="Order stages not found")
        return stages

    async def _get_stage_work_order_counts(self, order_id: int) -> dict[int, int]:
        result = await self.session.execute(
            text(
                """
                SELECT stage_id, COUNT(*)::INTEGER AS total_count
                FROM work_orders
                WHERE order_id = :order_id
                GROUP BY stage_id
                """
            ),
            {"order_id": order_id},
        )
        return {int(row["stage_id"]): int(row["total_count"]) for row in result.mappings().all()}

    @classmethod
    def _build_stage_model_candidates(cls, stage_type: str | None) -> list[str]:
        candidates: list[str] = []
        if stage_type == "picking" and settings.bailian_stage_model_picking:
            candidates.append(settings.bailian_stage_model_picking)
        if stage_type == "staging" and settings.bailian_stage_model_staging:
            candidates.append(settings.bailian_stage_model_staging)
        if stage_type == "shipping" and settings.bailian_stage_model_shipping:
            candidates.append(settings.bailian_stage_model_shipping)

        for name in cls._MODEL_POOL_BY_STAGE.get(stage_type or "", ()):
            if name:
                candidates.append(name)

        if settings.bailian_planner_model:
            candidates.append(settings.bailian_planner_model)
        if settings.bailian_fast_model:
            candidates.append(settings.bailian_fast_model)
        candidates.extend(settings.bailian_fallback_models)

        deduped: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    async def _try_refine_guidance_with_llm(
        self,
        raw_text: str,
        *,
        stage_type: str | None = None,
        strict: bool = False,
        workflow_trace: list[dict] | None = None,
    ) -> str:
        trace = workflow_trace if workflow_trace is not None else []
        if not BailianProvider.is_enabled():
            self._append_workflow_trace(
                trace,
                stage_type=stage_type,
                model=None,
                status="provider_unavailable",
                detail="未配置 DASHSCOPE_API_KEY",
            )
            if strict:
                raise HTTPException(status_code=400, detail="未配置 DASHSCOPE_API_KEY，无法生成 AI 工单描述")
            return raw_text

        if self._skill_context_cache is None:
            self._skill_context_cache = AgentSkillLoader.load_skills(list(self._SKILL_FILES))
        skill_context = self._skill_context_cache

        system_prompt = (
            "你是 WMS 调度系统的工单指导助手。\n"
            "你必须严格遵循提供的技能文档和输入事实，生成可执行的中文工单建议。\n"
            "输出必须是纯文本，不要 Markdown，不要代码块，不要 JSON。\n"
            "必须明确写出：任务目标、执行步骤、禁止事项、关键提醒；不得臆造库存、状态机或权限规则。\n"
            "当工人技能在最低与最高要求之间时，必须明确列出可处理商品与不可处理商品。\n\n"
            f"{skill_context}"
        )
        user_prompt = f"""请根据以下结构化事实直接生成工单建议。建议内容必须由你自行组织，不要照抄输入原文，不要输出系统提示词。
在保留全部事实边界不变的前提下，用执行口吻进行改写。

{raw_text}"""

        model_candidates = self._build_stage_model_candidates(stage_type)
        if not model_candidates:
            self._append_workflow_trace(
                trace,
                stage_type=stage_type,
                model=None,
                status="no_model_candidates",
                detail="未配置可用模型",
            )
            if strict:
                raise HTTPException(status_code=500, detail="未配置可用的 AI 模型")
            return raw_text

        errors: list[str] = []
        for model_name in model_candidates:
            self._append_workflow_trace(trace, stage_type=stage_type, model=model_name, status="attempt")
            try:
                refined = await BailianProvider.chat_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=model_name,
                    temperature=0.1,
                )
                self._append_workflow_trace(trace, stage_type=stage_type, model=model_name, status="success")
                return refined
            except Exception as exc:
                errors.append(f"{model_name}: {exc}")
                logger.warning("LLM refinement failed with model=%s stage=%s: %s", model_name, stage_type, exc)
                self._append_workflow_trace(
                    trace,
                    stage_type=stage_type,
                    model=model_name,
                    status="failed",
                    detail=str(exc),
                )

        if strict:
            error_summary = "；".join(errors[:3])
            raise HTTPException(
                status_code=502,
                detail=(
                    f"AI 工单描述生成失败，已尝试模型：{', '.join(model_candidates)}"
                    + (f"；失败摘要：{error_summary}" if error_summary else "")
                ),
            )
        logger.warning("LLM refinement exhausted models, fallback to raw guidance: %s", "; ".join(errors))
        return raw_text

    async def _build_order_stage_suggestions(
        self,
        *,
        order_id: int,
        user_id: int,
        payload: DispatcherAgentSuggestWorkOrderRequest,
        refine_guidance: bool = True,
        require_llm_guidance: bool = False,
        llm_failure_as_unassignable: bool = False,
        llm_failure_fallback_to_raw: bool = False,
        llm_workflow_trace: list[dict] | None = None,
    ) -> list[dict]:
        order_base = await self._get_dispatcher_order(order_id=order_id, user_id=user_id)
        if order_base["status"] != "in_progress":
            raise HTTPException(status_code=400, detail="仅进行中的订单可使用 Agent 派单")

        order_meta_result = await self.session.execute(
            text(
                """
                SELECT id, order_no, priority, timeout_revert_count
                FROM orders
                WHERE id = :order_id
                LIMIT 1
                """
            ),
            {"order_id": order_id},
        )
        order_meta = order_meta_result.mappings().first()
        if not order_meta:
            raise HTTPException(status_code=404, detail="Order not found")

        all_stages = await self._list_order_stages(order_id=order_id)
        stages = [row for row in all_stages if row["status"] != "completed"]
        stages.sort(key=lambda row: self._STAGE_ORDER.get(row["stage_type"], 99))
        stages_by_type = {row["stage_type"]: row for row in all_stages}

        workers = await self.list_workers(user_id=user_id, search=payload.search_worker)
        stage_work_order_counts = await self._get_stage_work_order_counts(order_id=order_id)

        suggestions: list[dict] = []
        pending_refinements: list[tuple[int, str, str]] = []
        for stage in stages:
            stage_id = int(stage["id"])
            existing_count = stage_work_order_counts.get(stage_id, 0)
            if existing_count > 0:
                suggestions.append(
                    {
                        "stage_id": stage_id,
                        "stage_type": stage["stage_type"],
                        "assignable": False,
                        "reason": "该阶段已存在工单",
                        "required_skill_min": 0,
                        "required_skill_max": 0,
                        "has_risk": False,
                        "risks": [],
                        "worker": None,
                        "score": None,
                        "priority": None,
                        "suggested_description": None,
                    }
                )
                continue

            if not workers:
                suggestions.append(
                    {
                        "stage_id": stage_id,
                        "stage_type": stage["stage_type"],
                        "assignable": False,
                        "reason": "当前仓库无可用工人",
                        "required_skill_min": 0,
                        "required_skill_max": 0,
                        "has_risk": False,
                        "risks": [],
                        "worker": None,
                        "score": None,
                        "priority": None,
                        "suggested_description": None,
                    }
                )
                continue

            candidate_rows: list[dict] = []
            for worker in workers:
                try:
                    assessment = await self._assess_work_order_assignment(
                        order_id=order_id,
                        user_id=user_id,
                        stage_id=stage_id,
                        worker_id=worker["id"],
                    )
                except HTTPException:
                    continue

                score = self._calculate_worker_score(
                    skill_level=assessment["worker_skill"],
                    pending_count=assessment["pending_count"],
                    in_progress_count=assessment["in_progress_count"],
                )
                candidate_rows.append(
                    {
                        "stage_id": stage_id,
                        "stage_type": assessment["stage_row"]["stage_type"],
                        "required_skill_min": assessment["required_skill_min"],
                        "required_skill_max": assessment["required_skill_max"],
                        "has_risk": len(assessment["risks"]) > 0,
                        "risks": assessment["risks"],
                        "skill_products": assessment["skill_products"],
                        "worker": {
                            "worker_id": int(worker["id"]),
                            "worker_name": worker["username"],
                            "worker_skill": int(assessment["worker_skill"]),
                            "pending_count": int(assessment["pending_count"]),
                            "in_progress_count": int(assessment["in_progress_count"]),
                            "active_work_order_count": int(assessment["active_work_order_count"]),
                            "active_work_order_limit": int(self.active_work_order_limit),
                        },
                        "score": score,
                    }
                )

            if not candidate_rows:
                suggestions.append(
                    {
                        "stage_id": stage_id,
                        "stage_type": stage["stage_type"],
                        "assignable": False,
                        "reason": "无工人满足该阶段最低技能要求",
                        "required_skill_min": 0,
                        "required_skill_max": 0,
                        "has_risk": False,
                        "risks": [],
                        "worker": None,
                        "score": None,
                        "priority": None,
                        "suggested_description": None,
                    }
                )
                continue

            candidate_rows.sort(key=lambda item: (-item["score"]["final_score"], item["worker"]["worker_id"]))
            selected = candidate_rows[0]

            priority = self._decide_agent_priority(
                order_priority=str(order_meta["priority"]),
                timeout_revert_count=int(order_meta.get("timeout_revert_count") or 0),
                stage_row=stage,
                stages_by_type=stages_by_type,
            )
            raw_guidance = self._build_guidance_text(
                order_no=str(order_meta["order_no"]),
                stage_type=selected["stage_type"],
                required_skill_min=selected["required_skill_min"],
                required_skill_max=selected["required_skill_max"],
                worker_skill=selected["worker"]["worker_skill"],
                skill_products=selected["skill_products"],
                priority=priority,
                intent=payload.intent,
            )
            final_guidance = self._sanitize_guidance_text(raw_guidance)

            suggestions.append(
                {
                    "stage_id": stage_id,
                    "stage_type": selected["stage_type"],
                    "assignable": True,
                    "reason": None,
                    "required_skill_min": selected["required_skill_min"],
                    "required_skill_max": selected["required_skill_max"],
                    "has_risk": selected["has_risk"],
                    "risks": selected["risks"],
                    "worker": selected["worker"],
                    "score": selected["score"],
                    "priority": priority,
                    "suggested_description": final_guidance,
                }
            )
            if refine_guidance:
                suggestion_idx = len(suggestions) - 1
                pending_refinements.append((suggestion_idx, raw_guidance, selected["stage_type"]))

        if refine_guidance and pending_refinements:
            refine_results = await asyncio.gather(
                *[
                    self._try_refine_guidance_with_llm(
                        raw_guidance,
                        stage_type=stage_type,
                        strict=require_llm_guidance,
                        workflow_trace=llm_workflow_trace,
                    )
                    for _, raw_guidance, stage_type in pending_refinements
                ],
                return_exceptions=True,
            )
            for (suggestion_idx, raw_guidance, stage_type), result in zip(pending_refinements, refine_results):
                if isinstance(result, Exception):
                    if require_llm_guidance:
                        if llm_failure_fallback_to_raw:
                            detail = self._format_llm_refine_error_detail(result)
                            suggestions[suggestion_idx]["suggested_description"] = self._sanitize_guidance_text(raw_guidance)
                            logger.warning(
                                "LLM refinement unavailable in stage %s, fallback to raw guidance: %s",
                                stage_type,
                                detail,
                            )
                            continue
                        if llm_failure_as_unassignable:
                            detail = self._format_llm_refine_error_detail(result)
                            suggestions[suggestion_idx]["suggested_description"] = self._sanitize_guidance_text(raw_guidance)
                            logger.warning(
                                "LLM refinement unavailable in stage %s, fallback to raw guidance: %s",
                                stage_type,
                                detail,
                            )
                            continue
                        if isinstance(result, HTTPException):
                            raise result
                        raise HTTPException(status_code=502, detail=f"AI 工单描述生成失败：{str(result)}")
                    logger.warning(
                        "LLM refinement failed in stage %s, fallback to raw guidance: %s",
                        stage_type,
                        result,
                    )
                    suggestions[suggestion_idx]["suggested_description"] = self._sanitize_guidance_text(raw_guidance)
                    continue
                suggestions[suggestion_idx]["suggested_description"] = self._sanitize_guidance_text(result)

        return suggestions

    async def _insert_agent_work_order_without_commit(
        self,
        *,
        order_id: int,
        user_id: int,
        stage_id: int,
        worker_id: int,
        priority: str,
        description: str | None,
        override_reason: str | None,
    ) -> int:
        payload = DispatcherCreateWorkOrderRequest(
            stage_id=stage_id,
            worker_id=worker_id,
            priority=priority,
            deadline=None,
            description=description,
            override_reason=override_reason,
            source="agent",
        )

        assessment = await self._assess_work_order_assignment(
            order_id=order_id,
            user_id=user_id,
            stage_id=payload.stage_id,
            worker_id=payload.worker_id,
        )
        order_row = assessment["order_row"]
        stage_row = assessment["stage_row"]
        risks = assessment["risks"]

        normalized_override_reason = (payload.override_reason or "").strip()
        if risks and not normalized_override_reason:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "存在风险，必须填写 override_reason",
                    "risk_codes": [item["code"] for item in risks],
                    "risks": risks,
                },
            )

        previous_stage_type = {
            "staging": "picking",
            "shipping": "staging",
        }.get(stage_row["stage_type"])
        previous_stage_id = None
        if previous_stage_type:
            previous_stage_result = await self.session.execute(
                text(
                    """
                    SELECT id
                    FROM order_stages
                    WHERE order_id = :order_id
                      AND stage_type = :stage_type
                    LIMIT 1
                    """
                ),
                {
                    "order_id": order_id,
                    "stage_type": previous_stage_type,
                },
            )
            previous_stage = previous_stage_result.mappings().first()
            previous_stage_id = previous_stage["id"] if previous_stage else None

        normalized_description = payload.description.strip() if payload.description else None
        normalized_description = self._sanitize_guidance_text(normalized_description)
        if risks:
            risk_codes = ",".join(item["code"] for item in risks)
            audit_prefix = f"[override][{risk_codes}] {normalized_override_reason}"
            normalized_description = f"{audit_prefix}\n{normalized_description}" if normalized_description else audit_prefix

        insert_result = await self.session.execute(
            text(
                """
                INSERT INTO work_orders (
                    order_id,
                    stage_id,
                    worker_id,
                    dispatcher_id,
                    warehouse_id,
                    status,
                    priority,
                    deadline,
                    description,
                    source,
                    created_at,
                    updated_at
                ) VALUES (
                    :order_id,
                    :stage_id,
                    :worker_id,
                    :dispatcher_id,
                    :warehouse_id,
                    'pending',
                    :priority,
                    :deadline,
                    :description,
                    :source,
                    (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                    (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                )
                RETURNING id
                """
            ),
            {
                "order_id": order_id,
                "stage_id": payload.stage_id,
                "worker_id": payload.worker_id,
                "dispatcher_id": user_id,
                "warehouse_id": order_row["warehouse_id"],
                "priority": payload.priority,
                "deadline": payload.deadline,
                "description": normalized_description,
                "source": payload.source,
            },
        )
        new_row = insert_result.mappings().first()
        if not new_row:
            raise HTTPException(status_code=409, detail="Failed to create work order")

        if previous_stage_id is not None:
            await self._try_auto_complete_stage(stage_id=previous_stage_id, operated_by=user_id)

        return int(new_row["id"])

    async def suggest_work_order_by_agent(
        self,
        *,
        order_id: int,
        user_id: int,
        payload: DispatcherAgentSuggestWorkOrderRequest,
    ) -> DispatcherAgentSuggestWorkOrderResponse:
        llm_trace: list[dict] = []
        suggestions = await self._build_order_stage_suggestions(
            order_id=order_id,
            user_id=user_id,
            payload=payload,
            refine_guidance=True,
            require_llm_guidance=True,
            llm_failure_as_unassignable=False,
            llm_failure_fallback_to_raw=True,
            llm_workflow_trace=llm_trace,
        )
        stage_items: list[DispatcherAgentStageSuggestionResponse] = []
        for stage in suggestions:
            worker = (
                DispatcherAgentWorkerSummaryResponse(**stage["worker"]) if stage["worker"] is not None else None
            )
            score = DispatcherAgentWorkerScoreResponse(**stage["score"]) if stage["score"] is not None else None
            risks = [DispatcherWorkOrderRiskResponse(**risk) for risk in stage["risks"]]
            stage_items.append(
                DispatcherAgentStageSuggestionResponse(
                    stage_id=stage["stage_id"],
                    stage_type=stage["stage_type"],
                    assignable=stage["assignable"],
                    reason=stage["reason"],
                    required_skill_min=stage["required_skill_min"],
                    required_skill_max=stage["required_skill_max"],
                    has_risk=stage["has_risk"],
                    risks=risks,
                    worker=worker,
                    score=score,
                    priority=stage["priority"],
                    suggested_description=stage["suggested_description"],
                )
            )
        return DispatcherAgentSuggestWorkOrderResponse(order_id=order_id, stages=stage_items, llm_workflow_trace=llm_trace)

    async def confirm_agent_work_order(
        self,
        *,
        order_id: int,
        user_id: int,
        payload: DispatcherAgentConfirmWorkOrderRequest,
    ) -> DispatcherAgentConfirmWorkOrderResponse:
        suggest_payload = DispatcherAgentSuggestWorkOrderRequest(
            intent=payload.intent,
            search_worker=None,
        )
        suggestions = await self._build_order_stage_suggestions(
            order_id=order_id,
            user_id=user_id,
            payload=suggest_payload,
            refine_guidance=True,
            require_llm_guidance=True,
        )

        override_map = {
            int(item.stage_id): (item.override_reason.strip() if item.override_reason else None)
            for item in payload.stage_overrides
        }

        created_work_order_ids: list[int] = []
        stage_results: list[DispatcherAgentConfirmStageResultResponse] = []
        try:
            for stage in suggestions:
                risks = [DispatcherWorkOrderRiskResponse(**risk) for risk in stage["risks"]]
                if not stage["assignable"]:
                    stage_results.append(
                        DispatcherAgentConfirmStageResultResponse(
                            stage_id=stage["stage_id"],
                            stage_type=stage["stage_type"],
                            status="unassignable",
                            reason=stage["reason"],
                            has_risk=False,
                            risks=[],
                            work_order_id=None,
                        )
                    )
                    continue

                stage_id = int(stage["stage_id"])
                if stage["has_risk"] and not override_map.get(stage_id):
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": f"阶段 {stage['stage_type']} 存在风险，必须填写 override_reason",
                            "stage_id": stage_id,
                            "risk_codes": [risk.code for risk in risks],
                            "risks": [risk.model_dump() for risk in risks],
                        },
                    )

                worker_id = int(stage["worker"]["worker_id"])
                work_order_id = await self._insert_agent_work_order_without_commit(
                    order_id=order_id,
                    user_id=user_id,
                    stage_id=stage_id,
                    worker_id=worker_id,
                    priority=stage["priority"] or "medium",
                    description=stage["suggested_description"],
                    override_reason=override_map.get(stage_id),
                )
                created_work_order_ids.append(work_order_id)
                stage_results.append(
                    DispatcherAgentConfirmStageResultResponse(
                        stage_id=stage_id,
                        stage_type=stage["stage_type"],
                        status="created",
                        reason=None,
                        has_risk=stage["has_risk"],
                        risks=risks,
                        work_order_id=work_order_id,
                    )
                )

            await self.session.commit()
        except HTTPException:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

        created_work_orders: list[DispatcherOrderWorkOrderResponse] = []
        for work_order_id in created_work_order_ids:
            work_order = await self._get_work_order_detail(work_order_id=work_order_id)
            created_work_orders.append(DispatcherOrderWorkOrderResponse(**work_order))

        return DispatcherAgentConfirmWorkOrderResponse(
            order_id=order_id,
            created_work_orders=created_work_orders,
            stages=stage_results,
        )
