-- Total revenue bulanan harus sama dengan total payments (order valid saja)
WITH mart AS (
    SELECT
        SUM(total_revenue) AS revenue,
        COUNT(*) AS n_rows
    FROM mart_revenue_by_month
),
raw AS (
    SELECT SUM(op.payment_value) AS revenue
    FROM olist_order_payments_dataset AS op
    JOIN olist_orders_dataset AS od
        ON od.order_id = op.order_id
    WHERE od.order_status NOT IN ('canceled', 'unavailable')
)
SELECT ABS(mart.revenue - raw.revenue) <= mart.n_rows * 0.01 AS monthly_revenue_matches_raw
FROM mart, raw;
