'use client';
import Link from 'next/link';
import {ArrowRight} from '@phosphor-icons/react';
import SiteNav from './site-nav';
import ToolIcon from './tool-icons';
import {HeroDecor} from './decor-layers';
import {tools, subjects, subjectBlurb} from './tools';

/* The landing page. Its job is to show what an answer actually looks like,
 * because the product's claim — grounded, cited, structured to the marking
 * scheme — is only credible when you can see one. */
export default function Home() {
  return <>
    <SiteNav/>
    <a href="#subjects" className="skip-link">Skip to subjects</a>
    <div className="decor-field">
    <HeroDecor/>

    <header className="hero">
      <h1 className="hero-title">Study from your own textbook, not from a guess.</h1>
      <p className="hero-sub">
        StudyMate answers 1st and 2nd PUC questions out of your prescribed Physics,
        Chemistry, Mathematics and Biology material — structured as the value points
        a board marking scheme rewards, with the page behind every claim.
      </p>
      <div className="hero-actions">
        <Link href="/tools/ask" className="primary-button">Ask a question<ArrowRight size={17}/></Link>
        <Link href="/tools/practice" className="ghost-button">Generate a practice paper</Link>
      </div>

      <section className="specimen" aria-label="Example answer">
        <div className="specimen-bar"><span className="dot"/>Physics · 2nd PUC · Karnataka</div>
        <div className="specimen-body">
          <p className="specimen-q">State and derive the lens maker&rsquo;s formula.</p>
          <ol>
            <li>The lens maker&rsquo;s formula relates focal length to refractive index and the radii of curvature.<sup>1</sup></li>
            <li>For refraction at the first surface, <var>n₂/v₁ − n₁/u = (n₂ − n₁)/R₁</var>.<sup>1</sup></li>
            <li>For refraction at the second surface, <var>n₁/v − n₂/v₁ = (n₁ − n₂)/R₂</var>.<sup>2</sup></li>
            <li>Adding both and substituting <var>1/f = 1/v − 1/u</var> gives <var>1/f = (n − 1)(1/R₁ − 1/R₂)</var>.<sup>2</sup></li>
            <li>Here <var>f</var> is the focal length in metres, <var>n</var> the refractive index, <var>R₁</var> and <var>R₂</var> the radii of curvature.<sup>3</sup></li>
          </ol>
          <cite>Retrieved sources — 132ndPhysicsPart-2.pdf, pages 36, 33, 45</cite>
        </div>
      </section>
    </header>

    <section className="subject-strip" id="subjects">
      <p>Built on the prescribed PUC and NCERT material</p>
      <div className="subject-row">
        {subjects.map(s => <Link key={s} href={`/tools/ask?subject=${s}`} className="subject-card" data-subject={s}>
          <b>{s[0].toUpperCase() + s.slice(1)}</b>
          <span>{subjectBlurb[s]}</span>
        </Link>)}
      </div>
    </section>

    <section className="features">
      <h2>Six ways to work</h2>
      <p>Each one is its own page. Pick the kind of help you need and go straight to it.</p>
      <div className="feature-grid">
        {tools.map(t => <Link key={t.slug} href={`/tools/${t.slug}`} className="feature">
          <ToolIcon slug={t.slug} size={22} weight="duotone"/>
          <h3>{t.label}</h3>
          <p>{t.blurb}</p>
          <span className="go">Open<ArrowRight size={14}/></span>
        </Link>)}
      </div>
    </section>

    <footer className="site-footer">
      <span>Made for focused study.</span>
      <span>Check important answers against your course material.</span>
    </footer>
    </div>
  </>;
}
