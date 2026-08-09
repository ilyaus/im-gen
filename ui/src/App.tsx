import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import GeneratePage from "./pages/GeneratePage";
import GalleryPage from "./pages/GalleryPage";
import JobDetailPage from "./pages/JobDetailPage";
import SettingsPage from "./pages/SettingsPage";
import { THEMES, useTheme } from "./theme";

export default function App() {
  const [theme, setTheme] = useTheme();
  const activeTheme = THEMES.find((entry) => entry.id === theme);

  return (
    <div className="layout">
      <header className="app-nav">
        <div className="brand-block">
          <span className="brand">im-gen</span>
          <span className="brand-sub">image generation studio</span>
        </div>
        <nav>
          <NavLink to="/generate">Generate</NavLink>
          <NavLink to="/gallery">Gallery</NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>
        <div className="theme-picker">
          <label htmlFor="theme-select">Theme</label>
          <select
            id="theme-select"
            value={theme}
            onChange={(event) => setTheme(event.target.value)}
          >
            {THEMES.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {entry.name}
              </option>
            ))}
          </select>
          {activeTheme && <span className="hint">{activeTheme.tagline}</span>}
        </div>
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/generate" replace />} />
          <Route path="/generate" element={<GeneratePage />} />
          <Route path="/gallery" element={<GalleryPage />} />
          <Route path="/gallery/:jobId" element={<JobDetailPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}
