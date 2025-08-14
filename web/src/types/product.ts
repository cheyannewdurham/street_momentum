export type Product = {
  id: string
  name: string
  price: number           // cents
  image_url: string
  description?: string
  in_stock?: boolean
}