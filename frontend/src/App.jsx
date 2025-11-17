import './App.css';

const highlights = [
  {
    title: 'Coach-first workflow',
    description:
      'Plan sessions, track progress, and keep every client touchpoint in one place without juggling spreadsheets.',
  },
  {
    title: 'Progress your clients notice',
    description:
      'Share beautiful summaries after each training block so clients always know where they stand and what is next.',
  },
  {
    title: 'Integrations in motion',
    description:
      'We are wiring up calendar, payments, and wearable data so Fitfolio fits the tools you already use.',
  },
];

const milestones = [
  { label: 'Staging preview', detail: 'Internal-only build for early validation' },
  { label: 'Private beta', detail: 'Inviting a small cohort of coaches next' },
  { label: 'Public waitlist', detail: 'Sign up to hear when we fully open the doors' },
];

const stats = [
  { label: 'Coaches advising fitfolio', value: '12' },
  { label: 'Client sessions modeled', value: '480+' },
  { label: 'Integrations scoped', value: '3' },
];

const contactEmail = 'hello@fitfolio.app';

function App() {
  return (
    <div className="landing-page">
      <header className="hero">
        <p className="eyebrow">A simple hello from Fitfolio</p>
        <h1>The training HQ for every rep you coach.</h1>
        <p className="subhead">
          We are building Fitfolio to give personal trainers a focused space to plan programs, share
          progress, and grow their business. This staging site is the earliest glimpse at what is
          coming.
        </p>
        <div className="cta-group">
          <a
            className="cta primary"
            href={`mailto:${contactEmail}?subject=Fitfolio%20Staging%20Preview`}
          >
            Join the staging waitlist
          </a>
          <a className="cta secondary" href="#roadmap">
            See what&apos;s next
          </a>
        </div>
        <p className="disclaimer">
          This is a staging preview environment. Features change quickly and accounts may be reset
          at any time.
        </p>
      </header>

      <main className="content">
        <section className="card-grid" aria-label="Fitfolio highlights">
          {highlights.map((item) => (
            <article className="card" key={item.title}>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </article>
          ))}
        </section>

        <section className="stats-panel" aria-label="Momentum indicators">
          {stats.map((stat) => (
            <div className="stat" key={stat.label}>
              <span className="value">{stat.value}</span>
              <span className="label">{stat.label}</span>
            </div>
          ))}
        </section>

        <section className="info-panel" id="roadmap">
          <h2>Where this is headed</h2>
          <p>
            Fitfolio pairs thoughtful workout planning with client-friendly updates and business
            basics like billing and scheduling. Here is the rough order of operations:
          </p>
          <ul>
            {milestones.map((milestone) => (
              <li key={milestone.label}>
                <span className="milestone-label">{milestone.label}</span>
                <span className="milestone-detail">{milestone.detail}</span>
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="footer">
        <p>Questions or feedback? Email us at</p>
        <a href={`mailto:${contactEmail}`}>{contactEmail}</a>
        <p>© {new Date().getFullYear()} Fitfolio · Built with care for trainers.</p>
      </footer>
    </div>
  );
}

export default App;
