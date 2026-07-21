'use client';

import { useEffect, useMemo, useState } from 'react';
import { BookOpen, CalendarDays, ExternalLink, Search, SlidersHorizontal } from 'lucide-react';

type Paper = { id: string; title: string; authors: string[]; abstract: string; journal: string; published: string; url: string; doi?: string | null; source: string; material_system: string; image_url?: string | null };
type Database = { updated_at: string; papers: Paper[] };

const labels: Record<string, string> = {
  All: 'All systems', MnBi2Te4_MTI: 'MnBi2Te4 / magnetic TI', Moire_Superlattice: 'Moire superlattices', Kagome_Lattice: 'Kagome lattices', Oxide_Heterostructure: 'Oxide interfaces', Other_New_Materials: 'Other new materials'
};
/*
  All: '全部体系', MnBi2Te4_MTI: '锰铋泰与磁性拓扑绝缘体', Moire_Superlattice: '转角与摩尔超晶格',
  Kagome_Lattice: '笼目晶格', Oxide_Heterostructure: '氧化物与界面磁性', Other_New_Materials: '其他与新型材料'
*/
const colors: Record<string, string> = { MnBi2Te4_MTI: 'bg-violet-50 text-violet-700', Moire_Superlattice: 'bg-cyan-50 text-cyan-700', Kagome_Lattice: 'bg-amber-50 text-amber-700', Oxide_Heterostructure: 'bg-rose-50 text-rose-700', Other_New_Materials: 'bg-slate-100 text-slate-700' };

export default function Home() {
  const [db, setDb] = useState<Database>({ updated_at: '', papers: [] });
  const [query, setQuery] = useState('');
  const [system, setSystem] = useState('All');
  const [error, setError] = useState(false);
  useEffect(() => { fetch(`${process.env.NEXT_PUBLIC_BASE_PATH || ''}/data/papers.json`).then(r => { if (!r.ok) throw new Error(); return r.json(); }).then(setDb).catch(() => setError(true)); }, []);
  const shown = useMemo(() => db.papers.filter(p => (system === 'All' || p.material_system === system) && `${p.title} ${p.abstract} ${p.authors.join(' ')}`.toLowerCase().includes(query.toLowerCase())), [db, query, system]);

  return <main className="min-h-screen">
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto max-w-7xl px-5 py-12 md:py-16">
        <div className="mb-4 flex items-center gap-3 text-accent"><BookOpen size={30}/><span className="text-sm font-semibold uppercase tracking-[.22em]">Open Research Index</span></div>
        <h1 className="text-4xl font-bold tracking-tight text-ink md:text-6xl">QAHE Paper Radar</h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-600">量子反常霍尔效应论文雷达：聚合预印本与期刊 Online / Early View 文章，并按材料体系自动归类。</p>
        <div className="mt-7 flex flex-wrap gap-5 text-sm text-slate-500"><span>{db.papers.length} 篇论文</span><span className="flex items-center gap-1.5"><CalendarDays size={15}/>更新于 {db.updated_at ? new Date(db.updated_at).toLocaleString('zh-CN') : '加载中'}</span></div>
      </div>
    </header>
    <section className="mx-auto max-w-7xl px-5 py-8">
      <div className="mb-7 grid gap-3 md:grid-cols-[1fr_auto]">
        <label className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 shadow-sm"><Search className="text-slate-400" size={19}/><input aria-label="搜索论文" className="w-full bg-transparent py-3.5 outline-none" placeholder="搜索标题、摘要或作者…" value={query} onChange={e => setQuery(e.target.value)}/></label>
        <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 shadow-sm"><SlidersHorizontal size={18}/><select aria-label="材料体系" className="bg-transparent py-3.5 outline-none" value={system} onChange={e => setSystem(e.target.value)}>{Object.entries(labels).map(([k,v]) => <option key={k} value={k}>{v}</option>)}</select></label>
      </div>
      {error && <p className="rounded-xl bg-red-50 p-4 text-red-700">数据加载失败，请稍后重试。</p>}
      <div className="grid gap-5 lg:grid-cols-2">{shown.map(p => <article key={p.id} className="paper-card overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {p.image_url && <img src={p.image_url} alt="论文主图" loading="lazy" referrerPolicy="no-referrer" className="h-48 w-full bg-slate-100 object-cover" onError={e => { e.currentTarget.style.display='none'; }}/>} 
        <div className="p-6"><div className="mb-3 flex flex-wrap items-center gap-2"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${colors[p.material_system] || colors.Other_New_Materials}`}>{labels[p.material_system] || p.material_system}</span><span className="text-xs font-medium uppercase tracking-wide text-slate-400">{p.source}</span></div>
        <h2 className="text-xl font-bold leading-snug text-ink">{p.title}</h2><p className="mt-2 text-sm text-slate-500">{p.authors.slice(0, 5).join(', ')}{p.authors.length > 5 ? ' 等' : ''}</p>
        <p className="mt-4 line-clamp-4 text-sm leading-6 text-slate-600">{p.abstract || '暂无摘要'}</p>
        <div className="mt-5 flex items-end justify-between gap-3 border-t border-slate-100 pt-4"><div className="text-xs text-slate-500"><div className="font-semibold text-slate-700">{p.journal}</div><time>{p.published}</time></div><a href={p.url} target="_blank" rel="noopener noreferrer" className="flex shrink-0 items-center gap-1.5 text-sm font-semibold text-accent">阅读全文 <ExternalLink size={15}/></a></div></div>
      </article>)}</div>
      {!error && shown.length === 0 && <p className="py-20 text-center text-slate-500">没有找到匹配的论文。</p>}
    </section>
    <footer className="mt-10 border-t border-slate-200 bg-white py-8 text-center text-sm text-slate-500">数据来自 arXiv 与 Crossref · 自动分类结果仅供检索参考</footer>
  </main>;
}
