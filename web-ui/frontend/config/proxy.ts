export default {
  development: {
    '/api': {
      target: 'http://127.0.0.1:5000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    },
    '/ws': {
      target: 'http://127.0.0.1:5000',
      ws: true
    }
  }
}
