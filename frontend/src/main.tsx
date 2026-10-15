import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// IBM Plex Sans Hebrew (#330 point 16), bundled and served by the site (invariant 15): only the Hebrew
// and Latin subsets (₪ is in the Hebrew one), each loaded by its unicode-range when the page uses it.
import '@fontsource/ibm-plex-sans-hebrew/hebrew-400.css'
import '@fontsource/ibm-plex-sans-hebrew/hebrew-500.css'
import '@fontsource/ibm-plex-sans-hebrew/hebrew-600.css'
import '@fontsource/ibm-plex-sans-hebrew/hebrew-700.css'
import '@fontsource/ibm-plex-sans-hebrew/latin-400.css'
import '@fontsource/ibm-plex-sans-hebrew/latin-500.css'
import '@fontsource/ibm-plex-sans-hebrew/latin-600.css'
import '@fontsource/ibm-plex-sans-hebrew/latin-700.css'
import './styles/tokens.css'
import './styles/base.css'
import './styles/card.css'
import './styles/post.css'
import './styles/bar.css'
import './styles/forms.css'
import './styles/actions.css'
import './styles/admin.css'
import { App } from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
