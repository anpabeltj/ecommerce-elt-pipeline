-- Pertanyaan: Apakah pengiriman yang terlambat membuat review pelanggan lebih buruk?
WITH delivered_orders AS (
    SELECT
        order_id,
        CASE
            WHEN order_delivered_customer_date::TIMESTAMP > order_estimated_delivery_date::TIMESTAMP
                THEN 'Late'
            ELSE 'On time'
        END AS delivery_status
    FROM olist_orders_dataset
    WHERE order_status = 'delivered'
      AND order_delivered_customer_date IS NOT NULL
),
reviews_per_order AS (
    SELECT
        order_id,
        AVG(review_score) AS review_score
    FROM olist_order_reviews_dataset
    GROUP BY order_id
)
SELECT
    d.delivery_status,
    COUNT(*) AS total_orders,
    ROUND(AVG(r.review_score)::NUMERIC, 2) AS avg_review_score,
    ROUND(AVG(CASE WHEN r.review_score <= 2 THEN 1.0 ELSE 0 END) * 100, 1) AS bad_review_pct
FROM delivered_orders AS d
JOIN reviews_per_order AS r
    ON r.order_id = d.order_id
GROUP BY d.delivery_status
ORDER BY d.delivery_status
