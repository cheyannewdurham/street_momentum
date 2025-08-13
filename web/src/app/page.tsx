'use client'
import { useEffect, useState } from 'react'

export default function Home() {
  const [api, setApi] = useState('checking...')
  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`)
      .then(r => r.json())
      .then(d => setApi(d.status || 'unknown'))
      .catch(() => setApi('error'))
  }, [])

  return (
    <main className="p-8 max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold">Street Momentum</h1>
      <p className="mt-2">API status: <span className="font-mono">{api}</span></p>
    </main>
  )
}