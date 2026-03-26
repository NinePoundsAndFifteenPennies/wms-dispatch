import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import text

from modules.admin.schemas import AdminReportResponse
from modules.agent.bailian_provider import BailianProvider
from modules.agent.skill_loader import AgentSkillLoader
from modules.shared.config import settings


class ReportAgentServiceMixin:
    _REPORT_SKILL_FILES = ("report-analysisSkill.md",)
    _report_skill_context_cache: str | None = None

    @staticmethod
    def _append_report_trace(trace: list[dict], *, model: str | None, status: str, detail: str | None = None) -> None:
        trace.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": model,
                "status": status,
                "detail": detail,
            }
        )

    @staticmethod
    def _dedupe_model_candidates(candidates: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            deduped.append(normalized)
            seen.add(normalized)
        return deduped

    @staticmethod
    def _to_json_safe(value):
        if isinstance(value, dict):
            return {str(k): ReportAgentServiceMixin._to_json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [ReportAgentServiceMixin._to_json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [ReportAgentServiceMixin._to_json_safe(item) for item in value]
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return value

    @classmethod
    def _build_report_model_candidates(cls) -> list[str]:
        candidates: list[str] = []
        if settings.bailian_report_model:
            candidates.append(settings.bailian_report_model)
        if settings.bailian_planner_model:
            candidates.append(settings.bailian_planner_model)
        if settings.bailian_fast_model:
            candidates.append(settings.bailian_fast_model)
        candidates.extend(settings.bailian_fallback_models)
        return cls._dedupe_model_candidates(candidates)

    async def _resolve_report_warehouse_name(self, warehouse_id: int | None) -> str | None:
        if warehouse_id is None:
            return None

        warehouse_result = await self.session.execute(
            text(
                """
                SELECT id, name
                FROM warehouses
                WHERE id = :warehouse_id
                LIMIT 1
                """
            ),
            {"warehouse_id": warehouse_id},
        )
        row = warehouse_result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        return str(row["name"])

    async def _build_efficiency_stats(self, *, period_start: date, period_end: date, warehouse_id: int | None) -> dict:
        range_start = datetime.combine(period_start, datetime.min.time())
        range_end = datetime.combine(period_end + timedelta(days=1), datetime.min.time())

        where_clauses = [
            "wo.created_at >= :range_start",
            "wo.created_at < :range_end",
        ]
        params: dict[str, object] = {
            "range_start": range_start,
            "range_end": range_end,
        }
        if warehouse_id is not None:
            where_clauses.append("wo.warehouse_id = :warehouse_id")
            params["warehouse_id"] = warehouse_id

        where_sql = " AND ".join(where_clauses)

        summary_result = await self.session.execute(
            text(
                f"""
                SELECT
                    COUNT(*)::INTEGER AS total_work_orders,
                    COUNT(*) FILTER (WHERE wo.status = 'completed')::INTEGER AS completed_work_orders,
                    COUNT(*) FILTER (
                        WHERE wo.deadline IS NOT NULL
                          AND (
                              (wo.status = 'completed' AND wo.completed_at > wo.deadline)
                              OR (wo.status IN ('pending', 'in_progress') AND wo.deadline < (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0))
                          )
                    )::INTEGER AS timeout_work_orders,
                    ROUND(
                        AVG(
                            CASE
                                WHEN wo.status = 'completed' AND wo.completed_at IS NOT NULL THEN
                                    EXTRACT(EPOCH FROM (wo.completed_at - wo.created_at)) / 3600.0
                                ELSE NULL
                            END
                        )::numeric,
                        2
                    ) AS avg_completion_hours
                FROM work_orders wo
                WHERE {where_sql}
                """
            ),
            params,
        )
        summary_row = summary_result.mappings().first() or {}
        total_work_orders = int(summary_row.get("total_work_orders") or 0)
        completed_work_orders = int(summary_row.get("completed_work_orders") or 0)
        timeout_work_orders = int(summary_row.get("timeout_work_orders") or 0)
        avg_completion_hours = float(summary_row.get("avg_completion_hours") or 0)

        completion_rate = round((completed_work_orders / total_work_orders) * 100, 2) if total_work_orders else 0.0
        timeout_rate = round((timeout_work_orders / total_work_orders) * 100, 2) if total_work_orders else 0.0

        stage_result = await self.session.execute(
            text(
                f"""
                SELECT
                    os.stage_type,
                    COUNT(*)::INTEGER AS total,
                    COUNT(*) FILTER (WHERE wo.status = 'completed')::INTEGER AS completed,
                    COUNT(*) FILTER (
                        WHERE wo.deadline IS NOT NULL
                          AND (
                              (wo.status = 'completed' AND wo.completed_at > wo.deadline)
                              OR (wo.status IN ('pending', 'in_progress') AND wo.deadline < (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0))
                          )
                    )::INTEGER AS timeout,
                    ROUND(
                        AVG(
                            CASE
                                WHEN wo.status = 'completed' AND wo.completed_at IS NOT NULL THEN
                                    EXTRACT(EPOCH FROM (wo.completed_at - wo.created_at)) / 3600.0
                                ELSE NULL
                            END
                        )::numeric,
                        2
                    ) AS avg_completion_hours
                FROM work_orders wo
                JOIN order_stages os ON os.id = wo.stage_id
                WHERE {where_sql}
                GROUP BY os.stage_type
                ORDER BY CASE os.stage_type
                    WHEN 'picking' THEN 1
                    WHEN 'staging' THEN 2
                    WHEN 'shipping' THEN 3
                    ELSE 99
                END
                """
            ),
            params,
        )

        warehouse_result = await self.session.execute(
            text(
                f"""
                SELECT
                    wo.warehouse_id,
                    w.name AS warehouse_name,
                    COUNT(*)::INTEGER AS total,
                    COUNT(*) FILTER (WHERE wo.status = 'completed')::INTEGER AS completed,
                    ROUND(
                        AVG(
                            CASE
                                WHEN wo.status = 'completed' AND wo.completed_at IS NOT NULL THEN
                                    EXTRACT(EPOCH FROM (wo.completed_at - wo.created_at)) / 3600.0
                                ELSE NULL
                            END
                        )::numeric,
                        2
                    ) AS avg_completion_hours
                FROM work_orders wo
                JOIN warehouses w ON w.id = wo.warehouse_id
                WHERE {where_sql}
                GROUP BY wo.warehouse_id, w.name
                ORDER BY completed DESC, total DESC, wo.warehouse_id ASC
                """
            ),
            params,
        )

        dispatcher_result = await self.session.execute(
            text(
                f"""
                SELECT
                    wo.dispatcher_id,
                    u.username AS dispatcher_name,
                    COUNT(*)::INTEGER AS total,
                    COUNT(*) FILTER (WHERE wo.status = 'completed')::INTEGER AS completed,
                    ROUND(
                        AVG(
                            CASE
                                WHEN wo.status = 'completed' AND wo.completed_at IS NOT NULL THEN
                                    EXTRACT(EPOCH FROM (wo.completed_at - wo.created_at)) / 3600.0
                                ELSE NULL
                            END
                        )::numeric,
                        2
                    ) AS avg_completion_hours
                FROM work_orders wo
                JOIN users u ON u.id = wo.dispatcher_id
                WHERE {where_sql}
                GROUP BY wo.dispatcher_id, u.username
                ORDER BY completed DESC, total DESC, wo.dispatcher_id ASC
                """
            ),
            params,
        )

        trend_result = await self.session.execute(
            text(
                f"""
                SELECT
                    DATE(wo.created_at) AS day,
                    COUNT(*)::INTEGER AS total,
                    COUNT(*) FILTER (WHERE wo.status = 'completed')::INTEGER AS completed,
                    COUNT(*) FILTER (
                        WHERE wo.deadline IS NOT NULL
                          AND (
                              (wo.status = 'completed' AND wo.completed_at > wo.deadline)
                              OR (wo.status IN ('pending', 'in_progress') AND wo.deadline < (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0))
                          )
                    )::INTEGER AS timeout
                FROM work_orders wo
                WHERE {where_sql}
                GROUP BY DATE(wo.created_at)
                ORDER BY DATE(wo.created_at) ASC
                """
            ),
            params,
        )

        raw_stats = {
            "summary": {
                "total_work_orders": total_work_orders,
                "completed_work_orders": completed_work_orders,
                "timeout_work_orders": timeout_work_orders,
                "completion_rate": completion_rate,
                "timeout_rate": timeout_rate,
                "avg_completion_hours": avg_completion_hours,
            },
            "by_stage": [dict(row) for row in stage_result.mappings().all()],
            "by_warehouse": [dict(row) for row in warehouse_result.mappings().all()],
            "by_dispatcher": [dict(row) for row in dispatcher_result.mappings().all()],
            "daily_trend": [dict(row) for row in trend_result.mappings().all()],
        }
        return self._to_json_safe(raw_stats)

    async def _try_generate_report_markdown_with_llm(self, *, stats_json: dict, llm_trace: list[dict]) -> str:
        if not BailianProvider.is_enabled():
            self._append_report_trace(llm_trace, model=None, status="provider_unavailable", detail="未配置 DASHSCOPE_API_KEY")
            raise RuntimeError("未配置 DASHSCOPE_API_KEY")

        if self._report_skill_context_cache is None:
            self._report_skill_context_cache = AgentSkillLoader.load_skills(list(self._REPORT_SKILL_FILES))

        system_prompt = (
            "你是 WMS 管理端效率分析助手。\n"
            "你只可基于输入的结构化统计事实生成结论，不得编造任何未提供的数据。\n"
            "必须输出 Markdown，结构固定为：执行摘要、关键指标、阶段分析、仓库分析、调度员分析、风险与建议。\n"
            "每条建议要可执行，避免空泛描述。\n\n"
            f"{self._report_skill_context_cache}"
        )
        user_prompt = (
            "请根据以下统计数据生成管理层可读的效率分析报告（Markdown）。\n"
            "要求使用简洁中文并突出异常、趋势和改进建议。\n\n"
            f"{json.dumps(stats_json, ensure_ascii=False, indent=2)}"
        )

        model_candidates = self._build_report_model_candidates()
        if not model_candidates:
            self._append_report_trace(llm_trace, model=None, status="no_model_candidates", detail="未配置可用模型")
            raise RuntimeError("未配置可用模型")

        for model_name in model_candidates:
            self._append_report_trace(llm_trace, model=model_name, status="attempt")
            try:
                markdown = await BailianProvider.chat_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=model_name,
                    temperature=0.2,
                )
                self._append_report_trace(llm_trace, model=model_name, status="success")
                return markdown
            except Exception as exc:
                self._append_report_trace(llm_trace, model=model_name, status="failed", detail=str(exc))

        raise RuntimeError("报表分析模型调用失败")

    async def generate_efficiency_report(
        self,
        *,
        generated_by: int,
        period_start: date,
        period_end: date,
        warehouse_id: int | None,
        include_llm_analysis: bool,
    ) -> AdminReportResponse:
        if period_end < period_start:
            raise HTTPException(status_code=400, detail="period_end must be greater than or equal to period_start")

        warehouse_name = await self._resolve_report_warehouse_name(warehouse_id)
        stats_json = await self._build_efficiency_stats(
            period_start=period_start,
            period_end=period_end,
            warehouse_id=warehouse_id,
        )
        stats_json["warehouse_id"] = warehouse_id
        stats_json["warehouse_name"] = warehouse_name

        llm_trace: list[dict] = []
        content = ""
        if include_llm_analysis:
            try:
                content = await self._try_generate_report_markdown_with_llm(stats_json=stats_json, llm_trace=llm_trace)
            except Exception as exc:
                llm_trace.append(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "model": None,
                        "status": "fallback",
                        "detail": str(exc),
                    }
                )

        if not content:
            summary = stats_json.get("summary", {})
            content = (
                "## 执行摘要\n"
                f"- 统计周期：{period_start} 至 {period_end}\n"
                f"- 工单总量：{summary.get('total_work_orders', 0)}\n"
                f"- 完成率：{summary.get('completion_rate', 0)}%\n"
                f"- 超时率：{summary.get('timeout_rate', 0)}%\n"
                f"- 平均完成耗时：{summary.get('avg_completion_hours', 0)} 小时\n\n"
                "## 说明\n"
                "本次 AI 分析降级为结构化统计摘要，请稍后重试以获取完整智能分析。"
            )

        insert_result = await self.session.execute(
            text(
                """
                INSERT INTO reports (
                    generated_by,
                    target_user_id,
                    period_start,
                    period_end,
                    stats_json,
                    content,
                    created_at
                ) VALUES (
                    :generated_by,
                    NULL,
                    :period_start,
                    :period_end,
                    CAST(:stats_json AS JSONB),
                    :content,
                    (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                )
                RETURNING id, generated_by, target_user_id, period_start, period_end, stats_json, content, created_at
                """
            ),
            {
                "generated_by": generated_by,
                "period_start": period_start,
                "period_end": period_end,
                "stats_json": json.dumps(stats_json, ensure_ascii=False),
                "content": content,
            },
        )
        await self.session.commit()

        row = insert_result.mappings().first()
        if not row:
            raise HTTPException(status_code=500, detail="Failed to create report")

        stats = row["stats_json"] or {}
        if isinstance(stats, str):
            try:
                stats = json.loads(stats)
            except json.JSONDecodeError:
                stats = {}

        return AdminReportResponse(
            id=int(row["id"]),
            generated_by=int(row["generated_by"]),
            target_user_id=row.get("target_user_id"),
            period_start=row["period_start"],
            period_end=row["period_end"],
            warehouse_id=warehouse_id,
            warehouse_name=warehouse_name,
            stats_json=stats,
            content=str(row["content"] or ""),
            content_format="markdown",
            llm_workflow_trace=llm_trace,
            created_at=row["created_at"],
        )

    async def list_reports(
        self,
        *,
        page: int,
        page_size: int,
        period_start: date | None,
        period_end: date | None,
        warehouse_id: int | None,
    ) -> dict:
        where_clauses = ["1=1"]
        params: dict[str, object] = {}

        if period_start is not None:
            where_clauses.append("r.period_start >= :period_start")
            params["period_start"] = period_start
        if period_end is not None:
            where_clauses.append("r.period_end <= :period_end")
            params["period_end"] = period_end
        if warehouse_id is not None:
            where_clauses.append("(r.stats_json ->> 'warehouse_id')::INT = :warehouse_id")
            params["warehouse_id"] = warehouse_id

        where_sql = " AND ".join(where_clauses)

        count_result = await self.session.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM reports r
                WHERE {where_sql}
                """
            ),
            params,
        )
        total = int(count_result.scalar_one() or 0)

        list_result = await self.session.execute(
            text(
                f"""
                SELECT
                    r.id,
                    r.generated_by,
                    u.username AS generated_by_name,
                    r.period_start,
                    r.period_end,
                    (r.stats_json ->> 'warehouse_id')::INT AS warehouse_id,
                    (r.stats_json ->> 'warehouse_name') AS warehouse_name,
                    r.created_at
                FROM reports r
                LEFT JOIN users u ON u.id = r.generated_by
                WHERE {where_sql}
                ORDER BY r.id DESC
                OFFSET :offset
                LIMIT :limit
                """
            ),
            {
                **params,
                "offset": (page - 1) * page_size,
                "limit": page_size,
            },
        )

        return {
            "items": [dict(row) for row in list_result.mappings().all()],
            "total": total,
        }

    async def get_report_detail(self, *, report_id: int) -> AdminReportResponse:
        detail_result = await self.session.execute(
            text(
                """
                SELECT
                    r.id,
                    r.generated_by,
                    r.target_user_id,
                    r.period_start,
                    r.period_end,
                    r.stats_json,
                    r.content,
                    r.created_at
                FROM reports r
                WHERE r.id = :report_id
                LIMIT 1
                """
            ),
            {"report_id": report_id},
        )
        row = detail_result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Report not found")

        stats = row["stats_json"] or {}
        if isinstance(stats, str):
            try:
                stats = json.loads(stats)
            except json.JSONDecodeError:
                stats = {}

        return AdminReportResponse(
            id=int(row["id"]),
            generated_by=int(row["generated_by"]),
            target_user_id=row.get("target_user_id"),
            period_start=row["period_start"],
            period_end=row["period_end"],
            warehouse_id=stats.get("warehouse_id"),
            warehouse_name=stats.get("warehouse_name"),
            stats_json=stats,
            content=str(row["content"] or ""),
            content_format="markdown",
            llm_workflow_trace=[],
            created_at=row["created_at"],
        )
