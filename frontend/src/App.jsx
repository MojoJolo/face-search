import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import IngestPage from './IngestPage';
import SearchPage from './SearchPage';

const navItems = [
  { to: '/ingest', label: 'Ingest' },
  { to: '/search', label: 'Search' },
];

export default function App() {
  return (
    <div className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">InsightFace + pgvector</p>
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
          <Route path="/" element={<Navigate to="/ingest" replace />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/search" element={<SearchPage />} />
        </Routes>
      </main>
    </div>
  );
}
