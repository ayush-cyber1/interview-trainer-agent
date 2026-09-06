/* App.tsx — root component with routing and state */

import { useState } from 'react'
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ProfilePage from './pages/ProfilePage'
import ResultsPage from './pages/ResultsPage'
import HistoryPage from './pages/HistoryPage'
import type { GenerateResponse, ProfileData } from './types'

export interface AppState {
  profile: ProfileData | null
  results: GenerateResponse | null
  history: Array<{ profile: ProfileData; results: GenerateResponse; timestamp: string }>
}

export default function App() {
  const [appState, setAppState] = useState<AppState>({
    profile: null,
    results: null,
    history: [],
  })

  function onGenerated(profile: ProfileData, results: GenerateResponse) {
    setAppState((prev) => ({
      profile,
      results,
      history: [
        { profile, results, timestamp: new Date().toLocaleString() },
        ...prev.history.slice(0, 9), // keep last 10
      ],
    }))
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/profile" replace />} />
          <Route
            path="profile"
            element={<ProfilePage onGenerated={onGenerated} />}
          />
          <Route
            path="results"
            element={
              appState.results ? (
                <ResultsPage profile={appState.profile!} results={appState.results} />
              ) : (
                <Navigate to="/profile" replace />
              )
            }
          />
          <Route
            path="history"
            element={<HistoryPage history={appState.history} />}
          />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
