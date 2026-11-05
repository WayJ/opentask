declare namespace Api {
  /**
   * namespace Project
   *
   * backend api module: "projects"
   */
  namespace Project {
    /** Project model */
    interface Project {
      /** Project id (UUID) */
      id: string;
      /** Project name (unique) */
      name: string;
      /** Project description */
      description: string | null;
      /** Is active */
      is_active: boolean;
      /** Created at */
      created_at: string;
      /** Updated at */
      updated_at: string;
      /** Project start (E8-S1) */
      starts_at?: string | null;
      /** Project target date (E8-S1) */
      target_date?: string | null;
      /** Latest health (E8-S2) */
      health_status?: 'on_track' | 'at_risk' | 'off_track' | string | null;
      health_note?: string | null;
      health_updated_at?: string | null;
      health_updated_by?: string | null;
    }

    /** Create project params */
    interface CreateProject {
      name: string;
      description?: string;
      /** E72 project template id */
      template_id?: string;
      starts_at?: string | null;
    }

    /** Update project params */
    interface UpdateProject {
      name?: string;
      description?: string;
      starts_at?: string | null;
      target_date?: string | null;
    }

    /** Milestone (E8-S1) */
    interface Milestone {
      id: string;
      workspace_id: string;
      project_id: string;
      name: string;
      description?: string | null;
      target_date?: string | null;
      status: 'planned' | 'done' | string;
      position: number;
      created_at: string;
      updated_at: string;
    }

    interface CreateMilestone {
      name: string;
      description?: string | null;
      target_date?: string | null;
      status?: string;
      position?: number;
    }

    interface UpdateMilestone {
      name?: string;
      description?: string | null;
      target_date?: string | null;
      status?: string;
      position?: number;
    }

    type HealthStatus = 'on_track' | 'at_risk' | 'off_track';

    interface HealthUpdate {
      id: string;
      workspace_id: string;
      project_id: string;
      status: HealthStatus | string;
      note?: string | null;
      actor_user_id: string;
      created_at: string;
    }

    interface HealthPayload {
      latest: {
        status: HealthStatus | string;
        note?: string | null;
        actor_user_id?: string | null;
        created_at?: string | null;
        project_id?: string;
      } | null;
      history: HealthUpdate[];
    }

    interface ProjectWatcher {
      id: string;
      workspace_id: string;
      project_id: string;
      user_id: string;
      created_at: string;
    }

    interface TimelineData {
      project: {
        id: string;
        name: string;
        starts_at?: string | null;
        target_date?: string | null;
        health_status?: string | null;
        health_note?: string | null;
      };
      milestones: Milestone[];
      issues: Array<{
        id: string;
        title: string;
        issue_code?: string | null;
        due_date: string;
        status?: string;
        milestone_id?: string | null;
      }>;
    }

    /** Repo config model */
    interface RepoConfig {
      id: number;
      project_id: string;
      name: string;
      url: string;
      main_branch: string;
      created_at: string;
      updated_at: string;
    }

    /** Create repo config params */
    interface CreateRepoConfig {
      project_id: string;
      name: string;
      url: string;
      main_branch?: string;
    }
  }

  /**
   * namespace Requirement
   *
   * backend api module: "requirements"
   */
  namespace Requirement {
    /** Requirement status enum */
    type RequirementStatus =
      | 'draft'
      | 'clarifying'
      | 'spec_ready'
      | 'designing'
      | 'coding'
      | 'reviewing'
      | 'testing'
      | 'released'
      | 'archived';

    /** Priority enum */
    type Priority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

    /** Requirement model */
    interface Requirement {
      id: string;
      code: string;
      title: string;
      description: string | null;
      status: RequirementStatus;
      priority: Priority | null;
      tags: string[];
      created_at: string;
      updated_at: string;
      created_by: string | null;
      assignee_id: string | null;
      project_id: string | null;
      /** 关联的设计文档 */
      documents: Document.Summary[];
    }

    /** 文档摘要（用于嵌入到其他实体响应中） */
    namespace Document {
      interface Summary {
        id: string;
        title: string;
        status: string;
        version: number;
        created_at: string;
        updated_at: string;
      }
    }

    /** Create requirement params */
    interface CreateRequirement {
      title: string;
      project_id: string;
      description?: string;
      priority?: Priority;
      tags?: string[];
      created_by?: string;
    }

    /** Update requirement params */
    interface UpdateRequirement {
      title?: string;
      description?: string;
      status?: RequirementStatus;
      priority?: Priority;
      tags?: string[];
      assignee_id?: string;
      project_id?: string;
    }

    /** Requirement list response */
    interface RequirementList {
      data: Requirement[];
      total: number;
      page: number;
      page_size: number;
    }

    /** Event model */
    interface Event {
      id: string;
      requirement_id: string;
      type: string;
      data: Record<string, any>;
      actor: string | null;
      reasoning: string | null;
      timestamp: string;
      snapshot: Record<string, any> | null;
    }

    /** Requirement with events */
    interface RequirementWithEvents extends Requirement {
      events: Event[];
    }

    /** Timeline response */
    interface Timeline {
      requirement_id: string;
      events: Event[];
      time_in_states: Record<string, number>;
    }

    /** Assign request */
    interface AssignRequest {
      assignee_id: string;
    }

    /** Requirement statistics */
    interface Statistics {
      total: number;
      by_status: Record<string, number>;
      by_priority: Record<string, number>;
    }
  }
}
