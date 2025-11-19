import PropTypes from 'prop-types';

const roles = [
  ['primary', ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900']],
  ['warning', ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900']],
  ['danger', ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900']],
  ['success', ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900']],
  ['info', ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900']],
  ['neutral', ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900']],
];

function Swatch({ varName, onVar }) {
  const style = {
    background: `var(${varName})`,
    color: onVar ? `var(${onVar})` : 'var(--color-text)',
    border: '1px solid rgba(15,23,42,0.12)',
    borderRadius: '0.75rem',
    padding: '0.75rem',
    fontSize: '0.875rem',
  };
  return (
    <div style={style}>
      <code>{varName}</code>
    </div>
  );
}

Swatch.propTypes = {
  varName: PropTypes.string.isRequired,
  onVar: PropTypes.string,
};

export default {
  title: 'Foundations/Colors',
};

export const Ramps = () => (
  <div style={{ display: 'grid', gap: '1rem' }}>
    {roles.map(([role, steps]) => (
      <div key={role}>
        <h4 style={{ margin: 0 }}>{role}</h4>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(140px,1fr))',
            gap: '0.5rem',
          }}
        >
          {steps.map((s) => (
            <Swatch key={s} varName={`--color-${role}-${s}`} />
          ))}
        </div>
      </div>
    ))}
    <div>
      <h4 style={{ margin: 0 }}>On-colors</h4>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px,1fr))',
          gap: '0.5rem',
        }}
      >
        <Swatch varName="--color-primary-600" onVar="--color-on-primary" />
        <Swatch varName="--color-success-600" onVar="--color-on-success" />
        <Swatch varName="--color-danger-600" onVar="--color-on-danger" />
        <Swatch varName="--color-info-600" onVar="--color-on-info" />
        <div style={{ display: 'grid', gap: '0.25rem' }}>
          <div>
            <code>--color-on-surface</code>
          </div>
          <div
            style={{
              background: 'var(--color-surface)',
              padding: '0.75rem',
              border: '1px solid var(--color-border)',
            }}
          >
            <span style={{ color: 'var(--color-on-surface)' }}>Text on surface</span>
            <div style={{ color: 'var(--color-on-surface-muted)' }}>Muted text on surface</div>
          </div>
        </div>
      </div>
    </div>
  </div>
);
