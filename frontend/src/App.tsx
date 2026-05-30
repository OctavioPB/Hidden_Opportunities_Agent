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
import AnalyticsDashboardPage from './pages/AnalyticsDashboardPage'
import ClientDetailPage from './pages/ClientDetailPage'

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
      <main style={{ flex: 1 }}>{renderPage()}</main>
      <Footer />
    </div>
  )
}
