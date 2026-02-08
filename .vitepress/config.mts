import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  base: '/NotebookLM2PPT/',
  srcDir: "docs",
  head: [['link', { rel: 'icon', href: '/favicon.ico' }]],
  title: "NotebookLM2PPT",
  description: "Công cụ tự động chuyển PDF thành PowerPoint có thể chỉnh sửa",
  themeConfig: {
    
    // https://vitepress.dev/reference/default-theme-config
      nav: [
      { text: 'Trang Chủ', link: '/' },
      { text: 'Hướng Dẫn Người Dùng', items: [
        { text: 'Giới Thiệu Tính Năng', link: '/features' },
        { text: 'Bắt Đầu Nhanh', link: '/quickstart' },
        { text: 'Hướng Dẫn Sử Dụng', link: '/tutorial' },
        { text: 'So Sánh Ví Dụ', link: '/compare' }
      ]},
      { text: 'Tài Liệu Kỹ Thuật', items: [
        { text: 'Nguyên Lý Hoạt Động', link: '/implementation' },
        { text: 'Tối Ưu MinerU', link: '/mineru' },
      ]},
      { text: 'Nhật Ký Cập Nhật', link: '/changelog' }
    ],

    sidebar: [
      {
        text: 'Hướng Dẫn Người Dùng',
        items: [
          { text: 'Trang Chủ', link: '/' },
          { text: 'Giới Thiệu Tính Năng', link: '/features' },
          { text: 'Bắt Đầu Nhanh', link: '/quickstart' },
          { text: 'Hướng Dẫn Sử Dụng', link: '/tutorial' },
          { text: 'So Sánh Ví Dụ', link: '/compare' }
        ]
      },
      {
        text: 'Tài Liệu Kỹ Thuật',
        items: [
          { text: 'Nguyên Lý Hoạt Động', link: '/implementation' },
          { text: 'Tối Ưu MinerU', link: '/mineru' },
        ]
      },
      {
        text: 'Khác',
        items: [
          { text: 'Nhật Ký Cập Nhật', link: '/changelog' }
        ]
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/elliottzheng/NotebookLM2PPT' }
    ],

    logo: '/logo_tiny.png',
    
    footer: {
      message: 'Mở nguồn theo giấy phép MIT',
      copyright: 'Copyright © 2026-Present NotebookLM2PPT'
    },

    search: {
      provider: 'local'
    },

    lastUpdated: {
      text: 'Cập nhật lần cuối',
      formatOptions: {
        dateStyle: 'short',
        timeStyle: 'medium'
      }
    }
  }
})
