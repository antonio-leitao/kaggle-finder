import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// If deploying to https://<user>.github.io/<repo>, set BASE_PATH=/repo at build time.
// For a user/org page (https://<user>.github.io/) leave it empty.
const dev = process.argv.includes('dev');
const BASE_PATH = dev ? '' : (process.env.BASE_PATH ?? '');

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      pages: 'build',
      assets: 'build',
      fallback: '404.html',
      precompress: false,
      strict: true
    }),
    paths: { base: BASE_PATH },
    // GitHub Pages requires a .nojekyll file; we ship one in /static.
    prerender: { entries: ['*'] }
  }
};

export default config;
