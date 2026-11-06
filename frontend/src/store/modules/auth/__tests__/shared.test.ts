import { beforeEach, describe, expect, it } from 'vitest';
import { localStg } from '@/utils/storage';
import { clearAuthStorage } from '../shared';

describe('clearAuthStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('removes the token and the workspace selection together', () => {
    localStg.set('token', 't');
    localStg.set('refreshToken', 'r');
    localStg.set('workspaceId', 'foreign-workspace');

    clearAuthStorage();

    expect(localStg.get('token')).toBeNull();
    expect(localStg.get('refreshToken')).toBeNull();
    expect(localStg.get('workspaceId')).toBeNull();
  });
});
