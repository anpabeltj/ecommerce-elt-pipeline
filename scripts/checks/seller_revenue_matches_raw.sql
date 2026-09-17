-- Revenue di mart seller harus sama dengan raw order items (order valid saja).
-- Kalau terjadi join fan-out, revenue di mart akan lebih besar dan check ini gagal.
-- Toleransi 0.01 per baris karena pembulatan ROUND.
WITH mart AS (
    SELECT
        SUM(total_revenue) AS revenue,
        COUNT(*) AS n_rows
    FROM mart_seller_performance
),
raw AS (
    SELECT SUM(oi.price + oi.freight_value) AS revenue
    FROM olist_order_items_dataset AS oi
    JOIN olist_orders_dataset AS od
        ON od.order_id = oi.order_id
    WHERE od.order_status NOT IN ('canceled', 'unavailable')
)
SELECT ABS(mart.revenue - raw.revenue) <= mart.n_rows * 0.01 AS seller_revenue_matches_raw
FROM mart, raw;
