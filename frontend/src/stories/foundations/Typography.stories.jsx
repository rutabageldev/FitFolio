export default {
  title: 'Foundations/Typography',
};

const items = [
  ['-2', 'Caption'],
  ['-1', 'Small'],
  ['0', 'Body'],
  ['1', 'Body Large'],
  ['2', 'Title'],
  ['3', 'Subtitle'],
  ['4', 'Headline'],
  ['5', 'Display'],
];

export const Scale = () => (
  <div style={{ display: 'grid', gap: '0.75rem' }}>
    {items.map(([step, label]) => (
      <div
        key={step}
        style={{ fontSize: `var(--font-size-${step})`, lineHeight: 'var(--line-height-normal)' }}
      >
        <strong>{label}</strong> — The quick brown fox jumps over the lazy dog.
      </div>
    ))}
  </div>
);
