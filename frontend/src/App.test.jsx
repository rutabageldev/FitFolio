import React from 'react';
import { describe, expect, it } from 'vitest';
import { renderToString } from 'react-dom/server';
import App from './App.jsx';

describe('App landing page', () => {
  it('renders the core hero content', () => {
    const html = renderToString(<App />);
    expect(html).toContain('Fitfolio');
    expect(html).toContain('training HQ for every rep you coach');
    expect(html).toContain('Join the staging waitlist');
  });
});
