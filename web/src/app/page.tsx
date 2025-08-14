'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

type ApiStatus = 'ok' | 'error' | 'checking...'

export default function Home() {
  const [api, setApi] = useState<ApiStatus>('checking...')

  useEffect(() => {
    async function check() {
      try {
        const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`)
        const d: { status?: string } = await r.json()
        setApi(d.status === 'ok' ? 'ok' : 'error')
      } catch {
        setApi('error')
      }
    }
    check()
  }, [])

  return (
    <main className="p-8 max-w-5xl mx-auto">
      <header className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Street Momentum</h1>
        <span
          className={[
            'rounded px-2 py-1 text-xs font-mono',
            api === 'ok' && 'bg-green-100 text-green-700',
            api === 'error' && 'bg-red-100 text-red-700',
            api === 'checking...' && 'bg-gray-100 text-gray-700',
          ]
            .filter(Boolean)
            .join(' ')}
        >
          API: {api}
        </span>
      </header>

      <section className="mt-8 grid gap-6 md:grid-cols-2 items-center">
        <div>
          <h2 className="text-2xl font-semibold">Motorsport-inspired apparel & decals</h2>
          <p className="mt-2 text-gray-600">
            Fresh drops, clean lines, and community events. Browse products and check out securely
            via Square.
          </p>
          <div className="mt-6 flex gap-3">
            <Link
              href="/products"
              className="inline-block rounded-lg bg-black px-5 py-2.5 text-white hover:bg-gray-800"
            >
              Shop Now
            </Link>
            <Link
              href="/about"
              className="inline-block rounded-lg border px-5 py-2.5 hover:bg-gray-50"
            >
              About Us
            </Link>
          </div>
        </div>

        {/* Placeholder hero block; swap for an Image when you have assets */}
        <div className="h-56 w-full rounded-2xl border bg-gradient-to-br from-gray-50 to-gray-100" />
      </section>

      <section className="mt-12">
        <h3 className="text-lg font-semibold">Upcoming</h3>
        <ul className="mt-2 list-disc pl-5 text-gray-600">
          <li>Pop-up meet & merch table — see our calendar of events soon.</li>
          <li>New banner colors & sticker packs.</li>
        </ul>
      </section>
    </main>
  )
}