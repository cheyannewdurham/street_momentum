import Image from 'next/image'
import { BuyButton } from '@/components/BuyButton'
import type { Product } from '@/types/product'

export default async function ProductsPage() {
  const base = process.env.NEXT_PUBLIC_API_URL!
  const res = await fetch(`${base}/products`, { next: { revalidate: 60 } })
  const products: Product[] = await res.json()

  return (
    <main className="p-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {products.map((p) => (
        <div key={p.id} className="border rounded-xl p-4">
          <div className="relative w-full h-48">
            <Image
              src={p.image_url}
              alt={p.name}
              fill
              className="object-cover rounded-md"
              sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
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