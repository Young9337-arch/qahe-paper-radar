'use client';

import { useEffect, useMemo, useState } from 'react';
import { CalendarDays, ExternalLink, Images, Search, Sparkles, X } from 'lucide-react';

type Paper = {
  id: string;
  title: string;
  authors: string[];
  affiliations?: string[];
  abstract: string;
  journal: string;
  published: string;
  url: string;
  doi?: string | null;
  source: string;
  material_system: string;
  image_url?: string | null;
  figure_urls?: string[];
  figure_captions?: string[];
  ai_summary?: string;
};

type DB = { updated_at: string; papers: Paper[] };

const labels: Record<string, string> = {
  All: 'All systems',
  MnBi2Te4_MTI: 'MnBi2Te4 magnetic TI',
  Moire_Superlattice: 'Moire superlattice',
  Kagome_Lattice: 'Kagome lattice',
  Oxide_Heterostructure: 'Oxide interface',
  Other_New_Materials: 'Other materials'
};

const colors: Record<string, string> = {
  MnBi2Te4_MTI: 'bg-fuchsia-100 text-fuchsia-800',
  Moire_Superlattice: 'bg-cyan-100 text-cyan-800',
  Kagome_Lattice: 'bg-amber-100 text-amber-800',
  Oxide_Heterostructure: 'bg-rose-100 text-rose-800',
  Other_New_Materials: 'bg-slate-100 text-slate-700'
};

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || '';
const fallback = `${basePath}/data/qahe-placeholder.svg`;

const asset = (src: string | null | undefined) => src?.startsWith('/') ? basePath + src : (src || fallback);
const badImage = (src: string | null | undefined) => !src || /arxiv-logo|ar5iv_card|favicon/i.test(src);
const figures = (p: Paper) => Array.from(new Set([...(p.figure_urls || []), p.image_url].filter((x): x is string => !!x && !badImage(x))));

const repair = (value = '') => value
  .replace(/\\\(|\\\)|\\\[|\\\]/g, '')
  .replace(/\\(mathbf|mathrm|text)\s*/g, '')
  .replace(/\\times/g, 'x').replace(/\\pm/g, '±').replace(/\\alpha/g, 'α').replace(/\\beta/g, 'β')
  .replace(/\\mu/g, 'μ').replace(/\\nu/g, 'ν').replace(/\\theta/g, 'θ').replace(/\\pi/g, 'π')
  .replace(/\\sigma/g, 'σ').replace(/\\Delta/g, 'Δ').replace(/\\hbar/g, 'ℏ')
  .replace(/\$+/g, '').replace(/\{([^{}]*)\}/g, '$1')
  .replace(/moir\u8305/g, 'moiré').replace(/Sierpi\u8245ski/g, 'Sierpiński')
  .replace(/\u922d\?/g, '−').replace(/\u9225\?/g, '–').replace(/\u9225/g, '’').replace(/\u63b3/g, '°').replace(/\u5364/g, '±')
  .replace(/\u8c13/g, 'ν').replace(/\u80c3/g, 'θ').replace(/\u6e2d/g, 'μ').replace(/\u8796/g, 'Δ')
  .replace(/\u87fa/g, 'π').replace(/\u87fd/g, 'σ').replace(/\u4f2a/g, 'α').replace(/\u8795/g, 'Γ').replace(/\u87ff/g, 'τ')
  .replace(/\s+/g, ' ')
  .trim();

const captionFor = (paper: Paper, index: number) => repair(paper.figure_captions?.[index] || 'Caption was not extracted for this figure.');

