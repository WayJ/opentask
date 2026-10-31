declare namespace Api {
  /**
   * namespace Task
   *
   * backend api module: "tasks"
   */
  namespace Task {
    /** Task status enum */
    type TaskStatus = 'PENDING' | 'ASSIGNED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'BLOCKED' | 'CANCELLED';

    /** Task type enum */
    type TaskType = 'DESIGN' | 'IMPLEMENT' | 'TEST' | 'REVIEW' | 'DEPLOY' | 'DOCUMENT' | 'RESEARCH';

    /** Task model */
    interface Task {
      id: string;
      requirement_id: string;
      parent_id: string | null;
      code: string | null;
      agent_task_id: string | null; // 关联的 Mission Center 任务 ID
      title: string;
      description: string | null;
      task_type: TaskType;
      status: TaskStatus;
      priority: number;
      assigned_to: string | null;
      started_at: string | null;
      completed_at: string | null;
      input_data: Record<string, any> | null;
      output_data: Record<string, any> | null;
      artifacts: Record<string, any> | null;
      error_message: string | null;
      retry_count: number;
      created_at: string;
      updated_at: string;
      order: number;
      dependencies: string[];
      dependents: string[];
      children: Task[];
    }

    /** Create task params */
    interface CreateTask {
      requirement_id: string;
      title: string;
      description?: string;
      task_type?: TaskType;
      priority?: number;
      assigned_to?: string;
      parent_id?: string;
      input_data?: Record<string, any>;
      depends_on?: string[];
      order?: number;
    }

    /** Update task params */
    interface UpdateTask {
      title?: string;
      description?: string;
      status?: TaskStatus;
      priority?: number;
      assigned_to?: string;
      parent_id?: string;
      output_data?: Record<string, any>;
      artifacts?: Record<string, any>;
      error_message?: string;
      order?: number;
    }

    /** Task list response - following API specification */
    interface TaskList {
      rows: Task[];
      total: number;
      current: number;
      pageSize: number;
      totalPages: number;
    }
  }
}
