import type { Config } from 'tailwindcss';
export default { content: ['./app/**/*.{js,ts,jsx,tsx}'], theme: { extend: { colors: { ink: '#101828', paper: '#f7f8fa', accent: '#5b5bd6' } } }, plugins: [] } satisfies Config;
