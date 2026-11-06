import { describe, expect, it } from 'vitest';
import { requirementSurfaceRedirect, workspaceGateRedirect } from '../surface';

describe('requirementSurfaceRedirect', () => {
  it('sends requirement pages to the issue list', () => {
    expect(requirementSurfaceRedirect('workflow_requirements')).toEqual({ name: 'issue_list' });
    expect(requirementSurfaceRedirect('workflow_requirement-detail')).toEqual({ name: 'issue_list' });
  });

  it('leaves customers and public routes alone', () => {
    expect(requirementSurfaceRedirect('customers')).toBeNull();
    expect(requirementSurfaceRedirect('public-form')).toBeNull();
    expect(requirementSurfaceRedirect('issue_list')).toBeNull();
  });
});

describe('workspaceGateRedirect', () => {
  it('does not pull public routes into onboarding', () => {
    for (const name of ['login', 'public-form', 'public-request-status', 'invite']) {
      expect(
        workspaceGateRedirect({ name, meta: { constant: true } }, { isLogin: true, gate: 'onboarding' })
      ).toBeNull();
    }
  });

  it('sends a logged-in user without a workspace to onboarding', () => {
    expect(workspaceGateRedirect({ name: 'issue_list', meta: {} }, { isLogin: true, gate: 'onboarding' })).toEqual({
      name: 'workspace-onboarding'
    });
  });

  it('does not loop once the user is already on onboarding', () => {
    expect(
      workspaceGateRedirect({ name: 'workspace-onboarding', meta: {} }, { isLogin: true, gate: 'onboarding' })
    ).toBeNull();
  });

  it('leaves onboarding for the root route after a workspace is ready', () => {
    expect(workspaceGateRedirect({ name: 'workspace-onboarding', meta: {} }, { isLogin: true, gate: 'ready' })).toEqual(
      { name: 'root' }
    );
  });

  it('sends a logged-out visitor away from onboarding to login', () => {
    expect(
      workspaceGateRedirect({ name: 'workspace-onboarding', meta: {} }, { isLogin: false, gate: 'pending' })
    ).toEqual({ name: 'login' });
  });
});
