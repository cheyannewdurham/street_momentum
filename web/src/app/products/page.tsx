import { BuyButton } from '../components/BuyButton'

export default async function ProductsPage() {
  const base = process.env.NEXT_PUBLIC_API_URL!
  const res = await fetch(`${base}/products`, { next: { revalidate: 60 } })
  const products = await res.json()

  return (
    <main className="p-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {products.map((p: any) => (
        <div key={p.id} className="border rounded-xl p-4">
          <img src={p.image_url} alt={p.name} className="w-full h-48 object-cover rounded-md" />
          <h3 className="mt-3 font-semibold">{p.name}</h3>
          <p className="text-sm text-gray-500">{p.description}</p>
          <div className="mt-3 flex items-center justify-between">
            <span className="font-mono">${(p.price/100).toFixed(2)}</span>
            <BuyButton productId={p.id} />
          </div>
        </div>
      ))}
    </main>
  )
}