-- Revenue per bulan, tidak termasuk order canceled dan unavailable
DROP TABLE IF EXISTS mart_revenue_by_month;
CREATE TABLE mart_revenue_by_month AS
SELECT
    DATE_TRUNC('month', od.order_purchase_timestamp::TIMESTAMP)::DATE AS date,
    ROUND(SUM(op.payment_value)::NUMERIC, 2) AS total_revenue
FROM olist_orders_dataset AS od
JOIN olist_order_payments_dataset AS op
    ON od.order_id = op.order_id
WHERE od.order_status NOT IN ('canceled', 'unavailable')
GROUP BY 1
ORDER BY 1;

-- Jumlah order unik per kategori
-- LEFT JOIN supaya kategori tanpa terjemahan atau produk tanpa kategori tidak hilang
DROP TABLE IF EXISTS mart_top_product_categories;
CREATE TABLE mart_top_product_categories AS
SELECT
    COALESCE(pc.product_category_name_english, p.product_category_name, 'unknown') AS category_english,
    COALESCE(p.product_category_name, 'unknown') AS category_portuguese,
    COUNT(DISTINCT oi.order_id) AS total_orders
FROM olist_order_items_dataset AS oi
JOIN olist_orders_dataset AS od
    ON od.order_id = oi.order_id
JOIN olist_products_dataset AS p
    ON oi.product_id = p.product_id
LEFT JOIN product_category_name_translation AS pc
    ON p.product_category_name = pc.product_category_name
WHERE od.order_status NOT IN ('canceled', 'unavailable')
GROUP BY 1, 2
ORDER BY total_orders DESC;

-- Grain: satu baris = satu seller per order, baru di-agregasi per seller
-- Revenue dari price + freight di order items karena payment_value adalah nilai per order
DROP TABLE IF EXISTS mart_seller_performance;
CREATE TABLE mart_seller_performance AS
WITH seller_orders AS (
    SELECT
        oi.seller_id,
        oi.order_id,
        SUM(oi.price + oi.freight_value) AS revenue
    FROM olist_order_items_dataset AS oi
    JOIN olist_orders_dataset AS od
        ON od.order_id = oi.order_id
    WHERE od.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY oi.seller_id, oi.order_id
),
reviews_per_order AS (
    SELECT
        order_id,
        AVG(review_score) AS review_score
    FROM olist_order_reviews_dataset
    GROUP BY order_id
)
SELECT
    so.seller_id,
    COUNT(so.order_id) AS total_orders,
    ROUND(SUM(so.revenue)::NUMERIC, 2) AS total_revenue,
    ROUND(AVG(r.review_score)::NUMERIC, 2) AS average_review_score
FROM seller_orders AS so
LEFT JOIN reviews_per_order AS r
    ON r.order_id = so.order_id
GROUP BY so.seller_id
ORDER BY total_revenue DESC;