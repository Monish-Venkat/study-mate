import type { Metadata } from 'next';
import '@fontsource/dm-sans/400.css';
import '@fontsource/dm-sans/500.css';
import '@fontsource/dm-sans/600.css';
import '@fontsource/dm-sans/700.css';
import './tokens.css';
import './globals.css';
import './components.css';
export const metadata: Metadata = { title: 'StudyMate | Your study workspace', description: 'Ask, revise and practice with your PUC course material.' };
export default function RootLayout({ children }: Readonly<{children: React.ReactNode}>) {
  const noFlash = "try{var t=localStorage.getItem('studymate-theme');if(t)document.documentElement.dataset.theme=t;}catch(e){}";
  return <html lang="en" suppressHydrationWarning>
    <head><script dangerouslySetInnerHTML={{__html: noFlash}}/></head>
    <body>{children}</body>
  </html>;
}
