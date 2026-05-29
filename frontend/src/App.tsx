import { useState } from 'react'
import Nav from './components/Nav'
import Footer from './components/Footer'
import OpportunitiesPage from './pages/OpportunitiesPage'
import AlertFeedPage from './pages/AlertFeedPage'
import AccuracyPage from './pages/AccuracyPage'
import ProposalsPage from './pages/ProposalsPage'
import PilotPage from './pages/PilotPage'
import MLModelPage from './pages/MLModelPage'
import TextSignalsPage from './pages/TextSignalsPage'
import NegotiationPage from './pages/NegotiationPage'
import InfoPage from './pages/InfoPage'

export type Page =
  | 'opportunities' | 'text-signals' | 'ml-model'
  | 'negotiation'   | 'proposals'    | 'pilot'
  | 'alert-feed'    | 'accuracy'     | 'info'

function renderPage(page: Page) {
  switch (page) {
    case 'opportunities': return <OpportunitiesPage />
    case 'text-signals':  return <TextSignalsPage />
    case 'ml-model':      return <MLModelPage />
    case 'negotiation':   return <NegotiationPage />
    case 'proposals':     return <ProposalsPage />
    case 'pilot':         return <PilotPage />
    case 'alert-feed':    return <AlertFeedPage />
    case 'accuracy':      return <AccuracyPage />
    case 'info':          return <InfoPage />
  }
}

export default function App() {
  const [page, setPage] = useState<Page>('opportunities')
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav currentPage={page} onNavigate={setPage} />
      <main style={{ flex: 1 }}>{renderPage(page)}</main>
      <Footer />
    </div>
  )
}
