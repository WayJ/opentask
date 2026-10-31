/** Dashboard 相关类型定义 */

declare namespace Api {
  namespace Dashboard {
    /** 状态分布 */
    interface StatusDistribution {
      status: string;
      count: number;
    }

    /** 类型分布 */
    interface TypeDistribution {
      type: string;
      count: number;
    }

    /** 优先级分布 */
    interface PriorityDistribution {
      priority: string;
      count: number;
    }

    /** 趋势数据点 */
    interface TrendDataPoint {
      date: string;
      requirement_count: number;
      issue_count: number;
    }

    /** 统计卡片数据 */
    interface StatCard {
      total: number;
      open_count: number;
      in_progress_count: number;
      completed_count: number;
    }

    /** 最近动态项 */
    interface RecentActivityItem {
      id: string;
      type: 'requirement' | 'issue';
      code: string;
      title: string;
      status: string;
      updated_at: string;
    }

    /** 看板总览数据 */
    interface DashboardOverview {
      requirements: StatCard;
      issues: StatCard;
      requirement_by_status: StatusDistribution[];
      requirement_by_priority: PriorityDistribution[];
      issue_by_status: StatusDistribution[];
      issue_by_type: TypeDistribution[];
      issue_by_priority: PriorityDistribution[];
      trend: TrendDataPoint[];
      recent_activities: RecentActivityItem[];
    }

    /** 看板总览响应 */
    interface DashboardOverviewResponse {
      code: number;
      message: string;
      data: DashboardOverview;
      timestamp: number;
    }
  }
}