export default function Home() {
  const [db, setDb] = useState<DB>({ updated_at: '', papers: [] });
  const [q, setQ] = useState('');
  const [s, setS] = useState('All');
  const [err, setErr] = useState(false);
  const [selected, setSelected] = useState<Paper | null>(null);

  useEffect(() => {
    fetch(`${basePath}/data/papers.json`)
      .then(r => r.json())
      .then((d: DB) => setDb({
        ...d,
        papers: d.papers.map(p => ({
          ...p,
          title: repair(p.title),
          abstract: repair(p.abstract),
          ai_summary: repair(p.ai_summary || ''),
          journal: repair(p.journal),
          authors: p.authors.map(repair),
          figure_captions: (p.figure_captions || []).map(repair)
        }))
      }))
      .catch(() => setErr(true));
  }, []);

  const shown = useMemo(() => db.papers.filter(p =>
    (s === 'All' || p.material_system === s) &&
    `${p.title} ${p.abstract} ${p.ai_summary || ''} ${p.authors.join(' ')}`.toLowerCase().includes(q.toLowerCase())
  ), [db, q, s]);

  return <main className="min-h-screen bg-[#f6f8fb] text-slate-900">
    <header className="hero">
      <div className="mx-auto max-w-7xl px-6 py-16">
        <div className="flex items-center gap-3 text-cyan-700"><Sparkles size={20}/><span className="text-xs font-bold uppercase tracking-[.3em]">Quantum materials intelligence</span></div>
        <h1 className="mt-5 text-5xl font-semibold tracking-tight md:text-7xl">QAHE <span className="text-cyan-700">Paper Radar</span></h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">A daily, curated index of quantum anomalous Hall research.</p>
        <div className="mt-8 flex gap-8 text-sm text-slate-500"><span>{db.papers.length} papers indexed</span><span className="flex items-center gap-2"><CalendarDays size={16}/> {db.updated_at ? new Date(db.updated_at).toLocaleDateString('en-US') : 'Updating'}</span></div>
      </div>
    </header>

    <section className="mx-auto max-w-7xl px-6 py-10">
      <div className="mb-8 grid gap-4 md:grid-cols-[1fr_280px]">
        <label className="glass flex items-center gap-3 px-5"><Search size={19} className="text-cyan-700"/><input className="w-full bg-transparent py-4 outline-none" placeholder="Search title, author, abstract..." value={q} onChange={e => setQ(e.target.value)}/></label>
        <select className="glass px-5 py-4 outline-none" value={s} onChange={e => setS(e.target.value)}>{Object.entries(labels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
      </div>
      {err && <p className="mb-6 text-rose-600">Unable to load paper data.</p>}
      <div className="grid gap-7 lg:grid-cols-2">{shown.map(p => {
        const imgs = figures(p);
        return <article key={p.id} className="card paper-card overflow-hidden"><button type="button" onClick={() => setSelected(p)} className="block w-full text-left">
          <figure className="relative bg-slate-50">
            <div className="flex h-72 items-center justify-center border-b border-slate-100 p-4"><img src={asset(imgs[0])} alt={`${p.title} main figure`} loading="lazy" decoding="async" className="h-full w-full object-contain" onError={e => { e.currentTarget.onerror = null; e.currentTarget.src = fallback; }}/></div>
            <figcaption className="absolute bottom-3 right-3 flex items-center gap-2 rounded-full bg-slate-950/75 px-3 py-1 text-[11px] font-medium text-white backdrop-blur"><Images size={13}/>{imgs.length ? `${imgs.length} figure${imgs.length > 1 ? 's' : ''}` : 'No figure'}</figcaption>
            <div className={`absolute left-4 top-4 rounded-full px-3 py-1 text-xs font-semibold ${colors[p.material_system] || 'bg-white text-slate-700'} backdrop-blur`}>{labels[p.material_system] || p.material_system}</div>
          </figure>
          <div className="p-7">
            <div className="mb-3 flex gap-3 text-xs uppercase tracking-widest text-slate-400"><span>{p.source}</span><span>·</span><span>{p.journal}</span></div>
            <h2 className="text-2xl font-medium leading-tight text-slate-900">{p.title}</h2>
            <p className="mt-4 text-sm leading-6 text-slate-600"><strong className="text-slate-900">Authors</strong> | {p.authors.join(', ') || 'Not listed'}</p>
            <p className="mt-4 rounded-xl bg-cyan-50 p-4 text-sm leading-6 text-slate-700"><strong className="text-cyan-800">AI summary</strong> | {p.ai_summary || 'Summary unavailable.'}</p>
            <p className="mt-5 text-sm font-semibold text-cyan-700">{imgs.length ? 'Click to view all figures, captions, and abstract' : 'Click to see why figures are unavailable'}</p>
            <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-5 text-xs text-slate-500"><span>{p.published}</span><span className="flex items-center gap-2 font-semibold text-cyan-700">Open details <ExternalLink size={15}/></span></div>
          </div>
        </button></article>;
      })}</div>
    </section>

    <footer className="border-t border-slate-200 bg-white py-10 text-center text-xs text-slate-500">QAHE Paper Radar | Automated open-research index</footer>
    {selected && <Detail paper={selected} onClose={() => setSelected(null)}/>}
  </main>;
}

function Detail({ paper, onClose }: { paper: Paper; onClose: () => void }) {
  const imgs = figures(paper);
  return <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/70 p-4 backdrop-blur-sm md:p-8">
    <div className="mx-auto max-w-6xl rounded-2xl bg-white shadow-2xl">
      <div className="sticky top-0 z-10 flex items-start justify-between gap-5 border-b border-slate-200 bg-white/95 p-5 backdrop-blur">
        <div><p className="text-xs uppercase tracking-widest text-slate-400">{paper.source} · {paper.published}</p><h3 className="mt-2 text-2xl font-semibold leading-tight">{paper.title}</h3></div>
        <button type="button" onClick={onClose} className="rounded-full border border-slate-200 p-2 text-slate-600 hover:bg-slate-50" aria-label="Close"><X size={20}/></button>
      </div>
      <div className="grid gap-8 p-5 lg:grid-cols-[1fr_340px]">
        <section>
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-700"><Images size={18}/><span>All figures ({imgs.length})</span></div>
          {imgs.length ? <div className="grid gap-5">{imgs.map((src, i) => <figure key={src} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <img src={asset(src)} alt={`${paper.title} figure ${i + 1}`} className="max-h-[720px] w-full object-contain" loading="lazy" decoding="async" onError={e => { e.currentTarget.onerror = null; e.currentTarget.src = fallback; }}/>
            <figcaption className="mt-3 rounded-lg bg-white p-3 text-sm leading-6 text-slate-600"><span className="font-semibold text-slate-900">Figure {i + 1}.</span> {captionFor(paper, i)}</figcaption>
          </figure>)}</div> : <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-sm leading-7 text-slate-500"><p className="font-semibold text-slate-700">No extracted figure is available for this article yet.</p><p className="mt-2">This usually happens when the publisher page hides figures behind scripts or access controls, or when an arXiv PDF stores diagrams as vector drawing commands instead of embedded images.</p></div>}
        </section>
        <aside>
          <h4 className="text-sm font-semibold text-slate-900">AI Summary</h4><p className="mt-3 rounded-xl bg-cyan-50 p-4 text-sm leading-7 text-slate-700">{paper.ai_summary || 'Summary unavailable.'}</p>
          <h4 className="mt-6 text-sm font-semibold text-slate-900">Abstract</h4><p className="mt-3 text-sm leading-7 text-slate-600">{paper.abstract || 'Abstract unavailable.'}</p>
          <h4 className="mt-6 text-sm font-semibold text-slate-900">Authors</h4><p className="mt-3 text-sm leading-6 text-slate-600">{paper.authors.join(', ') || 'Not listed'}</p>
          {paper.affiliations && paper.affiliations.length > 0 && <><h4 className="mt-6 text-sm font-semibold text-slate-900">Affiliations</h4><p className="mt-3 text-sm leading-6 text-slate-600">{paper.affiliations.join('; ')}</p></>}
          <a href={paper.url} target="_blank" rel="noreferrer" className="mt-8 inline-flex items-center gap-2 rounded-full bg-cyan-700 px-5 py-3 text-sm font-semibold text-white hover:bg-cyan-800">Open article <ExternalLink size={16}/></a>
        </aside>
      </div>
    </div>
  </div>;
}
