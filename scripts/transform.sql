CREATE TABLE mart_revenue_by_month AS SELECT
DATE_TRUNC('month', od.order_purchase_timestamp::TIMESTAMP)::DATE AS date,
ROUND(SUM(op.payment_value)::NUMERIC, 2) AS total_revenue
FROM olist_orders_dataset AS od 
JOIN olist_order_payments_dataset AS op 
ON od.order_id = op.order_id
GROUP BY date
ORDER BY date ASC;

CREATE TABLE mart_top_product_categories AS SELECT
pc.product_category_name_english AS category_english,
pc.product_category_name AS category_portuguese,
COUNT(oi.order_id) AS total_orders
FROM olist_order_items_dataset AS oi
JOIN olist_products_dataset AS p
ON oi.product_id = p.product_id
JOIN product_category_name_translation AS pc
ON p.product_category_name = pc.product_category_name
GROUP BY category_english, category_portuguese
ORDER BY total_orders DESC;

CREATE TABLE mart_seller_performance AS SELECT
s.seller_id,
COUNT (oi.order_id) AS total_orders,
ROUND(SUM (op.payment_value)::NUMERIC, 2) AS total_revenue,
ROUND(AVG(r.review_score)::NUMERIC, 2) AS average_review_score
FROM olist_orders_dataset AS od
JOIN olist_order_payments_dataset AS op
ON od.order_id = op.order_id
JOIN olist_order_items_dataset AS oi
ON od.order_id = oi.order_id
JOIN olist_sellers_dataset AS s
ON oi.seller_id = s.seller_id
JOIN olist_order_reviews_dataset AS r
ON od.order_id = r.order_id
GROUP BY s.seller_id
ORDER BY total_revenue DESC;

