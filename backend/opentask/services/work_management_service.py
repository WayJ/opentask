"""工作管理服务层"""
from datetime import date, datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import and_, or_, select

from opentask.models.work_management import (
    RdGroup, RdGroupMember, CostProject, WorkAssignment,
    WorkFeedback, WorkAssignmentAttachment
)
from opentask.schemas.work_management import (
    RdGroupCreate, RdGroupUpdate,
    CostProjectCreate, CostProjectUpdate,
    WorkAssignmentCreate, WorkAssignmentUpdate,
    WorkFeedbackCreate
)


class WorkManagementService:
    """工作管理服务"""

    def __init__(self, db):
        self.db = db

    # ============ 研发组管理 ============

    async def create_rd_group(self, name: str, director_id: str, leader_id: str) -> dict:
        """创建研发组"""
        group = RdGroup(
            name=name,
            director_id=director_id,
            leader_id=leader_id
        )
        self.db.add(group)
        await self.db.commit()

        # 返回dict而不是模型对象
        return {
            "id": group.id,
            "name": group.name,
            "director_id": group.director_id,
            "leader_id": group.leader_id,
            "status": group.status,
            "created_at": group.created_at.isoformat() if group.created_at else None,
            "updated_at": group.updated_at.isoformat() if group.updated_at else None
        }

    async def get_rd_groups(self, director_id: Optional[str] = None) -> List[dict]:
        """获取研发组列表"""
        query = select(RdGroup)
        if director_id:
            query = query.where(RdGroup.director_id == director_id)
        result = await self.db.execute(query)
        groups = result.scalars().all()

        # 手动构造dict，避免relationship序列化问题
        return [
            {
                "id": g.id,
                "name": g.name,
                "director_id": g.director_id,
                "leader_id": g.leader_id,
                "status": g.status,
                "created_at": g.created_at.isoformat() if g.created_at else None,
                "updated_at": g.updated_at.isoformat() if g.updated_at else None
            }
            for g in groups
        ]

    async def get_rd_group(self, group_id: str) -> Optional[dict]:
        """获取研发组详情"""
        group = await self.db.get(RdGroup, group_id)
        if not group:
            return None

        # 获取成员信息
        result = await self.db.execute(
            select(RdGroupMember).where(RdGroupMember.group_id == group_id)
        )
        members = result.scalars().all()

        return {
            "id": group.id,
            "name": group.name,
            "director_id": group.director_id,
            "leader_id": group.leader_id,
            "status": group.status,
            "created_at": group.created_at.isoformat() if group.created_at else None,
            "updated_at": group.updated_at.isoformat() if group.updated_at else None,
            "members": [
                {
                    "id": m.id,
                    "user_id": m.user_id,
                    "role": m.role,
                    "joined_at": m.joined_at.isoformat() if m.joined_at else None
                }
                for m in members
            ]
        }

    async def add_group_member(self, group_id: str, user_id: str, role: str = "member") -> RdGroupMember:
        """添加组成员"""
        member = RdGroupMember(
            group_id=group_id,
            user_id=user_id,
            role=role
        )
        self.db.add(member)
        await self.db.commit()
        return member

    async def remove_group_member(self, group_id: str, user_id: str) -> bool:
        """移除组成员"""
        result = await self.db.execute(
            select(RdGroupMember).where(
                and_(RdGroupMember.group_id == group_id, RdGroupMember.user_id == user_id)
            )
        )
        member = result.scalar_one_or_none()

        if member:
            await self.db.delete(member)
            await self.db.commit()
            return True
        return False

    # ============ 成本项目管理 ============

    async def create_cost_project(self, project_data: CostProjectCreate) -> CostProject:
        """创建成本项目"""
        project = CostProject(**project_data.model_dump())
        self.db.add(project)
        await self.db.commit()
        return project

    async def get_cost_projects(self, manager_id: Optional[str] = None) -> List[CostProject]:
        """获取成本项目列表"""
        query = select(CostProject)
        if manager_id:
            query = query.where(CostProject.manager_id == manager_id)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_cost_project_with_stats(self, project_id: str) -> Optional[Dict[str, Any]]:
        """获取成本项目详情（含统计）"""
        project = await self.db.get(CostProject, project_id)
        if not project:
            return None

        # 获取项目下所有工作
        result = await self.db.execute(
            select(WorkAssignment).where(WorkAssignment.cost_project_id == project_id)
        )
        assignments = result.scalars().all()

        total_hours = sum(float(a.estimated_hours) for a in assignments)
        completed_assignments = [a for a in assignments if a.status == "completed"]
        completed_hours = sum(float(a.estimated_hours) for a in completed_assignments)
        high_quality_count = sum(1 for a in completed_assignments if a.quality == "high")

        return {
            "project": project,
            "stats": {
                "total_estimated_hours": total_hours,
                "completed_hours": completed_hours,
                "completion_rate": float(completed_hours / total_hours * 100) if total_hours > 0 else 0,
                "high_quality_rate": float(high_quality_count / len(completed_assignments) * 100) if completed_assignments else 0
            }
        }

    # ============ 工作安排 ============

    async def create_work_assignment(self, assignment_data: WorkAssignmentCreate, assigner_id: str) -> WorkAssignment:
        """创建工作安排"""
        data = assignment_data.model_dump()
        data["assigner_id"] = assigner_id
        assignment = WorkAssignment(**data)
        self.db.add(assignment)
        await self.db.commit()
        return assignment

    async def get_work_assignments(
        self,
        assignee_id: Optional[str] = None,
        group_id: Optional[str] = None,
        week_start: Optional[date] = None
    ) -> List[WorkAssignment]:
        """获取工作安排列表"""
        query = select(WorkAssignment)

        if assignee_id:
            query = query.where(WorkAssignment.assignee_id == assignee_id)
        if group_id:
            query = query.where(WorkAssignment.group_id == group_id)
        if week_start:
            query = query.where(WorkAssignment.week_start == week_start)

        result = await self.db.execute(query)
        return result.scalars().all()

    def check_overdue(self, assignment: WorkAssignment) -> Tuple[bool, int]:
        """检查工作是否延期"""
        if assignment.status == "completed":
            return False, 0

        today = date.today()
        if assignment.deadline < today:
            overdue_days = (today - assignment.deadline).days
            return True, overdue_days

        return False, 0

    # ============ 工作反馈 ============

    async def create_work_feedback(self, feedback_data: WorkFeedbackCreate, user_id: str) -> WorkFeedback:
        """创建工作反馈"""
        data = feedback_data.model_dump()
        data["user_id"] = user_id
        feedback = WorkFeedback(**data)
        self.db.add(feedback)

        # 如果反馈的是计划内工作，更新工作状态
        if feedback.assignment_id and feedback.status:
            assignment = await self.db.get(WorkAssignment, feedback.assignment_id)
            if assignment:
                assignment.status = feedback.status

                # 质量评估逻辑
                if feedback.status == "completed":
                    result = await self.db.execute(
                        select(WorkAssignmentAttachment).where(
                            WorkAssignmentAttachment.assignment_id == feedback.assignment_id
                        )
                    )
                    has_attachments = result.first() is not None

                    assignment.quality = "high" if has_attachments else "low"

        await self.db.commit()
        return feedback

    # ============ 计划外工作抓取 ============

    async def get_unplanned_work(self, user_id: str, week_start: date) -> Dict[str, List[Dict[str, Any]]]:
        """获取计划外工作（自动抓取）"""
        # 计算周的起止日期
        week_end = week_start + timedelta(days=6)

        result = {
            "resolved_issues": [],
            "created_issues": [],
            "completed_reqs": [],
            "created_reqs": []
        }

        # 从 issue 表抓取
        try:
            from opentask.models.issue.model import Issue

            # 本周解决的 issue
            resolved_result = await self.db.execute(
                select(Issue).where(
                    and_(
                        Issue.assignee_id == user_id,
                        Issue.status.in_(["resolved", "closed"]),
                        Issue.updated_at >= week_start,
                        Issue.updated_at <= week_end
                    )
                )
            )
            resolved_issues = resolved_result.scalars().all()
            result["resolved_issues"] = [{"id": i.id, "title": i.title, "type": "issue_resolved"} for i in resolved_issues]

            # 本周创建的 issue
            created_result = await self.db.execute(
                select(Issue).where(
                    and_(
                        Issue.reporter_id == user_id,
                        Issue.created_at >= week_start,
                        Issue.created_at <= week_end
                    )
                )
            )
            created_issues = created_result.scalars().all()
            result["created_issues"] = [{"id": i.id, "title": i.title, "type": "issue_created"} for i in created_issues]

        except ImportError:
            pass

        # 从 requirement 表抓取
        try:
            from opentask.models.requirement.model import Requirement

            # 本周完成的 requirement
            completed_result = await self.db.execute(
                select(Requirement).where(
                    and_(
                        Requirement.assignee_id == user_id,
                        Requirement.status == "completed",
                        Requirement.updated_at >= week_start,
                        Requirement.updated_at <= week_end
                    )
                )
            )
            completed_reqs = completed_result.scalars().all()
            result["completed_reqs"] = [{"id": r.id, "title": r.title, "type": "req_completed"} for r in completed_reqs]

            # 本周创建的 requirement
            created_result = await self.db.execute(
                select(Requirement).where(
                    and_(
                        Requirement.created_by == user_id,
                        Requirement.created_at >= week_start,
                        Requirement.created_at <= week_end
                    )
                )
            )
            created_reqs = created_result.scalars().all()
            result["created_reqs"] = [{"id": r.id, "title": r.title, "type": "req_created"} for r in created_reqs]

        except ImportError:
            pass

        return result

    # ============ 附件管理 ============

    async def add_attachment(
        self,
        assignment_id: str,
        file_name: str,
        file_path: str,
        file_size: int,
        uploaded_by: str
    ) -> WorkAssignmentAttachment:
        """添加附件"""
        attachment = WorkAssignmentAttachment(
            assignment_id=assignment_id,
            file_name=file_name,
            file_path=file_path,
            file_size=file_size,
            uploaded_by=uploaded_by
        )
        self.db.add(attachment)

        # 上传附件后，更新质量为高
        assignment = await self.db.get(WorkAssignment, assignment_id)
        if assignment and assignment.quality == "low":
            assignment.quality = "high"

        await self.db.commit()
        return attachment
