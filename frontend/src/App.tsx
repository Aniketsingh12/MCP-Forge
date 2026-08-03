import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import NewProject from "./pages/NewProject";
import ToolProposal from "./pages/ToolProposal";
import Generation from "./pages/Generation";
import Playground from "./pages/Playground";
import Export from "./pages/Export";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/new" element={<NewProject />} />
        <Route path="/p/:id/proposal" element={<ToolProposal />} />
        <Route path="/p/:id/generate" element={<Generation />} />
        <Route path="/p/:id/playground" element={<Playground />} />
        <Route path="/p/:id/export" element={<Export />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
