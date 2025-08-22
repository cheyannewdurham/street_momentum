// web/app/products/page.tsx
import Image from 'next/image'
import { BuyButton } from '@/components/BuyButton'

// ⬇️ Don't pre-render with data at build time.
// This avoids Vercel failing when Render is asleep.
export const dynamic = 'force-dynamic'      // or: export const revalidate = 0

type Product = {
  id: string
  name: string
  description?: string
  image_url: string
  price: number   // cents
  in_stock: boolean
}

export default async function ProductsPage() {
  const base = process.env.NEXT_PUBLIC_API_URL || ''
  let products: Product[] = []

  try {
    const res = await fetch(`${base}/products`, { cache: 'no-store' })
    if (res.ok) {
      products = await res.json()
    }
  } catch {
    // leave products empty; UI shows a friendly message
  }

  return (
    <main className="p-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {products.length === 0 && (
        <p className="col-span-full text-sm text-gray-400">
          Products are temporarily unavailable. Please try again soon.
        </p>
      )}

      {products.map((p) => (
        <div key={p.id} className="border rounded-xl p-4">
          <div className="w-full h-48 relative">
            <Image
              src={p.image_url}
              alt={p.name}
              fill
              sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
              className="object-cover rounded-md"
            />
          </div>

          <h3 className="mt-3 font-semibold">{p.name}</h3>
          <p className="text-sm text-gray-500">{p.description}</p>

          <div className="mt-3 flex items-center justify-between">
            <span className="font-mono">${(p.price / 100).toFixed(2)}</span>
            <BuyButton productId={p.id} />
          </div>
        </div>
      ))}
    </main>
  )
}