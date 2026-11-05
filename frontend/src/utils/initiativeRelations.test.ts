import { describe, expect, it } from 'vitest';
import {
  formatRelationBadge,
  groupRelationItems,
  relationDirectionLabel,
  type InitiativeRelationItem
} from './initiativeRelations';

describe('E65 initiativeRelations', () => {
  it('labels direction by type', () => {
    expect(relationDirectionLabel('blocks', 'outgoing')).toBe('阻塞');
    expect(relationDirectionLabel('blocks', 'incoming')).toBe('被阻塞');
    expect(relationDirectionLabel('is_blocked_by', 'outgoing')).toBe('被阻塞');
    expect(relationDirectionLabel('is_blocked_by', 'incoming')).toBe('阻塞');
    expect(relationDirectionLabel('relates_to', 'outgoing')).toBe('相关');
    expect(relationDirectionLabel('relates_to', 'incoming')).toBe('相关');
  });

  it('groups items into blocks / blockedBy / relatesTo', () => {
    const items: InitiativeRelationItem[] = [
      {
        id: '1',
        type: 'blocks',
        direction: 'outgoing',
        initiative: { id: 'b', name: 'B', status: 'active' }
      },
      {
        id: '2',
        type: 'blocks',
        direction: 'incoming',
        initiative: { id: 'c', name: 'C', status: 'active' }
      },
      {
        id: '3',
        type: 'is_blocked_by',
        direction: 'outgoing',
        initiative: { id: 'd', name: 'D', status: 'planned' }
      },
      {
        id: '4',
        type: 'relates_to',
        direction: 'outgoing',
        initiative: { id: 'e', name: 'E', status: 'active' }
      }
    ];
    const g = groupRelationItems(items);
    expect(g.blocks.map(i => i.id)).toEqual(['1']);
    expect(g.blockedBy.map(i => i.id).sort()).toEqual(['2', '3']);
    expect(g.relatesTo.map(i => i.id)).toEqual(['4']);
  });

  it('formats optional list badge', () => {
    expect(formatRelationBadge(null)).toBeNull();
    expect(formatRelationBadge({ blocksCount: 0, blockedByCount: 0 })).toBeNull();
    expect(formatRelationBadge({ blocksCount: 2, blockedByCount: 1 })).toBe('阻塞 2 · 被阻 1');
    expect(formatRelationBadge({ blocksCount: 0, blockedByCount: 3 })).toBe('被阻 3');
  });
});
