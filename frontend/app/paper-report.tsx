'use client';

/* Past-paper review, rendered from the structured report rather than from the
 * markdown summary.
 *
 * The distinction this layout exists to protect: a board paper is evidence of
 * what gets asked, a question bank is not — it holds many questions per topic
 * because a compiler decided to write them. The two counts are therefore shown
 * as separate chips and never added together, and recurrence is judged on the
 * board-paper count alone.
 */
export type Study = {source?: string; page?: number | string};

export type Topic = {
  topic: string; question_count: number; paper_count: number; bank_count: number;
  years: number[]; known_marks: number; typical_marks: number | null;
  example: string; study: Study[];
};

export type Report = {
  available_years: number[]; missing_years: number[];
  question_count: number; paper_question_count: number; bank_question_count: number;
  composition?: Record<string, number>;
  topics: Topic[]; grouping: string;
  mark_distribution?: Record<string, number>;
  sources?: string[]; verified?: boolean;
  skipped_files?: {file: string; reason: string}[];
};

function Stat({label, value}: {label: string; value: string | number}) {
  return <div className="stat"><b>{value}</b><span>{label}</span></div>;
}

function TopicCard({topic}: {topic: Topic}) {
  const where = topic.study.filter(s => s.page != null);
  return <article className="topic-card">
    <header>
      <h4>{topic.topic}</h4>
      <div className="chips">
        {/* Two chips, never one total: the counts mean different things. */}
        {topic.paper_count > 0 && <span className="chip chip-paper">
          {topic.paper_count} in board paper{topic.paper_count === 1 ? '' : 's'}
          {topic.years.length > 0 && <i> · {topic.years.join(', ')}</i>}
        </span>}
        {topic.bank_count > 0 && <span className="chip">
          {topic.bank_count} practice question{topic.bank_count === 1 ? '' : 's'}
        </span>}
        {topic.typical_marks != null && <span className="chip">{topic.typical_marks} marks typical</span>}
      </div>
    </header>
    <blockquote>{topic.example}</blockquote>
    {where.length > 0 && <p className="where">
      <span>Answered in</span>
      {where.map((s, i) => <span key={i} className="ref">{s.source} p.&nbsp;{s.page}</span>)}
    </p>}
  </article>;
}

export default function PaperReport({report}: {report: Report}) {
  const recurring = report.topics.filter(t => t.paper_count > 1 || t.years.length > 1);
  const concentrated = [...report.topics].filter(t => t.bank_count > 1)
    .sort((a, b) => b.bank_count - a.bank_count);
  const years = report.available_years;

  return <section className="paper-report">
    <div className="stat-row">
      <Stat label="questions read" value={report.question_count}/>
      <Stat label="from board papers" value={report.paper_question_count}/>
      <Stat label="from question banks" value={report.bank_question_count}/>
      <Stat label={`exam year${years.length === 1 ? '' : 's'}`} value={years.join(', ') || '—'}/>
    </div>

    <p className="report-note">
      Recurrence is counted from board papers only. Question-bank entries show how much practice
      exists on a topic, which is an editorial choice by the compiler rather than evidence of what
      the board asks.
      {report.missing_years.length > 0 &&
        <> Missing from the five-year window: {report.missing_years.join(', ')}.</>}
    </p>

    {recurring.length > 0 ? <>
      <h3 className="report-heading">Recurring across board papers</h3>
      <div className="topic-list">{recurring.slice(0, 8).map((t, i) => <TopicCard key={i} topic={t}/>)}</div>
    </> : <>
      <h3 className="report-heading">No question recurred</h3>
      <p className="report-note">
        {report.paper_question_count} board-paper question{report.paper_question_count === 1 ? '' : 's'} were
        found across {years.length} year{years.length === 1 ? '' : 's'}, each asked once. Recurrence
        needs papers from more than one year.
      </p>
      {concentrated.length > 0 && <>
        <h3 className="report-heading">Where the practice is concentrated</h3>
        <p className="report-note">A weaker signal than recurrence, but still worth working through.</p>
        <div className="topic-list">{concentrated.slice(0, 8).map((t, i) => <TopicCard key={i} topic={t}/>)}</div>
      </>}
    </>}

    {report.skipped_files && report.skipped_files.length > 0 &&
      <details className="skipped">
        <summary>{report.skipped_files.length} paper{report.skipped_files.length === 1 ? '' : 's'} not used</summary>
        {/* Saying which papers were unreadable, and why, is the difference
            between "no trends found" and a student believing there are none. */}
        <ul>{report.skipped_files.map((s, i) => <li key={i}><b>{s.file}</b> — {s.reason}</li>)}</ul>
      </details>}
  </section>;
}
