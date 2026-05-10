import React from 'react'

export default function LoadingScreen() {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      background: 'var(--bg-primary)',
    }}>
      <div style={{
        textAlign: 'center',
      }}>
        <div style={{
          fontSize: '48px',
          marginBottom: '16px',
          animation: 'pulse 1.5s ease-in-out infinite',
        }}>
          🍿
        </div>
        <p style={{
          color: 'var(--text-secondary)',
          fontSize: '14px',
        }}>
          جاري التحميل...
        </p>
      </div>
    </div>
  )
}
