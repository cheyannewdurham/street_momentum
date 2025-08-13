'use client'

import { useEffect, useState } from 'react'

export default function Home() {
  const [api, setApi] = useState('checking...')
  const [products, setProducts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check API health
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`)
      .then(r => r.json())
      .then(d => setApi(d.status || 'unknown'))
      .catch(() => setApi('error'))

    // Load products
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/products`)
      .then(r => r.json())
      .then(setProducts)
      .catch(() => setProducts([]))
      .finally(() => setLoading(false))
  }, [])

  async function buy(productId: string) {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/create-payment-link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: [{ id: productId, quantity: 1 }],
          success_url: `${window.location.origin}/success`,
          cancel_url: `${window.location.origin}/products`
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Checkout failed')
      window.location.href = data.url
    } catch (err: any) {
      alert(err.message || 'Could not start checkout')
    }
  }

  return (
    <main className="p-8 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold">Street Momentum</h1>
      <p className="mt-2">API status: <span className="font-mono">{api}</span></p>

      {loading ? (
        <p className="mt-6 text-gray-500">Loading products…</p>
      ) : products.length === 0 ? (
        <p className="mt-6 text-red-500">No products found.</p>
      ) : (
        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((p) => (
            <div key={p.id} className="border rounded-xl p-4">
              <img
                src={p.image_url}
                alt={p.name}
                className="w-full h-48 object-cover rounded-md"
              />
              <h3 className="mt-3 font-semibold">{p.name}</h3>
              <p className="text-sm text-gray-500">{p.description}</p>
              <div className="mt-3 flex items-center justify-between">
                <span className="font-mono">${(p.price / 100).toFixed(2)}</span>
                <button
                  onClick={() => buy(p.id)}
                  className="px-3 py-1 rounded bg-black text-white hover:bg-gray-800"
                >
                  Buy Now
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  )
}