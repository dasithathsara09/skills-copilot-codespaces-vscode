import { useMemo, useState } from 'react';
import { Download, FileUp, LayoutDashboard, PlusCircle, Trash2 } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
  Legend,
} from 'recharts';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const chartColors = ['#3b82f6', '#14b8a6', '#f59e0b', '#a855f7', '#ef4444'];

const metricCardClass = 'rounded-xl bg-white border border-slate-200 p-4 shadow-sm';

async function request(path, { token, method = 'GET', body, isForm = false } = {}) {
  const headers = token ? { Authorization: ['Bearer', token].join(' ') } : {};
  if (!isForm) {
    headers['Content-Type'] = 'application/json';
  }
  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(detail.detail || 'Request failed');
  }
  if (response.status === 204) return null;
  if (response.headers.get('content-type')?.includes('text/csv')) {
    return response.text();
  }
  return response.json();
}

export default function App() {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [token, setToken] = useState('');
  const [records, setRecords] = useState([]);
  const [dashboard, setDashboard] = useState({ total_records: 0, total_value: 0, average_value: 0, trend: [], distribution: [] });
  const [filters, setFilters] = useState({ search: '', category: '' });
  const [form, setForm] = useState({ name: '', category: '', value: '', recorded_on: '', notes: '' });
  const [error, setError] = useState('');

  const categories = useMemo(() => [...new Set(records.map((r) => r.category))], [records]);

  const refresh = async (jwt = token) => {
    if (!jwt) return;
    const params = new URLSearchParams();
    if (filters.search) params.set('search', filters.search);
    if (filters.category) params.set('category', filters.category);

    const [recordData, dashboardData] = await Promise.all([
      request(`/records${params.toString() ? `?${params.toString()}` : ''}`, { token: jwt }),
      request('/dashboard', { token: jwt }),
    ]);
    setRecords(recordData);
    setDashboard(dashboardData);
  };

  const register = async () => {
    setError('');
    await request('/auth/register', { method: 'POST', body: credentials });
    await login();
  };

  const login = async () => {
    setError('');
    const body = new URLSearchParams(credentials).toString();
    const response = await fetch(`${API_URL}/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
    if (!response.ok) {
      setError('Invalid credentials');
      return;
    }
    const data = await response.json();
    setToken(data.access_token);
    await refresh(data.access_token);
  };

  const createRecord = async () => {
    await request('/records', {
      token,
      method: 'POST',
      body: {
        ...form,
        value: Number(form.value),
      },
    });
    setForm({ name: '', category: '', value: '', recorded_on: '', notes: '' });
    await refresh();
  };

  const removeRecord = async (id) => {
    await request(`/records/${id}`, { token, method: 'DELETE' });
    await refresh();
  };

  const downloadCsv = async () => {
    const csvText = await request('/records/export/csv', { token });
    const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'records.csv';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const importCsv = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    await request('/records/import', { token, method: 'POST', body: formData, isForm: true });
    await refresh();
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="font-bold text-2xl flex items-center gap-2"><LayoutDashboard className="w-6 h-6" /> Analytics Manager</h1>
          {token && <button onClick={downloadCsv} className="px-4 py-2 rounded-lg bg-slate-900 text-white flex items-center gap-2"><Download className="w-4 h-4" /> Export CSV</button>}
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6 space-y-6">
        {!token ? (
          <div className="max-w-md mx-auto bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
            <h2 className="text-lg font-semibold">Sign in</h2>
            <input className="w-full border rounded-lg p-2" placeholder="Username" value={credentials.username} onChange={(e) => setCredentials({ ...credentials, username: e.target.value })} />
            <input className="w-full border rounded-lg p-2" type="password" placeholder="Password" value={credentials.password} onChange={(e) => setCredentials({ ...credentials, password: e.target.value })} />
            {error && <p className="text-sm text-red-500">{error}</p>}
            <div className="flex gap-2">
              <button className="flex-1 bg-slate-900 text-white rounded-lg py-2" onClick={login}>Login</button>
              <button className="flex-1 bg-slate-200 rounded-lg py-2" onClick={register}>Register</button>
            </div>
          </div>
        ) : (
          <>
            <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <article className={metricCardClass}><p className="text-sm text-slate-500">Total Records</p><p className="text-3xl font-bold">{dashboard.total_records}</p></article>
              <article className={metricCardClass}><p className="text-sm text-slate-500">Total Value</p><p className="text-3xl font-bold">{dashboard.total_value}</p></article>
              <article className={metricCardClass}><p className="text-sm text-slate-500">Average Value</p><p className="text-3xl font-bold">{dashboard.average_value}</p></article>
            </section>

            <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className={metricCardClass}>
                <h3 className="font-semibold mb-2">Trend</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={dashboard.trend}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="period" />
                      <YAxis />
                      <Tooltip />
                      <Line type="monotone" dataKey="value" stroke="#3b82f6" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className={metricCardClass}>
                <h3 className="font-semibold mb-2">Category Distribution</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={dashboard.distribution} dataKey="value" nameKey="category" cx="50%" cy="50%" outerRadius={80} label>
                        {dashboard.distribution.map((entry, index) => (
                          <Cell key={entry.category} fill={chartColors[index % chartColors.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </section>

            <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className={`${metricCardClass} lg:col-span-1 space-y-2`}>
                <h3 className="font-semibold flex items-center gap-2"><PlusCircle className="w-4 h-4" /> Add Record</h3>
                {Object.entries(form).map(([key, value]) => (
                  <input
                    key={key}
                    className="w-full border rounded-lg p-2"
                    placeholder={key}
                    type={key === 'recorded_on' ? 'date' : key === 'value' ? 'number' : 'text'}
                    value={value}
                    onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  />
                ))}
                <button className="w-full bg-slate-900 text-white rounded-lg py-2" onClick={createRecord}>Create</button>
                <label className="inline-flex items-center gap-2 text-sm px-3 py-2 rounded-lg border cursor-pointer">
                  <FileUp className="w-4 h-4" /> Import CSV
                  <input type="file" accept=".csv" className="hidden" onChange={importCsv} />
                </label>
              </div>

              <div className={`${metricCardClass} lg:col-span-2`}>
                <div className="flex flex-wrap gap-2 mb-3">
                  <input className="border rounded-lg p-2" placeholder="Search name" value={filters.search} onChange={(e) => setFilters({ ...filters, search: e.target.value })} />
                  <select className="border rounded-lg p-2" value={filters.category} onChange={(e) => setFilters({ ...filters, category: e.target.value })}>
                    <option value="">All categories</option>
                    {categories.map((category) => <option key={category} value={category}>{category}</option>)}
                  </select>
                  <button className="bg-slate-900 text-white px-4 rounded-lg" onClick={() => refresh()}>Apply</button>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left border-b">
                        <th className="py-2">Name</th><th>Category</th><th>Value</th><th>Date</th><th>Notes</th><th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {records.map((record) => (
                        <tr key={record.id} className="border-b">
                          <td className="py-2">{record.name}</td>
                          <td>{record.category}</td>
                          <td>{record.value}</td>
                          <td>{record.recorded_on}</td>
                          <td>{record.notes}</td>
                          <td>
                            <button className="text-red-500" onClick={() => removeRecord(record.id)}><Trash2 className="w-4 h-4" /></button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>

            <section className={metricCardClass}>
              <h3 className="font-semibold mb-2">Volume by Category</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dashboard.distribution}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="category" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill="#14b8a6" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
