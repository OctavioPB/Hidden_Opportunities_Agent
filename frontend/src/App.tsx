import { Suspense, lazy, useState } from 'react'
import Nav from './components/Nav'
import Footer from './components/Footer'
import OpportunitiesPage from './pages/OpportunitiesPage'

// The landing page ships in the main bundle; every other page is fetched the
// first time it is opened.
const AlertFeedPage          = lazy(() => import('./pages/AlertFeedPage'))
const AccuracyPage           = lazy(() => import('./pages/AccuracyPage'))
const ProposalsPage          = lazy(() => import('./pages/ProposalsPage'))
const PilotPage              = lazy(() => import('./pages/PilotPage'))
const MLModelPage            = lazy(() => import('./pages/MLModelPage'))
const TextSignalsPage        = lazy(() => import('./pages/TextSignalsPage'))
const NegotiationPage        = lazy(() => import('./pages/NegotiationPage'))
const InfoPage               = lazy(() => import('./pages/InfoPage'))
const AnalyticsDashboardPage = lazy(() => import('./pages/AnalyticsDashboardPage'))
const ClientDetailPage       = lazy(() => import('./pages/ClientDetailPage'))

export type Page =
  | 'opportunities' | 'text-signals' | 'ml-model'
  | 'negotiation'   | 'proposals'    | 'pilot'
  | 'alert-feed'    | 'accuracy'     | 'info'
  | 'analytics-dashboard' | 'client-detail'

export default function App() {
  const [page,     setPage]     = useState<Page>('opportunities')
  const [clientId, setClientId] = useState<string | null>(null)

  const navigateTo = (p: Page) => {
    setPage(p)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const openClient = (id: string) => {
    setClientId(id)
    navigateTo('client-detail')
  }

  const renderPage = () => {
    if (page === 'client-detail' && clientId) {
      return <ClientDetailPage clientId={clientId} onBack={() => navigateTo('opportunities')} />
    }
    switch (page) {
      case 'opportunities':       return <OpportunitiesPage onSelectClient={openClient} />
      case 'text-signals':        return <TextSignalsPage />
      case 'ml-model':            return <MLModelPage />
      case 'negotiation':         return <NegotiationPage />
      case 'proposals':           return <ProposalsPage />
      case 'pilot':               return <PilotPage />
      case 'alert-feed':          return <AlertFeedPage />
      case 'accuracy':            return <AccuracyPage />
      case 'info':                return <InfoPage />
      case 'analytics-dashboard': return <AnalyticsDashboardPage />
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav currentPage={page} onNavigate={navigateTo} />
      <main style={{ flex: 1 }}>
        <Suspense fallback={<div style={{ padding: 48, fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>Loading…</div>}>
          {renderPage()}
        </Suspense>
      </main>
      <Footer />
    </div>
  )
}
