'use client'

type Props = { productId: string }

export function BuyButton({ productId }: Props) {
  async function handleClick() {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/create-payment-link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: [{ id: productId, quantity: 1 }],
          success_url: `${window.location.origin}/success`,
          cancel_url: `${window.location.origin}/products`,
        }),
      })
      const data: { url?: string; detail?: string } = await res.json()
      if (!res.ok || !data.url) throw new Error(data.detail || 'Checkout failed')
      window.location.href = data.url
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error creating checkout'
      alert(msg)
    }
  }

  return (
    <button
      onClick={handleClick}
      className="px-3 py-1 rounded bg-black text-white hover:bg-gray-800"
    >
      Buy Now
    </button>
  )
}