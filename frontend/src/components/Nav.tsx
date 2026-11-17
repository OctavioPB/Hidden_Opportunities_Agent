import { useState } from 'react'
import type { Page } from '../App'
import { useTheme } from '../hooks/useTheme'

type NavGroupDef = { label: string; pages: { id: Page; label: string }[] }

const GROUPS: NavGroupDef[] = [
  {
    label: 'Intelligence',
    pages: [
      { id: 'opportunities', label: 'Opportunities' },
      { id: 'text-signals',  label: 'Text Signals'  },
      { id: 'ml-model',      label: 'ML Model'       },
    ],
  },
  {
    label: 'Deal Pipeline',
    pages: [
      { id: 'negotiation', label: 'Negotiation' },
      { id: 'proposals',   label: 'Proposals'   },
      { id: 'pilot',       label: 'Pilot Demo'  },
    ],
  },
  {
    label: 'Analytics',
    pages: [
      { id: 'analytics-dashboard', label: 'ROI Dashboard' },
      { id: 'alert-feed',          label: 'Alert Feed'    },
      { id: 'accuracy',            label: 'Accuracy'      },
    ],
  },
  {
    label: 'System',
    pages: [
      { id: 'info', label: 'Overview' },
    ],
  },
]

function NavGroup({ group, currentPage, onNavigate }: {
  group: NavGroupDef
  currentPage: Page
  onNavigate: (p: Page) => void
}) {
  const [open, setOpen] = useState(false)
  const isActive = group.pages.some(p => p.id === currentPage)

  const btnStyle: React.CSSProperties = {
    background:      'none',
    border:          'none',
    cursor:          'pointer',
    fontFamily:      'var(--fb)',
    fontSize:        9,
    fontWeight:      500,
    letterSpacing:   '2px',
    textTransform:   'uppercase',
    padding:         '5px 10px',
    borderRadius:    'var(--radius-sm)',
    color:           isActive ? 'var(--gold-light)' : open ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.45)',
    backgroundColor: isActive ? 'rgba(201,168,76,0.12)' : open ? 'rgba(255,255,255,0.05)' : 'transparent',
    display:         'flex',
    alignItems:      'center',
    gap:             5,
    transition:      'color 0.15s, background-color 0.15s',
    whiteSpace:      'nowrap',
  }

  return (
    <div
      style={{ position: 'relative', alignSelf: 'stretch', display: 'flex', alignItems: 'center' }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button style={btnStyle}>
        {group.label}
        <span style={{
          fontSize:   7,
          opacity:    0.55,
          display:    'inline-block',
          transform:  open ? 'rotate(180deg)' : 'none',
          transition: 'transform 0.15s',
        }}>▾</span>
      </button>

      {open && (
        <div style={{
          position:        'absolute',
          top:             'calc(100% + 1px)',
          left:            0,
          backgroundColor: 'rgba(0,32,76,0.98)',
          backdropFilter:  'blur(16px)',
          border:          '1px solid rgba(255,255,255,0.1)',
          borderRadius:    'var(--radius-md)',
          boxShadow:       '0 8px 32px rgba(0,0,0,0.45)',
          padding:         '6px',
          minWidth:        156,
          zIndex:          1000,
          display:         'flex',
          flexDirection:   'column',
          gap:             2,
        }}>
          {group.pages.map(p => (
            <DropdownItem
              key={p.id}
              label={p.label}
              isActive={currentPage === p.id}
              onClick={() => { onNavigate(p.id); setOpen(false) }}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function DropdownItem({ label, isActive, onClick }: {
  label: string; isActive: boolean; onClick: () => void
}) {
  const [hovered, setHovered] = useState(false)
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background:      'none',
        border:          'none',
        cursor:          'pointer',
        width:           '100%',
        textAlign:       'left',
        fontFamily:      'var(--fb)',
        fontSize:        11,
        fontWeight:      isActive ? 600 : 400,
        letterSpacing:   '0.5px',
        color:           isActive ? 'var(--gold-light)' : hovered ? '#fff' : 'rgba(255,255,255,0.65)',
        backgroundColor: isActive ? 'rgba(201,168,76,0.10)' : hovered ? 'rgba(255,255,255,0.06)' : 'transparent',
        padding:         '7px 12px',
        borderRadius:    6,
        transition:      'background-color 0.1s, color 0.1s',
        whiteSpace:      'nowrap',
      }}
    >
      {label}
    </button>
  )
}

export default function Nav({ currentPage, onNavigate }: {
  currentPage: Page
  onNavigate: (p: Page) => void
}) {
  const { theme, toggleTheme } = useTheme()

  return (
    <nav style={{
      backgroundColor: 'rgba(0,51,102,0.97)',
      backdropFilter:  'blur(12px)',
      height:          'var(--nav-height)',
      position:        'sticky',
      top:             0,
      zIndex:          999,
      borderBottom:    '1px solid rgba(255,255,255,0.08)',
      padding:         '0 40px',
      display:         'flex',
      alignItems:      'center',
      justifyContent:  'space-between',
    }}>
      {/* Left — OPB monogram + app title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
          <span style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, color: '#fff', lineHeight: 1 }}>O</span>
          <em style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, fontStyle: 'italic', color: 'var(--gold-light)', lineHeight: 1 }}>PB</em>
        </div>
        <div style={{ width: 1, height: 16, backgroundColor: 'rgba(255,255,255,0.12)', flexShrink: 0 }} />
        <span style={{
          fontFamily:    'var(--fb)',
          fontSize:      9,
          letterSpacing: '3px',
          textTransform: 'uppercase',
          color:         'rgba(255,255,255,0.4)',
          whiteSpace:    'nowrap',
        }}>
          Hidden Opportunities Agent
        </span>
      </div>

      {/* Right — nav groups + demo badge + theme toggle */}
      <div style={{ display: 'flex', alignItems: 'stretch', gap: 4 }}>
        {GROUPS.map(g => (
          <NavGroup key={g.label} group={g} currentPage={currentPage} onNavigate={onNavigate} />
        ))}

        <span style={{
          fontFamily:    'var(--fb)',
          fontSize:      8,
          letterSpacing: '2px',
          textTransform: 'uppercase',
          color:         'rgba(232,196,106,0.55)',
          marginLeft:    12,
          whiteSpace:    'nowrap',
          alignSelf:     'center',
        }}>
          DEMO
        </span>

        <button
          style={{
            background:      'none',
            backgroundColor: 'transparent',
            border:          'none',
            color:           'rgba(255,255,255,0.45)',
            cursor:          'pointer',
            fontSize:        14,
            padding:         '3px 8px',
            borderRadius:    'var(--radius-sm)',
            marginLeft:      8,
            alignSelf:       'center',
          }}
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? '☀' : '◑'}
        </button>
      </div>
    </nav>
  )
}
