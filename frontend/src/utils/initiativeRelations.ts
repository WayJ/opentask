/** E65: Initiative relation helpers (flatten / direction labels). */

export type InitiativeRelationType = 'blocks' | 'is_blocked_by' | 'relates_to';
export type InitiativeRelationDirection = 'outgoing' | 'incoming';

export interface InitiativeRelationPeer {
  id: string;
  name: string;
  status: string;
}

export interface InitiativeRelationItem {
  id: string;
  type: InitiativeRelationType;
  direction: InitiativeRelationDirection;
  initiative: InitiativeRelationPeer;
}

export interface GroupedInitiativeRelations {
  blocks: InitiativeRelationItem[];
  blockedBy: InitiativeRelationItem[];
  relatesTo: InitiativeRelationItem[];
}

/** Semantic label from stored type + direction (Q2a literal store, bidirectional view). */
export function relationDirectionLabel(
  type: InitiativeRelationType,
  direction: InitiativeRelationDirection
): string {
  if (type === 'relates_to') return '相关';
  if (type === 'blocks') {
    return direction === 'outgoing' ? '阻塞' : '被阻塞';
  }
  // is_blocked_by
  return direction === 'outgoing' ? '被阻塞' : '阻塞';
}

export function isBlockingEdge(
  type: InitiativeRelationType,
  direction: InitiativeRelationDirection
): boolean {
  return (
    (type === 'blocks' && direction === 'outgoing') ||
    (type === 'is_blocked_by' && direction === 'incoming')
  );
}

export function isBlockedByEdge(
  type: InitiativeRelationType,
  direction: InitiativeRelationDirection
): boolean {
  return (
    (type === 'blocks' && direction === 'incoming') ||
    (type === 'is_blocked_by' && direction === 'outgoing')
  );
}

export function groupRelationItems(items: InitiativeRelationItem[]): GroupedInitiativeRelations {
  const blocks: InitiativeRelationItem[] = [];
  const blockedBy: InitiativeRelationItem[] = [];
  const relatesTo: InitiativeRelationItem[] = [];
  for (const item of items) {
    if (item.type === 'relates_to') {
      relatesTo.push(item);
    } else if (isBlockingEdge(item.type, item.direction)) {
      blocks.push(item);
    } else if (isBlockedByEdge(item.type, item.direction)) {
      blockedBy.push(item);
    }
  }
  return { blocks, blockedBy, relatesTo };
}

export function formatRelationBadge(counts?: {
  blocksCount?: number;
  blockedByCount?: number;
} | null): string | null {
  if (!counts) return null;
  const b = counts.blocksCount ?? 0;
  const bb = counts.blockedByCount ?? 0;
  if (b === 0 && bb === 0) return null;
  const parts: string[] = [];
  if (b > 0) parts.push(`阻塞 ${b}`);
  if (bb > 0) parts.push(`被阻 ${bb}`);
  return parts.join(' · ');
}
