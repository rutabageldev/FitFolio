export default {
  title: 'Foundations/Radius & Elevation',
};

export const Samples = () => (
  <div
    style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(220px,1fr))',
      gap: '1rem',
    }}
  >
    <div
      style={{
        borderRadius: 'var(--radius-1)',
        boxShadow: 'var(--elevation-1)',
        padding: '1rem',
        background: 'var(--color-surface)',
      }}
    >
      radius-1 + elevation-1
    </div>
    <div
      style={{
        borderRadius: 'var(--radius-2)',
        boxShadow: 'var(--elevation-2)',
        padding: '1rem',
        background: 'var(--color-surface)',
      }}
    >
      radius-2 + elevation-2
    </div>
    <div
      style={{
        borderRadius: 'var(--radius-3)',
        boxShadow: 'var(--elevation-3)',
        padding: '1rem',
        background: 'var(--color-surface)',
      }}
    >
      radius-3 + elevation-3
    </div>
    <div
      style={{
        borderRadius: 'var(--radius-4)',
        boxShadow: 'var(--elevation-4)',
        padding: '1rem',
        background: 'var(--color-surface)',
      }}
    >
      radius-4 + elevation-4
    </div>
  </div>
);
