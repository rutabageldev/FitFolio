export default {
  title: 'Foundations/Spacing',
};

const steps = ['1', '2', '3', '4', '5', '6', '7', '8', '9'];

export const Scale = () => (
  <div
    style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(180px,1fr))',
      gap: '1rem',
    }}
  >
    {steps.map((s) => (
      <div
        key={s}
        style={{
          border: '1px solid var(--color-border)',
          borderRadius: '0.75rem',
          padding: '0.75rem',
        }}
      >
        <div style={{ fontSize: '0.875rem', marginBottom: '0.5rem' }}>
          <code>--space-{s}</code>
        </div>
        <div style={{ height: `var(--space-${s})`, background: 'var(--color-neutral-300)' }} />
      </div>
    ))}
  </div>
);
