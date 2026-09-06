/* HistoryPage.tsx — session history list */

import { useNavigate } from 'react-router-dom'
import type { GenerateResponse, ProfileData } from '../types'
import styles from './HistoryPage.module.css'
import { Clock, ArrowRight } from 'lucide-react'

interface HistoryEntry {
  profile: ProfileData
  results: GenerateResponse
  timestamp: string
}

interface Props {
  history: HistoryEntry[]
}

export default function HistoryPage({ history }: Props) {
  const navigate = useNavigate()

  if (history.length === 0) {
    return (
      <div className={`${styles.empty} fade-in`}>
        <Clock size={48} strokeWidth={1.5} color="var(--muted2)" />
        <h2>No history yet</h2>
        <p>Generate your first interview prep to see it here.</p>
        <button className={styles.btn} onClick={() => navigate('/profile')}>
          Get Started <ArrowRight size={15} />
        </button>
      </div>
    )
  }

  return (
    <div className={`${styles.page} fade-in`}>
      <h1 className={styles.title}>Session History</h1>
      <p className={styles.sub}>Your last {history.length} generation{history.length !== 1 ? 's' : ''}.</p>

      <div className={styles.list}>
        {history.map((entry, i) => (
          <div key={i} className={styles.card}>
            <div className={styles.cardLeft}>
              <span className={styles.badge}>{entry.profile.experience_level}</span>
              <div>
                <div className={styles.cardName}>{entry.profile.name}</div>
                <div className={styles.cardRole}>{entry.profile.job_role}</div>
              </div>
            </div>
            <div className={styles.cardMid}>
              <div className={styles.statRow}>
                <span className={styles.statItem}>
                  <strong>{entry.results.technical.length}</strong> technical
                </span>
                <span className={styles.statItem}>
                  <strong>{entry.results.behavioral.length}</strong> behavioral
                </span>
                <span className={styles.statItem}>
                  Score <strong>{entry.results.readiness.score}/10</strong>
                </span>
              </div>
              <div className={styles.timestamp}><Clock size={12} /> {entry.timestamp}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
