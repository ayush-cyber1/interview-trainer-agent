/// <reference types="vite/client" />

// Tell TypeScript that *.module.css imports are valid and return a string-keyed object
declare module '*.module.css' {
  const classes: Record<string, string>
  export default classes
}

// Plain CSS imports (non-module)
declare module '*.css' {
  const css: string
  export default css
}
