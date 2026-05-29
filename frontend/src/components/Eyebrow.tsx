export default function Eyebrow({ children, light = false }: {
  children: React.ReactNode
  light?: boolean
}) {
  const color = light ? 'var(--gold-light)' : 'var(--gold)'
  return (
    <div style={{
      display:       'inline-flex',
      alignItems:    'center',
      gap:           8,
      fontFamily:    'var(--fb)',
      fontSize:      9,
      fontWeight:    500,
      letterSpacing: '4px',
      textTransform: 'uppercase',
      color,
      marginBottom:  10,
    }}>
      <div style={{ width: 24, height: 1, flexShrink: 0, backgroundColor: color }} />
      {children}
    </div>
  )
}
