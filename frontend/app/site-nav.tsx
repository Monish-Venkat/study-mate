'use client';
import {useEffect, useState} from 'react';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {BookOpen, Sun, Moon} from '@phosphor-icons/react';
import {tools} from './tools';

/* The top bar replaces the old permanent left sidebar. Service health moved
 * here as a single dot: it was a panel taking a quarter of the aside to say
 * one word, and it is the same answer on every route. */
export default function SiteNav() {
  const pathname = usePathname();
  const [theme, setTheme] = useState<'light' | 'dark' | null>(null);
  const [health, setHealth] = useState<'checking' | 'offline' | 'empty' | 'ready'>('checking');

  useEffect(() => {
    const stored = document.documentElement.dataset.theme as 'light' | 'dark' | undefined;
    setTheme(stored || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
    let live = true;
    fetch('/api/study/health')
      .then(async r => { const d = await r.json(); if (live) setHealth(!r.ok ? 'offline' : d.index_ready ? 'ready' : 'empty'); })
      .catch(() => { if (live) setHealth('offline'); });
    return () => { live = false; };
  }, []);

  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('studymate-theme', next); } catch {}
  }

  const statusText = health === 'ready' ? 'Index ready'
    : health === 'empty' ? 'Index empty'
    : health === 'offline' ? 'Backend offline' : 'Checking';

  return <nav className="site-nav" aria-label="Primary">
    <Link href="/" className="wordmark"><BookOpen weight="duotone" size={22}/>StudyMate</Link>
    <div className="nav-links">
      {tools.map(t => {
        const href = `/tools/${t.slug}`;
        return <Link key={t.slug} href={href} aria-current={pathname === href ? 'page' : undefined}>{t.label}</Link>;
      })}
    </div>
    <div className="nav-end">
      <span className={`nav-status ${health}`} role="status"><i/>{statusText}</span>
      <button type="button" className="icon-button" onClick={toggleTheme}
        title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
        aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
        {theme === 'dark' ? <Sun size={17}/> : <Moon size={17}/>}
      </button>
    </div>
  </nav>;
}
