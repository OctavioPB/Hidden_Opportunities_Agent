export default function Footer() {
  const month = new Date()
    .toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
    .toUpperCase()

  return (
    <footer style={{
      backgroundColor: 'var(--primary)',
      padding:         '20px 48px',
      display:         'flex',
      justifyContent:  'space-between',
      alignItems:      'center',
      fontFamily:      'var(--fb)',
      fontSize:        9,
      letterSpacing:   '3px',
      textTransform:   'uppercase',
      color:           'rgba(255,255,255,0.35)',
      marginTop:       64,
    }}>
      <span>OPB · OCTAVIO PÉREZ BRAVO · HIDDEN OPPORTUNITIES</span>
      <span>{month}</span>
    </footer>
  )
}
