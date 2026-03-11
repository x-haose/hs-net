import * as path from 'node:path';
import { defineConfig } from '@rspress/core';

export default defineConfig({
  root: path.join(__dirname, 'docs'),
  title: 'hs-net',
  description: '统一多引擎的增强型 HTTP 客户端',
  icon: '/rspress-icon.png',
  logo: {
    light: '/rspress-light-logo.png',
    dark: '/rspress-dark-logo.png',
  },
  themeConfig: {
    darkMode: true,
    socialLinks: [
      {
        icon: 'github',
        mode: 'link',
        content: 'https://github.com/x-haose/hs-net',
      },
    ],
    footer: {
      message: 'Released under the MIT License.',
    },
  },
  markdown: {
    showLineNumbers: true,
  },
});
