import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import IngestPage from './IngestPage';
import SearchPage from './SearchPage';

const navItems = [
  { to: '/app/ingest', label: 'Ingest' },
  { to: '/app/search', label: 'Search' },
];

export default function App() {
  return (
    <div className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Aitonomee Face Technology</p>
          <h1>Local Face Search Prototype</h1>
          <p className="subtitle">
            Ingest a mounted photo folder, then search similar faces from a selfie upload.
          </p>
        </div>
        <nav className="nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/app/ingest" replace />} />
          <Route path="/app/ingest" element={<IngestPage />} />
          <Route path="/app/search" element={<SearchPage />} />
        </Routes>
      </main>
    </div>
  );
}
