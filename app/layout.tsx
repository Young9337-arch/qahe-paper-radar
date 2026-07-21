import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'QAHE Paper Radar',
  description: '每日更新的量子反常霍尔效应论文聚合与材料体系分类站'
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
