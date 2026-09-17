-- Pertanyaan: Kategori produk apa yang paling banyak dibeli, dan berapa porsinya dari total order?
SELECT
    category_english AS category,
    total_orders,
    ROUND(total_orders * 100.0 / SUM(total_orders) OVER (), 1) AS share_pct
FROM mart_top_product_categories
ORDER BY total_orders DESC
LIMIT 10
