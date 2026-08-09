import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import GeneratePage from "./pages/GeneratePage";
import GalleryPage from "./pages/GalleryPage";
import JobDetailPage from "./pages/JobDetailPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <div className="layout">
      <header className="topbar">
        <span className="brand">im-gen</span>
        <nav>
          <NavLink to="/generate">Generate</NavLink>
          <NavLink to="/gallery">Gallery</NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<Navigate to="/generate" replace />} />
        <Route path="/generate" element={<GeneratePage />} />
        <Route path="/gallery" element={<GalleryPage />} />
        <Route path="/gallery/:jobId" element={<JobDetailPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </div>
  );
}
