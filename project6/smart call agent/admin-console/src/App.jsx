import { useEffect, useMemo, useRef, useState } from 'react';
import {
  BarChart,
  Bar,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const API_BASE = 'http://localhost:8080/api';
const defaultQuery = 'TRK-1001';

function App() {
  const [session, setSession] = useState(() => ({
    token: localStorage.getItem('admin_token') || '',
    user: JSON.parse(localStorage.getItem('admin_user') || 'null'),
  }));
  const [loginForm, setLoginForm] = useState({ email: 'counter@service.gov', password: 'staff123' });
  const [search, setSearch] = useState(defaultQuery);
  const [dashboard, setDashboard] = useState({ appointments: [], dashboard: { total: 0, checkedIn: 0 } });
  const [capacity, setCapacity] = useState({ slots: [] });
  const [analytics, setAnalytics] = useState(null);
  const [inputText, setInputText] = useState('Hello, I need a passport appointment.');
  const [voiceResponse, setVoiceResponse] = useState('');
  const [conversation, setConversation] = useState([]);
  const [loading, setLoading] = useState(false);
  const recognitionRef = useRef(null);

  const fetchJson = async (path, options = {}) => {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (session.token) headers.Authorization = `Bearer ${session.token}`;
    const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || payload.error || 'Request failed');
    }
    return payload;
  };

  const refreshData = async () => {
    if (!session.token) return;
    const [dashboardPayload, capacityPayload, analyticsPayload] = await Promise.all([
      fetchJson('/dashboard'),
      fetchJson('/capacity'),
      fetchJson('/analytics'),
    ]);
    setDashboard(dashboardPayload);
    setCapacity(capacityPayload);
    setAnalytics(analyticsPayload);
  };

  useEffect(() => {
    if (session.token) {
      refreshData().catch((err) => console.error(err));
    }
  }, [session.token]);

  const filteredAppointments = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return dashboard.appointments;
    return dashboard.appointments.filter((appt) => {
      const haystack = [appt.trackingNumber, appt.applicantName, appt.phoneNumber].join(' ').toLowerCase();
      return haystack.includes(term);
    });
  }, [dashboard.appointments, search]);

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      const payload = await fetchJson('/auth/login', {
        method: 'POST',
        body: JSON.stringify(loginForm),
      });
      localStorage.setItem('admin_token', payload.token);
      localStorage.setItem('admin_user', JSON.stringify(payload.user));
      setSession({ token: payload.token, user: payload.user });
    } catch (error) {
      alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    setSession({ token: '', user: null });
  };

  const updateStatus = async (trackingNumber, toStatus) => {
    try {
      await fetchJson(`/appointments/${trackingNumber}/status`, {
        method: 'PUT',
        body: JSON.stringify({ to_status: toStatus, staff_id: session.user?.id || 'staff-001' }),
      });
      await refreshData();
    } catch (error) {
      alert(error.message);
    }
  };

  const performCheckIn = async (trackingNumber) => {
    try {
      await fetchJson(`/appointments/${trackingNumber}/check-in`, { method: 'POST' });
      await refreshData();
    } catch (error) {
      alert(error.message);
    }
  };

  const handleVoiceSubmit = async () => {
    const command = inputText.trim();
    if (!command) return;

    try {
      const payload = await fetchJson('/voice/command', {
        method: 'POST',
        body: JSON.stringify({ command }),
      });
      const response = payload.textResponse || payload.spokenResponse || 'I understood your request.';
      setVoiceResponse(response);
      setConversation((items) => [...items, { type: 'user', text: command }, { type: 'agent', text: response, slots: payload.slots, booking: payload.booking }]);
      setInputText('');

      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(response);
        utterance.lang = 'en-US';
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
      }
    } catch (error) {
      alert(error.message);
    }
  };

  const startVoiceCapture = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. You can still type a command and use the generated response.');
      return;
    }

    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setInputText(transcript);
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error', event.error);
      alert(`Voice capture error: ${event.error}`);
    };

    recognition.onend = () => {
      recognitionRef.current = null;
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  const useSuggestedCommand = (command) => { setInputText(command); };

  if (!session.token) {
    return (
      <div className="app-shell">
        <div className="login-card">
          <h2>Staff Console Login</h2>
          <form onSubmit={handleLogin} className="form-grid">
            <label>
              Email
              <input
                type="email"
                value={loginForm.email}
                onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={loginForm.password}
                onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
              />
            </label>
            <button className="primary-btn" type="submit" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (!analytics) return null;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <h1>Smart Call Agent Admin</h1>
          <small>Counter staff & admin console</small>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div className="user-chip">
            <span>{session.user?.name}</span>
            <span>â€¢</span>
            <strong>{session.user?.role}</strong>
          </div>
          <button className="secondary-btn" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <section className="summary-grid">
        <div className="summary-card">
          <h3>Total appointments</h3>
          <div className="value">{dashboard.dashboard.total}</div>
        </div>
        <div className="summary-card">
          <h3>Checked in</h3>
          <div className="value">{dashboard.dashboard.checkedIn}</div>
        </div>
        <div className="summary-card">
          <h3>Booking conversion</h3>
          <div className="value">{analytics.conversionRate}%</div>
        </div>
        <div className="summary-card">
          <h3>Avg call duration</h3>
          <div className="value">{analytics.avgCallDuration}s</div>
        </div>
      </section>

      <div className="content-grid">
        <section className="panel table-card">
          <h3>Daily appointment schedule</h3>
          <div className="search-box">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by tracking number, name, or phone"
            />
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Tracking</th>
                  <th>Name</th>
                  <th>Service</th>
                  <th>Time</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredAppointments.map((appt) => (
                  <tr key={appt.trackingNumber}>
                    <td>{appt.trackingNumber}</td>
                    <td>{appt.applicantName}</td>
                    <td>{appt.serviceName}</td>
                    <td>{appt.slotDate} {appt.timeBlock}</td>
                    <td><span className="status-badge">{appt.status}</span></td>
                    <td className="row-actions">
                      <button className="status-btn" onClick={() => performCheckIn(appt.trackingNumber)}>Check In</button>
                      <button className="status-btn secondary" onClick={() => updateStatus(appt.trackingNumber, 'DocumentsVerified')}>Verify</button>
                      <button className="status-btn secondary" onClick={() => updateStatus(appt.trackingNumber, 'Completed')}>Complete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="panel voice-panel">
          <h3>Appointment agent</h3>
          <p className="helper-text">Try: “I want to renew my ID card” ? “show available slots” ? “another day” ? “book 09:30-10:00”.</p>
          <div className="conversation" aria-live="polite">
            {conversation.length === 0 && <p className="empty-state">Your appointment conversation will appear here.</p>}
            {conversation.map((message, index) => (
              <div className={`message ${message.type}`} key={index}>
                <strong>{message.type === 'user' ? 'You' : 'Agent'}</strong><span>{message.text}</span>
                {message.slots && <div className="slot-list">{message.slots.map((slot) => <button key={`${slot.date}-${slot.timeBlock}`} className="slot-choice" onClick={() => useSuggestedCommand(`book ${slot.timeBlock}`)}>{slot.date} · {slot.timeBlock} ({slot.available} left)</button>)}</div>}
                {message.booking && <div className="booking-id">Booking ID: {message.booking.trackingNumber}</div>}
              </div>
            ))}
          </div>
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Type a voice command here..."
          />
          <div className="voice-controls">
            <button className="primary-btn" onClick={startVoiceCapture}>Use microphone</button>
            <button className="secondary-btn" onClick={handleVoiceSubmit}>Generate voice + text response</button>
          </div>
          <div className="voice-response">
            <strong>Text reply:</strong>
            <p>{voiceResponse || 'No response generated yet.'}</p>
          </div>
        </aside>
      </div>

      <div className="content-grid" style={{ marginTop: 24 }}>
        <section className="panel">
          <h3>Call volume</h3>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={analytics.callVolume}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#cbd5e1" />
                <YAxis stroke="#cbd5e1" />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="calls" stroke="#60a5fa" strokeWidth={3} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="panel">
          <h3>Most requested services</h3>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={analytics.topServices}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#cbd5e1" />
                <YAxis stroke="#cbd5e1" />
                <Tooltip />
                <Bar dataKey="value" fill="#34d399" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <div className="content-grid" style={{ marginTop: 24 }}>
        <section className="panel">
          <h3>Capacity management</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Location</th>
                  <th>Date</th>
                  <th>Time</th>
                  <th>Capacity</th>
                </tr>
              </thead>
              <tbody>
                {capacity.slots.map((slot, index) => (
                  <tr key={`${slot.date}-${slot.timeBlock}-${index}`}>
                    <td>{slot.serviceName}</td>
                    <td>{slot.locationName}</td>
                    <td>{slot.date}</td>
                    <td>{slot.timeBlock}</td>
                    <td>{slot.capacity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <h3>Status pipeline</h3>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={analytics.statusBreakdown} dataKey="value" nameKey="name" outerRadius={80} fill="#8884d8" label />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>
    </div>
  );
}

export default App;
