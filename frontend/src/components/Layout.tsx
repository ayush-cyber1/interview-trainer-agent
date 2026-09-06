/* Layout.tsx — top nav + outlet */

import { NavLink, Outlet } from 'react-router-dom'
import styles from './Layout.module.css'
import { Brain } from 'lucide-react'

export default function Layout() {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <Brain size={26} strokeWidth={2.2} />
          <span>Interview Trainer</span>
        </div>
        <nav className={styles.nav}>
          <NavLink to="/profile"  className={({ isActive }) => isActive ? `${styles.link} ${styles.active}` : styles.link}>
            Profile Setup
          </NavLink>
          <NavLink to="/results"  className={({ isActive }) => isActive ? `${styles.link} ${styles.active}` : styles.link}>
            Results & Tips
          </NavLink>
          <NavLink to="/history"  className={({ isActive }) => isActive ? `${styles.link} ${styles.active}` : styles.link}>
            History
          </NavLink>
        </nav>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
      <footer className={styles.footer}>
        Built with IBM watsonx.ai · sentence-transformers · Chroma
      </footer>
    </div>
  )
}
