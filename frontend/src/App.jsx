import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import PlanPage from './pages/PlanPage';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-slate-50 text-slate-900 font-sans flex flex-col">
        {/* Simple Navbar */}
        <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="bg-brand-600 text-white p-1.5 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.2-1.1.6L3 8l5 5-2 2-3-1-2 2 4 4 2-2-1-3 2-2 5 5 1.2-.8c.4-.2.7-.6.6-1.1z"/></svg>
              </div>
              <span className="font-bold text-xl tracking-tight text-slate-900">TBuddy</span>
            </div>
            <nav className="hidden sm:block">
              <div className="flex space-x-4 text-sm font-medium">
                <a href="/" className="text-slate-600 hover:text-brand-600 transition-colors">Home</a>
                <a href="#" className="text-slate-600 hover:text-brand-600 transition-colors">Destinations</a>
                <a href="#" className="text-slate-600 hover:text-brand-600 transition-colors">About</a>
              </div>
            </nav>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 flex flex-col">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/plan" element={<PlanPage />} />
          </Routes>
        </main>
        
        {/* Simple Footer */}
        <footer className="bg-white border-t border-slate-200 mt-auto">
          <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-center text-sm text-slate-500">
            <p>© 2026 TBuddy Travel. All rights reserved.</p>
            <p className="mt-2 sm:mt-0">Powered by Agentic AI</p>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
