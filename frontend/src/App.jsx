import { useState } from 'react';
import './App.css';

function App() {
  const [apiResult, setApiResult] = useState(null);

  const pingApi = async () => {
    try {
      const res = await fetch('/api/healthz');
      const ct = res.headers.get('content-type') || '';
      let data;
      if (ct.includes('application/json')) {
        data = await res.json();
      } else {
        const text = await res.text();
        data = { status: res.status, body: text };
      }
      setApiResult(data);
    } catch (e) {
      setApiResult({ error: String(e) });
    }
  };

  return (
    <>
      <h1>FitFolio Dev</h1>

      <div className="card">
        <button onClick={pingApi}>Ping API</button>
        <pre style={{ marginTop: 12 }}>
          {apiResult ? JSON.stringify(apiResult, null, 2) : 'No result yet'}
        </pre>
      </div>
    </>
  );
}

export default App;
