import { describe, expect, it } from 'vitest';
import { generatedRoutes } from './routes';

describe('OAuth routes', () => {
  it('keeps the consent page separate from the parameterized legacy installation page', () => {
    const consent = generatedRoutes.find(route => route.name === 'oauth2');
    const installation = generatedRoutes.find(route => route.name === 'oauth2-install');
    expect(consent?.path).toBe('/oauth2/authorize');
    expect(consent?.component).toContain('view.oauth2');
    expect(consent && 'children' in consent).toBe(false);
    expect(installation?.path).toBe('/oauth2/install/:installId');
  });
});
